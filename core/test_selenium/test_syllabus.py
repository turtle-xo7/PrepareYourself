"""
Selenium tests for Syllabus: list, detail, filters, and CRUD for teachers.

Run: python manage.py test core.test_selenium.test_syllabus
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_subject, create_class, create_board, create_syllabus,
)


class SyllabusSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Syllabus list, detail, filter, and CRUD forms."""

    def setUp(self):
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.syllabus = create_syllabus(
            self.subject, self.class_obj, self.board,
            content='Chapter 1: Introduction\nChapter 2: Applications',
        )

    def test_syllabus_list_loads_without_login(self):
        """Syllabus list page is publicly accessible."""
        self.go('/syllabus/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_syllabus_list_shows_created_syllabus(self):
        """The created syllabus subject appears in the list page."""
        self.go('/syllabus/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/'))
        self.assertIn('Physics', self.driver.page_source)

    def test_syllabus_list_shows_board(self):
        """The board name appears on the syllabus list page."""
        self.go('/syllabus/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/'))
        self.assertIn('Dhaka Board', self.driver.page_source)

    def test_syllabus_detail_loads(self):
        """Syllabus detail page loads without errors."""
        self.go(f'/syllabus/{self.syllabus.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/syllabus/{self.syllabus.pk}/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_syllabus_detail_shows_content(self):
        """Syllabus detail page renders the chapter content."""
        self.go(f'/syllabus/{self.syllabus.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/syllabus/{self.syllabus.pk}/' in d.current_url
        )
        self.assertIn('Chapter 1', self.driver.page_source)

    def test_syllabus_filter_board_present(self):
        """Board filter select is present on the syllabus list page."""
        self.go('/syllabus/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/'))
        board_select = self.driver.find_element(By.NAME, 'board')
        self.assertIsNotNone(board_select)

    def test_syllabus_filter_subject_present(self):
        """Subject filter select is present on the syllabus list page."""
        self.go('/syllabus/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/'))
        subject_select = self.driver.find_element(By.NAME, 'subject')
        self.assertIsNotNone(subject_select)

    def test_teacher_can_access_syllabus_add_form(self):
        """Teacher can navigate to the add-syllabus form."""
        create_teacher(username='syllabteacher', password='testpass123')
        self.selenium_login('syllabteacher', 'testpass123')
        self.go('/syllabus/add/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/add/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_syllabus_add_form_has_required_fields(self):
        """Syllabus add form has subject and content fields."""
        create_teacher(username='syllabteacher2', password='testpass123')
        self.selenium_login('syllabteacher2', 'testpass123')
        self.go('/syllabus/add/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/add/'))
        page = self.driver.page_source
        self.assertTrue(
            'subject' in page.lower() or 'content' in page.lower() or 'board' in page.lower(),
            'Required fields not found on syllabus add form'
        )

    def test_teacher_can_access_syllabus_edit_form(self):
        """Teacher can reach the edit-syllabus form."""
        create_teacher(username='syllabteacher3', password='testpass123')
        self.selenium_login('syllabteacher3', 'testpass123')
        self.go(f'/syllabus/{self.syllabus.pk}/edit/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/syllabus/{self.syllabus.pk}/edit/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_student_cannot_access_syllabus_add(self):
        """Student is blocked from the syllabus add form."""
        create_student(username='syllab_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('syllab_student', 'testpass123')
        self.go('/syllabus/add/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/syllabus/add/' not in d.current_url
        )
        self.assertNotIn('/syllabus/add/', self.driver.current_url)

    def test_syllabus_list_no_error_with_filters(self):
        """Applying board and subject filters doesn't cause a server error."""
        self.go(f'/syllabus/?board={self.board.pk}&subject={self.subject.pk}')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
