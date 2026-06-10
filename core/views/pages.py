"""Home, pricing, and global search.

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

def home(request):
    from ..models import Board
    boards = Board.objects.filter(is_active=True)
    return render(request, 'core/home.html', {'boards': boards})

def pricing(request):
    return render(request, 'core/pricing.html')


def _search_scope(request):
    """Return (board_id, class_id) to scope search to, from the user's profile."""
    if request.user.is_authenticated:
        try:
            p = request.user.profile
            return (getattr(p, 'board_id', None), getattr(p, 'class_obj_id', None))
        except UserProfile.DoesNotExist:
            pass
    return (None, None)


def _run_search(query, board_id=None, class_id=None, scoped=True, limit=6):
    """Search questions, notes, exam papers. Returns dict of grouped lists."""
    from ..models import StudyNote, ExamPaper
    from django.db.models import Q
    q = (query or '').strip()
    if not q:
        return {'questions': [], 'notes': [], 'papers': []}

    questions = Question.objects.select_related('subject', 'board', 'class_obj').filter(
        is_active=True
    ).filter(
        Q(question_text__icontains=q) | Q(chapter__icontains=q) | Q(subject__name__icontains=q)
    )
    notes = StudyNote.objects.select_related('subject', 'class_obj').filter(
        is_active=True
    ).filter(
        Q(title__icontains=q) | Q(chapter__icontains=q) | Q(content__icontains=q)
    )
    papers = ExamPaper.objects.select_related('subject', 'class_obj', 'board').filter(
        is_active=True
    ).filter(
        Q(title__icontains=q) | Q(subject__name__icontains=q)
    )

    if scoped and class_id:
        questions = questions.filter(class_obj_id=class_id)
        notes = notes.filter(class_obj_id=class_id)
        papers = papers.filter(class_obj_id=class_id)
    if scoped and board_id:
        questions = questions.filter(board_id=board_id)
        papers = papers.filter(Q(board_id=board_id) | Q(board__isnull=True))

    return {
        'questions': list(questions[:limit]),
        'notes': list(notes[:limit]),
        'papers': list(papers[:limit]),
    }


def search_api(request):
    """JSON endpoint for the ⌘K quick-search modal."""
    query = request.GET.get('q', '')
    scoped = request.GET.get('all') != '1'
    board_id, class_id = _search_scope(request)
    results = _run_search(query, board_id, class_id, scoped=scoped, limit=5)

    def label(obj_subject, obj_class):
        bits = []
        if obj_subject:
            bits.append(obj_subject)
        if obj_class:
            bits.append(obj_class)
        return ' · '.join(bits)

    payload = {
        'questions': [{
            'id': x.pk,
            'title': (x.question_text[:80] + '…') if len(x.question_text) > 80 else x.question_text,
            'meta': label(x.subject.name if x.subject_id else '', x.class_obj.name if x.class_obj_id else '') + (' · ' + str(x.year) if x.year else ''),
            'url': f'/question-bank/?subject={x.subject_id}' if x.subject_id else '/question-bank/',
        } for x in results['questions']],
        'notes': [{
            'id': x.pk,
            'title': x.title,
            'meta': label(x.subject.name if x.subject_id else '', x.class_obj.name if x.class_obj_id else ''),
            'url': f'/study-notes/{x.pk}/',
        } for x in results['notes']],
        'papers': [{
            'id': x.pk,
            'title': x.title,
            'meta': label(x.subject.name if x.subject_id else '', x.class_obj.name if x.class_obj_id else ''),
            'url': f'/exam-papers/{x.pk}/',
        } for x in results['papers']],
    }
    payload['total'] = len(payload['questions']) + len(payload['notes']) + len(payload['papers'])
    payload['scoped'] = scoped
    return JsonResponse(payload)


def search_page(request):
    """Full-page grouped search results."""
    query = request.GET.get('q', '')
    scoped = request.GET.get('all') != '1'
    board_id, class_id = _search_scope(request)
    results = _run_search(query, board_id, class_id, scoped=scoped, limit=30)
    total = len(results['questions']) + len(results['notes']) + len(results['papers'])
    return render(request, 'core/search.html', {
        'query': query,
        'results': results,
        'total': total,
        'scoped': scoped,
    })


SUBJECT_COLOR_HEX = {
    'blue': '#3b82f6', 'red': '#ef4444', 'green': '#22c55e',
    'purple': '#a855f7', 'orange': '#f97316', 'yellow': '#eab308',
    'pink': '#ec4899', 'teal': '#14b8a6', 'indigo': '#6366f1',
    'cyan': '#06b6d4', 'emerald': '#10b981',
}

_SUBJECT_EMOJI = {
    'bangla': '✍️',
    'বাংলা': '✍️',
    'english': '💬',
    'higher math': '📐',
    'higher mathematics': '📐',
    'উচ্চতর গণিত': '📐',
    'physics': '⚛️',
    'পদার্থবিজ্ঞান': '⚛️',
    'chemistry': '🧪',
    'রসায়ন': '🧪',
    'biology': '🧬',
    'জীববিজ্ঞান': '🧬',
    'ict': '💻',
    'information and communication technology': '💻',
    'math': '🔢',
    'mathematics': '🔢',
    'গণিত': '🔢',
    'history': '🏛️',
    'geography': '🌍',
    'economics': '📊',
    'accounting': '🧾',
    'civics': '⚖️',
    'islam': '🕌',
    'religion': '🙏',
}


