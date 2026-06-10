"""Shared helpers, constants, and role decorators for all view modules."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction
from ..models import Board, Subject, Class, Question, UserProfile, UserProgress
from ..services import ai as ai_svc
from datetime import datetime
import json
import logging
import uuid

logger = logging.getLogger('core')

CURRENT_YEAR = datetime.now().year
YEARS = list(range(CURRENT_YEAR, CURRENT_YEAR - 6, -1))


def _L(request, en, bn):
    """Return English or Bangla based on the active language."""
    return en if getattr(request, 'LANG', 'bn') == 'en' else bn


# -------- UPLOAD VALIDATION --------

ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
ALLOWED_DOC_EXTS = ALLOWED_IMAGE_EXTS | {'.pdf'}


def _upload_error(uploaded, kind='image', max_mb=10):
    """Validate an uploaded file's extension and size.

    Returns None when acceptable, otherwise an (english, bangla) error pair.
    Pass kind='doc' to additionally allow PDFs.
    """
    if uploaded is None:
        return None
    import os
    allowed = ALLOWED_DOC_EXTS if kind == 'doc' else ALLOWED_IMAGE_EXTS
    ext = os.path.splitext(uploaded.name)[1].lower()
    if ext not in allowed:
        kinds = 'image/PDF' if kind == 'doc' else 'image'
        return (f'"{uploaded.name}" is not an allowed {kinds} file.',
                f'"{uploaded.name}" অনুমোদিত {kinds} ফাইল নয়।')
    if uploaded.size > max_mb * 1024 * 1024:
        return (f'"{uploaded.name}" is too large (max {max_mb} MB).',
                f'"{uploaded.name}" খুব বড় (সর্বোচ্চ {max_mb} MB)।')
    return None


# -------- DECORATORS --------

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            profile = request.user.profile
            if profile.role != 'ADMIN':
                messages.error(request, _L(request, 'Only Teachers/Tutors/Institutions can access this page.', 'শুধু Teacher/Tutor/Institution এই page access করতে পারবে।'))
                return redirect('home')
            if not profile.is_approved and not profile.is_superadmin:
                return redirect('teacher_pending')
        except UserProfile.DoesNotExist:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def superadmin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if not request.user.profile.is_superadmin:
                return redirect('home')
        except:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def premium_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            profile = request.user.profile
            if profile.role == 'ADMIN' or profile.is_superadmin:
                return view_func(request, *args, **kwargs)
            if not profile.is_premium:
                messages.error(request, _L(request, 'This feature is for Premium users only.', 'এই feature শুধু Premium users এর জন্য।'))
                return redirect('pricing')
        except UserProfile.DoesNotExist:
            return redirect('pricing')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# -------- SHARED CROSS-MODULE HELPERS --------

def _is_exam_staff(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    try:
        p = user.profile
        return p.is_superadmin or p.role == 'ADMIN'
    except Exception:
        return False


def _notify_all_students(notif_type, title, message, link='', title_bn='', message_bn=''):
    from ..models import Notification, UserProfile
    student_ids = UserProfile.objects.filter(role='STUDENT').values_list('user_id', flat=True)
    Notification.objects.bulk_create([
        Notification(
            recipient_id=uid, notif_type=notif_type,
            title=title, message=message,
            title_bn=title_bn, message_bn=message_bn,
            link=link,
        )
        for uid in student_ids
    ])


