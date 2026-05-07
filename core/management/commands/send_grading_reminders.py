from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User
from core.models import ExamAttempt


class Command(BaseCommand):
    help = 'CQ submission ২৪ ঘণ্টার বেশি পুরনো হলে staff-দের reminder email পাঠায়'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        overdue = ExamAttempt.objects.filter(
            status='CQ_PENDING',
            cq_submitted_at__lt=cutoff,
        ).select_related('student', 'exam_paper')

        if not overdue.exists():
            self.stdout.write(self.style.SUCCESS('No overdue CQ submissions found.'))
            return

        staff_emails = list(
            User.objects.filter(is_staff=True).exclude(email='').values_list('email', flat=True)
        )

        if not staff_emails:
            self.stdout.write(self.style.WARNING('No staff email addresses found.'))
            return

        lines = [
            f'- {a.student.username}: {a.exam_paper.title} '
            f'(জমা: {a.cq_submitted_at.strftime("%d-%m-%Y %H:%M")})'
            for a in overdue
        ]
        body = (
            f'নিচের {overdue.count()}টি CQ submission ২৪ ঘণ্টার বেশি সময় ধরে মূল্যায়নের অপেক্ষায়:\n\n'
            + '\n'.join(lines)
            + '\n\nঅনুগ্রহ করে grade করুন: /manage/grade-queue/'
        )

        send_mail(
            subject=f'[PrepareYourself] {overdue.count()}টি CQ Grading এখনো বাকি',
            message=body,
            from_email='prepareyourselfsupport20226@gmail.com',
            recipient_list=staff_emails,
            fail_silently=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Notified {len(staff_emails)} staff about {overdue.count()} overdue CQ submission(s).'
            )
        )
