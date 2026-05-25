"""Contest rating algorithm — Elo-inspired, adapted from Codeforces."""
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from ..models import (
    Contest, ContestSubmission, ContestRatingHistory, UserRating,
)


MIN_RATING = 600


def _interp(p, p_low, p_high, v_low, v_high):
    """Linear interpolation: at p_low get v_low, at p_high get v_high."""
    if p_high == p_low:
        return v_low
    t = (p - p_low) / (p_high - p_low)
    return v_low + (v_high - v_low) * t


def _rating_change(rank, total):
    """Compute rating change based on rank in contest of `total` participants.

    Returns integer delta (can be negative).
    """
    if total <= 0:
        return 0
    if rank == 1:
        return 150
    percentile = rank / total
    if percentile <= 0.05:
        delta = _interp(percentile, 0.0, 0.05, 100, 80)
    elif percentile <= 0.10:
        delta = _interp(percentile, 0.05, 0.10, 80, 50)
    elif percentile <= 0.25:
        delta = _interp(percentile, 0.10, 0.25, 50, 20)
    elif percentile <= 0.50:
        delta = _interp(percentile, 0.25, 0.50, 20, 5)
    elif percentile <= 0.75:
        delta = _interp(percentile, 0.50, 0.75, 5, -5)
    else:
        delta = _interp(percentile, 0.75, 1.0, -5, -30)
    return int(round(delta))


@transaction.atomic
def calculate_contest_ratings(contest_id, force=False):
    """Compute and persist rating changes for a finished contest.

    Idempotent unless force=True.
    Returns summary dict.
    """
    from . import coins as coin_svc
    from . import badges as badge_svc

    contest = Contest.objects.get(pk=contest_id)
    if contest.ratings_calculated and not force:
        return {'status': 'already_calculated', 'contest': contest.title}

    subs = list(
        ContestSubmission.objects.filter(
            contest=contest, is_submitted=True, is_virtual=False,
            student__profile__role='STUDENT',
        ).select_related('student').order_by('-total_marks', 'duration_taken')
    )

    rated_subs = [s for s in subs if s.is_rated_participant and contest.is_rated]
    total_rated = len(rated_subs)
    total_all = len(subs)

    summary = {
        'contest': contest.title,
        'total_participants': total_all,
        'rated_participants': total_rated,
        'changes': [],
        'badges_awarded': [],
        'coins_awarded': [],
    }

    today = timezone.now().date()

    for idx, sub in enumerate(subs):
        rank = idx + 1
        percentile_pct = round((rank / total_all) * 100, 2) if total_all else 0

        sub.rank_in_contest = rank
        sub.percentile = percentile_pct
        if sub.time_taken_seconds is None:
            sub.time_taken_seconds = sub.duration_taken

        rating_profile, _ = UserRating.objects.get_or_create(user=sub.student)

        rating_profile.contests_entered += 1
        if rating_profile.best_rank is None or rank < rating_profile.best_rank:
            rating_profile.best_rank = rank
        rating_profile.total_score_earned += sub.total_marks

        if (rating_profile.last_contest_date
                and (today - rating_profile.last_contest_date) <= timedelta(days=14)):
            rating_profile.current_streak += 1
        else:
            rating_profile.current_streak = 1
        if rating_profile.current_streak > rating_profile.longest_streak:
            rating_profile.longest_streak = rating_profile.current_streak
        rating_profile.last_contest_date = today

        if sub.is_rated_participant and contest.is_rated:
            rating_profile.contests_rated += 1
            old = rating_profile.rating
            sub.rating_before = old

            rated_rank = next(
                (i + 1 for i, r in enumerate(rated_subs) if r.pk == sub.pk),
                rank,
            )
            change = _rating_change(rated_rank, total_rated)

            if rating_profile.contests_rated <= 5:
                change = int(round(change * 1.5))

            new_rating = max(MIN_RATING, old + change)
            actual_change = new_rating - old
            rating_profile.rating = new_rating
            if new_rating > rating_profile.peak_rating:
                rating_profile.peak_rating = new_rating

            sub.rating_after = new_rating
            sub.rating_change = actual_change

            ContestRatingHistory.objects.create(
                user=sub.student, contest=contest,
                old_rating=old, new_rating=new_rating, change=actual_change,
                rank=rated_rank, percentile=percentile_pct,
            )
            summary['changes'].append({
                'user': sub.student.username,
                'old': old, 'new': new_rating, 'change': actual_change,
                'rank': rated_rank,
            })

        rating_profile.save()
        sub.save()

        awarded = coin_svc.award_for_finish(
            sub.student, contest, percentile_pct, rank,
        )
        summary['coins_awarded'].append({'user': sub.student.username, 'awards': awarded})

        new_badges = badge_svc.check_and_award_badges(sub.student, contest=contest)
        if new_badges:
            summary['badges_awarded'].append({
                'user': sub.student.username,
                'badges': [b.name for b in new_badges],
            })

    contest.ratings_calculated = True
    contest.save(update_fields=['ratings_calculated'])
    summary['status'] = 'ok'
    return summary
