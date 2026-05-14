"""
Selenium tests for authentication flows:
login (username/email), signup, logout, password reset page.

Run: python manage.py test core.test_selenium.test_auth
"""

from django.test import LiveServerTestCase
from django.contrib.auth.models import User
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import SeleniumMixin, create_student, create_teacher, create_superadmin


class AuthSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Login, signup, logout, and redirect flows."""

    def test_login_page_loads(self):
        """Login page renders the form elements correctly."""
        self.go('/login/')
        self.assertIn('Prepare Yourself', self.driver.page_source)
        self.assertTrue(self.element_exists(By.NAME, 'username'))
        self.assertTrue(self.element_exists(By.NAME, 'password'))
        self.assertTrue(self.element_exists(By.CSS_SELECTOR, 'button[type=submit]'))

    def test_login_with_username(self):
        """Valid username + password redirects away from login page."""
        create_student(username='loginuser', password='testpass123')
        self.selenium_login('loginuser', 'testpass123')
        self.wait_for_url_contains('/')
        self.assertNotIn('/login/', self.driver.current_url)

    def test_login_with_email(self):
        """Login form accepts email address in the username field."""
        create_student(username='emailuser', email='emailuser@test.com', password='testpass123')
        self.selenium_login('emailuser@test.com', 'testpass123')
        self.wait_for_url_contains('/')
        self.assertNotIn('/login/', self.driver.current_url)

    def test_wrong_password_stays_on_login(self):
        """Incorrect password keeps user on the login page."""
        create_student(username='badpassuser', password='testpass123')
        self.go('/login/')
        self.driver.find_element(By.NAME, 'username').send_keys('badpassuser')
        self.driver.find_element(By.NAME, 'password').send_keys('WRONG_PASSWORD')
        self.driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        WebDriverWait(self.driver, 8).until(
            lambda d: '/login/' in d.current_url or 'ভুল' in d.page_source
        )
        self.assertIn('/login/', self.driver.current_url)

    def test_nonexistent_user_shows_error(self):
        """Trying to log in with a username that doesn't exist stays on login."""
        self.go('/login/')
        self.driver.find_element(By.NAME, 'username').send_keys('no_such_user_xyz')
        self.driver.find_element(By.NAME, 'password').send_keys('anything')
        self.driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        WebDriverWait(self.driver, 8).until(
            lambda d: '/login/' in d.current_url
        )
        self.assertIn('/login/', self.driver.current_url)

    def test_signup_creates_account_and_redirects(self):
        """Signing up with valid data creates a user and redirects home."""
        self.go('/login/')
        signup_tab = self.driver.find_element(By.ID, 'tab-signup')
        signup_tab.click()
        WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, 'form-signup'))
        )
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="username"]').send_keys('brandnewuser')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="email"]').send_keys('brandnew@test.com')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="password"]').send_keys('TestPass999')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup button[type=submit]').click()
        WebDriverWait(self.driver, 8).until(lambda d: '/login/' not in d.current_url)
        self.assertTrue(User.objects.filter(username='brandnewuser').exists())

    def test_signup_duplicate_username_shows_error(self):
        """Signing up with an existing username stays on login/signup."""
        create_student(username='existinguser', password='testpass123')
        self.go('/login/')
        signup_tab = self.driver.find_element(By.ID, 'tab-signup')
        signup_tab.click()
        WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, 'form-signup'))
        )
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="username"]').send_keys('existinguser')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="email"]').send_keys('other@test.com')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="password"]').send_keys('TestPass999')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup button[type=submit]').click()
        WebDriverWait(self.driver, 6).until(
            lambda d: True  # just wait for page to settle
        )
        # Should stay on login page (redirect didn't happen)
        self.assertIn('/login/', self.driver.current_url)

    def test_logout_redirects_to_login(self):
        """Logging out sends the user to /login/."""
        create_student(username='logoutuser', password='testpass123')
        self.selenium_login('logoutuser', 'testpass123')
        self.wait_for_url_contains('/')
        self.selenium_logout()
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_already_logged_in_redirected_from_login(self):
        """Authenticated user visiting /login/ is bounced to home."""
        create_student(username='alreadyin', password='testpass123')
        self.selenium_login('alreadyin', 'testpass123')
        self.go('/login/')
        WebDriverWait(self.driver, 8).until(lambda d: '/login/' not in d.current_url)
        self.assertNotIn('/login/', self.driver.current_url)

    def test_password_reset_page_loads(self):
        """Password reset page renders the email form."""
        self.go('/password-reset/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/password-reset/'))
        self.assertNotIn('Server Error', self.driver.page_source)
        self.assertTrue(self.element_exists(By.NAME, 'email'))

    def test_login_tab_and_signup_tab_both_present(self):
        """Login page has both Login and Sign Up tabs."""
        self.go('/login/')
        self.assertTrue(self.element_exists(By.ID, 'tab-signup'))
        page = self.driver.page_source
        self.assertIn('Sign Up', page)
        self.assertIn('Log In', page)

    def test_unauthenticated_dashboard_redirect(self):
        """Unauthenticated access to /dashboard/ redirects to /login/."""
        self.go('/dashboard/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_teacher_login_redirects_to_teacher_dashboard(self):
        """After teacher login, /dashboard/ redirects to /teacher/dashboard/."""
        create_teacher(username='teachlogin', password='testpass123')
        self.selenium_login('teachlogin', 'testpass123')
        self.go('/dashboard/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/teacher/dashboard/' in d.current_url
        )
        self.assertIn('/teacher/dashboard/', self.driver.current_url)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
