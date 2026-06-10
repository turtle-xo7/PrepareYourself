"""Superadmin dashboard and teacher approval queue.

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

@superadmin_required
def superadmin_dashboard(request):
    from ..models import PracticalVideo, StudyNote, Contest

    total_superadmins = UserProfile.objects.filter(is_superadmin=True).count()
    total_users = UserProfile.objects.filter(is_superadmin=False).count()
    total_students = UserProfile.objects.filter(role='STUDENT', is_superadmin=False).count()
    total_teachers = UserProfile.objects.filter(role='ADMIN', is_superadmin=False).count()
    free_users = UserProfile.objects.filter(plan='FREE', is_superadmin=False).count()
    basic_users = UserProfile.objects.filter(plan='BASIC', is_superadmin=False).count()
    premium_users = UserProfile.objects.filter(plan='PREMIUM', is_superadmin=False).count()
    paid_users = basic_users + premium_users
    total_questions = Question.objects.filter(is_active=True).count()
    total_boards = Board.objects.filter(is_active=True).count()
    total_subjects = Subject.objects.filter(is_active=True).count()
    total_videos = PracticalVideo.objects.filter(is_active=True).count()
    total_notes = StudyNote.objects.filter(is_active=True).count()
    total_contests = Contest.objects.filter(is_active=True).count()
    recent_users = UserProfile.objects.filter(is_superadmin=False).select_related('user').order_by('-user__date_joined')[:10]
    pending_teachers_count = UserProfile.objects.filter(role='ADMIN', is_approved=False, is_superadmin=False).count()

    return render(request, 'core/superadmin_dashboard.html', {
        'total_superadmins': total_superadmins,
        'total_users': total_users,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'free_users': free_users,
        'basic_users': basic_users,
        'premium_users': premium_users,
        'paid_users': paid_users,
        'total_questions': total_questions,
        'total_boards': total_boards,
        'total_subjects': total_subjects,
        'total_videos': total_videos,
        'total_notes': total_notes,
        'total_contests': total_contests,
        'recent_users': recent_users,
        'pending_teachers_count': pending_teachers_count,
    })


@login_required
def teacher_pending(request):
    try:
        profile = request.user.profile
        if profile.role != 'ADMIN':
            return redirect('home')
        if profile.is_approved or profile.is_superadmin:
            return redirect('teacher_dashboard')
    except Exception:
        return redirect('home')
    return render(request, 'core/teacher_pending.html', {'profile': profile})


@superadmin_required
def teacher_applications(request):
    from ..models import Subject
    pending = UserProfile.objects.filter(
        role='ADMIN', is_approved=False, is_superadmin=False
    ).select_related('user').order_by('user__date_joined')
    approved = UserProfile.objects.filter(
        role='ADMIN', is_approved=True, is_superadmin=False
    ).select_related('user').prefetch_related('subjects').order_by('-user__date_joined')[:30]
    all_subjects = Subject.objects.filter(is_active=True).order_by('name')
    return render(request, 'core/teacher_applications.html', {
        'pending': pending,
        'approved': approved,
        'all_subjects': all_subjects,
    })


@superadmin_required
def assign_teacher_subjects(request, pk):
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, pk=pk, role='ADMIN')
        subject_ids = request.POST.getlist('subjects')
        profile.subjects.set(subject_ids)
        messages.success(request, f'Subjects updated for {profile.user.username}.')
    return redirect('teacher_applications')


@superadmin_required
def approve_teacher(request, pk):
    from django.shortcuts import get_object_or_404
    from ..models import Notification
    profile = get_object_or_404(UserProfile, pk=pk, role='ADMIN')
    profile.is_approved = True
    profile.rejection_reason = ''
    profile.save()
    Notification.objects.create(
        recipient=profile.user,
        notif_type='question',
        title='Teacher Application Approved!',
        title_bn='শিক্ষক আবেদন অনুমোদিত!',
        message='Your teacher application has been approved. You can now access your teacher dashboard.',
        message_bn='আপনার শিক্ষক আবেদন অনুমোদিত হয়েছে। এখন আপনি Teacher Dashboard ব্যবহার করতে পারবেন।',
        link='/teacher/dashboard/',
    )
    messages.success(request, f'{profile.user.username} approved successfully.')
    return redirect('teacher_applications')


@superadmin_required
def reject_teacher(request, pk):
    from django.shortcuts import get_object_or_404
    from ..models import Notification
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, pk=pk, role='ADMIN')
        reason = request.POST.get('reason', 'No reason provided.')
        profile.is_approved = False
        profile.rejection_reason = reason
        profile.save()
        Notification.objects.create(
            recipient=profile.user,
            notif_type='question',
            title='Teacher Application Update',
            title_bn='শিক্ষক আবেদনের আপডেট',
            message=f'Your teacher application was not approved. Reason: {reason}',
            message_bn=f'আপনার শিক্ষক আবেদন অনুমোদিত হয়নি। কারণ: {reason}',
        )
        messages.info(request, f'{profile.user.username} application rejected.')
    return redirect('teacher_applications')


# -------- MANAGE PANEL (ADMIN ONLY) --------

