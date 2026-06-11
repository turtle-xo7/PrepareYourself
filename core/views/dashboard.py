"""Student dashboard, progress history, practical lab.

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
from .pages import SUBJECT_COLOR_HEX, _SUBJECT_EMOJI
from .exams import EXAM_TOTAL_MAX

def _streak_from_dates(active_dates, today):
    """Walk backwards from today (or yesterday) and count consecutive active days."""
    from datetime import timedelta
    if today in active_dates:
        day = today
    elif (today - timedelta(days=1)) in active_dates:
        day = today - timedelta(days=1)
    else:
        return 0
    count = 0
    while day in active_dates:
        count += 1
        day = day - timedelta(days=1)
    return count


def _longest_streak(active_dates):
    from datetime import timedelta
    if not active_dates:
        return 0
    sorted_dates = sorted(active_dates)
    longest = run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    return max(longest, run)


@login_required
def dashboard(request):
    try:
        profile = request.user.profile
        # Staff land on their own dashboards — the student dashboard (and its
        # premium gate below) is for students only.
        if profile.is_superadmin:
            return redirect('superadmin_dashboard')
        if profile.role == 'ADMIN':
            return redirect('teacher_dashboard')
    except:
        pass

    try:
        if not request.user.profile.is_premium:
            messages.error(request, _L(request, 'This feature is for Premium users only.', 'এই feature শুধু Premium users এর জন্য।'))
            return redirect('pricing')
    except:
        return redirect('pricing')

    from ..models import UserProgress, TeacherFeedback
    from django.db.models import Count, Q
    from django.db.models.functions import TruncDate
    from datetime import timedelta
    from django.utils import timezone
    from collections import defaultdict, Counter

    user = request.user
    progress = UserProgress.objects.filter(user=user).select_related(
        'question', 'question__subject'
    )

    # ----- Headline stats -----
    total_answered = progress.count()
    total_correct = progress.filter(is_correct=True).count()
    total_wrong = total_answered - total_correct
    accuracy = round((total_correct / total_answered * 100), 1) if total_answered else 0

    # ----- This week vs last week (for trend arrows) -----
    today = timezone.now().date()
    week_start = today - timedelta(days=6)
    last_week_start = today - timedelta(days=13)
    last_week_end = today - timedelta(days=7)

    this_week_qs = progress.filter(answered_at__date__gte=week_start)
    last_week_qs = progress.filter(answered_at__date__range=(last_week_start, last_week_end))
    this_week_count = this_week_qs.count()
    last_week_count = last_week_qs.count()
    this_week_correct = this_week_qs.filter(is_correct=True).count()
    last_week_correct = last_week_qs.filter(is_correct=True).count()

    this_week_acc = round((this_week_correct / this_week_count * 100), 1) if this_week_count else 0
    last_week_acc = round((last_week_correct / last_week_count * 100), 1) if last_week_count else 0
    accuracy_delta = round(this_week_acc - last_week_acc, 1)

    if last_week_count == 0:
        volume_delta_pct = None
    else:
        volume_delta_pct = round(((this_week_count - last_week_count) / last_week_count) * 100, 1)

    # ----- Streak -----
    active_dates = set(
        progress.annotate(d=TruncDate('answered_at'))
                .values_list('d', flat=True).distinct()
    )
    current_streak = _streak_from_dates(active_dates, today)
    longest_streak = _longest_streak(active_dates)

    daily_goal = 10
    today_count = progress.filter(answered_at__date=today).count()
    goal_progress = min(round((today_count / daily_goal) * 100), 100) if daily_goal else 0

    lang = getattr(request, 'LANG', 'bn')
    if current_streak >= 30:
        streak_msg = "🔥 You're nearly unstoppable — keep the fire alive!" if lang == 'en' else "🔥 দারুণ! তুমি প্রায় অপ্রতিরোধ্য — এই আগুন ধরে রাখো!"
    elif current_streak >= 7:
        streak_msg = "A full week of consistency — keep going!" if lang == 'en' else "এক সপ্তাহ ধরে ধারাবাহিকভাবে চালিয়ে যাচ্ছ — চালিয়ে যাও!"
    elif current_streak >= 3:
        streak_msg = "Great streak building! Practice a few more questions today." if lang == 'en' else "ভালো ধারাবাহিকতা তৈরি হচ্ছে। আজ আরও কয়েকটা প্রশ্নের অনুশীলন করো।"
    elif current_streak >= 1:
        streak_msg = "You've started! Log in tomorrow to keep your streak alive." if lang == 'en' else "শুরু হয়েছে! আগামীকালও লগ ইন করে ধারাবাহিকতা ধরে রাখো।"
    else:
        streak_msg = "Start today — answer just one question to begin your streak!" if lang == 'en' else "আজই শুরু করো — একটাই প্রশ্নের উত্তর দাও, ধারাবাহিকতা শুরু হবে।"

    # ----- 30-day heatmap -----
    counts_30 = dict(
        progress.filter(answered_at__date__gte=today - timedelta(days=29))
                .annotate(d=TruncDate('answered_at'))
                .values_list('d')
                .annotate(c=Count('id'))
                .values_list('d', 'c')
    )
    heatmap = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        c = counts_30.get(day, 0)
        if c == 0:
            lvl = 0
        elif c < 5:
            lvl = 1
        elif c < 15:
            lvl = 2
        elif c < 30:
            lvl = 3
        else:
            lvl = 4
        heatmap.append({
            'date': day.strftime('%Y-%m-%d'),
            'label': day.strftime('%d %b'),
            'count': c,
            'level': lvl,
        })

    # ----- 7-day daily activity -----
    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        c = progress.filter(answered_at__date=day).count()
        cc = progress.filter(answered_at__date=day, is_correct=True).count()
        daily_data.append({'day': day.strftime('%a'), 'count': c, 'correct': cc})

    # ----- 30-day accuracy trend -----
    by_day = {}
    rows_30 = (
        progress.filter(answered_at__date__gte=today - timedelta(days=29))
                .annotate(d=TruncDate('answered_at'))
                .values('d')
                .annotate(total=Count('id'), correct=Count('id', filter=Q(is_correct=True)))
    )
    for r in rows_30:
        by_day[r['d']] = (r['total'], r['correct'])
    accuracy_trend = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        t, c = by_day.get(day, (0, 0))
        accuracy_trend.append({
            'day': day.strftime('%d %b'),
            'accuracy': round((c / t * 100), 1) if t else None,
        })

    # ----- Subjects (collapsible cards + pie) -----
    subj_agg = list(
        progress.values(
            'question__subject__id',
            'question__subject__name',
            'question__subject__icon',
            'question__subject__color',
        ).annotate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True)),
            written_correct=Count('id', filter=Q(is_correct=True, question__question_type='WRITTEN')),
            mcq_correct=Count('id', filter=Q(is_correct=True, question__question_type='MCQ')),
        ).order_by('-total')
    )
    diff_rows = list(
        progress.values('question__subject__id', 'question__difficulty')
                .annotate(c=Count('id'))
    )
    diff_map = defaultdict(lambda: {'Easy': 0, 'Medium': 0, 'Hard': 0})
    for r in diff_rows:
        diff_map[r['question__subject__id']][r['question__difficulty']] = r['c']

    week_rows = list(
        this_week_qs.annotate(d=TruncDate('answered_at'))
                    .values('question__subject__id', 'd')
                    .annotate(c=Count('id'))
    )
    week_map = defaultdict(dict)
    for r in week_rows:
        week_map[r['question__subject__id']][r['d']] = r['c']

    subjects_data = []
    for s in subj_agg:
        sid = s['question__subject__id']
        total = s['total']
        correct = s['correct']
        wrong = total - correct
        acc = round((correct / total * 100), 1) if total else 0
        weekly = []
        max_in_week = 0
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            c = week_map.get(sid, {}).get(day, 0)
            max_in_week = max(max_in_week, c)
            weekly.append({'day': day.strftime('%a'), 'count': c})
        for w in weekly:
            w['height'] = round((w['count'] / max_in_week) * 100) if max_in_week else 0
        color_name = s['question__subject__color'] or 'blue'
        marks = s['mcq_correct'] * 1 + s['written_correct'] * 10
        subjects_data.append({
            'id': sid,
            'name': s['question__subject__name'],
            'icon': s['question__subject__icon'] or _SUBJECT_EMOJI.get(s['question__subject__name'].lower(), '📚'),
            'color': color_name,
            'hex': SUBJECT_COLOR_HEX.get(color_name, '#3b82f6'),
            'total': total,
            'correct': correct,
            'wrong': wrong,
            'accuracy': acc,
            'marks': marks,
            'difficulty': diff_map[sid],
            'weekly': weekly,
        })

    # ----- Insights -----
    weekday_total = Counter()
    for ts in progress.values_list('answered_at', flat=True):
        weekday_total[ts.strftime('%A')] += 1
    best_day = max(weekday_total, key=weekday_total.get) if weekday_total else None

    weakest = None
    for s in subjects_data:
        if s['total'] >= 5:
            if weakest is None or s['accuracy'] < weakest['accuracy']:
                weakest = s

    # ----- Rank (among students) by total correct answers -----
    # Aggregates over every student's progress; cache per (user, score) so the
    # rank refreshes immediately when the viewer answers more questions but the
    # heavy scan runs at most once per 5 minutes otherwise.
    from django.core.cache import cache
    rank = cache.get_or_set(
        f'dash_rank:{user.id}:{total_correct}',
        lambda: User.objects.filter(profile__role='STUDENT').annotate(
            cc=Count('progress', filter=Q(progress__is_correct=True))
        ).filter(cc__gt=total_correct).count() + 1,
        300,
    )
    total_students = cache.get_or_set(
        'dash_total_students',
        lambda: User.objects.filter(profile__role='STUDENT').count() or 1,
        300,
    )

    # ----- Teacher feedback -----
    feedbacks = list(
        TeacherFeedback.objects.filter(student=user)
                                .select_related('teacher', 'progress__question__subject')
                                .order_by('-created_at')[:3]
    )
    unread_count = TeacherFeedback.objects.filter(student=user, is_read=False).count()

    # ----- Exam results grouped by subject -----
    from ..models import ExamAttempt

    graded_attempts = list(
        ExamAttempt.objects.filter(student=user, status='GRADED')
                           .select_related('exam_paper', 'exam_paper__subject')
                           .order_by('-graded_at')
    )

    exam_results_by_subject = []
    if graded_attempts:
        subject_groups = {}
        for a in graded_attempts:
            max_marks = EXAM_TOTAL_MAX
            score = a.total_score or 0
            pct = round(score / max_marks * 100, 1) if max_marks else 0

            subj = a.exam_paper.subject
            sid = subj.id if subj else 0
            if sid not in subject_groups:
                color_name = (subj.color if subj else None) or 'blue'
                subject_groups[sid] = {
                    'id': sid,
                    'name': subj.name if subj else 'Other',
                    'icon': (subj.icon if subj and subj.icon
                             else _SUBJECT_EMOJI.get((subj.name if subj else '').lower(), '📚')),
                    'color': color_name,
                    'hex': SUBJECT_COLOR_HEX.get(color_name, '#3b82f6'),
                    'attempts': [],
                    'pct_sum': 0,
                    'best_pct': 0,
                    'count': 0,
                }
            subject_groups[sid]['attempts'].append({
                'id': a.id,
                'title': a.exam_paper.title,
                'score': score,
                'max': max_marks,
                'pct': pct,
                'grade': a.grade,
                'date': a.graded_at,
            })
            subject_groups[sid]['pct_sum'] += pct
            subject_groups[sid]['count'] += 1
            if pct > subject_groups[sid]['best_pct']:
                subject_groups[sid]['best_pct'] = pct

        for s in subject_groups.values():
            s['avg_pct'] = round(s['pct_sum'] / s['count'], 1) if s['count'] else 0
            s['attempts'].sort(key=lambda x: x['date'])
            for att in s['attempts']:
                att['bar_height'] = max(4, min(100, int(att['pct'])))
            exam_results_by_subject.append(s)
        exam_results_by_subject.sort(key=lambda s: -s['count'])

    return render(request, 'core/dashboard.html', {
        # headline
        'total_answered': total_answered,
        'total_correct': total_correct,
        'total_wrong': total_wrong,
        'accuracy': accuracy,
        # trends
        'this_week_count': this_week_count,
        'last_week_count': last_week_count,
        'volume_delta_pct': volume_delta_pct,
        'this_week_acc': this_week_acc,
        'accuracy_delta': accuracy_delta,
        # streak
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'today_count': today_count,
        'daily_goal': daily_goal,
        'goal_progress': goal_progress,
        'streak_msg': streak_msg,
        'heatmap': heatmap,
        # charts
        'daily_data': daily_data,
        'accuracy_trend': accuracy_trend,
        # subjects
        'subjects_data': subjects_data,
        # insights
        'best_day': best_day,
        'weakest': weakest,
        # rank
        'rank': rank,
        'total_students': total_students,
        # feedback
        'feedbacks': feedbacks,
        'unread_count': unread_count,
        # exam results
        'exam_results_by_subject': exam_results_by_subject,
    })


@login_required
def progress_history(request):
    try:
        profile = request.user.profile
        # Staff have no student progress — route them to their dashboards
        # instead of tripping the premium gate below.
        if profile.is_superadmin:
            return redirect('superadmin_dashboard')
        if profile.role == 'ADMIN':
            return redirect('teacher_dashboard')
    except:
        pass

    try:
        if not request.user.profile.is_premium:
            messages.error(request, _L(request, 'This feature is for Premium users only.', 'এই feature শুধু Premium users এর জন্য।'))
            return redirect('pricing')
    except:
        return redirect('pricing')

    from ..models import UserProgress
    from django.db.models import Count, Q
    from django.db.models.functions import TruncDate
    from datetime import timedelta, datetime as dt
    from django.utils import timezone
    from django.core.paginator import Paginator

    user = request.user
    base = UserProgress.objects.filter(user=user).select_related(
        'question', 'question__subject', 'question__board'
    )

    # Filters
    subject_filter = request.GET.get('subject') or ''
    result_filter = request.GET.get('result') or ''
    difficulty_filter = request.GET.get('difficulty') or ''
    date_from = request.GET.get('from') or ''
    date_to = request.GET.get('to') or ''

    qs = base
    if subject_filter:
        qs = qs.filter(question__subject_id=subject_filter)
    if result_filter == 'correct':
        qs = qs.filter(is_correct=True)
    elif result_filter == 'wrong':
        qs = qs.filter(is_correct=False)
    if difficulty_filter in ('Easy', 'Medium', 'Hard'):
        qs = qs.filter(question__difficulty=difficulty_filter)
    if date_from:
        try:
            qs = qs.filter(answered_at__date__gte=dt.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(answered_at__date__lte=dt.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    qs = qs.order_by('-answered_at')

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    filtered_count = paginator.count

    # Summary stats — over user's full history (not the filter)
    today = timezone.now().date()
    week_start = today - timedelta(days=6)
    week_qs = base.filter(answered_at__date__gte=week_start)
    week_total = week_qs.count()
    week_correct = week_qs.filter(is_correct=True).count()
    week_accuracy = round((week_correct / week_total * 100), 1) if week_total else 0

    active_dates = set(
        base.annotate(d=TruncDate('answered_at')).values_list('d', flat=True).distinct()
    )
    current_streak = _streak_from_dates(active_dates, today)

    total_all = base.count()
    correct_all = base.filter(is_correct=True).count()
    accuracy_all = round((correct_all / total_all * 100), 1) if total_all else 0

    subjects = Subject.objects.filter(is_active=True).order_by('name')

    params = request.GET.copy()
    params.pop('page', None)
    qs_string = params.urlencode()

    has_filters = any([subject_filter, result_filter, difficulty_filter, date_from, date_to])

    return render(request, 'core/progress_history.html', {
        'page_obj': page_obj,
        'filtered_count': filtered_count,
        'subjects': subjects,
        'subject_filter': subject_filter,
        'result_filter': result_filter,
        'difficulty_filter': difficulty_filter,
        'date_from': date_from,
        'date_to': date_to,
        'has_filters': has_filters,
        'qs_string': qs_string,
        # summary
        'current_streak': current_streak,
        'week_total': week_total,
        'week_correct': week_correct,
        'week_accuracy': week_accuracy,
        'total_all': total_all,
        'accuracy_all': accuracy_all,
    })


@premium_required
def practical_lab(request):
    from ..models import PracticalVideo
    videos = PracticalVideo.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()

    subject_filter = request.GET.get('subject')
    class_filter = request.GET.get('class_obj')

    if subject_filter:
        videos = videos.filter(subject__slug=subject_filter)
    if class_filter:
        videos = videos.filter(class_obj__id=class_filter)

    return render(request, 'core/practical_lab.html', {
        'videos': videos,
        'subjects': subjects,
        'classes': classes,
    })


