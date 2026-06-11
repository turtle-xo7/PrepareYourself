"""Teacher dashboard, student detail, feedback.

Split from the original monolithic core/views.py.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction
from datetime import datetime
import json
import uuid

from ..models import Board, Subject, Class, Question, UserProfile, UserProgress
from ..services import ai as ai_svc
from .base import (
    logger, _L, _upload_error, ALLOWED_IMAGE_EXTS, ALLOWED_DOC_EXTS,
    CURRENT_YEAR, YEARS,
    admin_required, superadmin_required, premium_required,
    _is_exam_staff, _notify_all_students,
)

def _teacher_student_stats():
    """Per-student practice stats shared by the teacher Overview and the
    Students page. Returns (student_data, total_answered_all, active_today,
    avg_accuracy)."""
    from ..models import UserProgress
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Count, Q

    today = timezone.localdate()
    week_ago = today - timedelta(days=7)

    students = UserProfile.objects.filter(
        role='STUDENT', is_superadmin=False
    ).select_related('user').order_by('-user__date_joined')

    all_progress = UserProgress.objects.filter(
        user__profile__role='STUDENT',
        user__profile__is_superadmin=False
    )

    stat_map = {s['user_id']: s for s in all_progress.values('user_id').annotate(
        total=Count('id'), correct=Count('id', filter=Q(is_correct=True))
    )}
    today_map = {s['user_id']: s['count'] for s in all_progress.filter(
        answered_at__date=today).values('user_id').annotate(count=Count('id'))}
    week_map = {s['user_id']: s for s in all_progress.filter(
        answered_at__date__gte=week_ago).values('user_id').annotate(
        total=Count('id'), correct=Count('id', filter=Q(is_correct=True)))}

    student_data = []
    total_answered_all = 0
    active_today = 0
    accuracy_list = []

    for s in students:
        uid = s.user.id
        st = stat_map.get(uid, {'total': 0, 'correct': 0})
        total, correct = st['total'], st['correct']
        today_count = today_map.get(uid, 0)
        wk = week_map.get(uid, {'total': 0, 'correct': 0})
        week_total, week_correct = wk['total'], wk['correct']
        accuracy = round(correct / total * 100, 1) if total > 0 else 0
        week_accuracy = round(week_correct / week_total * 100, 1) if week_total > 0 else 0
        total_answered_all += total
        if today_count > 0:
            active_today += 1
        if total > 0:
            accuracy_list.append(accuracy)
        student_data.append({
            'profile': s,
            'total': total,
            'correct': correct,
            'wrong': total - correct,
            'accuracy': accuracy,
            'today_count': today_count,
            'week_total': week_total,
            'week_accuracy': week_accuracy,
        })

    avg_accuracy = round(sum(accuracy_list) / len(accuracy_list), 1) if accuracy_list else 0
    return student_data, total_answered_all, active_today, avg_accuracy


@admin_required
def teacher_dashboard(request):
    """Overview only: KPIs, attention items, charts, insights, feedback.
    The full student table lives on /teacher/students/."""
    from ..models import UserProgress, TeacherFeedback, Contest, ExamPaper, ExamAttempt, NoteRequest
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Count, Q

    today = timezone.localdate()  # local calendar day - now().date() is the UTC date
    week_ago = today - timedelta(days=7)

    all_progress = UserProgress.objects.filter(
        user__profile__role='STUDENT',
        user__profile__is_superadmin=False
    )

    student_data, total_answered_all, active_today, avg_accuracy = _teacher_student_stats()

    at_risk = sorted(
        [s for s in student_data if s['week_total'] >= 3 and s['week_accuracy'] < 50],
        key=lambda x: x['week_accuracy']
    )[:5]

    top_performers = sorted(
        [s for s in student_data if s['total'] >= 5],
        key=lambda x: (-x['accuracy'], -x['total'])
    )[:5]

    subject_perf = all_progress.values('question__subject__name').annotate(
        total=Count('id'), correct=Count('id', filter=Q(is_correct=True))
    ).filter(total__gt=0).order_by('-total')
    subject_performance = [
        {'name': sp['question__subject__name'], 'total': sp['total'],
         'correct': sp['correct'],
         'accuracy': round(sp['correct'] / sp['total'] * 100, 1) if sp['total'] > 0 else 0}
        for sp in subject_perf
    ]

    recent_feedbacks = TeacherFeedback.objects.filter(
        teacher=request.user
    ).select_related('student', 'progress__question').order_by('-created_at')[:8]
    feedbacks_this_week = TeacherFeedback.objects.filter(
        teacher=request.user, created_at__date__gte=week_ago).count()
    questions_set = Contest.objects.filter(created_by=request.user).count()

    # One aggregated scan covers both the 7-day chart and the 30-day heatmap
    # (previously 37 separate per-day queries).
    from django.db.models.functions import TruncDate
    month_ago = today - timedelta(days=29)
    day_counts = {
        row['d']: row for row in all_progress.filter(
            answered_at__date__gte=month_ago
        ).annotate(d=TruncDate('answered_at')).values('d').annotate(
            count=Count('id'), correct=Count('id', filter=Q(is_correct=True))
        )
    }

    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        row = day_counts.get(day, {})
        daily_data.append({
            'day': day.strftime('%a'),
            'count': row.get('count', 0),
            'correct': row.get('correct', 0),
        })

    heatmap_days = []
    max_count = 1
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        cnt = day_counts.get(day, {}).get('count', 0)
        heatmap_days.append({'date': day.strftime('%d %b'), 'count': cnt})
        if cnt > max_count:
            max_count = cnt

    insights = []
    inactive_count = sum(1 for s in student_data if s['week_total'] == 0)
    if inactive_count:
        insights.append(_L(request, f"⚠️ {inactive_count} students did not attempt a single question last week.", f"⚠️ {inactive_count} জন student গত সপ্তাহে একটিও প্রশ্ন করেননি।"))
    if subject_performance:
        weakest = min(subject_performance, key=lambda x: x['accuracy'])
        if weakest['accuracy'] < 60:
            insights.append(_L(request, f"📚 Class average accuracy in {weakest['name']} is only {weakest['accuracy']}% — revision needed.", f"📚 {weakest['name']}-এ class-এর গড় accuracy মাত্র {weakest['accuracy']}% — revision দরকার।"))
    if at_risk:
        insights.append(_L(request, f"🔴 {len(at_risk)} students are below 50% this week — talk to them.", f"🔴 {len(at_risk)} জন student এই সপ্তাহে ৫০%-এর নিচে — তাদের সাথে কথা বলুন।"))
    if len(student_data) > 0 and active_today < len(student_data) * 0.3:
        insights.append(_L(request, f"📉 Only {active_today} active today — engagement needs a boost.", f"📉 আজ মাত্র {active_today} জন active — engagement বাড়ানো দরকার।"))
    if not insights:
        insights.append(_L(request, "✅ All good. The class is performing well!", "✅ সব ঠিকঠাক আছে। Class ভালো perform করছে!"))

    # ---- Grading workload ----
    pending_cq_count = ExamAttempt.objects.filter(status='CQ_PENDING').count()

    urgent_cutoff = timezone.now() - timedelta(hours=24)
    urgent_cq_count = ExamAttempt.objects.filter(
        status='CQ_PENDING', cq_submitted_at__lt=urgent_cutoff
    ).count()

    recent_exam_pending = ExamAttempt.objects.filter(
        status='CQ_PENDING'
    ).select_related('student', 'exam_paper').order_by('cq_submitted_at')[:5]

    note_request_count = NoteRequest.objects.filter(status='PENDING').count()

    if pending_cq_count:
        insights.append(_L(request, f"📝 {pending_cq_count} CQ submissions are still ungraded.", f"📝 {pending_cq_count}টি CQ submission এখনো grade করা হয়নি।"))

    return render(request, 'teacher/dashboard.html', {
        'student_count': len(student_data),
        'total_answered_all': total_answered_all,
        'active_today': active_today,
        'avg_accuracy': avg_accuracy,
        'daily_data': daily_data,
        'at_risk': at_risk,
        'at_risk_count': len(at_risk),
        'top_performers': top_performers,
        'subject_performance': subject_performance,
        'recent_feedbacks': recent_feedbacks,
        'feedbacks_this_week': feedbacks_this_week,
        'questions_set': questions_set,
        'heatmap_days': heatmap_days,
        'max_heatmap': max_count,
        'insights': insights,
        'pending_cq_count': pending_cq_count,
        'urgent_cq_count': urgent_cq_count,
        'recent_exam_pending': recent_exam_pending,
        'note_request_count': note_request_count,
        'tt_active': 'overview',
    })


@admin_required
def teacher_students(request):
    """Full student roster: server-side search, plan/status filters,
    pagination, and the latest exam attempt per visible row."""
    from ..models import ExamAttempt
    from django.core.paginator import Paginator

    student_data, _total, active_today, _avg = _teacher_student_stats()

    search = (request.GET.get('q') or '').strip().lower()
    sel_plan = request.GET.get('plan', '')
    sel_status = request.GET.get('status', '')

    rows = student_data
    if search:
        rows = [s for s in rows
                if search in s['profile'].user.username.lower()
                or search in (s['profile'].user.email or '').lower()]
    if sel_plan in ('FREE', 'BASIC', 'PREMIUM'):
        rows = [s for s in rows if s['profile'].plan == sel_plan]
    if sel_status == 'at_risk':
        rows = [s for s in rows if s['week_total'] >= 3 and s['week_accuracy'] < 50]
    elif sel_status == 'inactive':
        rows = [s for s in rows if s['week_total'] == 0]
    elif sel_status == 'active_today':
        rows = [s for s in rows if s['today_count'] > 0]

    total_matched = len(rows)
    params = request.GET.copy()
    params.pop('page', None)
    page_obj = Paginator(rows, 20).get_page(request.GET.get('page'))

    # Latest exam attempt — only for the rows on this page
    page_ids = [s['profile'].user.id for s in page_obj.object_list]
    latest_attempt_map = {}
    for attempt in ExamAttempt.objects.filter(
        student_id__in=page_ids
    ).select_related('exam_paper').order_by('-started_at'):
        if attempt.student_id not in latest_attempt_map:
            latest_attempt_map[attempt.student_id] = attempt
    for s in page_obj.object_list:
        s['exam_attempt'] = latest_attempt_map.get(s['profile'].user.id)

    return render(request, 'teacher/students.html', {
        'page_obj': page_obj,
        'base_qs': params.urlencode(),
        'total_matched': total_matched,
        'student_count': len(student_data),
        'active_today': active_today,
        'search': request.GET.get('q', ''),
        'sel_plan': sel_plan,
        'sel_status': sel_status,
        'tt_active': 'students',
    })


@admin_required
def student_detail(request, pk):
    from ..models import UserProgress, TeacherFeedback
    from django.db.models import Count, Q
    from datetime import timedelta
    from django.utils import timezone

    profile = get_object_or_404(UserProfile, pk=pk)
    progress = UserProgress.objects.filter(user=profile.user).select_related('question', 'question__subject')

    total_answered = progress.count()
    total_correct = progress.filter(is_correct=True).count()
    total_wrong = total_answered - total_correct
    accuracy = round(total_correct / total_answered * 100, 1) if total_answered > 0 else 0

    subject_progress = list(progress.values('question__subject__name').annotate(
        total=Count('id'), correct=Count('id', filter=Q(is_correct=True))
    ).order_by('-total'))
    for sp in subject_progress:
        sp['accuracy'] = round(sp['correct'] / sp['total'] * 100, 1) if sp['total'] > 0 else 0

    diff_rows = {
        r['question__difficulty']: r
        for r in progress.values('question__difficulty').annotate(
            total=Count('id'), correct=Count('id', filter=Q(is_correct=True))
        )
    }
    difficulty_data = {}
    for diff in ['Easy', 'Medium', 'Hard']:
        r = diff_rows.get(diff, {'total': 0, 'correct': 0})
        difficulty_data[diff] = {
            'total': r['total'],
            'correct': r['correct'],
            'accuracy': round(r['correct'] / r['total'] * 100, 1) if r['total'] > 0 else 0,
        }

    today = timezone.localdate()  # local calendar day - now().date() is the UTC date
    week_ago = today - timedelta(days=7)

    # One aggregated scan for the 14-day chart and 30-day heatmap
    # (previously 58 per-day queries), plus distinct dates for the streak.
    from django.db.models.functions import TruncDate
    month_ago = today - timedelta(days=29)
    day_counts = {
        row['d']: row for row in progress.filter(
            answered_at__date__gte=month_ago
        ).annotate(d=TruncDate('answered_at')).values('d').annotate(
            count=Count('id'), correct=Count('id', filter=Q(is_correct=True))
        )
    }

    daily_data = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        row = day_counts.get(day, {})
        daily_data.append({
            'day': day.strftime('%d %b'),
            'count': row.get('count', 0),
            'correct': row.get('correct', 0),
        })

    heatmap_days = []
    max_count = 1
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        cnt = day_counts.get(day, {}).get('count', 0)
        heatmap_days.append({'date': day.strftime('%d %b'), 'count': cnt})
        if cnt > max_count:
            max_count = cnt

    answered_dates = set(
        progress.annotate(d=TruncDate('answered_at')).values_list('d', flat=True)
    )
    streak = 0
    check_day = today
    while check_day in answered_dates:
        streak += 1
        check_day -= timedelta(days=1)

    all_stats = list(UserProgress.objects.filter(
        user__profile__role='STUDENT', user__profile__is_superadmin=False
    ).values('user_id').annotate(
        total=Count('id'), correct=Count('id', filter=Q(is_correct=True))
    ))
    ranked = sorted(
        [(s['user_id'], round(s['correct'] / s['total'] * 100, 1) if s['total'] > 0 else 0)
         for s in all_stats], key=lambda x: -x[1]
    )
    class_rank = next((i + 1 for i, (uid, _) in enumerate(ranked) if uid == profile.user.id), None)
    total_students = UserProfile.objects.filter(role='STUDENT', is_superadmin=False).count()

    week_progress = progress.filter(answered_at__date__gte=week_ago)
    week_total = week_progress.count()
    week_correct = week_progress.filter(is_correct=True).count()
    week_accuracy = round(week_correct / week_total * 100, 1) if week_total > 0 else 0
    is_at_risk = week_total >= 3 and week_accuracy < 50

    insights = []
    if subject_progress:
        weakest = min(subject_progress, key=lambda x: x['accuracy'])
        if weakest['total'] >= 3 and weakest['accuracy'] < 60:
            insights.append(_L(request, f"⚠️ Only {weakest['accuracy']}% accuracy in {weakest['question__subject__name']} — this subject needs special attention.", f"⚠️ {weakest['question__subject__name']}-এ মাত্র {weakest['accuracy']}% accuracy — এই বিষয়ে বিশেষ মনোযোগ দরকার।"))
    easy_acc = difficulty_data['Easy']['accuracy']
    hard_acc = difficulty_data['Hard']['accuracy']
    if difficulty_data['Hard']['total'] >= 3 and difficulty_data['Easy']['total'] >= 3:
        if easy_acc >= 70 and hard_acc < 50:
            insights.append(_L(request, f"Strong on easy ({easy_acc}%) but weak on hard ({hard_acc}%) — move from Medium toward Hard.", f"সহজ প্রশ্নে ভালো ({easy_acc}%) কিন্তু কঠিনে দুর্বল ({hard_acc}%) — Medium থেকে Hard-এ নিয়ে যান।"))
    recent_7 = sum(d['count'] for d in daily_data[-7:])
    prev_7 = sum(d['count'] for d in daily_data[:7])
    if prev_7 > 0 and recent_7 < prev_7 * 0.5:
        insights.append(_L(request, "📉 Engagement dropped notably this week — send motivational feedback.", "📉 এই সপ্তাহে engagement উল্লেখযোগ্যভাবে কমেছে — motivational feedback পাঠান।"))
    elif recent_7 > prev_7 * 1.5 and recent_7 > 0:
        insights.append(_L(request, "📈 Very active this week! Do not forget to encourage them.", "📈 এই সপ্তাহে দারুণ active! উৎসাহ দিতে ভুলবেন না।"))
    if streak == 0:
        insights.append(_L(request, "❌ No questions attempted today. Consider sending a reminder.", "❌ আজ কোনো প্রশ্ন করেনি। Reminder পাঠানো যেতে পারে।"))
    elif streak >= 7:
        insights.append(_L(request, f"🔥 Great {streak}-day streak! Acknowledge it.", f"🔥 {streak} দিনের দারুণ streak! এটা acknowledge করুন।"))
    if not insights:
        insights.append(_L(request, "📊 All good. Keep giving regular feedback.", "📊 সব ঠিকঠাক আছে। Regular feedback দিতে থাকুন।"))

    teacher_feedbacks = TeacherFeedback.objects.filter(
        teacher=request.user, student=profile.user
    ).select_related('progress__question').order_by('-created_at')[:20]

    history = progress.prefetch_related('feedbacks__teacher').order_by('-answered_at')[:30]

    return render(request, 'teacher/student_detail.html', {
        'profile': profile,
        'total_answered': total_answered,
        'total_correct': total_correct,
        'total_wrong': total_wrong,
        'accuracy': accuracy,
        'subject_progress': subject_progress,
        'difficulty_data': difficulty_data,
        'daily_data': daily_data,
        'heatmap_days': heatmap_days,
        'max_heatmap': max_count,
        'streak': streak,
        'class_rank': class_rank,
        'total_students': total_students,
        'is_at_risk': is_at_risk,
        'week_accuracy': week_accuracy,
        'week_total': week_total,
        'insights': insights,
        'teacher_feedbacks': teacher_feedbacks,
        'history': history,
    })


@admin_required
def give_feedback(request, progress_pk):
    from ..models import UserProgress, TeacherFeedback
    progress = get_object_or_404(UserProgress, pk=progress_pk)
    if request.method == 'POST':
        comment = request.POST.get('comment', '').strip()
        if comment:
            TeacherFeedback.objects.create(
                teacher=request.user,
                student=progress.user,
                progress=progress,
                comment=comment
            )
            messages.success(request, _L(request, 'Feedback sent!', 'Feedback পাঠানো হয়েছে!'))
    return redirect('student_detail', pk=progress.user.profile.pk)


@admin_required
def send_general_feedback(request, student_pk):
    from ..models import UserProgress, TeacherFeedback
    profile = get_object_or_404(UserProfile, pk=student_pk)
    if request.method == 'POST':
        comment = request.POST.get('comment', '').strip()
        if comment:
            latest = UserProgress.objects.filter(user=profile.user).order_by('-answered_at').first()
            if latest:
                TeacherFeedback.objects.create(
                    teacher=request.user,
                    student=profile.user,
                    progress=latest,
                    comment=comment
                )
                messages.success(request, _L(request, 'Feedback sent!', 'Feedback পাঠানো হয়েছে!'))
            else:
                messages.warning(request, _L(request, 'The student has not attempted any questions yet.', 'Student এখনো কোনো প্রশ্ন করেননি।'))
    return redirect('student_detail', pk=student_pk)


