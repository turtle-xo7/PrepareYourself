"""
Shared helpers: data-creation factories and SeleniumMixin.
Import from here in every test module to avoid duplication.
"""

import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from core.models import (
    Board, Subject, Class, Question, UserProfile,
    UserProgress, StudyNote, TeacherFeedback, Contest,
    ContestQuestion, Syllabus, ExamPaper, ExamPaperMCQ, CQQuestion,
    Notification, NoteBookmark, NoteComment, NoteRequest, PracticalVideo,
)


# ── factories ──────────────────────────────────────────────────────────────

def create_student(username='student1', email='student@test.com',
                   password='testpass123', plan='PREMIUM'):
    user = User.objects.create_user(username=username, email=email, password=password)
    UserProfile.objects.create(user=user, role='STUDENT', plan=plan)
    return user


def create_free_student(username='freestudent', email='free@test.com',
                        password='testpass123'):
    return create_student(username=username, email=email, password=password, plan='FREE')


def create_teacher(username='teacher1', email='teacher@test.com',
                   password='testpass123'):
    user = User.objects.create_user(username=username, email=email, password=password)
    UserProfile.objects.create(user=user, role='ADMIN', plan='FREE')
    return user


def create_superadmin(username='superadmin1', email='superadmin@test.com',
                      password='testpass123'):
    user = User.objects.create_user(username=username, email=email, password=password)
    UserProfile.objects.create(user=user, role='ADMIN', plan='FREE', is_superadmin=True)
    return user


def create_board(name='Dhaka Board'):
    return Board.objects.create(name=name, student_count='100000', is_active=True)


def create_subject(name='Physics', icon='⚛', color='blue'):
    return Subject.objects.create(name=name, icon=icon, color=color, is_active=True)


def create_class(name='Class 9', numeric_value=9):
    return Class.objects.create(name=name, numeric_value=numeric_value)


def create_question(board, subject, class_obj,
                    text='What is force?', answer_hint='Force is push or pull.',
                    year=2024, chapter='Chapter 1', q_type='MCQ'):
    return Question.objects.create(
        board=board, subject=subject, class_obj=class_obj,
        year=year, chapter=chapter,
        question_text=text,
        question_type=q_type, difficulty='Easy',
        option1='Push', option2='Pull', option3='Both', option4='None',
        correct_option=3,
        answer_hint=answer_hint,
        is_active=True,
    )


def create_written_question(board, subject, class_obj,
                             text='Explain Newton\'s laws.', year=2024, chapter='Chapter 2'):
    return Question.objects.create(
        board=board, subject=subject, class_obj=class_obj,
        year=year, chapter=chapter,
        question_text=text,
        question_type='WRITTEN', difficulty='Medium',
        is_active=True,
    )


def create_study_note(teacher, subject, class_obj,
                      title='Test Note', chapter='Chapter 1',
                      content='This is test note content for study.'):
    return StudyNote.objects.create(
        title=title, subject=subject, class_obj=class_obj,
        chapter=chapter, content=content,
        created_by=teacher, is_active=True,
    )


def create_contest(teacher, subject, class_obj,
                   title='Test Contest', minutes_ago=5, hours_ahead=1):
    now = timezone.now()
    return Contest.objects.create(
        title=title,
        created_by=teacher,
        subject=subject,
        class_obj=class_obj,
        duration_minutes=30,
        start_time=now - datetime.timedelta(minutes=minutes_ago),
        end_time=now + datetime.timedelta(hours=hours_ahead),
        is_active=True,
    )


def create_contest_question(contest, text='What is 2+2?', correct=2):
    return ContestQuestion.objects.create(
        contest=contest,
        question_text=text,
        question_type='MCQ',
        option1='3', option2='4', option3='5', option4='6',
        correct_option=correct,
        marks=1,
    )


def create_exam_paper(teacher, subject, class_obj, board=None,
                      title='Test Exam Paper', year=2024):
    paper = ExamPaper.objects.create(
        title=title, subject=subject, class_obj=class_obj,
        board=board, year=year,
        created_by=teacher, is_active=True,
    )
    ExamPaperMCQ.objects.create(
        exam_paper=paper,
        question_text='What is force?',
        option1='Push', option2='Pull', option3='Both', option4='None',
        correct_option=3, marks=1, order=0,
    )
    return paper


def create_syllabus(subject, class_obj, board, content='Chapter 1, Chapter 2'):
    return Syllabus.objects.create(
        subject=subject, class_obj=class_obj, board=board,
        content=content, is_active=True,
    )


def create_practical_video(subject, class_obj, title='Test Video',
                            youtube_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'):
    return PracticalVideo.objects.create(
        title=title, subject=subject, class_obj=class_obj,
        youtube_url=youtube_url, is_active=True,
    )


def create_notification(user, title='Test Notification', message='Test message'):
    return Notification.objects.create(
        user=user,
        title=title, title_bn=title,
        message=message, message_bn=message,
        notif_type='GENERAL',
        is_read=False,
    )


# ── SeleniumMixin ───────────────────────────────────────────────────────────

class SeleniumMixin:
    """Shared driver setup and helper utilities for all Selenium test classes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        opts = Options()
        opts.add_argument('--headless')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--window-size=1280,800')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--log-level=3')

        cls.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=opts,
        )
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    # navigation

    def go(self, path):
        self.driver.get(self.live_server_url + path)

    def wait_for(self, by, value, timeout=8):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def wait_for_visible(self, by, value, timeout=8):
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )

    def wait_for_url_contains(self, fragment, timeout=8):
        WebDriverWait(self.driver, timeout).until(EC.url_contains(fragment))

    def wait_for_text(self, by, value, text, timeout=8):
        return WebDriverWait(self.driver, timeout).until(
            EC.text_to_be_present_in_element((by, value), text)
        )

    def element_exists(self, by, value):
        try:
            self.driver.find_element(by, value)
            return True
        except NoSuchElementException:
            return False

    # auth

    def selenium_login(self, username, password):
        self.go('/login/')
        self.driver.find_element(By.NAME, 'username').send_keys(username)
        self.driver.find_element(By.NAME, 'password').send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        WebDriverWait(self.driver, 8).until(
            lambda d: '/login/' not in d.current_url or 'messages' in d.page_source
        )

    def selenium_logout(self):
        self.go('/logout/')
