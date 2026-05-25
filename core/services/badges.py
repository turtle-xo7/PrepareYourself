"""Badge awarding engine — checks all earnable badges for a user."""
from django.db import transaction
from django.db.models import Count, Q

from ..models import (
    Badge, UserBadge, UserRating, ContestSubmission, Contest,
    ContestRatingHistory, VirtualContest,
)


RANK_TIERS = [
    (1000, "Skilled"),
    (1200, "Expert"),
    (1400, "Master"),
    (1600, "Grandmaster"),
    (1800, "Legend (Rank)"),
]


def _award(user, badge_name, contest=None):
    try:
        badge = Badge.objects.get(name=badge_name)
    except Badge.DoesNotExist:
        return None
    user_badge, created = UserBadge.objects.get_or_create(
        user=user, badge=badge, defaults={'contest': contest},
    )
    if created:
        badge.earned_by_count = badge.earned_by_count + 1
        badge.save(update_fields=['earned_by_count'])
        from . import coins as coin_svc
        rarity_action = f'badge_earned_{badge.rarity}'
        coin_svc.award_coins(
            user, rarity_action, contest=contest,
            note=f'Badge earned: {badge.name}',
        )
        return badge
    return None


@transaction.atomic
def check_and_award_badges(user, contest=None):
    """Re-check every badge condition for `user`.

    Returns list of newly awarded Badge objects.
    """
    newly = []
    rating, _ = UserRating.objects.get_or_create(user=user)

    submissions = ContestSubmission.objects.filter(
        student=user, is_submitted=True, is_virtual=False,
    ).select_related('contest', 'contest__subject')

    sub_count = submissions.count()

    # ---- Contest performance ----
    if sub_count >= 1:
        b = _award(user, 'First Step', contest=contest); b and newly.append(b)

    # use latest finish for tier badges
    if contest is not None:
        last = submissions.filter(contest=contest).first()
        if last and last.percentile is not None:
            if last.percentile <= 50:
                b = _award(user, 'Bronze Contender', contest=contest); b and newly.append(b)
            if last.percentile <= 25:
                b = _award(user, 'Silver Challenger', contest=contest); b and newly.append(b)
            if last.percentile <= 10:
                b = _award(user, 'Gold Champion', contest=contest); b and newly.append(b)
            if last.rank_in_contest == 1:
                b = _award(user, 'Contest Winner', contest=contest); b and newly.append(b)

    # Perfect score in any contest
    for sub in submissions:
        max_marks = sub.contest.questions.aggregate(
            total=Count('id')
        )['total']  # placeholder — recompute below
    perfect_in_any = False
    for sub in submissions.select_related('contest'):
        from django.db.models import Sum
        max_marks = sub.contest.questions.aggregate(t=Sum('marks'))['t'] or 0
        if max_marks > 0 and sub.total_marks >= max_marks:
            perfect_in_any = True
            break
    if perfect_in_any:
        b = _award(user, 'Perfect Score', contest=contest); b and newly.append(b)

    # Hat Trick - 3 wins
    wins = submissions.filter(rank_in_contest=1).count()
    if wins >= 3:
        b = _award(user, 'Hat Trick', contest=contest); b and newly.append(b)

    # ---- Streak badges (consecutive contests) ----
    streak = rating.current_streak
    if streak >= 3:
        b = _award(user, 'Regular', contest=contest); b and newly.append(b)
    if streak >= 7:
        b = _award(user, 'Dedicated', contest=contest); b and newly.append(b)
    if streak >= 15:
        b = _award(user, 'Iron Will', contest=contest); b and newly.append(b)
    if streak >= 30:
        b = _award(user, 'Unstoppable', contest=contest); b and newly.append(b)

    # ---- Milestone ----
    if sub_count >= 5:
        b = _award(user, 'Curious', contest=contest); b and newly.append(b)
    if sub_count >= 20:
        b = _award(user, 'Active', contest=contest); b and newly.append(b)
    if sub_count >= 50:
        b = _award(user, 'Veteran', contest=contest); b and newly.append(b)
    if sub_count >= 100:
        b = _award(user, 'Legend', contest=contest); b and newly.append(b)

    # ---- Rank tier ----
    for threshold, title in RANK_TIERS:
        if rating.peak_rating >= threshold:
            b = _award(user, title, contest=contest); b and newly.append(b)

    # ---- Subject mastery (wins per subject) ----
    win_subjects = submissions.filter(rank_in_contest=1).values_list(
        'contest__subject__name', flat=True,
    )
    win_subject_set = set(s.lower() for s in win_subjects if s)
    subject_to_badge = {
        'physics':   'Physics Pro',
        'math':      'Math Wizard',
        'mathematics': 'Math Wizard',
        'chemistry': 'Chemistry Expert',
        'biology':   'Biology Star',
    }
    for keyword, badge_name in subject_to_badge.items():
        if any(keyword in s for s in win_subject_set):
            b = _award(user, badge_name, contest=contest); b and newly.append(b)
    if len(win_subject_set) >= 4:
        b = _award(user, 'All-Rounder', contest=contest); b and newly.append(b)

    # ---- Special ----
    if contest is not None:
        last = submissions.filter(contest=contest).first()
        if last and last.percentile is not None and last.percentile <= 10:
            if last.time_taken_seconds and contest.duration_minutes:
                remaining = (contest.duration_minutes * 60) - last.time_taken_seconds
                if remaining > 600:
                    b = _award(user, 'Speed Demon', contest=contest); b and newly.append(b)

    # Virtual veteran
    if VirtualContest.objects.filter(user=user, finished_at__isnull=False).count() >= 10:
        b = _award(user, 'Virtual Veteran', contest=contest); b and newly.append(b)

    # Comeback Kid: dropped below 800 then back to 1000+
    history = ContestRatingHistory.objects.filter(user=user).order_by('recorded_at')
    saw_low = False
    for h in history:
        if h.new_rating < 800:
            saw_low = True
        if saw_low and h.new_rating >= 1000:
            b = _award(user, 'Comeback Kid', contest=contest); b and newly.append(b)
            break

    return [b for b in newly if b is not None]


def award_early_bird(user, contest):
    """Called at registration if user registered within 1h of contest creation."""
    from . import coins as coin_svc
    coin_svc.award_coins(user, 'early_bird', contest=contest,
                         note='Early bird registration')
    b = _award(user, 'Early Bird', contest=contest)
    return b
