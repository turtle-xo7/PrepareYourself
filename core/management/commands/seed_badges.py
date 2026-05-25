"""Seed all PrepareYourself contest badges. Idempotent."""
from django.core.management.base import BaseCommand
from core.models import Badge


BADGES = [
    # Contest Performance
    {'name': 'First Step',         'badge_type': 'contest',   'rarity': 'common',
     'icon': 'bi-flag',            'color_hex': '#6c757d',
     'description': 'Participated in your first contest.',
     'earn_condition': 'Submit any contest.'},
    {'name': 'Bronze Contender',   'badge_type': 'contest',   'rarity': 'common',
     'icon': 'bi-award',           'color_hex': '#cd7f32',
     'description': 'Finished in the top 50% of a contest.',
     'earn_condition': 'Finish in the top 50% in any rated contest.'},
    {'name': 'Silver Challenger',  'badge_type': 'contest',   'rarity': 'rare',
     'icon': 'bi-award-fill',      'color_hex': '#c0c0c0',
     'description': 'Finished in the top 25% of a contest.',
     'earn_condition': 'Finish in the top 25% in any rated contest.'},
    {'name': 'Gold Champion',      'badge_type': 'contest',   'rarity': 'epic',
     'icon': 'bi-trophy',          'color_hex': '#ffd700',
     'description': 'Finished in the top 10% of a contest.',
     'earn_condition': 'Finish in the top 10% in any rated contest.'},
    {'name': 'Contest Winner',     'badge_type': 'contest',   'rarity': 'epic',
     'icon': 'bi-trophy-fill',     'color_hex': '#ff8c00',
     'description': 'Won a contest (rank #1).',
     'earn_condition': 'Reach rank 1 in any rated contest.'},
    {'name': 'Hat Trick',          'badge_type': 'contest',   'rarity': 'legendary',
     'icon': 'bi-stars',           'color_hex': '#ff0000',
     'description': 'Won 3 contests in total.',
     'earn_condition': 'Reach rank 1 in 3 contests.'},
    {'name': 'Perfect Score',      'badge_type': 'contest',   'rarity': 'epic',
     'icon': 'bi-patch-check',     'color_hex': '#28a745',
     'description': 'Achieved a perfect score in a contest.',
     'earn_condition': 'Score 100% of the available marks in a contest.'},

    # Streak
    {'name': 'Regular',            'badge_type': 'streak',    'rarity': 'common',
     'icon': 'bi-calendar-check',  'color_hex': '#17a2b8',
     'description': 'Participated in 3 contests in a row.',
     'earn_condition': 'Participate in 3 consecutive contests within 14 days of each other.'},
    {'name': 'Dedicated',          'badge_type': 'streak',    'rarity': 'rare',
     'icon': 'bi-calendar-week',   'color_hex': '#007bff',
     'description': '7-contest participation streak.',
     'earn_condition': 'Participate in 7 consecutive contests.'},
    {'name': 'Iron Will',          'badge_type': 'streak',    'rarity': 'epic',
     'icon': 'bi-fire',            'color_hex': '#fd7e14',
     'description': '15-contest streak — remarkable consistency.',
     'earn_condition': 'Participate in 15 consecutive contests.'},
    {'name': 'Unstoppable',        'badge_type': 'streak',    'rarity': 'legendary',
     'icon': 'bi-lightning-charge', 'color_hex': '#ffc107',
     'description': '30-contest streak — true devotion.',
     'earn_condition': 'Participate in 30 consecutive contests.'},

    # Milestone
    {'name': 'Curious',            'badge_type': 'milestone', 'rarity': 'common',
     'icon': 'bi-search',          'color_hex': '#6c757d',
     'description': 'Joined 5 contests.',
     'earn_condition': 'Submit 5 contests.'},
    {'name': 'Active',             'badge_type': 'milestone', 'rarity': 'rare',
     'icon': 'bi-bar-chart',       'color_hex': '#17a2b8',
     'description': 'Joined 20 contests.',
     'earn_condition': 'Submit 20 contests.'},
    {'name': 'Veteran',            'badge_type': 'milestone', 'rarity': 'epic',
     'icon': 'bi-shield-check',    'color_hex': '#6610f2',
     'description': 'Joined 50 contests.',
     'earn_condition': 'Submit 50 contests.'},
    {'name': 'Legend',             'badge_type': 'milestone', 'rarity': 'legendary',
     'icon': 'bi-gem',             'color_hex': '#e83e8c',
     'description': 'Joined 100 contests — Hall of Fame material.',
     'earn_condition': 'Submit 100 contests.'},

    # Rank tier
    {'name': 'Skilled',            'badge_type': 'rank',      'rarity': 'common',
     'icon': 'bi-star',            'color_hex': '#008080',
     'description': 'Reached 1000 rating.',
     'earn_condition': 'Reach a rating of 1000.'},
    {'name': 'Expert',             'badge_type': 'rank',      'rarity': 'rare',
     'icon': 'bi-star-fill',       'color_hex': '#0000ff',
     'description': 'Reached 1200 rating.',
     'earn_condition': 'Reach a rating of 1200.'},
    {'name': 'Master',             'badge_type': 'rank',      'rarity': 'epic',
     'icon': 'bi-stars',           'color_hex': '#aa00aa',
     'description': 'Reached 1400 rating.',
     'earn_condition': 'Reach a rating of 1400.'},
    {'name': 'Grandmaster',        'badge_type': 'rank',      'rarity': 'legendary',
     'icon': 'bi-trophy',          'color_hex': '#ff8c00',
     'description': 'Reached 1600 rating.',
     'earn_condition': 'Reach a rating of 1600.'},
    {'name': 'Legend (Rank)',      'badge_type': 'rank',      'rarity': 'legendary',
     'icon': 'bi-trophy-fill',     'color_hex': '#ff0000',
     'description': 'Reached 1800 rating — legendary tier.',
     'earn_condition': 'Reach a rating of 1800.'},

    # Subject mastery
    {'name': 'Physics Pro',        'badge_type': 'subject',   'rarity': 'rare',
     'icon': 'bi-magnet',          'color_hex': '#dc3545',
     'description': 'Won a Physics contest.',
     'earn_condition': 'Reach rank 1 in a Physics-subject contest.'},
    {'name': 'Math Wizard',        'badge_type': 'subject',   'rarity': 'rare',
     'icon': 'bi-calculator',      'color_hex': '#007bff',
     'description': 'Won a Math contest.',
     'earn_condition': 'Reach rank 1 in a Math-subject contest.'},
    {'name': 'Chemistry Expert',   'badge_type': 'subject',   'rarity': 'rare',
     'icon': 'bi-eyedropper',      'color_hex': '#28a745',
     'description': 'Won a Chemistry contest.',
     'earn_condition': 'Reach rank 1 in a Chemistry-subject contest.'},
    {'name': 'Biology Star',       'badge_type': 'subject',   'rarity': 'rare',
     'icon': 'bi-tree',            'color_hex': '#20c997',
     'description': 'Won a Biology contest.',
     'earn_condition': 'Reach rank 1 in a Biology-subject contest.'},
    {'name': 'All-Rounder',        'badge_type': 'subject',   'rarity': 'legendary',
     'icon': 'bi-globe',           'color_hex': '#e83e8c',
     'description': 'Won contests in 4 different subjects.',
     'earn_condition': 'Reach rank 1 in 4 different subjects.'},

    # Special / Event
    {'name': 'Early Bird',         'badge_type': 'early',     'rarity': 'common',
     'icon': 'bi-sunrise',         'color_hex': '#ffc107',
     'description': 'Registered within 1 hour of a contest announcement.',
     'earn_condition': 'Register for a contest within 1 hour of its creation.'},
    {'name': 'Night Owl',          'badge_type': 'special',   'rarity': 'common',
     'icon': 'bi-moon-stars',      'color_hex': '#6f42c1',
     'description': 'Submitted a contest answer after 11 PM.',
     'earn_condition': 'Submit a contest after 23:00 local time.'},
    {'name': 'Speed Demon',        'badge_type': 'special',   'rarity': 'epic',
     'icon': 'bi-speedometer2',    'color_hex': '#fd7e14',
     'description': 'Top 10% finish with 10+ min remaining on the clock.',
     'earn_condition': 'Finish in top 10% with more than 10 minutes left.'},
    {'name': 'Comeback Kid',       'badge_type': 'special',   'rarity': 'rare',
     'icon': 'bi-arrow-up-circle', 'color_hex': '#20c997',
     'description': 'Dropped below 800 rating and climbed back to 1000+.',
     'earn_condition': 'Recover from rating below 800 back to 1000.'},
    {'name': 'SSC Champion',       'badge_type': 'special',   'rarity': 'epic',
     'icon': 'bi-mortarboard',     'color_hex': '#007bff',
     'description': 'Won an SSC-tagged contest.',
     'earn_condition': 'Reach rank 1 in any contest tagged "ssc".'},
    {'name': 'HSC Champion',       'badge_type': 'special',   'rarity': 'epic',
     'icon': 'bi-mortarboard-fill', 'color_hex': '#6f42c1',
     'description': 'Won an HSC-tagged contest.',
     'earn_condition': 'Reach rank 1 in any contest tagged "hsc".'},
    {'name': 'Virtual Veteran',    'badge_type': 'special',   'rarity': 'epic',
     'icon': 'bi-play-circle',     'color_hex': '#17a2b8',
     'description': 'Completed 10 virtual contests.',
     'earn_condition': 'Finish 10 virtual contests.'},
]


class Command(BaseCommand):
    help = 'Seed all PrepareYourself contest badges (idempotent).'

    def handle(self, *args, **opts):
        created, skipped = 0, 0
        for spec in BADGES:
            obj, was_created = Badge.objects.get_or_create(
                name=spec['name'],
                defaults=spec,
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  + {obj.name}'))
            else:
                changed = False
                for key, val in spec.items():
                    if getattr(obj, key) != val and key != 'name':
                        setattr(obj, key, val)
                        changed = True
                if changed:
                    obj.save()
                skipped += 1
        self.stdout.write(self.style.SUCCESS(
            f'Done. Created: {created}, existing: {skipped}, total: {Badge.objects.count()}'
        ))
