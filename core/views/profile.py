"""User profile view and updates.

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
def profile_view(request):
    from ..models import UserProgress, UserRating, UserBadge
    from django.utils import timezone

    profile = request.user.profile
    ctx = {'profile': profile}
    if profile.role == 'ADMIN':
        ctx['all_subjects'] = Subject.objects.filter(is_active=True).order_by('name')

    rating, _ = UserRating.objects.get_or_create(user=request.user)
    progress = UserProgress.objects.filter(user=request.user)
    total = progress.count()
    correct = progress.filter(is_correct=True).count()

    days_left = None
    if profile.plan_expires_at:
        days_left = max((profile.plan_expires_at - timezone.now()).days, 0)

    # Rating band progress (toward next rank)
    thresholds = [0, 800, 1000, 1200, 1400, 1600, 1800]
    r = rating.rating
    lo = max([t for t in thresholds if t <= r] or [0])
    higher = [t for t in thresholds if t > r]
    hi = min(higher) if higher else lo + 200
    band_pct = round((r - lo) / (hi - lo) * 100) if hi > lo else 100

    ctx.update({
        'rating': rating,
        'rank': rating.rank_title,
        'next_rank': rating.next_rank_info,
        'band_pct': band_pct,
        'total_answered': total,
        'total_correct': correct,
        'accuracy': round(correct / total * 100) if total else 0,
        'badges': list(UserBadge.objects.filter(user=request.user).select_related('badge')[:10]),
        'badge_count': UserBadge.objects.filter(user=request.user).count(),
        'days_left': days_left,
        'study_subjects': profile.study_subjects.all(),
    })
    return render(request, 'core/profile.html', ctx)


@login_required
def profile_picture_delete(request):
    if request.method == 'POST':
        profile = request.user.profile
        if profile.profile_picture:
            profile.profile_picture.delete(save=False)
            profile.profile_picture = None
            profile.save(update_fields=['profile_picture'])
            messages.success(request, _L(request, 'Picture removed.', 'ছবি মুছে ফেলা হয়েছে।'))
    return redirect('profile')


@login_required
def profile_update(request):
    if request.method == 'POST':
        user = request.user
        profile = user.profile

        if request.FILES.get('profile_picture'):
            err = _upload_error(request.FILES['profile_picture'], kind='image', max_mb=5)
            if err:
                messages.error(request, _L(request, *err))
                return redirect('profile')
            profile.profile_picture = request.FILES['profile_picture']
            profile.save(update_fields=['profile_picture'])
            messages.success(request, _L(request, 'Profile picture updated!', 'প্রোফাইল ছবি আপডেট হয়েছে!'))
            return redirect('profile')

        if 'update_subjects' in request.POST:
            subject_ids = request.POST.getlist('subjects')
            profile.subjects.set(subject_ids)
            messages.success(request, 'Teaching subjects updated!')
            return redirect('profile')

        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        messages.success(request, _L(request, 'Profile updated!', 'প্রোফাইল আপডেট হয়েছে!'))
        return redirect('profile')
    ctx = {'profile': request.user.profile}
    if request.user.profile.role == 'ADMIN':
        ctx['all_subjects'] = Subject.objects.filter(is_active=True).order_by('name')
    return render(request, 'core/profile.html', ctx)


# -------- SYLLABUS --------

