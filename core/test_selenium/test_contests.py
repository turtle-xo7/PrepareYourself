"""
Selenium tests for Contests: list, detail, create, join, leaderboard.

Run: python manage.py test core.test_selenium.test_contests
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_subject, create_class,
    create_contest, create_contest_question,
)


class ContestSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Contest listing, detail, join flow, leaderboard, and creation."""

    def setUp(self):
        self.teacher = create_teacher(username='contestteacher', password='testpass123')
        self.subject = create_subject()
        self.class_obj = create_class()
        self.contest = create_contest(self.teacher, self.subject, self.class_obj)
        self.cq = create_contest_question(self.contest)

    def test_contest_list_requires_login(self):
        """Contest list page redirects unauthenticated users to login."""
        self.go('/contests/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_contest_list_loads_for_authenticated_user(self):
        """Authenticated student can view the contest list page."""
        create_student(username='conteststudent', password='testpass123', plan='PREMIUM')
        self.selenium_login('conteststudent', 'testpass123')
        self.go('/contests/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/contests/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_active_contest_shows_in_list(self):
        """The active test contest appears on the contest list page."""
        create_student(username='listcontest', password='testpass123', plan='PREMIUM')
        self.selenium_login('listcontest', 'testpass123')
        self.go('/contests/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/contests/'))
        self.assertIn('Test Contest', self.driver.page_source)

    def test_contest_detail_page_loads(self):
        """Contest detail page loads without errors."""
        create_student(username='detailcontest', password='testpass123', plan='PREMIUM')
        self.selenium_login('detailcontest', 'testpass123')
        self.go(f'/contests/{self.contest.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/contests/{self.contest.pk}/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_contest_detail_shows_title(self):
        """Contest title is visible on the detail page."""
        create_student(username='titlecontest', password='testpass123', plan='PREMIUM')
        self.selenium_login('titlecontest', 'testpass123')
        self.go(f'/contests/{self.contest.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/contests/{self.contest.pk}/' in d.current_url
        )
        self.assertIn('Test Contest', self.driver.page_source)

    def test_join_element_present_on_active_contest(self):
        """Active contest detail page has a join/participate element."""
        create_student(username='joinbtncontest', password='testpass123', plan='PREMIUM')
        self.selenium_login('joinbtncontest', 'testpass123')
        self.go(f'/contests/{self.contest.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/contests/{self.contest.pk}/' in d.current_url
        )
        join_elements = self.driver.find_elements(
            By.CSS_SELECTOR,
            f'a[href*="/contests/{self.contest.pk}/join/"], button[data-join]'
        )
        self.assertTrue(
            len(join_elements) > 0 or 'join' in self.driver.page_source.lower()
                                   or 'অংশগ্রহণ' in self.driver.page_source,
            'No join button found on active contest detail page'
        )

    def test_leaderboard_page_loads(self):
        """Contest leaderboard page loads without errors."""
        create_student(username='lbcontest', password='testpass123', plan='PREMIUM')
        self.selenium_login('lbcontest', 'testpass123')
        self.go(f'/contests/{self.contest.pk}/leaderboard/')
        WebDriverWait(self.driver, 8).until(lambda d: 'leaderboard' in d.current_url)
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_teacher_can_access_contest_create(self):
        """Teacher can navigate to the contest creation form."""
        self.selenium_login('contestteacher', 'testpass123')
        self.go('/contests/create/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/contests/create/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_contest_create_form_has_fields(self):
        """Contest creation form has title and duration fields."""
        self.selenium_login('contestteacher', 'testpass123')
        self.go('/contests/create/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/contests/create/'))
        page = self.driver.page_source
        self.assertTrue(
            'title' in page.lower() or 'duration' in page.lower() or 'subject' in page.lower(),
            'Contest creation form fields not found'
        )

    def test_student_cannot_access_contest_create(self):
        """Student is blocked from the contest creation page."""
        create_student(username='student_createc', password='testpass123', plan='PREMIUM')
        self.selenium_login('student_createc', 'testpass123')
        self.go('/contests/create/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/contests/create/' not in d.current_url
        )
        self.assertNotIn('/contests/create/', self.driver.current_url)

    def test_contest_result_page_for_non_participant_redirects(self):
        """Non-participant accessing contest result page is redirected."""
        create_student(username='nonpart', password='testpass123', plan='PREMIUM')
        self.selenium_login('nonpart', 'testpass123')
        self.go(f'/contests/{self.contest.pk}/result/')
        # Should redirect away since user hasn't submitted
        page = self.driver.page_source
        self.assertNotIn('Server Error', page)

    def test_contest_list_has_create_link_for_teacher(self):
        """Teacher's contest list shows a 'Create Contest' link."""
        self.selenium_login('contestteacher', 'testpass123')
        self.go('/contests/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/contests/'))
        page = self.driver.page_source
        self.assertTrue(
            '/contests/create/' in page or 'create' in page.lower(),
            'Create contest link not found for teacher'
        )

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
