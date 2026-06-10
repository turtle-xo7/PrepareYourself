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
    from ..models import PracticalVideo, StudyNote, Contest, ExamAttempt, Payment
    from django.db.models import Count, Q, Sum
    from django.core.paginator import Paginator
    from django.utils import timezone

    # All eight profile counts in a single aggregate query (was 8 separate COUNTs)
    pc = UserProfile.objects.aggregate(
        total_superadmins=Count('id', filter=Q(is_superadmin=True)),
        total_users=Count('id', filter=Q(is_superadmin=False)),
        total_students=Count('id', filter=Q(role='STUDENT', is_superadmin=False)),
        total_teachers=Count('id', filter=Q(role='ADMIN', is_superadmin=False)),
        free_users=Count('id', filter=Q(plan='FREE', is_superadmin=False)),
        basic_users=Count('id', filter=Q(plan='BASIC', is_superadmin=False)),
        premium_users=Count('id', filter=Q(plan='PREMIUM', is_superadmin=False)),
        pending_teachers_count=Count('id', filter=Q(role='ADMIN', is_approved=False, is_superadmin=False)),
    )

    total_questions = Question.objects.filter(is_active=True).count()
    total_boards = Board.objects.filter(is_active=True).count()
    total_subjects = Subject.objects.filter(is_active=True).count()
    total_videos = PracticalVideo.objects.filter(is_active=True).count()
    total_notes = StudyNote.objects.filter(is_active=True).count()
    total_contests = Contest.objects.filter(is_active=True).count()
    grade_queue_count = ExamAttempt.objects.filter(status='CQ_PENDING').count()

    # ----- User management: search + filters + pagination -----
    users = UserProfile.objects.filter(is_superadmin=False).select_related('user').order_by('-user__date_joined')
    search = (request.GET.get('q') or '').strip()
    sel_role = request.GET.get('role', '')
    sel_plan = request.GET.get('plan', '')
    if search:
        users = users.filter(Q(user__username__icontains=search) | Q(user__email__icontains=search))
    if sel_role in ('STUDENT', 'ADMIN'):
        users = users.filter(role=sel_role)
    if sel_plan in ('FREE', 'BASIC', 'PREMIUM'):
        users = users.filter(plan=sel_plan)
    total_matched = users.count()
    params = request.GET.copy()
    params.pop('page', None)
    base_qs = params.urlencode()
    page_obj = Paginator(users, 20).get_page(request.GET.get('page'))

    # ----- Revenue (completed payments only) -----
    now = timezone.now()
    completed = Payment.objects.filter(status='COMPLETED')
    revenue = completed.aggregate(total=Sum('amount'), count=Count('id'))
    month_revenue = completed.filter(
        created_at__year=now.year, created_at__month=now.month
    ).aggregate(total=Sum('amount'))['total'] or 0
    recent_payments = completed.select_related('user')[:6]

    return render(request, 'core/superadmin_dashboard.html', {
        **pc,
        'paid_users': pc['basic_users'] + pc['premium_users'],
        'total_questions': total_questions,
        'total_boards': total_boards,
        'total_subjects': total_subjects,
        'total_videos': total_videos,
        'total_notes': total_notes,
        'total_contests': total_contests,
        'grade_queue_count': grade_queue_count,
        'recent_users': page_obj.object_list,
        'page_obj': page_obj,
        'base_qs': base_qs,
        'total_matched': total_matched,
        'search': search,
        'sel_role': sel_role,
        'sel_plan': sel_plan,
        'total_revenue': revenue['total'] or 0,
        'payment_count': revenue['count'] or 0,
        'month_revenue': month_revenue,
        'recent_payments': recent_payments,
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
        subject_ids = [s for s in request.POST.getlist('subjects') if s.isdigit()]
        valid_subjects = Subject.objects.filter(pk__in=subject_ids, is_active=True)
        profile.subjects.set(valid_subjects)
        messages.success(request, f'Subjects updated for {profile.user.username}.')
    return redirect('teacher_applications')


@superadmin_required
def approve_teacher(request, pk):
    from django.shortcuts import get_object_or_404
    from ..models import Notification
    if request.method != 'POST':
        return redirect('teacher_applications')
    profile = get_object_or_404(UserProfile, pk=pk, role='ADMIN')
    profile.is_approved = True
    profile.rejection_reason = ''
    profile.save()
    logger.info('superadmin %s approved teacher %s', request.user.username, profile.user.username)
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
        logger.info('superadmin %s rejected teacher %s: %s', request.user.username, profile.user.username, reason)
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

