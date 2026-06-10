"""
End-to-end Selenium flows covering multiple pages in sequence.

Run: python manage.py test core.test_selenium.test_e2e
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import (
    SeleniumMixin, create_student, create_teacher, create_superadmin,
    create_board, create_subject, create_class, create_question,
    create_contest, create_contest_question, create_syllabus,
    create_study_note, create_exam_paper,
)


class EndToEndSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Full user journeys covering multiple pages in sequence."""

    def setUp(self):
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.question = create_question(self.board, self.subject, self.class_obj)

    # ── signup flows ──────────────────────────────────────────────────────

    def test_signup_then_view_question_bank(self):
        """New user can sign up and immediately view the question bank."""
        self.go('/login/')
        signup_tab = self.driver.find_element(By.ID, 'tab-signup')
        signup_tab.click()
        WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, 'form-signup'))
        )
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="username"]').send_keys('e2euser')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="email"]').send_keys('e2e@test.com')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="password"]').send_keys('TestPass999')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup button[type=submit]').click()
        WebDriverWait(self.driver, 8).until(lambda d: '/login/' not in d.current_url)

        self.go('/question-bank/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/question-bank/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_signup_then_view_home(self):
        """New user redirected to home (not login) after signing up."""
        self.go('/login/')
        signup_tab = self.driver.find_element(By.ID, 'tab-signup')
        signup_tab.click()
        WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, 'form-signup'))
        )
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="username"]').send_keys('e2ehome')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="email"]').send_keys('e2ehome@test.com')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup input[name="password"]').send_keys('TestPass999')
        self.driver.find_element(By.CSS_SELECTOR, '#form-signup button[type=submit]').click()
        WebDriverWait(self.driver, 8).until(lambda d: '/login/' not in d.current_url)
        self.assertNotIn('/login/', self.driver.current_url)

    # ── login → multi-page visit → logout ─────────────────────────────────

    def test_login_then_profile_then_logout(self):
        """Complete login → profile visit → logout journey."""
        create_student(username='e2eprofile', password='testpass123', plan='PREMIUM')
        self.selenium_login('e2eprofile', 'testpass123')
        self.wait_for_url_contains('/')

        self.go('/profile/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/profile/'))
        self.assertIn('e2eprofile', self.driver.page_source)

        self.selenium_logout()
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_teacher_login_manage_logout(self):
        """Teacher logs in, visits manage panel, then logs out."""
        create_teacher(username='e2eteacher', password='testpass123')
        self.selenium_login('e2eteacher', 'testpass123')

        self.go('/dashboard/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/teacher/dashboard/' in d.current_url
        )

        self.go('/manage/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/'))
        self.assertNotIn('Server Error', self.driver.page_source)

        self.selenium_logout()
        self.wait_for_url_contains('/login/')

    def test_superadmin_login_then_superadmin_dashboard(self):
        """Superadmin can log in and reach the superadmin dashboard."""
        create_superadmin(username='e2esuperadmin', password='testpass123')
        self.selenium_login('e2esuperadmin', 'testpass123')
        self.go('/superadmin/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/superadmin/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    # ── public pages ──────────────────────────────────────────────────────

    def test_syllabus_without_login(self):
        """Syllabus list is reachable without authentication."""
        create_syllabus(self.subject, self.class_obj, self.board)
        self.go('/syllabus/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/syllabus/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_home_to_pricing_navigation(self):
        """User can navigate from home page to pricing page."""
        self.go('/')
        # The redesigned home renders some pricing links hidden (e.g. inside the
        # collapsed mobile menu) — only a visible one counts as navigable.
        pricing_links = [
            link for link in self.driver.find_elements(By.CSS_SELECTOR, 'a[href="/pricing/"]')
            if link.is_displayed()
        ]
        self.assertGreater(len(pricing_links), 0, 'No visible pricing link found on home page')
        self.driver.execute_script('arguments[0].click()', pricing_links[0])
        WebDriverWait(self.driver, 8).until(EC.url_contains('/pricing/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    # ── student complete flow ─────────────────────────────────────────────

    def test_premium_student_contest_list_to_detail(self):
        """Premium student can go from contest list to a contest detail page."""
        teacher = create_teacher(username='e2contestteacher', password='testpass123')
        contest = create_contest(teacher, self.subject, self.class_obj, title='E2E Contest')
        create_student(username='e2conteststudent', password='testpass123', plan='PREMIUM')
        self.selenium_login('e2conteststudent', 'testpass123')

        # The contest list defaults to the "upcoming" tab; this contest already
        # started (minutes_ago=5), so it lives on the "live" tab.
        self.go('/contests/?tab=live')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/contests/'))
        self.assertIn('E2E Contest', self.driver.page_source)

        contest_link = self.driver.find_element(
            By.CSS_SELECTOR, f'a[href*="/contests/{contest.pk}/"]'
        )
        contest_link.click()
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/contests/{contest.pk}/' in d.current_url
        )
        self.assertIn('E2E Contest', self.driver.page_source)

    def test_premium_student_study_notes_to_detail(self):
        """Premium student can navigate from study notes list to a note detail."""
        teacher = create_teacher(username='e2note_teacher', password='testpass123')
        note = create_study_note(teacher, self.subject, self.class_obj, title='E2E Note')
        create_student(username='e2note_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('e2note_student', 'testpass123')

        self.go('/study-notes/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/study-notes/'))
        self.assertIn('E2E Note', self.driver.page_source)

        note_link = self.driver.find_element(
            By.CSS_SELECTOR, f'a[href*="/study-notes/{note.pk}/"]'
        )
        note_link.click()
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/study-notes/{note.pk}/' in d.current_url
        )
        self.assertIn('E2E Note', self.driver.page_source)

    def test_exam_paper_list_to_start_exam(self):
        """Premium student can go from exam list to starting an exam."""
        teacher = create_teacher(username='e2exam_teacher', password='testpass123')
        paper = create_exam_paper(teacher, self.subject, self.class_obj, self.board,
                                  title='E2E Exam Paper')
        create_student(username='e2exam_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('e2exam_student', 'testpass123')

        self.go('/exam-papers/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/exam-papers/'))
        self.assertIn('E2E Exam Paper', self.driver.page_source)

        self.go(f'/exam-papers/{paper.pk}/exam/')
        WebDriverWait(self.driver, 8).until(lambda d: 'exam' in d.current_url)
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_question_bank_filter_then_view(self):
        """Student can filter questions by board and see results."""
        create_student(username='e2qb_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('e2qb_student', 'testpass123')

        self.go('/question-bank/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/question-bank/'))

        board_select = self.driver.find_element(By.NAME, 'board')
        # The select has onchange="this.form.submit()" — clicking the option
        # auto-submits, so don't call .submit() again on the now-stale element.
        board_select.find_element(By.CSS_SELECTOR, f'option[value="{self.board.pk}"]').click()

        WebDriverWait(self.driver, 8).until(
            EC.url_contains(f'board={self.board.pk}')
        )
        self.assertIn('What is force', self.driver.page_source)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
