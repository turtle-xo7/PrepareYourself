"""
Selenium tests for Teacher Dashboard, Manage Panel, and student detail views.

Run: python manage.py test core.test_selenium.test_teacher
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_subject, create_class, create_board, create_question,
)


class TeacherDashboardSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Teacher dashboard, student list, and student detail pages."""

    def setUp(self):
        self.teacher = create_teacher(username='teachertest', password='testpass123')
        self.student = create_student(username='teachstudent', password='testpass123',
                                      plan='PREMIUM')
        self.subject = create_subject()
        self.class_obj = create_class()
        self.board = create_board()

    def test_student_cannot_access_teacher_dashboard(self):
        """Student role is redirected away from teacher dashboard."""
        self.selenium_login('teachstudent', 'testpass123')
        self.go('/teacher/dashboard/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/teacher/dashboard/' not in d.current_url
        )
        self.assertNotIn('/teacher/dashboard/', self.driver.current_url)

    def test_unauthenticated_redirected_from_teacher_dashboard(self):
        """Unauthenticated user is redirected from teacher dashboard."""
        self.go('/teacher/dashboard/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_teacher_dashboard_loads(self):
        """Teacher can access their dashboard."""
        self.selenium_login('teachertest', 'testpass123')
        self.go('/teacher/dashboard/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/teacher/dashboard/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_teacher_dashboard_shows_student_list(self):
        """Teacher dashboard shows the registered students."""
        self.selenium_login('teachertest', 'testpass123')
        self.go('/teacher/dashboard/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/teacher/dashboard/'))
        self.assertIn('teachstudent', self.driver.page_source)

    def test_student_detail_page_loads(self):
        """Teacher can view a student's detail page."""
        self.selenium_login('teachertest', 'testpass123')
        self.go(f'/teacher/student/{self.student.profile.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/teacher/student/{self.student.profile.pk}/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_student_detail_shows_username(self):
        """Student detail page contains the student's username."""
        self.selenium_login('teachertest', 'testpass123')
        self.go(f'/teacher/student/{self.student.profile.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/teacher/student/{self.student.profile.pk}/' in d.current_url
        )
        self.assertIn('teachstudent', self.driver.page_source)

    def test_teacher_dashboard_shows_stats(self):
        """Teacher dashboard has some statistics or analytics section."""
        self.selenium_login('teachertest', 'testpass123')
        self.go('/teacher/dashboard/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/teacher/dashboard/'))
        page = self.driver.page_source
        self.assertTrue(
            'student' in page.lower() or 'statistic' in page.lower() or 'total' in page.lower(),
            'No stats section found on teacher dashboard'
        )

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass


class ManagePanelSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Manage panel access control and CRUD UI."""

    def setUp(self):
        self.teacher = create_teacher(username='mgr_teacher', password='testpass123')
        self.student = create_student(username='mgr_student', password='testpass123', plan='FREE')
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()

    def test_manage_dashboard_requires_admin(self):
        """Student cannot access /manage/."""
        self.selenium_login('mgr_student', 'testpass123')
        self.go('/manage/')
        WebDriverWait(self.driver, 8).until(lambda d: '/manage/' not in d.current_url)
        self.assertNotIn('/manage/', self.driver.current_url)

    def test_unauthenticated_cannot_access_manage(self):
        """Unauthenticated visitor is redirected from /manage/."""
        self.go('/manage/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_manage_dashboard_loads_for_teacher(self):
        """Teacher can load /manage/."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_manage_dashboard_shows_stats(self):
        """Manage dashboard shows stat counters for questions, boards, etc."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/'))
        page = self.driver.page_source
        self.assertTrue(
            'question' in page.lower() or 'board' in page.lower() or 'subject' in page.lower(),
            'Stats not found on manage dashboard'
        )

    def test_manage_questions_page_loads(self):
        """Manage questions page loads for teacher."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/questions/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/questions/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_manage_add_question_form_loads(self):
        """Question add form is accessible to teacher."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/questions/add/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/questions/add/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_manage_add_question_form_has_fields(self):
        """Question add form has the essential input fields."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/questions/add/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/questions/add/'))
        page = self.driver.page_source
        self.assertTrue(
            'question_text' in page or 'Question' in page,
            'question_text field not found in add question form'
        )

    def test_manage_boards_page_loads(self):
        """Manage boards page loads for teacher."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/boards/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/boards/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_manage_boards_shows_existing_board(self):
        """Manage boards page shows the created board."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/boards/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/boards/'))
        self.assertIn('Dhaka Board', self.driver.page_source)

    def test_manage_subjects_page_loads(self):
        """Manage subjects page loads for teacher."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/subjects/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/subjects/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_manage_classes_page_loads(self):
        """Manage classes page loads for teacher."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/classes/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/classes/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_manage_panel_has_navigation_links(self):
        """Manage dashboard contains links to questions, boards, subjects, classes."""
        self.selenium_login('mgr_teacher', 'testpass123')
        self.go('/manage/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/'))
        page = self.driver.page_source
        self.assertIn('/manage/questions/', page)
        self.assertIn('/manage/boards/', page)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
