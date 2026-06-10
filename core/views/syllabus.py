"""Syllabus list, detail, and CRUD.

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

def syllabus_list(request):
    from ..models import Syllabus
    syllabi = Syllabus.objects.filter(is_active=True).select_related('subject', 'class_obj', 'board')
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    boards = Board.objects.filter(is_active=True)

    subject_filter = request.GET.get('subject')
    class_filter = request.GET.get('class_obj')
    board_filter = request.GET.get('board')

    if subject_filter:
        syllabi = syllabi.filter(subject__slug=subject_filter)
    if class_filter:
        syllabi = syllabi.filter(class_obj__id=class_filter)
    if board_filter:
        syllabi = syllabi.filter(board__id=board_filter)

    return render(request, 'core/syllabus_list.html', {
        'syllabi': syllabi,
        'subjects': subjects,
        'classes': classes,
        'boards': boards,
    })


def syllabus_detail(request, pk):
    from ..models import Syllabus
    syllabus = get_object_or_404(Syllabus, pk=pk, is_active=True)
    return render(request, 'core/syllabus_detail.html', {
        'syllabus': syllabus,
    })


@admin_required
def syllabus_add(request):
    from ..models import Syllabus
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    boards = Board.objects.filter(is_active=True)
    if request.method == 'POST':
        Syllabus.objects.create(
            subject=get_object_or_404(Subject, pk=request.POST.get('subject')),
            class_obj=get_object_or_404(Class, pk=request.POST.get('class_obj')),
            board=get_object_or_404(Board, pk=request.POST.get('board')),
            content=request.POST.get('content', ''),
            is_active=True
        )
        messages.success(request, 'Syllabus added!')
        return redirect('syllabus_list')
    return render(request, 'core/syllabus_form.html', {
        'subjects': subjects,
        'classes': classes,
        'boards': boards,
        'action': 'Add',
    })


@admin_required
def syllabus_edit(request, pk):
    from ..models import Syllabus
    syllabus = get_object_or_404(Syllabus, pk=pk)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    boards = Board.objects.filter(is_active=True)
    if request.method == 'POST':
        syllabus.subject = get_object_or_404(Subject, pk=request.POST.get('subject'))
        syllabus.class_obj = get_object_or_404(Class, pk=request.POST.get('class_obj'))
        syllabus.board = get_object_or_404(Board, pk=request.POST.get('board'))
        syllabus.content = request.POST.get('content', '')
        syllabus.save()
        messages.success(request, 'Syllabus updated!')
        return redirect('syllabus_detail', pk=syllabus.pk)
    return render(request, 'core/syllabus_form.html', {
        'syllabus': syllabus,
        'subjects': subjects,
        'classes': classes,
        'boards': boards,
        'action': 'Edit',
    })


@admin_required
def syllabus_delete(request, pk):
    from ..models import Syllabus
    syllabus = get_object_or_404(Syllabus, pk=pk)
    if request.method == 'POST':
        syllabus.delete()
        messages.success(request, 'Syllabus deleted!')
    return redirect('syllabus_list')
