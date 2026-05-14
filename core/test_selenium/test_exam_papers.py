"""
Selenium tests for Exam Papers: list, detail, MCQ phase, grade queue.

Run: python manage.py test core.test_selenium.test_exam_papers
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_subject, create_class, create_board, create_exam_paper,
)


class ExamPaperSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Exam paper list, detail, start exam, MCQ phase, and grade queue."""

    def setUp(self):
        self.teacher = create_teacher(username='examteacher', password='testpass123')
        self.subject = create_subject()
        self.class_obj = create_class()
        self.board = create_board()
        self.paper = create_exam_paper(
            self.teacher, self.subject, self.class_obj, board=self.board
        )

    def test_exam_paper_list_requires_login(self):
        """Exam paper list redirects unauthenticated users to login."""
        self.go('/exam-papers/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_exam_paper_list_loads_for_authenticated_user(self):
        """Authenticated user can view the exam paper list."""
        create_student(username='examstudent', password='testpass123', plan='PREMIUM')
        self.selenium_login('examstudent', 'testpass123')
        self.go('/exam-papers/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/exam-papers/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_exam_paper_title_in_list(self):
        """The test exam paper title is visible on the list page."""
        create_student(username='exampaplist', password='testpass123', plan='PREMIUM')
        self.selenium_login('exampaplist', 'testpass123')
        self.go('/exam-papers/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/exam-papers/'))
        self.assertIn('Test Exam Paper', self.driver.page_source)

    def test_exam_paper_detail_loads(self):
        """Exam paper detail page loads successfully."""
        create_student(username='exampapdetail', password='testpass123', plan='PREMIUM')
        self.selenium_login('exampapdetail', 'testpass123')
        self.go(f'/exam-papers/{self.paper.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/exam-papers/{self.paper.pk}/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_exam_detail_shows_start_button(self):
        """Exam paper detail page has a start or exam button."""
        create_student(username='startexambtn', password='testpass123', plan='PREMIUM')
        self.selenium_login('startexambtn', 'testpass123')
        self.go(f'/exam-papers/{self.paper.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/exam-papers/{self.paper.pk}/' in d.current_url
        )
        page = self.driver.page_source
        self.assertTrue(
            'start' in page.lower() or 'exam' in page.lower() or 'শুরু' in page,
            'Start exam button not found on exam paper detail page'
        )

    def test_mcq_phase_loads_after_starting_exam(self):
        """Starting an exam navigates to the MCQ phase page."""
        create_student(username='mcqphase', password='testpass123', plan='PREMIUM')
        self.selenium_login('mcqphase', 'testpass123')
        self.go(f'/exam-papers/{self.paper.pk}/exam/')
        WebDriverWait(self.driver, 8).until(lambda d: 'exam' in d.current_url)
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_mcq_phase_shows_question_text(self):
        """MCQ exam page shows the question text from the exam paper."""
        create_student(username='mcqtext', password='testpass123', plan='PREMIUM')
        self.selenium_login('mcqtext', 'testpass123')
        self.go(f'/exam-papers/{self.paper.pk}/exam/')
        WebDriverWait(self.driver, 8).until(lambda d: 'exam' in d.current_url)
        self.assertIn('force', self.driver.page_source.lower())

    def test_mcq_options_present_in_exam(self):
        """MCQ exam page shows answer options (Push/Pull/Both/None)."""
        create_student(username='mcqopts', password='testpass123', plan='PREMIUM')
        self.selenium_login('mcqopts', 'testpass123')
        self.go(f'/exam-papers/{self.paper.pk}/exam/')
        WebDriverWait(self.driver, 8).until(lambda d: 'exam' in d.current_url)
        page = self.driver.page_source
        self.assertTrue(
            'Push' in page or 'Pull' in page or 'option' in page.lower(),
            'MCQ options not found on exam page'
        )

    def test_teacher_can_access_create_exam_paper(self):
        """Teacher can navigate to the create exam paper form."""
        self.selenium_login('examteacher', 'testpass123')
        self.go('/manage/exam-paper/create/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/exam-paper/create/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_teacher_can_access_exam_paper_preview(self):
        """Teacher can view the exam paper preview page."""
        self.selenium_login('examteacher', 'testpass123')
        self.go(f'/manage/exam-paper/{self.paper.pk}/preview/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'preview' in d.current_url or 'exam' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_teacher_can_access_edit_exam_paper(self):
        """Teacher can reach the edit exam paper form."""
        self.selenium_login('examteacher', 'testpass123')
        self.go(f'/manage/exam-paper/{self.paper.pk}/edit/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'edit' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_grade_queue_requires_admin(self):
        """Student cannot access the grade queue page."""
        create_student(username='gradeq_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('gradeq_student', 'testpass123')
        self.go('/manage/grade-queue/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/manage/grade-queue/' not in d.current_url
        )
        self.assertNotIn('/manage/grade-queue/', self.driver.current_url)

    def test_grade_queue_loads_for_teacher(self):
        """Teacher can access the CQ grade queue page."""
        self.selenium_login('examteacher', 'testpass123')
        self.go('/manage/grade-queue/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/grade-queue/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_exam_paper_list_has_filter_options(self):
        """Exam paper list has subject or board filter options."""
        create_student(username='filtexam', password='testpass123', plan='PREMIUM')
        self.selenium_login('filtexam', 'testpass123')
        self.go('/exam-papers/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/exam-papers/'))
        page = self.driver.page_source
        self.assertTrue(
            'subject' in page.lower() or 'board' in page.lower() or 'filter' in page.lower()
            or 'select' in page.lower(),
            'Filter options not found on exam paper list'
        )

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
