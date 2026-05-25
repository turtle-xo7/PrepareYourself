"""LeetCode-style daily check-in: award coins to users who logged in today."""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import UserRating
from core.services.coins import award_coins


class Command(BaseCommand):
    help = 'Award daily check-in coins + streak bonuses for active users.'

    def handle(self, *args, **opts):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        cutoff = timezone.now() - timedelta(hours=24)
        active_users = User.objects.filter(last_login__gte=cutoff)

        awarded = 0
        streak_bonuses = 0

        for user in active_users:
            rating, _ = UserRating.objects.get_or_create(user=user)
            if rating.last_checkin_date == today:
                continue
            if rating.last_checkin_date == yesterday:
                rating.checkin_streak += 1
            else:
                rating.checkin_streak = 1
            rating.last_checkin_date = today
            rating.save(update_fields=['last_checkin_date', 'checkin_streak'])

            award_coins(user, 'daily_checkin', note=f'Day {rating.checkin_streak}')
            awarded += 1

            if rating.checkin_streak > 0 and rating.checkin_streak % 30 == 0:
                award_coins(user, 'streak_30',
                            note=f'{rating.checkin_streak}-day streak')
                streak_bonuses += 1
            elif rating.checkin_streak > 0 and rating.checkin_streak % 7 == 0:
                award_coins(user, 'streak_7',
                            note=f'{rating.checkin_streak}-day streak')
                streak_bonuses += 1

        self.stdout.write(self.style.SUCCESS(
            f'Daily check-in: {awarded} users credited, '
            f'{streak_bonuses} streak bonuses awarded.'
        ))
