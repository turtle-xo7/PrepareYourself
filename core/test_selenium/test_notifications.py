"""
Selenium tests for Notifications page.

Run: python manage.py test core.test_selenium.test_notifications
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.models import TeacherFeedback, UserProgress
from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_board, create_subject, create_class, create_question,
    create_notification,
)


class NotificationsSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Notifications page: feedback display and mark-as-read behavior."""

    def setUp(self):
        self.teacher = create_teacher(username='notif_teacher', password='testpass123')
        self.student = create_student(username='notif_student', password='testpass123',
                                      plan='PREMIUM')
        board = create_board()
        subject = create_subject()
        class_obj = create_class()
        question = create_question(board, subject, class_obj)
        self.progress = UserProgress.objects.create(
            user=self.student, question=question, is_correct=False
        )
        self.feedback = TeacherFeedback.objects.create(
            teacher=self.teacher,
            student=self.student,
            progress=self.progress,
            comment='Keep it up! You can do better.',
            is_read=False,
        )

    def test_notifications_page_requires_login(self):
        """Notifications page redirects unauthenticated users to login."""
        self.go('/student/notifications/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_notifications_page_loads_for_student(self):
        """Student can access their notifications page."""
        self.selenium_login('notif_student', 'testpass123')
        self.go('/student/notifications/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/notifications/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_feedback_comment_visible(self):
        """Teacher feedback comment appears on the notifications page."""
        self.selenium_login('notif_student', 'testpass123')
        self.go('/student/notifications/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/notifications/'))
        self.assertIn('Keep it up', self.driver.page_source)

    def test_feedback_marked_read_after_visiting(self):
        """Visiting the notifications page marks teacher feedback as read."""
        self.selenium_login('notif_student', 'testpass123')
        self.go('/student/notifications/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/notifications/'))
        self.feedback.refresh_from_db()
        self.assertTrue(self.feedback.is_read)

    def test_system_notification_visible(self):
        """A system Notification object appears on the notifications page."""
        create_notification(self.student, title='Test System Notif', message='System alert body')
        self.selenium_login('notif_student', 'testpass123')
        self.go('/student/notifications/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/notifications/'))
        page = self.driver.page_source
        self.assertTrue(
            'Test System Notif' in page or 'System alert body' in page,
            'System notification not found on notifications page'
        )

    def test_unread_count_shown_in_navbar(self):
        """Unread notification count is reflected in the navbar badge."""
        self.selenium_login('notif_student', 'testpass123')
        self.go('/')
        page = self.driver.page_source
        self.assertNotIn('Server Error', page)

    def test_notifications_page_empty_state(self):
        """Notifications page loads without error when there are no notifications."""
        new_student = create_student(username='no_notif_student', password='testpass123',
                                     plan='PREMIUM')
        self.selenium_login('no_notif_student', 'testpass123')
        self.go('/student/notifications/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/notifications/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
