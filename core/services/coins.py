"""PrepCoin economy — LeetCoin-inspired earn/spend ledger."""
from django.db import transaction
from ..models import UserRating, ContestCoinLedger


RATES = {
    'contest_participate':    5,
    'contest_top50pct':       15,
    'contest_top25pct':       30,
    'contest_top10pct':       75,
    'contest_win':            150,
    'daily_checkin':          1,
    'streak_7':               10,
    'streak_30':              50,
    'badge_earned_common':    10,
    'badge_earned_rare':      25,
    'badge_earned_epic':      50,
    'badge_earned_legendary': 100,
    'first_contest':          100,
    'early_bird':             10,
    'virtual_complete':       5,
}


def _ensure_rating(user):
    rating, _ = UserRating.objects.get_or_create(user=user)
    return rating


@transaction.atomic
def award_coins(user, action, contest=None, note='', amount=None):
    """Award coins for an action. Creates a ContestCoinLedger row.

    Returns (coins_awarded, new_balance).
    """
    rating = _ensure_rating(user)
    if amount is None:
        amount = RATES.get(action, 0)
    if amount == 0:
        return 0, rating.coin_balance

    rating.coin_balance = rating.coin_balance + amount
    rating.save(update_fields=['coin_balance'])

    ledger_action = action
    if action.startswith('badge_earned_'):
        ledger_action = 'badge_earned'

    ContestCoinLedger.objects.create(
        user=user,
        action=ledger_action,
        amount=amount,
        balance=rating.coin_balance,
        contest=contest,
        note=note,
    )
    return amount, rating.coin_balance


def get_balance(user):
    rating, _ = UserRating.objects.get_or_create(user=user)
    return rating.coin_balance


def award_for_finish(user, contest, percentile, rank):
    """Award participation + tier coins based on contest result.

    percentile: 0-100 (lower = better).
    rank: 1-based rank.
    """
    awarded = []
    a, _ = award_coins(user, 'contest_participate', contest=contest,
                       note=f'Participated in {contest.title}')
    awarded.append(('contest_participate', a))

    if rank == 1:
        a, _ = award_coins(user, 'contest_win', contest=contest,
                           note=f'Won {contest.title}')
        awarded.append(('contest_win', a))
    elif percentile <= 10:
        a, _ = award_coins(user, 'contest_top10pct', contest=contest)
        awarded.append(('contest_top10pct', a))
    elif percentile <= 25:
        a, _ = award_coins(user, 'contest_top25pct', contest=contest)
        awarded.append(('contest_top25pct', a))
    elif percentile <= 50:
        a, _ = award_coins(user, 'contest_top50pct', contest=contest)
        awarded.append(('contest_top50pct', a))

    return awarded
