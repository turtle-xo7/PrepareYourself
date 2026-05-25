"""Calculate rating changes for a finished contest."""
from django.core.management.base import BaseCommand, CommandError
from core.models import Contest
from core.services.rating import calculate_contest_ratings


class Command(BaseCommand):
    help = 'Calculate ratings, award coins and badges for a finished contest.'

    def add_arguments(self, parser):
        parser.add_argument('--contest_id', type=int, required=True)
        parser.add_argument('--force', action='store_true',
                            help='Recalculate even if already done.')

    def handle(self, *args, **opts):
        cid = opts['contest_id']
        try:
            Contest.objects.get(pk=cid)
        except Contest.DoesNotExist:
            raise CommandError(f'Contest {cid} not found.')
        summary = calculate_contest_ratings(cid, force=opts['force'])
        if summary.get('status') == 'already_calculated':
            self.stdout.write(self.style.WARNING(
                f"Already calculated for contest #{cid}. Pass --force to redo."
            ))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Contest: {summary['contest']}"
        ))
        self.stdout.write(f"Participants: {summary['total_participants']} "
                          f"(rated: {summary['rated_participants']})")
        for c in summary['changes'][:20]:
            arrow = '+' if c['change'] >= 0 else ''
            self.stdout.write(f"  #{c['rank']:>3}  {c['user']:<20}  "
                              f"{c['old']} -> {c['new']} ({arrow}{c['change']})")
        if len(summary['changes']) > 20:
            self.stdout.write(f"  ... and {len(summary['changes']) - 20} more")
        if summary['badges_awarded']:
            self.stdout.write(self.style.SUCCESS('\nBadges awarded:'))
            for ba in summary['badges_awarded']:
                self.stdout.write(f"  {ba['user']}: {', '.join(ba['badges'])}")
