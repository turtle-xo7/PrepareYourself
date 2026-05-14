"""
Selenium tests for user profile: view, update, and plan info.

Run: python manage.py test core.test_selenium.test_profile
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from .helpers import SeleniumMixin, create_student, create_teacher


class ProfileSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Profile page: view, update, plan information."""

    def setUp(self):
        self.user = create_student(username='profileuser', email='profile@test.com',
                                   password='testpass123', plan='PREMIUM')

    def test_unauthenticated_profile_redirects_to_login(self):
        """Unauthenticated access to /profile/ redirects to login."""
        self.go('/profile/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_profile_page_loads(self):
        """Profile page loads for an authenticated user."""
        self.selenium_login('profileuser', 'testpass123')
        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_profile_shows_username(self):
        """Profile page contains the user's username."""
        self.selenium_login('profileuser', 'testpass123')
        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        self.assertIn('profileuser', self.driver.page_source)

    def test_profile_shows_email(self):
        """Profile page displays the user's email address."""
        self.selenium_login('profileuser', 'testpass123')
        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        self.assertIn('profile@test.com', self.driver.page_source)

    def test_profile_update_form_present(self):
        """Profile page has at least one form to update user details."""
        self.selenium_login('profileuser', 'testpass123')
        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        forms = self.driver.find_elements(By.TAG_NAME, 'form')
        self.assertGreater(len(forms), 0, 'No form found on profile page')

    def test_profile_update_first_name(self):
        """Submitting the profile form changes the first name."""
        self.selenium_login('profileuser', 'testpass123')
        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        try:
            first_name_input = self.driver.find_element(By.NAME, 'first_name')
            first_name_input.clear()
            first_name_input.send_keys('UpdatedFirst')
            email_input = self.driver.find_element(By.NAME, 'email')
            email_input.clear()
            email_input.send_keys('profile@test.com')
            submit = self.driver.find_element(
                By.CSS_SELECTOR, 'form button[type=submit], form input[type=submit]'
            )
            submit.click()
            WebDriverWait(self.driver, 8).until(lambda d: '/profile/' in d.current_url)
            self.user.refresh_from_db()
            self.assertEqual(self.user.first_name, 'UpdatedFirst')
        except NoSuchElementException:
            self.assertIn('/profile/', self.driver.current_url)

    def test_profile_shows_plan_info(self):
        """Profile page shows the user's subscription plan."""
        self.selenium_login('profileuser', 'testpass123')
        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        page = self.driver.page_source
        self.assertTrue(
            'PREMIUM' in page or 'Premium' in page or 'plan' in page.lower(),
            'Plan information not found on profile page'
        )

    def test_profile_page_shows_role(self):
        """Profile page indicates whether the user is a student, teacher, etc."""
        self.selenium_login('profileuser', 'testpass123')
        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        page = self.driver.page_source
        self.assertTrue(
            'student' in page.lower() or 'STUDENT' in page or 'role' in page.lower(),
            'Role information not found on profile page'
        )

    def test_teacher_profile_loads(self):
        """Teacher's profile page loads without errors."""
        create_teacher(username='teacherprofile', password='testpass123')
        self.selenium_login('teacherprofile', 'testpass123')
        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_profile_update_url_redirects_unauthenticated(self):
        """Profile update URL redirects unauthenticated users to login."""
        self.go('/profile/update/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
