"""Login, signup, onboarding, logout, language toggle.

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

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Email দিয়ে login support
        if '@' in username:
            try:
                from django.contrib.auth.models import User
                user_obj = User.objects.get(email=username)
                username = user_obj.username
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, _L(request, 'Incorrect username/email or password.', 'Username/Email বা Password ভুল।'))
    return render(request, 'core/login.html')


def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'STUDENT')
        plan = request.POST.get('plan', 'FREE')
        admin_code = request.POST.get('admin_code', '')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return redirect('login')

        for doc in (request.FILES.get('nid_document'), request.FILES.get('qualification_document')):
            err = _upload_error(doc, kind='doc', max_mb=10)
            if err:
                messages.error(request, _L(request, *err))
                return redirect('login')

        is_superadmin = False
        if admin_code == 'PY2026ADMIN':
            role = 'ADMIN'
            is_superadmin = True

        is_approved = True
        if role == 'ADMIN' and not is_superadmin:
            is_approved = False

        # User + profile must be created together — an orphan User without a
        # UserProfile breaks every profile-dependent view after login.
        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            profile = UserProfile.objects.create(
                user=user,
                role=role,
                plan=plan,
                is_superadmin=is_superadmin,
                is_approved=is_approved,
            )

            if role == 'ADMIN' and not is_superadmin:
                profile.teacher_bio = request.POST.get('teacher_bio', '')
                profile.subject_expertise = request.POST.get('subject_expertise', '')
                if request.FILES.get('nid_document'):
                    profile.nid_document = request.FILES['nid_document']
                if request.FILES.get('qualification_document'):
                    profile.qualification_document = request.FILES['qualification_document']
                profile.save()

        logger.info('New signup: %s (role=%s, plan=%s)', username, role, plan)
        login(request, user)

        if role == 'ADMIN' and not is_superadmin:
            return redirect('teacher_pending')

        if plan != 'FREE':
            return redirect(f'/checkout/?plan={plan}')

        # New students go through onboarding first
        return redirect('onboarding')

    return redirect('login')


@login_required
def onboarding(request):
    """One-time setup: capture Board + Class + Subjects so content is personalized."""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        return redirect('home')

    # Teachers/admins don't onboard as students
    if profile.role == 'ADMIN' or profile.is_superadmin:
        return redirect('home')

    if request.method == 'POST':
        board_id = request.POST.get('board')
        class_id = request.POST.get('class')
        subject_ids = request.POST.getlist('subjects')
        goal = request.POST.get('goal', '').strip()

        if board_id:
            profile.board_id = board_id
        if class_id:
            profile.class_obj_id = class_id
        profile.exam_goal = goal[:120]
        profile.onboarded = True
        profile.save()
        if subject_ids:
            profile.study_subjects.set(subject_ids)

        messages.success(request, 'Your study space is ready! 🎉' if getattr(request, 'LANG', 'bn') == 'en' else 'তোমার স্টাডি স্পেস তৈরি! 🎉')
        return redirect('dashboard' if profile.is_premium else 'question_bank')

    return render(request, 'core/onboarding.html', {
        'boards': Board.objects.filter(is_active=True),
        'classes': Class.objects.all(),
        'subjects': Subject.objects.filter(is_active=True),
    })


def logout_view(request):
    logout(request)
    return redirect('login')


def toggle_language(request):
    current = getattr(request, 'LANG', 'bn')
    new_lang = 'en' if current == 'bn' else 'bn'
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            profile.preferred_language = new_lang
            profile.save(update_fields=['preferred_language'])
        except Exception:
            pass
    request.session['preferred_language'] = new_lang
    return redirect(request.META.get('HTTP_REFERER', '/'))


