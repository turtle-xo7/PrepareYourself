"""Checkout, simulated payment gateway, plan activation.

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

PLAN_PRICES = {'FREE': 0, 'BASIC': 99, 'PREMIUM': 199}
PLAN_LABELS = {'FREE': 'Free', 'BASIC': 'Basic', 'PREMIUM': 'Premium'}


def _activate_plan(profile, plan):
    """Single source of truth for granting a paid plan (30 days; extends if still active)."""
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    base = profile.plan_expires_at if (profile.plan_expires_at and profile.plan_expires_at > now) else now
    profile.plan = plan
    profile.plan_expires_at = base + timedelta(days=30)
    profile.save(update_fields=['plan', 'plan_expires_at'])


@login_required
def checkout(request):
    from ..models import Payment
    if request.method == 'POST':
        plan = (request.POST.get('plan') or 'BASIC').upper()
        if plan not in ('BASIC', 'PREMIUM'):
            plan = 'BASIC'
        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            amount=PLAN_PRICES[plan],
            method=request.POST.get('method', ''),
            tran_id=uuid.uuid4().hex,
            gateway='simulation',
            status='PENDING',
        )
        # Plan is NOT activated here. Activation only happens after a verified
        # payment (payment_process). To go live, replace this redirect with the
        # gateway "initiate" call and redirect to the returned checkout URL.
        return redirect('payment_simulate', tran_id=payment.tran_id)

    plan = request.GET.get('plan') or request.user.profile.plan or 'BASIC'
    plan = plan.upper()
    if plan not in PLAN_PRICES or plan == 'FREE':
        plan = 'BASIC'
    return render(request, 'core/checkout.html', {
        'plan': plan,
        'plan_label': PLAN_LABELS.get(plan, plan.title()),
        'price': PLAN_PRICES.get(plan, 99),
    })


@login_required
def payment_simulate(request, tran_id):
    """Dev-only fake gateway. Disabled when DEBUG is False, so production cannot
    grant free plans before a real gateway is integrated."""
    from ..models import Payment
    if not settings.DEBUG:
        messages.error(request, _L(request, 'Online payment is not available yet.', 'অনলাইন পেমেন্ট এখনো চালু হয়নি।'))
        return redirect('pricing')
    payment = get_object_or_404(Payment, tran_id=tran_id, user=request.user)
    if payment.status == 'COMPLETED':
        return redirect('payment_success', tran_id=tran_id)
    if payment.status != 'PENDING':
        return redirect('pricing')
    return render(request, 'core/payment_simulate.html', {'payment': payment})


@login_required
def payment_process(request, tran_id):
    """Completes a simulated payment. In a real gateway this becomes the
    server-side validation callback: verify val_id + amount with the gateway
    BEFORE calling _activate_plan."""
    from ..models import Payment
    if request.method != 'POST' or not settings.DEBUG:
        return redirect('pricing')
    payment = get_object_or_404(Payment, tran_id=tran_id, user=request.user)
    if payment.status != 'PENDING':
        return redirect('payment_success', tran_id=tran_id)
    if request.POST.get('result') == 'success':
        # Marking the payment COMPLETED and granting the plan must succeed or
        # fail together — a COMPLETED payment without an active plan (or vice
        # versa) cannot be reconciled later.
        with transaction.atomic():
            payment.status = 'COMPLETED'
            payment.val_id = 'SIM-' + payment.tran_id[:12]
            payment.save(update_fields=['status', 'val_id', 'updated_at'])
            _activate_plan(request.user.profile, payment.plan)
        logger.info('Payment completed: tran_id=%s user=%s plan=%s amount=%s',
                    payment.tran_id, request.user.username, payment.plan, payment.amount)
        return redirect('payment_success', tran_id=tran_id)
    payment.status = 'FAILED'
    payment.save(update_fields=['status', 'updated_at'])
    logger.warning('Payment failed: tran_id=%s user=%s plan=%s',
                   payment.tran_id, request.user.username, payment.plan)
    return redirect('payment_failed')


@login_required
def payment_success(request, tran_id):
    from ..models import Payment
    payment = get_object_or_404(Payment, tran_id=tran_id, user=request.user)
    profile = request.user.profile
    needs_onboarding = (not profile.onboarded and profile.role != 'ADMIN'
                        and not profile.is_superadmin)
    return render(request, 'core/payment_success.html', {
        'payment': payment,
        'needs_onboarding': needs_onboarding,
    })


def payment_failed(request):
    return render(request, 'core/payment_failed.html', {
        'error_message': _L(request,
                            'The payment was cancelled or could not be completed.',
                            'পেমেন্ট বাতিল হয়েছে বা সম্পন্ন করা যায়নি।'),
    })


# -------- FRONTEND VIEWS --------

