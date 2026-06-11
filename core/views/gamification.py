"""Contest registration, ratings, badges, coins, virtual contests.

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
def contest_register(request, pk):
    """POST: register the current user for a contest.

    Honors entry_requirement, registration_deadline, max_participants, and
    is_rated/allow_unrated_join. Awards early_bird bonus where applicable.
    """
    from ..models import Contest, ContestRegistration
    from ..services import coins as coin_svc
    from ..services import badges as badge_svc
    from django.utils import timezone

    if request.method != 'POST':
        return redirect('contest_detail', pk=pk)

    contest = get_object_or_404(Contest, pk=pk)
    now = timezone.now()

    try:
        profile = request.user.profile
        if profile.role == 'ADMIN' or profile.is_superadmin:
            messages.error(request, 'Teachers/admins cannot register for contests.')
            return redirect('contest_detail', pk=pk)
    except Exception:
        pass

    if contest.registration_deadline and now > contest.registration_deadline:
        messages.error(request, 'Registration deadline has passed.')
        return redirect('contest_detail', pk=pk)
    if now > contest.end_time:
        messages.error(request, 'This contest has already ended.')
        return redirect('contest_detail', pk=pk)

    req = contest.entry_requirement
    if req == 'premium' and not getattr(profile, 'is_premium', False):
        messages.error(request, 'Premium membership required for this contest.')
        return redirect('contest_detail', pk=pk)
    class_map = {'class_9': '9', 'class_10': '10', 'class_11': '11', 'class_12': '12'}
    if req in class_map:
        cls_name = (contest.class_obj.name or '').strip()
        if class_map[req] not in cls_name:
            messages.error(request, f'This contest is only for {contest.class_obj.name}.')
            return redirect('contest_detail', pk=pk)

    if contest.max_participants:
        reg_count = ContestRegistration.objects.filter(contest=contest).count()
        if reg_count >= contest.max_participants:
            existing = ContestRegistration.objects.filter(
                contest=contest, user=request.user,
            ).first()
            if not existing:
                messages.error(request, 'Contest is full.')
                return redirect('contest_detail', pk=pk)

    want_rated = (request.POST.get('is_rated', '1') == '1')
    if not contest.is_rated:
        want_rated = False
    if not contest.allow_unrated_join and contest.is_rated:
        want_rated = True

    is_first = not contest.registrations.filter(user=request.user).exists()
    is_early = (now - contest.created_at).total_seconds() <= 3600

    # Registration and its one-time rewards (first-contest coins, early-bird
    # badge) must commit together so a failure can't leave a registration
    # whose rewards were already paid out, or vice versa.
    with transaction.atomic():
        reg, created = ContestRegistration.objects.update_or_create(
            contest=contest, user=request.user,
            defaults={'is_rated': want_rated, 'is_early_bird': is_early and is_first},
        )

        if created:
            if is_first and ContestRegistration.objects.filter(user=request.user).count() == 1:
                coin_svc.award_coins(request.user, 'first_contest', contest=contest,
                                     note='Your very first contest!')
            if is_early:
                badge_svc.award_early_bird(request.user, contest)

    if created:
        messages.success(request, f'Registered for {contest.title} '
                                  f'({"rated" if want_rated else "unrated"}).')
    else:
        messages.info(request, f'Updated registration to '
                               f'{"rated" if want_rated else "unrated"}.')

    return redirect('contest_detail', pk=pk)


@login_required
def contest_set_rated(request, pk):
    """POST: toggle rated/unrated participation before contest start."""
    from ..models import Contest, ContestRegistration
    from django.utils import timezone
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
    contest = get_object_or_404(Contest, pk=pk)
    if timezone.now() >= contest.start_time:
        return JsonResponse({'ok': False, 'error': 'Contest has started'}, status=400)
    reg, _ = ContestRegistration.objects.get_or_create(
        contest=contest, user=request.user,
    )
    want = request.POST.get('is_rated', '1') == '1'
    if not contest.is_rated:
        want = False
    if not contest.allow_unrated_join and contest.is_rated:
        want = True
    reg.is_rated = want
    reg.save(update_fields=['is_rated'])
    return JsonResponse({'ok': True, 'is_rated': reg.is_rated})


@login_required
def leaderboard_data(request, pk):
    """JSON leaderboard for AJAX polling."""
    from ..models import Contest, ContestSubmission, UserRating
    from django.core.cache import cache
    from django.http import JsonResponse
    from django.utils import timezone

    contest = get_object_or_404(Contest, pk=pk)
    now = timezone.now()
    if contest.hide_leaderboard_until_end and contest.start_time <= now <= contest.end_time:
        return JsonResponse({
            'hidden': True,
            'rows': [],
            'updated_at': now.isoformat(),
        })

    # Every participant polls this endpoint; cache the shared rows briefly and
    # apply the viewer-specific is_me flag after retrieval.
    cache_key = f'contest_lb_rows:{contest.pk}'
    cached = cache.get(cache_key)
    if cached is None:
        subs = ContestSubmission.objects.filter(
            contest=contest, is_submitted=True,
            student__profile__role='STUDENT',
        ).select_related('student').order_by('-total_marks', 'duration_taken')

        ratings = {
            ur.user_id: ur for ur in UserRating.objects.filter(
                user_id__in=[s.student_id for s in subs]
            )
        }
        rows = []
        for idx, s in enumerate(subs):
            ur = ratings.get(s.student_id)
            title = ur.rank_title if ur else {'title': 'Newcomer', 'color': '#808080'}
            rows.append({
                'rank': idx + 1,
                'user_id': s.student_id,
                'username': s.student.username,
                'score': s.total_marks,
                'time_taken': s.duration_taken,
                'rating': ur.rating if ur else 1000,
                'rank_title': title['title'],
                'rank_color': title['color'],
                'rating_change': s.rating_change,
                'percentile': s.percentile,
                'is_virtual': s.is_virtual,
            })
        cached = {'rows': rows, 'updated_at': now.isoformat()}
        cache.set(cache_key, cached, 15)

    rows = [
        {**{k: v for k, v in row.items() if k != 'user_id'},
         'is_me': row['user_id'] == request.user.id}
        for row in cached['rows']
    ]
    return JsonResponse({
        'hidden': False,
        'rows': rows,
        'updated_at': cached['updated_at'],
        'contest_status': 'live' if contest.start_time <= now <= contest.end_time
                          else ('past' if now > contest.end_time else 'upcoming'),
    })


@login_required
def virtual_contest(request, pk):
    """Replay a past contest as a virtual practice attempt (no rating change)."""
    from ..models import Contest, VirtualContest, ContestSubmission
    from django.utils import timezone

    contest = get_object_or_404(Contest, pk=pk)
    if not contest.allows_virtual:
        messages.error(request, 'Virtual replay is disabled for this contest.')
        return redirect('contest_detail', pk=pk)
    if timezone.now() < contest.end_time:
        messages.error(request, 'Virtual contests are only available after the contest ends.')
        return redirect('contest_detail', pk=pk)

    vc, _ = VirtualContest.objects.get_or_create(
        user=request.user, contest=contest, finished_at__isnull=True,
        defaults={},
    )

    sub, _ = ContestSubmission.objects.get_or_create(
        contest=contest, student=request.user,
        defaults={'is_virtual': True, 'is_rated_participant': False},
    )
    if not sub.is_virtual:
        sub.is_virtual = True
        sub.is_rated_participant = False
        sub.save(update_fields=['is_virtual', 'is_rated_participant'])

    questions = contest.questions.all()
    return render(request, 'core/virtual_contest.html', {
        'contest': contest,
        'questions': questions,
        'submission': sub,
        'virtual': vc,
    })


@login_required
def badge_gallery(request):
    """Public badge gallery: shows all badges + which the user has earned."""
    from ..models import Badge, UserBadge
    badges = Badge.objects.filter(is_active=True).order_by('badge_type', 'rarity', 'name')
    earned = {
        ub.badge_id: ub for ub in UserBadge.objects.filter(user=request.user).select_related('badge')
    }
    grouped = {}
    for b in badges:
        grouped.setdefault(b.get_badge_type_display(), []).append({
            'badge': b,
            'earned': b.id in earned,
            'earned_at': earned[b.id].earned_at if b.id in earned else None,
        })
    total_badges = badges.count()
    earned_count = len(earned)
    rarest = None
    rarity_order = {'legendary': 4, 'epic': 3, 'rare': 2, 'common': 1}
    for b in badges:
        if b.id in earned:
            if rarest is None or rarity_order[b.rarity] > rarity_order[rarest.rarity]:
                rarest = b
    return render(request, 'core/badge_gallery.html', {
        'grouped': grouped,
        'total_badges': total_badges,
        'earned_count': earned_count,
        'rarest': rarest,
    })


@login_required
def profile_contests(request):
    """Codeforces-style contest profile: rating chart, badges, history."""
    from ..models import (
        UserRating, ContestRatingHistory, UserBadge, Badge, ContestSubmission,
    )
    from django.db.models import Avg
    from django.core.paginator import Paginator
    from django.utils import timezone

    rating, _ = UserRating.objects.get_or_create(user=request.user)
    history = ContestRatingHistory.objects.filter(
        user=request.user,
    ).select_related('contest').order_by('recorded_at')[:20]

    earned = UserBadge.objects.filter(
        user=request.user,
    ).select_related('badge').order_by('-earned_at')
    earned_ids = set(eb.badge_id for eb in earned)
    all_badges = Badge.objects.filter(is_active=True).order_by('badge_type', 'rarity')

    badge_list = []
    for b in all_badges:
        badge_list.append({
            'badge': b,
            'earned': b.id in earned_ids,
        })

    submissions = ContestSubmission.objects.filter(
        student=request.user, is_submitted=True, is_virtual=False,
    ).select_related('contest').order_by('-submitted_at')
    paginator = Paginator(submissions, 15)
    page = paginator.get_page(request.GET.get('page'))

    stats = {
        'entered': rating.contests_entered,
        'best_rank': rating.best_rank or '—',
        'wins': submissions.filter(rank_in_contest=1).count(),
        'avg_percentile': submissions.aggregate(a=Avg('percentile'))['a'] or 0,
    }
    if rating.contests_entered:
        stats['win_rate'] = round((stats['wins'] / rating.contests_entered) * 100, 1)
    else:
        stats['win_rate'] = 0
    stats['avg_percentile'] = round(stats['avg_percentile'], 1)

    chart_data = [{
        'contest': h.contest.title[:30],
        'rating': h.new_rating,
        'change': h.change,
        'date': h.recorded_at.strftime('%Y-%m-%d'),
    } for h in history]

    # Activity calendar (last 52 weeks)
    from datetime import timedelta
    today = timezone.localdate()  # local calendar day - now().date() is the UTC date
    days = []
    activity_map = {}
    for s in submissions:
        if not s.submitted_at:
            continue
        d = s.submitted_at.date()
        score = 1
        if s.percentile is not None:
            if s.percentile <= 10 or s.rank_in_contest == 1:
                score = 4
            elif s.percentile <= 25:
                score = 3
            elif s.percentile <= 50:
                score = 2
        prev = activity_map.get(d, (0, None))
        if score > prev[0]:
            activity_map[d] = (score, s.contest.title)
    start = today - timedelta(days=7 * 52)
    cur = start
    while cur <= today:
        level, label = activity_map.get(cur, (0, None))
        days.append({
            'date': cur.isoformat(),
            'level': level,
            'label': label,
        })
        cur += timedelta(days=1)

    return render(request, 'core/profile_contests.html', {
        'rating': rating,
        'history': history,
        'chart_data_json': json.dumps(chart_data),
        'earned_badges': earned,
        'badge_list': badge_list,
        'submissions_page': page,
        'paginator': paginator,
        'stats': stats,
        'activity_days': days,
    })


@login_required
def coin_balance_api(request):
    from ..models import UserRating
    from django.http import JsonResponse
    rating, _ = UserRating.objects.get_or_create(user=request.user)
    return JsonResponse({
        'balance': rating.coin_balance,
        'rating': rating.rating,
        'rank_title': rating.rank_title['title'],
    })


@login_required
def check_badges_api(request):
    """POST: run the badge engine and return any newly awarded badges."""
    from ..services import badges as badge_svc
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    new_badges = badge_svc.check_and_award_badges(request.user)
    return JsonResponse({
        'ok': True,
        'new_badges': [
            {
                'name': b.name,
                'icon': b.icon,
                'rarity': b.rarity,
                'color_hex': b.color_hex,
                'description': b.description,
            }
            for b in new_badges
        ],
    })
