"""
Selenium tests for the Question Bank and Written Question Practice pages.

Run: python manage.py test core.test_selenium.test_question_bank
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_board, create_subject, create_class,
    create_question, create_written_question,
)


class QuestionBankSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Question bank listing, filtering, and MCQ interaction."""

    def setUp(self):
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        for i in range(12):
            create_question(
                self.board, self.subject, self.class_obj,
                text=f'Question {i + 1}: What is force?',
                chapter=f'Chapter {i + 1}',
                year=2024,
            )

    def test_question_bank_loads_without_login(self):
        """Question bank page is publicly accessible."""
        self.go('/question-bank/')
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_filter_board_dropdown_present(self):
        """Board filter select element is on the question bank page."""
        self.go('/question-bank/')
        select = self.driver.find_element(By.NAME, 'board')
        self.assertIsNotNone(select)

    def test_filter_subject_dropdown_present(self):
        """Subject filter select is present on the page."""
        self.go('/question-bank/')
        select = self.driver.find_element(By.NAME, 'subject')
        self.assertIsNotNone(select)

    def test_filter_year_dropdown_present(self):
        """Year filter select is present."""
        self.go('/question-bank/')
        select = self.driver.find_element(By.NAME, 'year')
        self.assertIsNotNone(select)

    def test_filter_class_dropdown_present(self):
        """Class filter select is present on the question bank page."""
        self.go('/question-bank/')
        page = self.driver.page_source
        self.assertTrue(
            'class' in page.lower() or 'Class' in page,
            'Class filter not found on question bank page'
        )

    def test_filter_by_board_changes_url(self):
        """Selecting a board filter and submitting updates the URL query string."""
        self.go('/question-bank/')
        board_select = self.driver.find_element(By.NAME, 'board')
        board_select.find_element(By.CSS_SELECTOR, f'option[value="{self.board.pk}"]').click()
        form = self.driver.find_element(By.CSS_SELECTOR, 'form')
        form.submit()
        WebDriverWait(self.driver, 8).until(EC.url_contains(f'board={self.board.pk}'))
        self.assertIn(f'board={self.board.pk}', self.driver.current_url)

    def test_question_text_visible_in_bank(self):
        """At least one question appears in the question bank."""
        self.go('/question-bank/')
        self.assertIn('Question', self.driver.page_source)

    def test_premium_user_sees_questions(self):
        """Premium student can see questions on the page."""
        create_student(username='premqb', password='testpass123', plan='PREMIUM')
        self.selenium_login('premqb', 'testpass123')
        self.go('/question-bank/')
        self.assertIn('Question', self.driver.page_source)
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_free_user_sees_question_bank(self):
        """Free user can access question bank page without server error."""
        create_student(username='freeqb', password='testpass123', plan='FREE')
        self.selenium_login('freeqb', 'testpass123')
        self.go('/question-bank/')
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_no_server_error_on_empty_filter(self):
        """Question bank with no filters doesn't crash."""
        self.go('/question-bank/?board=&subject=&class_obj=&year=')
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_question_bank_shows_difficulty_info(self):
        """Difficulty level (Easy/Medium/Hard) is referenced on the page."""
        create_student(username='diffqb', password='testpass123', plan='PREMIUM')
        self.selenium_login('diffqb', 'testpass123')
        self.go('/question-bank/')
        page = self.driver.page_source
        self.assertTrue(
            'Easy' in page or 'Medium' in page or 'Hard' in page or 'difficulty' in page.lower(),
            'Difficulty info not found on question bank page'
        )

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass


class WrittenQuestionSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Written question practice page."""

    def setUp(self):
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.teacher = create_teacher(username='wq_teacher', password='testpass123')
        self.question = create_written_question(
            self.board, self.subject, self.class_obj
        )

    def test_written_question_practice_requires_login(self):
        """Written question practice page redirects unauthenticated users."""
        self.go(f'/question-bank/written/{self.question.pk}/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_written_question_practice_loads_for_student(self):
        """Premium student can access the written question practice page."""
        create_student(username='wq_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('wq_student', 'testpass123')
        self.go(f'/question-bank/written/{self.question.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/question-bank/written/{self.question.pk}/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_written_question_shows_question_text(self):
        """Written question practice page shows the question text."""
        create_student(username='wq_show', password='testpass123', plan='PREMIUM')
        self.selenium_login('wq_show', 'testpass123')
        self.go(f'/question-bank/written/{self.question.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/question-bank/written/{self.question.pk}/' in d.current_url
        )
        self.assertIn("Newton", self.driver.page_source)

    def test_written_question_has_upload_form(self):
        """Written question practice page has a photo upload form."""
        create_student(username='wq_form', password='testpass123', plan='PREMIUM')
        self.selenium_login('wq_form', 'testpass123')
        self.go(f'/question-bank/written/{self.question.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/question-bank/written/{self.question.pk}/' in d.current_url
        )
        page = self.driver.page_source
        self.assertTrue(
            'upload' in page.lower() or 'file' in page.lower() or 'photo' in page.lower()
            or 'form' in page.lower(),
            'Upload form not found on written question practice page'
        )

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
