"""
Selenium tests for the home page and navbar.

Run: python manage.py test core.test_selenium.test_home
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import SeleniumMixin, create_student, create_teacher, create_superadmin, create_board


class HomeSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Home page hero, stat boxes, feature sections, and CTA buttons."""

    def test_home_page_loads_without_error(self):
        """Home page responds successfully."""
        self.go('/')
        self.assertNotIn('Server Error', self.driver.page_source)
        self.assertNotIn('Page not found', self.driver.page_source)

    def test_hero_headline_present(self):
        """Hero section contains the main headline text."""
        self.go('/')
        self.assertIn('Ace Your Board Exams', self.driver.page_source)

    def test_stat_boxes_present(self):
        """Stat boxes with count-up spans are present in the hero section."""
        self.go('/')
        count_up_elements = self.driver.find_elements(By.CSS_SELECTOR, '.count-up')
        self.assertGreater(len(count_up_elements), 0,
                           'Expected .count-up elements in hero stat boxes')

    def test_browse_questions_cta_visible(self):
        """'Browse Questions' CTA button is present and links to question bank."""
        self.go('/')
        link = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/question-bank/"]')
        self.assertIsNotNone(link)

    def test_start_free_trial_cta_visible(self):
        """'Start Free Trial' CTA is visible in the hero section."""
        self.go('/')
        self.assertIn('Start Free Trial', self.driver.page_source)

    def test_home_page_title(self):
        """Page <title> contains 'Home' or 'Prepare'."""
        self.go('/')
        title = self.driver.title
        self.assertTrue(
            'Home' in title or 'Prepare' in title,
            f'Unexpected page title: {title}'
        )

    def test_pricing_link_present(self):
        """Pricing page is linked somewhere on the home page."""
        self.go('/')
        self.assertIn('/pricing/', self.driver.page_source)

    def test_boards_section_present(self):
        """Home page contains a boards/or features section."""
        self.go('/')
        page = self.driver.page_source
        self.assertTrue(
            'board' in page.lower() or 'Board' in page or 'feature' in page.lower(),
            'Boards/features section not found on home page'
        )

    def test_unauthenticated_home_loads(self):
        """Anonymous users can load the home page."""
        self.go('/')
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_home_with_board_data_shows_board(self):
        """Home page shows created boards."""
        create_board(name='Chittagong Board')
        self.go('/')
        self.assertIn('Chittagong Board', self.driver.page_source)


class NavbarSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Navbar rendering, links, hamburger icon, and role-based items."""

    def test_navbar_present_on_home(self):
        """Navbar element is rendered on the home page."""
        self.go('/')
        nav = self.wait_for(By.ID, 'main-navbar')
        self.assertIsNotNone(nav)

    def test_logo_links_to_home(self):
        """Clicking the PY logo navigates back to home."""
        self.go('/question-bank/')
        logo = self.wait_for(By.CSS_SELECTOR, 'a[href="/"]')
        logo.click()
        self.wait_for_url_contains('/')
        self.assertNotIn('question-bank', self.driver.current_url)

    def test_navbar_question_bank_link_navigates(self):
        """Question Bank nav link goes to the correct page."""
        self.go('/')
        link = self.driver.find_element(By.CSS_SELECTOR, 'a[href="/question-bank/"]')
        link.click()
        self.wait_for_url_contains('/question-bank/')
        self.assertIn('question-bank', self.driver.current_url)

    def test_navbar_shows_login_signup_unauthenticated(self):
        """Unauthenticated visitors see Login and Sign Up in navbar."""
        self.go('/')
        page = self.driver.page_source
        self.assertIn('Log In', page)
        self.assertIn('Sign Up', page)

    def test_navbar_shows_logout_when_authenticated(self):
        """Authenticated user sees Log Out link in navbar."""
        create_student(username='navbaruser', password='testpass123')
        self.selenium_login('navbaruser', 'testpass123')
        self.go('/')
        self.wait_for(By.LINK_TEXT, 'Log Out')
        self.assertIn('Log Out', self.driver.page_source)

    def test_hamburger_button_present(self):
        """Hamburger icon is in the DOM for mobile navigation."""
        self.go('/')
        hamburger = self.wait_for(By.ID, 'hamburger')
        self.assertIsNotNone(hamburger)

    def test_superadmin_navbar_shows_crown_link(self):
        """Superadmin users see the crown link to /superadmin/ in the navbar."""
        create_superadmin(username='sa_nav', password='testpass123')
        self.selenium_login('sa_nav', 'testpass123')
        self.go('/')
        self.wait_for(By.CSS_SELECTOR, 'a[href="/superadmin/"]')
        self.assertIn('/superadmin/', self.driver.page_source)

    def test_teacher_navbar_shows_manage_link(self):
        """Teacher (ADMIN role) sees manage panel icon in navbar."""
        create_teacher(username='teacher_nav', password='testpass123')
        self.selenium_login('teacher_nav', 'testpass123')
        self.go('/')
        self.wait_for(By.CSS_SELECTOR, 'a[href="/manage/"]')
        self.assertIn('/manage/', self.driver.page_source)

    def test_navbar_syllabus_link_present(self):
        """Syllabus link is accessible from the navbar or home page."""
        self.go('/')
        self.assertIn('/syllabus/', self.driver.page_source)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
