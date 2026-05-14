"""
Selenium tests for the Superadmin Dashboard.

Run: python manage.py test core.test_selenium.test_superadmin
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import SeleniumMixin, create_student, create_teacher, create_superadmin


class SuperAdminSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Superadmin dashboard: access control, user list, and export button."""

    def setUp(self):
        self.superadmin = create_superadmin(username='sadmin', password='testpass123')
        self.student = create_student(username='sa_student', password='testpass123', plan='FREE')

    def test_unauthenticated_redirected_from_superadmin(self):
        """Unauthenticated visitor is redirected from /superadmin/."""
        self.go('/superadmin/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_student_cannot_access_superadmin_dashboard(self):
        """Regular student is blocked from the superadmin dashboard."""
        self.selenium_login('sa_student', 'testpass123')
        self.go('/superadmin/')
        WebDriverWait(self.driver, 8).until(lambda d: '/superadmin/' not in d.current_url)
        self.assertNotIn('/superadmin/', self.driver.current_url)

    def test_teacher_cannot_access_superadmin_dashboard(self):
        """Regular teacher (non-superadmin ADMIN) cannot access superadmin dashboard."""
        create_teacher(username='sa_teacher', password='testpass123')
        self.selenium_login('sa_teacher', 'testpass123')
        self.go('/superadmin/')
        WebDriverWait(self.driver, 8).until(lambda d: '/superadmin/' not in d.current_url)
        self.assertNotIn('/superadmin/', self.driver.current_url)

    def test_superadmin_dashboard_loads(self):
        """Superadmin can view their dashboard."""
        self.selenium_login('sadmin', 'testpass123')
        self.go('/superadmin/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/superadmin/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_superadmin_dashboard_shows_user_stats(self):
        """Superadmin dashboard contains user count statistics."""
        self.selenium_login('sadmin', 'testpass123')
        self.go('/superadmin/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/superadmin/'))
        page = self.driver.page_source
        self.assertTrue(
            'student' in page.lower() or 'user' in page.lower() or 'teacher' in page.lower(),
            'User statistics not found on superadmin dashboard'
        )

    def test_superadmin_dashboard_shows_registered_student(self):
        """The student created in setUp appears in the superadmin user table."""
        self.selenium_login('sadmin', 'testpass123')
        self.go('/superadmin/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/superadmin/'))
        self.assertIn('sa_student', self.driver.page_source)

    def test_export_button_present(self):
        """Superadmin dashboard has an Excel export link."""
        self.selenium_login('sadmin', 'testpass123')
        self.go('/superadmin/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/superadmin/'))
        export_elements = self.driver.find_elements(
            By.CSS_SELECTOR, 'a[href*="export"], button[data-export]'
        )
        self.assertTrue(
            len(export_elements) > 0 or 'export' in self.driver.page_source.lower(),
            'Export button not found on superadmin dashboard'
        )

    def test_superadmin_can_see_manage_link(self):
        """Superadmin has a link to the manage panel."""
        self.selenium_login('sadmin', 'testpass123')
        self.go('/superadmin/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/superadmin/'))
        page = self.driver.page_source
        self.assertTrue(
            '/manage/' in page or 'manage' in page.lower(),
            'Manage panel link not found on superadmin dashboard'
        )

    def test_export_excel_requires_superadmin(self):
        """Export Excel endpoint is protected from regular students."""
        self.selenium_login('sa_student', 'testpass123')
        self.go('/superadmin/export/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/superadmin/export/' not in d.current_url
        )
        self.assertNotIn('/superadmin/export/', self.driver.current_url)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
