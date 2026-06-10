"""Public question bank and MCQ progress tracking.

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

def question_bank(request):
    boards = Board.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    questions = Question.objects.select_related('board', 'subject', 'class_obj').filter(is_active=True)

    board = request.GET.get('board')
    subject = request.GET.get('subject')
    class_id = request.GET.get('class')
    year = request.GET.get('year')
    qtype = request.GET.get('type')                 # MCQ | WRITTEN
    difficulties = request.GET.getlist('difficulty')  # Easy/Medium/Hard (multi)
    status = request.GET.get('status')              # unsolved | wrong

    # Default scope to the student's profile board/class if not overridden
    profile = None
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            profile = None
    if profile and 'board' not in request.GET and getattr(profile, 'board_id', None):
        board = str(profile.board_id)
    if profile and 'class' not in request.GET and getattr(profile, 'class_obj_id', None):
        class_id = str(profile.class_obj_id)

    if board:
        questions = questions.filter(board_id=board)
    if subject:
        questions = questions.filter(subject_id=subject)
    if class_id:
        questions = questions.filter(class_obj_id=class_id)
    if year:
        questions = questions.filter(year=year)
    if qtype in ('MCQ', 'WRITTEN'):
        questions = questions.filter(question_type=qtype)
    if difficulties:
        valid = [d for d in difficulties if d in ('Easy', 'Medium', 'Hard')]
        if valid:
            questions = questions.filter(difficulty__in=valid)

    is_premium = False
    is_teacher = False
    if profile:
        is_premium = profile.is_premium
        is_teacher = profile.role == 'ADMIN' or profile.is_superadmin

    # Personal status filters (logged-in students only)
    if request.user.is_authenticated and not is_teacher and status in ('unsolved', 'wrong'):
        answered_ids = UserProgress.objects.filter(user=request.user).values_list('question_id', flat=True)
        if status == 'unsolved':
            questions = questions.exclude(pk__in=list(answered_ids))
        elif status == 'wrong':
            wrong_ids = UserProgress.objects.filter(user=request.user, is_correct=False).values_list('question_id', flat=True)
            questions = questions.filter(pk__in=list(wrong_ids))

    # Count of active refine filters (for the UI badge)
    active_filters = sum([
        bool(request.GET.get('board')), bool(request.GET.get('class')),
        bool(subject), bool(year), bool(qtype),
        bool(difficulties), bool(status),
    ])
    total_matched = questions.count()

    # Free users see a fixed 10-question teaser; everyone else gets pages of 30
    # so huge banks don't render thousands of rows at once.
    page_obj = None
    base_qs = ''
    if not is_premium and not is_teacher:
        questions = questions[:10]
    else:
        from django.core.paginator import Paginator
        params = request.GET.copy()
        params.pop('page', None)
        base_qs = params.urlencode()
        page_obj = Paginator(questions, 30).get_page(request.GET.get('page'))
        questions = page_obj.object_list

    # Per-question attempt stats for teachers
    if is_teacher:
        from ..models import UserProgress
        from django.db.models import Count, Q as DQ
        questions = list(questions)
        q_ids = [q.pk for q in questions]
        stats_map = {}
        for s in UserProgress.objects.filter(question_id__in=q_ids).values('question_id').annotate(
            attempted=Count('id'),
            correct=Count('id', filter=DQ(is_correct=True))
        ):
            pct = round(s['correct'] / s['attempted'] * 100) if s['attempted'] else 0
            stats_map[s['question_id']] = (s['attempted'], pct)
        for q in questions:
            sv = stats_map.get(q.pk, (0, 0))
            q.stats_attempted = sv[0]
            q.stats_correct_pct = sv[1]

    # Map question_id → WrittenSolveSubmission for the current user
    written_solves = {}
    if request.user.is_authenticated and not is_teacher:
        from ..models import WrittenSolveSubmission
        q_ids = [q.pk for q in questions]
        for sub in WrittenSolveSubmission.objects.filter(student=request.user, question_id__in=q_ids):
            written_solves[sub.question_id] = sub

    return render(request, 'core/question_bank.html', {
        'boards': boards,
        'subjects': subjects,
        'classes': classes,
        'questions': questions,
        'years': YEARS,
        'is_premium': is_premium,
        'is_teacher': is_teacher,
        'written_solves': written_solves,
        'active_filters': active_filters,
        'total_matched': total_matched,
        'sel_type': qtype or '',
        'sel_difficulties': difficulties,
        'sel_status': status or '',
        'page_obj': page_obj,
        'base_qs': base_qs,
    })


@login_required
def track_progress(request):
    if request.method == 'POST':
        try:
            profile = request.user.profile
            if profile.role == 'ADMIN' or profile.is_superadmin:
                return JsonResponse({'status': 'ok'})
        except UserProfile.DoesNotExist:
            pass
        from ..models import UserProgress
        data = json.loads(request.body)
        question_id = data.get('question_id')
        is_correct = data.get('is_correct', False)
        question_obj = Question.objects.filter(pk=question_id).first()
        if question_obj:
            UserProgress.objects.get_or_create(
                user=request.user,
                question=question_obj,
                defaults={'is_correct': is_correct}
            )
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'})


# -------- SUPERADMIN DASHBOARD --------

