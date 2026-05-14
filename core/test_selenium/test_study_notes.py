"""
Selenium tests for Study Notes: list, detail, bookmark, comments, and note requests.

Run: python manage.py test core.test_selenium.test_study_notes
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.models import NoteBookmark, NoteComment, NoteRequest
from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_subject, create_class, create_study_note,
)


class StudyNotesSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Study notes list, detail, bookmarks, and comments."""

    def setUp(self):
        self.teacher = create_teacher(username='noteteacher', password='testpass123')
        self.subject = create_subject()
        self.class_obj = create_class()
        self.note = create_study_note(self.teacher, self.subject, self.class_obj)

    def test_unauthenticated_redirected_from_study_notes(self):
        """Unauthenticated users are redirected from /study-notes/."""
        self.go('/study-notes/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_free_student_redirected_from_study_notes(self):
        """Free student is sent away from the study notes list."""
        create_student(username='freenote', password='testpass123', plan='FREE')
        self.selenium_login('freenote', 'testpass123')
        self.go('/study-notes/')
        WebDriverWait(self.driver, 8).until(lambda d: '/study-notes/' not in d.current_url)
        self.assertNotIn('/study-notes/', self.driver.current_url)

    def test_premium_student_can_see_study_notes_list(self):
        """Premium student can load the study notes list."""
        create_student(username='premnote', password='testpass123', plan='PREMIUM')
        self.selenium_login('premnote', 'testpass123')
        self.go('/study-notes/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/study-notes/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_study_note_title_visible_in_list(self):
        """The created note title appears in the study notes list."""
        create_student(username='listnote', password='testpass123', plan='PREMIUM')
        self.selenium_login('listnote', 'testpass123')
        self.go('/study-notes/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/study-notes/'))
        self.assertIn('Test Note', self.driver.page_source)

    def test_study_note_detail_loads(self):
        """Note detail page loads without server errors."""
        create_student(username='detailnote', password='testpass123', plan='PREMIUM')
        self.selenium_login('detailnote', 'testpass123')
        self.go(f'/study-notes/{self.note.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/study-notes/{self.note.pk}/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_study_note_detail_shows_content(self):
        """Note detail page displays the note's body content."""
        create_student(username='contentnote', password='testpass123', plan='PREMIUM')
        self.selenium_login('contentnote', 'testpass123')
        self.go(f'/study-notes/{self.note.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/study-notes/{self.note.pk}/' in d.current_url
        )
        self.assertIn('test note content', self.driver.page_source.lower())

    def test_bookmark_element_present_on_detail(self):
        """A bookmark link or button exists on the note detail page."""
        create_student(username='booknote', password='testpass123', plan='PREMIUM')
        self.selenium_login('booknote', 'testpass123')
        self.go(f'/study-notes/{self.note.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/study-notes/{self.note.pk}/' in d.current_url
        )
        page = self.driver.page_source
        self.assertTrue(
            'bookmark' in page.lower(),
            'Bookmark element not found on note detail page'
        )

    def test_comment_form_present_on_detail(self):
        """Comment form is present on the note detail page."""
        create_student(username='commentnote', password='testpass123', plan='PREMIUM')
        self.selenium_login('commentnote', 'testpass123')
        self.go(f'/study-notes/{self.note.pk}/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/study-notes/{self.note.pk}/' in d.current_url
        )
        page = self.driver.page_source
        self.assertTrue(
            'comment' in page.lower() or 'textarea' in page.lower(),
            'Comment form not found on note detail page'
        )

    def test_teacher_can_see_study_notes_list(self):
        """Teacher (ADMIN) can access the study notes list."""
        self.selenium_login('noteteacher', 'testpass123')
        self.go('/study-notes/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/study-notes/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_teacher_can_access_add_study_note(self):
        """Teacher can reach the add study note page."""
        self.selenium_login('noteteacher', 'testpass123')
        self.go('/study-notes/add/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/study-notes/add/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_teacher_can_access_edit_study_note(self):
        """Teacher can reach the edit study note page."""
        self.selenium_login('noteteacher', 'testpass123')
        self.go(f'/study-notes/{self.note.pk}/edit/')
        WebDriverWait(self.driver, 8).until(
            lambda d: f'/study-notes/{self.note.pk}/edit/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_study_notes_list_has_search_or_filter(self):
        """Study notes list page has some filtering or search UI."""
        create_student(username='filtnote', password='testpass123', plan='PREMIUM')
        self.selenium_login('filtnote', 'testpass123')
        self.go('/study-notes/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/study-notes/'))
        page = self.driver.page_source
        self.assertTrue(
            'search' in page.lower() or 'subject' in page.lower() or 'filter' in page.lower(),
            'No search/filter UI found on study notes list'
        )

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass


class NoteRequestSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Note request submission and management pages."""

    def setUp(self):
        self.teacher = create_teacher(username='req_teacher', password='testpass123')
        self.subject = create_subject()
        self.class_obj = create_class()

    def test_note_request_submit_requires_login(self):
        """Note request submit endpoint redirects unauthenticated users."""
        self.go('/note-requests/submit/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_manage_note_requests_requires_admin(self):
        """Student cannot access note-request management page."""
        create_student(username='req_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('req_student', 'testpass123')
        self.go('/manage/note-requests/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/manage/note-requests/' not in d.current_url
        )
        self.assertNotIn('/manage/note-requests/', self.driver.current_url)

    def test_manage_note_requests_loads_for_teacher(self):
        """Teacher can access the manage note-requests page."""
        self.selenium_login('req_teacher', 'testpass123')
        self.go('/manage/note-requests/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/manage/note-requests/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_note_request_form_in_study_notes(self):
        """Study notes list has a way to request a note (button or form)."""
        create_student(username='reqbtn_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('reqbtn_student', 'testpass123')
        self.go('/study-notes/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/study-notes/'))
        page = self.driver.page_source
        self.assertTrue(
            'request' in page.lower() or 'note-requests' in page,
            'Note request button not found on study notes list'
        )

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
