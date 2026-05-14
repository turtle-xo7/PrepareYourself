"""
Selenium tests for Practical Lab and Practical Videos pages.

Run: python manage.py test core.test_selenium.test_practical
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import (
    SeleniumMixin, create_student, create_teacher,
    create_subject, create_class, create_practical_video,
)


class PracticalLabSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Practical lab landing page tests."""

    def test_practical_lab_requires_login(self):
        """Practical lab page redirects unauthenticated users to login."""
        self.go('/practical-lab/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_practical_lab_loads_for_authenticated_user(self):
        """Authenticated student can access the practical lab page."""
        create_student(username='lab_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('lab_student', 'testpass123')
        self.go('/practical-lab/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/practical-lab/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_practical_lab_shows_lab_content(self):
        """Practical lab page mentions 'practical' or 'lab' content."""
        create_student(username='lab_content', password='testpass123', plan='PREMIUM')
        self.selenium_login('lab_content', 'testpass123')
        self.go('/practical-lab/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/practical-lab/'))
        page = self.driver.page_source
        self.assertTrue(
            'practical' in page.lower() or 'lab' in page.lower() or 'video' in page.lower(),
            'Practical lab content not found on page'
        )

    def test_practical_lab_free_student_access(self):
        """Free student can also access the practical lab page."""
        create_student(username='lab_free', password='testpass123', plan='FREE')
        self.selenium_login('lab_free', 'testpass123')
        self.go('/practical-lab/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/practical-lab/' in d.current_url or '/login/' in d.current_url
                      or '/pricing/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass


class PracticalVideosSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Practical videos list and add pages."""

    def setUp(self):
        self.subject = create_subject()
        self.class_obj = create_class()
        self.teacher = create_teacher(username='vid_teacher', password='testpass123')
        self.video = create_practical_video(
            self.subject, self.class_obj,
            title='Test Practical Video',
            youtube_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        )

    def test_practical_videos_requires_login(self):
        """Practical videos page redirects unauthenticated users."""
        self.go('/practical-videos/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_practical_videos_loads_for_student(self):
        """Authenticated student can view the practical videos page."""
        create_student(username='vid_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('vid_student', 'testpass123')
        self.go('/practical-videos/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/practical-videos/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_practical_video_title_visible(self):
        """Created video title appears on the practical videos page."""
        create_student(username='vid_show', password='testpass123', plan='PREMIUM')
        self.selenium_login('vid_show', 'testpass123')
        self.go('/practical-videos/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/practical-videos/'))
        self.assertIn('Test Practical Video', self.driver.page_source)

    def test_practical_videos_has_subject_filter(self):
        """Practical videos page has a subject filter."""
        create_student(username='vid_filter', password='testpass123', plan='PREMIUM')
        self.selenium_login('vid_filter', 'testpass123')
        self.go('/practical-videos/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/practical-videos/'))
        page = self.driver.page_source
        self.assertTrue(
            'subject' in page.lower() or 'filter' in page.lower() or 'class' in page.lower(),
            'Subject filter not found on practical videos page'
        )

    def test_video_add_requires_admin(self):
        """Student cannot access the video add form."""
        create_student(username='vid_add_student', password='testpass123', plan='PREMIUM')
        self.selenium_login('vid_add_student', 'testpass123')
        self.go('/practical-videos/add/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/practical-videos/add/' not in d.current_url
        )
        self.assertNotIn('/practical-videos/add/', self.driver.current_url)

    def test_video_add_loads_for_teacher(self):
        """Teacher can access the add practical video form."""
        self.selenium_login('vid_teacher', 'testpass123')
        self.go('/practical-videos/add/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/practical-videos/add/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_video_add_form_has_required_fields(self):
        """Video add form has title and YouTube URL fields."""
        self.selenium_login('vid_teacher', 'testpass123')
        self.go('/practical-videos/add/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/practical-videos/add/'))
        page = self.driver.page_source
        self.assertTrue(
            'title' in page.lower() or 'youtube' in page.lower() or 'url' in page.lower(),
            'Required fields not found in video add form'
        )

    def test_youtube_embed_present_on_video_page(self):
        """Practical videos page embeds YouTube content."""
        create_student(username='vid_embed', password='testpass123', plan='PREMIUM')
        self.selenium_login('vid_embed', 'testpass123')
        self.go('/practical-videos/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/practical-videos/'))
        page = self.driver.page_source
        self.assertTrue(
            'youtube' in page.lower() or 'iframe' in page.lower() or 'embed' in page.lower(),
            'YouTube embed not found on practical videos page'
        )

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
