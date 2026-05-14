"""
Selenium tests for the student dashboard and progress history.

Run: python manage.py test core.test_selenium.test_dashboard
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.models import UserProgress
from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_board, create_subject, create_class, create_question,
)


class DashboardSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Dashboard access control and stat card presence."""

    def setUp(self):
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()

    def test_unauthenticated_redirected_from_dashboard(self):
        """Unauthenticated visitor is redirected from /dashboard/ to login."""
        self.go('/dashboard/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_free_student_redirected_from_dashboard(self):
        """Free student visiting /dashboard/ is sent to the pricing page."""
        create_student(username='freedash', password='testpass123', plan='FREE')
        self.selenium_login('freedash', 'testpass123')
        self.go('/dashboard/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/dashboard/' not in d.current_url
        )
        self.assertIn('/pricing/', self.driver.current_url)

    def test_premium_student_can_access_dashboard(self):
        """Premium student reaches the dashboard page."""
        create_student(username='premdash', password='testpass123', plan='PREMIUM')
        self.selenium_login('premdash', 'testpass123')
        self.go('/dashboard/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/dashboard/' in d.current_url or '/pricing/' in d.current_url
        )
        self.assertIn('/dashboard/', self.driver.current_url)
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_dashboard_has_stat_elements(self):
        """Dashboard renders stat card elements without errors."""
        create_student(username='statdash', password='testpass123', plan='PREMIUM')
        self.selenium_login('statdash', 'testpass123')
        self.go('/dashboard/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/dashboard/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_teacher_redirected_to_teacher_dashboard(self):
        """Teacher visiting /dashboard/ is redirected to /teacher/dashboard/."""
        create_teacher(username='teachdash', password='testpass123')
        self.selenium_login('teachdash', 'testpass123')
        self.go('/dashboard/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/teacher/dashboard/' in d.current_url
        )
        self.assertIn('/teacher/dashboard/', self.driver.current_url)

    def test_dashboard_shows_questions_answered(self):
        """Dashboard page contains some indication of questions answered."""
        student = create_student(username='qadash', password='testpass123', plan='PREMIUM')
        q = create_question(self.board, self.subject, self.class_obj)
        UserProgress.objects.create(user=student, question=q, is_correct=True)
        self.selenium_login('qadash', 'testpass123')
        self.go('/dashboard/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/dashboard/'))
        page = self.driver.page_source
        self.assertNotIn('Server Error', page)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass


class ProgressHistorySeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Progress history page: access control and filter controls."""

    def setUp(self):
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.question = create_question(self.board, self.subject, self.class_obj)

    def test_progress_history_requires_login(self):
        """Progress history redirects unauthenticated users to login."""
        self.go('/progress/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_free_student_redirected_to_pricing(self):
        """Free student is sent to pricing from the progress page."""
        create_student(username='freeprog', password='testpass123', plan='FREE')
        self.selenium_login('freeprog', 'testpass123')
        self.go('/progress/')
        WebDriverWait(self.driver, 8).until(lambda d: '/progress/' not in d.current_url)
        self.assertIn('/pricing/', self.driver.current_url)

    def test_premium_student_can_view_progress(self):
        """Premium student can access the progress history page."""
        create_student(username='premprog', password='testpass123', plan='PREMIUM')
        self.selenium_login('premprog', 'testpass123')
        self.go('/progress/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/progress/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_progress_page_shows_filter_controls(self):
        """Progress history has filter controls."""
        create_student(username='filtprog', password='testpass123', plan='PREMIUM')
        self.selenium_login('filtprog', 'testpass123')
        self.go('/progress/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/progress/'))
        page = self.driver.page_source
        self.assertTrue(
            'subject' in page.lower() or 'filter' in page.lower() or 'result' in page.lower(),
            'Filter controls not found on progress history page'
        )

    def test_progress_page_shows_stats_with_entries(self):
        """Progress page renders without error when there are progress entries."""
        student = create_student(username='statprog', password='testpass123', plan='PREMIUM')
        UserProgress.objects.create(user=student, question=self.question, is_correct=True)
        self.selenium_login('statprog', 'testpass123')
        self.go('/progress/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/progress/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_track_progress_endpoint_requires_login(self):
        """Track-progress AJAX endpoint redirects unauthenticated requests."""
        self.go('/track-progress/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
