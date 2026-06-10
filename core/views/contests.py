"""Contest CRUD, joining, submission, results, leaderboard.

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

@login_required
def contest_list(request):
    from ..models import Contest, ContestSubmission, ContestRegistration, UserRating
    from django.utils import timezone
    from django.db.models import Count
    from django.core.paginator import Paginator

    now = timezone.now()
    tab = request.GET.get('tab', 'upcoming')
    q = (request.GET.get('q') or '').strip()
    subject_id = request.GET.get('subject')
    difficulty = request.GET.get('difficulty')
    ctype = request.GET.get('type')

    base = Contest.objects.filter(is_active=True).select_related(
        'subject', 'class_obj', 'created_by'
    )
    if tab == 'live':
        base = base.filter(start_time__lte=now, end_time__gte=now)
    elif tab == 'past':
        base = base.filter(end_time__lt=now).order_by('-end_time')
    elif tab == 'mine':
        reg_ids = ContestRegistration.objects.filter(
            user=request.user
        ).values_list('contest_id', flat=True)
        sub_ids = ContestSubmission.objects.filter(
            student=request.user
        ).values_list('contest_id', flat=True)
        base = base.filter(id__in=list(reg_ids) + list(sub_ids))
    elif tab == 'virtual':
        base = base.filter(end_time__lt=now, allows_virtual=True).order_by('-end_time')
    else:
        tab = 'upcoming'
        base = base.filter(start_time__gte=now).order_by('start_time')

    if tab not in ('past', 'virtual'):
        base = base.order_by('start_time')

    if q:
        base = base.filter(title__icontains=q)
    if subject_id:
        base = base.filter(subject_id=subject_id)
    if difficulty:
        base = base.filter(difficulty=difficulty)
    if ctype:
        base = base.filter(contest_type=ctype)

    paginator = Paginator(base, 20)
    page = paginator.get_page(request.GET.get('page'))

    contest_ids = [c.id for c in page.object_list]
    my_registered = set(ContestRegistration.objects.filter(
        user=request.user, contest_id__in=contest_ids,
    ).values_list('contest_id', flat=True))
    my_submitted = set(ContestSubmission.objects.filter(
        student=request.user, is_submitted=True, contest_id__in=contest_ids,
    ).values_list('contest_id', flat=True))

    participant_counts = {
        c['contest_id']: c['cnt']
        for c in ContestRegistration.objects.filter(
            contest_id__in=contest_ids,
        ).values('contest_id').annotate(cnt=Count('id'))
    }

    featured = Contest.objects.filter(
        is_active=True, is_featured=True, end_time__gte=now,
    ).select_related('subject', 'class_obj').first()

    total_contests = Contest.objects.filter(is_active=True).count()
    live_now = Contest.objects.filter(
        is_active=True, start_time__lte=now, end_time__gte=now,
    ).count()
    total_participants = ContestRegistration.objects.values('user').distinct().count()
    my_rating_obj, _ = UserRating.objects.get_or_create(user=request.user)

    return render(request, 'core/contest_list.html', {
        'contests': page.object_list,
        'page': page,
        'paginator': paginator,
        'tab': tab,
        'q': q,
        'subject_id': int(subject_id) if subject_id and subject_id.isdigit() else None,
        'difficulty': difficulty or '',
        'ctype': ctype or '',
        'subjects': Subject.objects.filter(is_active=True),
        'CONTEST_TYPE': Contest.CONTEST_TYPE,
        'DIFFICULTY': Contest.DIFFICULTY,
        'my_registered': my_registered,
        'my_submissions': my_submitted,
        'participant_counts': participant_counts,
        'featured': featured,
        'stats': {
            'total': total_contests,
            'live': live_now,
            'participants': total_participants,
        },
        'my_rating': my_rating_obj,
        'now': now,
    })


@admin_required
def contest_create(request):
    from ..models import Contest, ContestQuestion
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    if request.method == 'POST':
        from django.utils import timezone
        import datetime
        contest = Contest.objects.create(
            title=request.POST.get('title'),
            created_by=request.user,
            subject=get_object_or_404(Subject, pk=request.POST.get('subject')),
            class_obj=get_object_or_404(Class, pk=request.POST.get('class_obj')),
            duration_minutes=int(request.POST.get('duration_minutes', 30)),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            is_active=True
        )
        question_texts = request.POST.getlist('question_text')
        question_types = request.POST.getlist('question_type')
        marks_list = request.POST.getlist('marks')
        option1s = request.POST.getlist('option1')
        option2s = request.POST.getlist('option2')
        option3s = request.POST.getlist('option3')
        option4s = request.POST.getlist('option4')
        correct_options = request.POST.getlist('correct_option')

        for i, qtext in enumerate(question_texts):
            if qtext.strip():
                ContestQuestion.objects.create(
                    contest=contest,
                    question_text=qtext,
                    question_type=question_types[i] if i < len(question_types) else 'MCQ',
                    marks=int(marks_list[i]) if i < len(marks_list) and marks_list[i] else 1,
                    option1=option1s[i] if i < len(option1s) else '',
                    option2=option2s[i] if i < len(option2s) else '',
                    option3=option3s[i] if i < len(option3s) else '',
                    option4=option4s[i] if i < len(option4s) else '',
                    correct_option=int(correct_options[i]) if i < len(correct_options) and correct_options[i] else None,
                )
        _notify_all_students(
            'contest',
            f'New Contest: {contest.title}',
            f'{request.user.username} created a new contest — "{contest.title}" ({contest.subject.name}, {contest.class_obj.name})',
            link=f'/contests/{contest.pk}/',
            title_bn=f'নতুন Contest: {contest.title}',
            message_bn=f'{request.user.username} একটি নতুন contest তৈরি করেছেন — "{contest.title}" ({contest.subject.name}, {contest.class_obj.name})',
        )
        messages.success(request, 'Contest created!')
        return redirect('contest_detail', pk=contest.pk)
    return render(request, 'core/contest_create.html', {
        'subjects': subjects,
        'classes': classes,
    })


@login_required
def contest_detail(request, pk):
    from ..models import (
        Contest, ContestSubmission, ContestRegistration, UserRating,
    )
    from django.utils import timezone
    from django.db.models import F
    try:
        contest = Contest.objects.select_related(
            'subject', 'class_obj', 'created_by'
        ).get(pk=pk)
    except Contest.DoesNotExist:
        messages.warning(request, 'This contest is no longer available (deleted).')
        return redirect('contest_list')

    Contest.objects.filter(pk=pk).update(view_count=F('view_count') + 1)

    now = timezone.now()
    has_submitted = ContestSubmission.objects.filter(
        contest=contest, student=request.user, is_submitted=True,
    ).exists()
    my_registration = ContestRegistration.objects.filter(
        contest=contest, user=request.user,
    ).first()
    is_active = contest.start_time <= now <= contest.end_time

    participant_count = ContestRegistration.objects.filter(contest=contest).count()
    recent_participants = ContestRegistration.objects.filter(
        contest=contest,
    ).select_related('user').order_by('-registered_at')[:8]

    question_count = contest.questions.count()
    my_rating, _ = UserRating.objects.get_or_create(user=request.user)

    leaderboard_preview = None
    if contest.is_past or (not contest.hide_leaderboard_until_end and is_active):
        leaderboard_preview = ContestSubmission.objects.filter(
            contest=contest, is_submitted=True,
            student__profile__role='STUDENT',
        ).select_related('student').order_by(
            '-total_marks', 'duration_taken',
        )[:10]

    return render(request, 'core/contest_detail.html', {
        'contest': contest,
        'has_submitted': has_submitted,
        'is_active': is_active,
        'now': now,
        'my_registration': my_registration,
        'participant_count': participant_count,
        'recent_participants': recent_participants,
        'question_count': question_count,
        'my_rating': my_rating,
        'leaderboard_preview': leaderboard_preview,
    })


@login_required
def contest_join(request, pk):
    from ..models import Contest, ContestSubmission
    from django.utils import timezone
    try:
        if request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin:
            messages.info(request, _L(request, 'Teachers/Admins cannot join contests — view only.', 'Teacher/Admin contest-এ অংশ নিতে পারবেন না — শুধু দেখতে পারবেন।'))
            return redirect('contest_detail', pk=pk)
    except Exception:
        pass
    try:
        contest = Contest.objects.get(pk=pk)
    except Contest.DoesNotExist:
        messages.warning(request, _L(request, 'This contest is no longer available.', 'এই contest আর available নেই।'))
        return redirect('contest_list')
    now = timezone.now()

    if now < contest.start_time:
        messages.error(request, _L(request, 'The contest has not started yet.', 'Contest এখনো শুরু হয়নি।'))
        return redirect('contest_detail', pk=pk)
    if now > contest.end_time:
        messages.error(request, _L(request, 'The contest has ended.', 'Contest শেষ হয়ে গেছে।'))
        return redirect('contest_detail', pk=pk)

    submission, created = ContestSubmission.objects.get_or_create(
        contest=contest,
        student=request.user,
    )
    if submission.is_submitted:
        messages.error(request, _L(request, 'You have already submitted.', 'তুমি আগেই submit করেছ।'))
        return redirect('contest_leaderboard', pk=pk)

    questions = contest.questions.all()
    return render(request, 'core/contest_exam.html', {
        'contest': contest,
        'questions': questions,
        'submission': submission,
    })


@login_required
def contest_submit(request, pk):
    from ..models import Contest, ContestSubmission, ContestAnswer
    from django.utils import timezone
    try:
        if request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin:
            messages.error(request, _L(request, 'Teachers/Admins cannot submit contest answers.', 'Teacher/Admin contest answer submit করতে পারবেন না।'))
            return redirect('contest_detail', pk=pk)
    except Exception:
        pass
    if request.method != 'POST':
        return redirect('contest_detail', pk=pk)

    contest = get_object_or_404(Contest, pk=pk)
    submission = get_object_or_404(ContestSubmission, contest=contest, student=request.user)

    if submission.is_submitted:
        return redirect('contest_leaderboard', pk=pk)

    # Answer rows and the final submission state must land together — a partial
    # set of ContestAnswers with is_submitted=False would block resubmission
    # while scoring only half the paper.
    with transaction.atomic():
        total_marks = 0
        questions = contest.questions.all()

        for q in questions:
            if q.question_type == 'MCQ':
                answer_val = request.POST.get(f'q_{q.pk}')
                mcq_answer = int(answer_val) if answer_val else None
                is_correct = mcq_answer == q.correct_option if mcq_answer else False
                marks_obtained = q.marks if is_correct else 0
                total_marks += marks_obtained
                ContestAnswer.objects.create(
                    submission=submission,
                    question=q,
                    mcq_answer=mcq_answer,
                    is_correct=is_correct,
                    marks_obtained=marks_obtained
                )
            else:
                creative_answer = request.POST.get(f'q_{q.pk}', '')
                ContestAnswer.objects.create(
                    submission=submission,
                    question=q,
                    creative_answer=creative_answer,
                    is_correct=None,
                    marks_obtained=0
                )

        now = timezone.now()
        duration = int((now - submission.started_at).total_seconds())
        submission.submitted_at = now
        submission.total_marks = total_marks
        submission.duration_taken = duration
        submission.time_taken_seconds = duration
        submission.is_submitted = True

        from ..models import ContestRegistration
        reg = ContestRegistration.objects.filter(
            contest=contest, user=request.user,
        ).first()
        if reg is not None:
            submission.is_rated_participant = reg.is_rated and contest.is_rated
        else:
            submission.is_rated_participant = contest.is_rated
        submission.save()

    logger.info('Contest submission: contest=%s user=%s marks=%s',
                contest.pk, request.user.username, total_marks)
    messages.success(request, f'Submitted! Your marks: {total_marks}')
    return redirect('contest_result', pk=pk)


@login_required
def contest_result(request, pk):
    from ..models import Contest, ContestSubmission, ContestAnswer
    from django.db.models import Sum
    try:
        if request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin:
            return redirect('contest_leaderboard', pk=pk)
    except Exception:
        pass
    contest = get_object_or_404(Contest, pk=pk)
    submission = get_object_or_404(ContestSubmission, contest=contest, student=request.user, is_submitted=True)
    answers = ContestAnswer.objects.filter(submission=submission).select_related('question')
    max_marks = contest.questions.aggregate(total=Sum('marks'))['total'] or 0
    correct_count = answers.filter(is_correct=True).count()
    percentage = round(submission.total_marks / max_marks * 100, 1) if max_marks > 0 else 0
    all_subs = list(ContestSubmission.objects.filter(
        contest=contest, is_submitted=True,
        student__profile__role='STUDENT',
    ).order_by('-total_marks', 'duration_taken').values_list('student_id', flat=True))
    rank = next((i + 1 for i, uid in enumerate(all_subs) if uid == request.user.id), None)
    return render(request, 'core/contest_result.html', {
        'contest': contest,
        'submission': submission,
        'answers': answers,
        'correct_count': correct_count,
        'max_marks': max_marks,
        'percentage': percentage,
        'rank': rank,
        'total_participants': len(all_subs),
    })


@login_required
def contest_leaderboard(request, pk):
    from ..models import Contest, ContestSubmission, UserRating
    from django.db.models import Sum
    from django.utils import timezone

    contest = get_object_or_404(Contest, pk=pk)
    now = timezone.now()
    is_live = contest.start_time <= now <= contest.end_time
    hide = contest.hide_leaderboard_until_end and is_live

    submissions_qs = ContestSubmission.objects.filter(
        contest=contest, is_submitted=True,
        student__profile__role='STUDENT',
    ).select_related('student', 'student__profile').order_by(
        '-total_marks', 'duration_taken',
    )

    submissions = list(submissions_qs) if not hide else []
    user_rating_map = {
        ur.user_id: ur for ur in UserRating.objects.filter(
            user_id__in=[s.student_id for s in submissions]
        )
    }
    for s in submissions:
        s.user_rating_obj = user_rating_map.get(s.student_id)

    my_submission = ContestSubmission.objects.filter(
        contest=contest, student=request.user, is_submitted=True,
    ).first()
    max_marks = contest.questions.aggregate(total=Sum('marks'))['total'] or 0
    podium = submissions[:3]
    rest = submissions[3:]
    return render(request, 'core/contest_leaderboard.html', {
        'contest': contest,
        'submissions': submissions,
        'podium': podium,
        'rest': rest,
        'my_submission': my_submission,
        'now': now,
        'max_marks': max_marks,
        'is_live': is_live,
        'hide_leaderboard': hide,
    })


@admin_required
def contest_stats(request, pk):
    from ..models import Contest, ContestSubmission, ContestAnswer
    from django.db.models import Sum, Count, Q
    contest = get_object_or_404(Contest, pk=pk)
    submissions = ContestSubmission.objects.filter(
        contest=contest, is_submitted=True,
        student__profile__role='STUDENT',
    ).select_related('student')
    total_participants = submissions.count()
    max_possible = contest.questions.aggregate(total=Sum('marks'))['total'] or 0

    if total_participants > 0:
        marks_list = list(submissions.values_list('total_marks', flat=True))
        avg_marks = round(sum(marks_list) / len(marks_list), 1)
        highest = max(marks_list)
        lowest = min(marks_list)
        pass_count = sum(1 for m in marks_list if m >= max_possible * 0.5)
        pass_rate = round(pass_count / total_participants * 100, 1)
    else:
        avg_marks = highest = lowest = pass_count = pass_rate = 0

    question_stats = []
    for q in contest.questions.all():
        ans = ContestAnswer.objects.filter(submission__in=submissions, question=q)
        t = ans.count()
        c = ans.filter(is_correct=True).count()
        question_stats.append({
            'question': q,
            'total': t,
            'correct': c,
            'accuracy': round(c / t * 100, 1) if t > 0 else 0,
        })
    question_stats.sort(key=lambda x: x['accuracy'])

    return render(request, 'core/contest_stats.html', {
        'contest': contest,
        'total_participants': total_participants,
        'avg_marks': avg_marks,
        'highest': highest,
        'lowest': lowest,
        'max_possible': max_possible,
        'pass_rate': pass_rate,
        'pass_count': pass_count,
        'question_stats': question_stats,
        'top_submissions': submissions.order_by('-total_marks', 'duration_taken')[:10],
    })


@admin_required
def contest_bank_questions(request):
    from ..models import Question
    from django.http import JsonResponse
    subject_id = request.GET.get('subject')
    class_id = request.GET.get('class_obj')
    qs = Question.objects.filter(is_active=True, question_type='MCQ')
    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    if class_id:
        qs = qs.filter(class_obj_id=class_id)
    data = [{'id': q.id, 'text': q.question_text[:120], 'difficulty': q.difficulty,
              'option1': q.option1, 'option2': q.option2, 'option3': q.option3,
              'option4': q.option4, 'correct_option': q.correct_option}
            for q in qs[:60]]
    return JsonResponse({'questions': data})


@admin_required
def contest_delete(request, pk):
    from ..models import Contest
    contest = get_object_or_404(Contest, pk=pk)
    if request.method == 'POST':
        contest.delete()
        messages.success(request, 'Contest deleted!')
        return redirect('contest_list')
    return redirect('contest_detail', pk=pk)


