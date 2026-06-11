from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import (
    Board, Subject, Class, Question, UserProfile,
    UserProgress, StudyNote, TeacherFeedback, Contest,
    ContestQuestion, ContestSubmission, NoteBookmark,
    NoteComment, Syllabus
)
from django.utils import timezone
import datetime


# -------- HELPER --------

def create_student(username='student1', email='student@test.com', plan='PREMIUM'):
    user = User.objects.create_user(username=username, email=email, password='testpass123')
    UserProfile.objects.create(user=user, role='STUDENT', plan=plan)
    return user

def create_teacher(username='teacher1', email='teacher@test.com'):
    user = User.objects.create_user(username=username, email=email, password='testpass123')
    UserProfile.objects.create(user=user, role='ADMIN', plan='FREE')
    return user

def create_superadmin(username='superadmin1'):
    user = User.objects.create_user(username=username, email='admin@test.com', password='testpass123')
    UserProfile.objects.create(user=user, role='ADMIN', plan='FREE', is_superadmin=True)
    return user

def create_board():
    return Board.objects.create(name='Dhaka Board', student_count='100000', is_active=True)

def create_subject():
    return Subject.objects.create(name='Physics', icon='⚛️', color='blue', is_active=True)

def create_class():
    return Class.objects.create(name='Class 9', numeric_value=9)

def create_question(board, subject, class_obj, year=2024):
    return Question.objects.create(
        board=board, subject=subject, class_obj=class_obj,
        year=year, chapter='Chapter 1',
        question_text='What is force?',
        question_type='MCQ', difficulty='Easy',
        option1='Push', option2='Pull', option3='Both', option4='None',
        correct_option=3,
        answer_hint='Force is push or pull.',
        is_active=True
    )


# -------- AUTH TESTS --------

class AuthTests(TestCase):

    def test_signup(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'testpass123',
            'role': 'STUDENT',
            'plan': 'FREE',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login(self):
        create_student()
        response = self.client.post(reverse('login'), {
            'username': 'student1',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_with_email(self):
        create_student(email='student@test.com')
        response = self.client.post(reverse('login'), {
            'username': 'student@test.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_wrong_password(self):
        create_student()
        response = self.client.post(reverse('login'), {
            'username': 'student1',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        create_student()
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    def test_signup_duplicate_username(self):
        create_student()
        response = self.client.post(reverse('signup'), {
            'username': 'student1',
            'email': 'other@test.com',
            'password': 'testpass123',
            'role': 'STUDENT',
            'plan': 'FREE',
        })
        self.assertEqual(User.objects.filter(username='student1').count(), 1)


# -------- RBAC TESTS --------

class RBACTests(TestCase):

    def test_student_cannot_access_manage(self):
        create_student()
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('manage_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_teacher_can_access_manage(self):
        create_teacher()
        self.client.login(username='teacher1', password='testpass123')
        response = self.client.get(reverse('manage_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_superadmin(self):
        create_student()
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_superadmin_can_access_superadmin(self):
        create_superadmin()
        self.client.login(username='superadmin1', password='testpass123')
        response = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_free_student_cannot_access_study_notes(self):
        create_student(plan='FREE')
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('study_notes'))
        self.assertEqual(response.status_code, 302)

    def test_premium_student_can_access_study_notes(self):
        create_student(plan='PREMIUM')
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('study_notes'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_can_access_study_notes(self):
        create_teacher()
        self.client.login(username='teacher1', password='testpass123')
        response = self.client.get(reverse('study_notes'))
        self.assertEqual(response.status_code, 200)


# -------- MANAGE (TEACHER ADMIN) TESTS --------

class ManageAdminTests(TestCase):

    def setUp(self):
        self.teacher = create_teacher()
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.client.login(username='teacher1', password='testpass123')

    def test_board_add_duplicate_rejected(self):
        response = self.client.post(reverse('board_add'), {'name': 'dhaka board'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Board.objects.count(), 1)

    def test_board_add_empty_name_rejected(self):
        response = self.client.post(reverse('board_add'), {'name': '   '})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Board.objects.count(), 1)

    def test_subject_add_duplicate_rejected(self):
        self.client.post(reverse('subject_add'), {'name': 'Physics'})
        self.assertEqual(Subject.objects.count(), 1)

    def test_class_add_non_numeric_sort_rejected(self):
        response = self.client.post(reverse('class_add'), {'name': 'Class 10', 'numeric_value': 'abc'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Class.objects.count(), 1)

    def test_class_add_duplicate_sort_rejected(self):
        self.client.post(reverse('class_add'), {'name': 'Class Nine', 'numeric_value': '9'})
        self.assertEqual(Class.objects.count(), 1)

    def test_video_delete_requires_post(self):
        from .models import PracticalVideo
        video = PracticalVideo.objects.create(
            title='Demo', youtube_url='https://youtu.be/dQw4w9WgXcQ',
            subject=self.subject, class_obj=self.class_obj,
        )
        self.client.get(reverse('video_delete', kwargs={'pk': video.pk}))
        self.assertTrue(PracticalVideo.objects.filter(pk=video.pk).exists())
        self.client.post(reverse('video_delete', kwargs={'pk': video.pk}))
        self.assertFalse(PracticalVideo.objects.filter(pk=video.pk).exists())

    def test_claim_cq_is_exclusive(self):
        from .models import ExamPaper, ExamAttempt
        student = create_student()
        paper = ExamPaper.objects.create(
            title='Model Test', subject=self.subject,
            class_obj=self.class_obj, created_by=self.teacher,
        )
        attempt = ExamAttempt.objects.create(
            exam_paper=paper, student=student, status='CQ_PENDING',
        )
        self.client.post(reverse('claim_cq_attempt', kwargs={'attempt_id': attempt.pk}))
        attempt.refresh_from_db()
        self.assertEqual(attempt.assigned_teacher, self.teacher)

        teacher2 = create_teacher(username='teacher2', email='t2@test.com')
        self.client.logout()
        self.client.login(username='teacher2', password='testpass123')
        self.client.post(reverse('claim_cq_attempt', kwargs={'attempt_id': attempt.pk}))
        attempt.refresh_from_db()
        self.assertEqual(attempt.assigned_teacher, self.teacher)  # still teacher1

    def test_teacher_dashboard_renders_with_activity(self):
        student = create_student()
        q = create_question(self.board, self.subject, self.class_obj)
        UserProgress.objects.create(user=student, question=q, is_correct=True)
        response = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['daily_data']), 7)
        self.assertEqual(len(response.context['heatmap_days']), 30)
        self.assertEqual(response.context['daily_data'][-1]['count'], 1)

    def test_student_detail_renders_with_activity(self):
        student = create_student()
        q = create_question(self.board, self.subject, self.class_obj)
        UserProgress.objects.create(user=student, question=q, is_correct=True)
        response = self.client.get(reverse('student_detail', kwargs={'pk': student.profile.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_answered'], 1)
        self.assertEqual(response.context['streak'], 1)
        self.assertEqual(response.context['difficulty_data']['Easy']['correct'], 1)

    def test_manage_questions_filter_and_pagination(self):
        create_question(self.board, self.subject, self.class_obj)
        for year in range(1990, 2024):
            create_question(self.board, self.subject, self.class_obj, year=year)
        page1 = self.client.get(reverse('manage_questions'))
        self.assertEqual(len(page1.context['questions']), 30)
        self.assertEqual(page1.context['total_matched'], 35)
        page2 = self.client.get(reverse('manage_questions') + '?page=2')
        self.assertEqual(len(page2.context['questions']), 5)
        filtered = self.client.get(reverse('manage_questions') + '?type=WRITTEN')
        self.assertEqual(filtered.context['total_matched'], 0)
        searched = self.client.get(reverse('manage_questions') + '?q=force')
        self.assertEqual(searched.context['total_matched'], 35)


# -------- QUESTION BANK TESTS --------

class QuestionBankTests(TestCase):

    def setUp(self):
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.question = create_question(self.board, self.subject, self.class_obj)

    def test_question_bank_visible_to_all(self):
        response = self.client.get(reverse('question_bank'))
        self.assertEqual(response.status_code, 200)

    def test_free_user_sees_limited_questions(self):
        create_student(plan='FREE')
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('question_bank'))
        self.assertLessEqual(len(response.context['questions']), 10)

    def test_premium_user_sees_all_questions(self):
        create_student(plan='PREMIUM')
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('question_bank'))
        self.assertGreaterEqual(len(response.context['questions']), 1)

    def test_premium_question_bank_paginated(self):
        # Distinct years — Question is unique on (board, subject, class, year, type).
        for year in range(1990, 2024):
            create_question(self.board, self.subject, self.class_obj, year=year)
        create_student(plan='PREMIUM')
        self.client.login(username='student1', password='testpass123')
        page1 = self.client.get(reverse('question_bank'))
        self.assertEqual(len(page1.context['questions']), 30)
        page2 = self.client.get(reverse('question_bank') + '?page=2')
        self.assertEqual(len(page2.context['questions']), 5)
        self.assertEqual(page2.context['page_obj'].number, 2)

    def test_filter_by_board(self):
        response = self.client.get(reverse('question_bank') + f'?board={self.board.pk}')
        self.assertEqual(response.status_code, 200)

    def test_filter_by_subject(self):
        response = self.client.get(reverse('question_bank') + f'?subject={self.subject.pk}')
        self.assertEqual(response.status_code, 200)


# -------- PROGRESS TRACKING TESTS --------

class ProgressTests(TestCase):

    def setUp(self):
        self.student = create_student()
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.question = create_question(self.board, self.subject, self.class_obj)
        self.client.login(username='student1', password='testpass123')

    def test_track_progress(self):
        import json
        response = self.client.post(
            reverse('track_progress'),
            json.dumps({'question_id': self.question.pk, 'is_correct': True}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProgress.objects.filter(user=self.student, question=self.question).exists())

    def test_progress_not_duplicated(self):
        import json
        self.client.post(
            reverse('track_progress'),
            json.dumps({'question_id': self.question.pk, 'is_correct': True}),
            content_type='application/json'
        )
        self.client.post(
            reverse('track_progress'),
            json.dumps({'question_id': self.question.pk, 'is_correct': False}),
            content_type='application/json'
        )
        self.assertEqual(UserProgress.objects.filter(user=self.student, question=self.question).count(), 1)

    def test_dashboard_loads(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_progress_history_loads(self):
        response = self.client.get(reverse('progress_history'))
        self.assertEqual(response.status_code, 200)


# -------- STUDY NOTES TESTS --------

class StudyNoteTests(TestCase):

    def setUp(self):
        self.teacher = create_teacher()
        self.student = create_student()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.client.login(username='teacher1', password='testpass123')
        self.note = StudyNote.objects.create(
            title='Test Note',
            subject=self.subject,
            class_obj=self.class_obj,
            chapter='Chapter 1',
            content='Test content',
            created_by=self.teacher,
            is_active=True
        )

    def test_teacher_can_add_note(self):
        response = self.client.post(reverse('study_note_add'), {
            'title': 'New Note',
            'subject': self.subject.pk,
            'class_obj': self.class_obj.pk,
            'chapter': 'Chapter 2',
            'content': 'Some content',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StudyNote.objects.filter(title='New Note').exists())

    def test_teacher_can_edit_note(self):
        response = self.client.post(reverse('study_note_edit', kwargs={'pk': self.note.pk}), {
            'title': 'Updated Note',
            'subject': self.subject.pk,
            'class_obj': self.class_obj.pk,
            'chapter': 'Chapter 1',
            'content': 'Updated content',
        })
        self.assertEqual(response.status_code, 302)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, 'Updated Note')

    def test_teacher_can_delete_note(self):
        response = self.client.post(reverse('study_note_delete', kwargs={'pk': self.note.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StudyNote.objects.filter(pk=self.note.pk).exists())

    def test_student_can_bookmark(self):
        self.client.login(username='student1', password='testpass123')
        response = self.client.post(reverse('toggle_bookmark', kwargs={'pk': self.note.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(NoteBookmark.objects.filter(user=self.student, note=self.note).exists())

    def test_student_can_unbookmark(self):
        self.client.login(username='student1', password='testpass123')
        NoteBookmark.objects.create(user=self.student, note=self.note)
        response = self.client.post(reverse('toggle_bookmark', kwargs={'pk': self.note.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NoteBookmark.objects.filter(user=self.student, note=self.note).exists())

    def test_student_comment_pending(self):
        self.client.login(username='student1', password='testpass123')
        response = self.client.post(reverse('add_comment', kwargs={'pk': self.note.pk}), {
            'comment': 'Great note!'
        })
        self.assertEqual(response.status_code, 302)
        comment = NoteComment.objects.filter(note=self.note, user=self.student).first()
        self.assertFalse(comment.is_approved)

    def test_teacher_comment_auto_approved(self):
        response = self.client.post(reverse('add_comment', kwargs={'pk': self.note.pk}), {
            'comment': 'Teacher comment'
        })
        self.assertEqual(response.status_code, 302)
        comment = NoteComment.objects.filter(note=self.note, user=self.teacher).first()
        self.assertTrue(comment.is_approved)

    def test_teacher_can_approve_comment(self):
        self.client.login(username='student1', password='testpass123')
        self.client.post(reverse('add_comment', kwargs={'pk': self.note.pk}), {
            'comment': 'Student comment'
        })
        comment = NoteComment.objects.filter(note=self.note).first()
        self.client.login(username='teacher1', password='testpass123')
        response = self.client.post(reverse('approve_comment', kwargs={'comment_pk': comment.pk}))
        self.assertEqual(response.status_code, 302)
        comment.refresh_from_db()
        self.assertTrue(comment.is_approved)


# -------- TEACHER FEEDBACK TESTS --------

class TeacherFeedbackTests(TestCase):

    def setUp(self):
        self.teacher = create_teacher()
        self.student = create_student()
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.question = create_question(self.board, self.subject, self.class_obj)
        self.progress = UserProgress.objects.create(
            user=self.student,
            question=self.question,
            is_correct=False
        )
        self.client.login(username='teacher1', password='testpass123')

    def test_teacher_can_give_feedback(self):
        response = self.client.post(
            reverse('give_feedback', kwargs={'progress_pk': self.progress.pk}),
            {'comment': 'Good try!'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TeacherFeedback.objects.filter(
            teacher=self.teacher, student=self.student
        ).exists())

    def test_feedback_marked_as_read(self):
        TeacherFeedback.objects.create(
            teacher=self.teacher,
            student=self.student,
            progress=self.progress,
            comment='Good try!',
            is_read=False
        )
        self.client.login(username='student1', password='testpass123')
        self.client.get(reverse('notifications'))
        feedback = TeacherFeedback.objects.get(teacher=self.teacher, student=self.student)
        self.assertTrue(feedback.is_read)

    def test_notifications_paginated(self):
        from .models import Notification
        for i in range(30):
            Notification.objects.create(
                recipient=self.student, notif_type='note',
                title=f'Notif {i}', message='hello',
            )
        self.client.login(username='student1', password='testpass123')
        page1 = self.client.get(reverse('notifications'))
        self.assertEqual(len(page1.context['notifications']), 25)
        page2 = self.client.get(reverse('notifications') + '?page=2')
        self.assertEqual(len(page2.context['notifications']), 5)


# -------- CONTEST TESTS --------

class ContestTests(TestCase):

    def setUp(self):
        # The leaderboard JSON endpoint caches rows per contest pk; pks repeat
        # across test cases, so start each test with a clean cache.
        from django.core.cache import cache
        cache.clear()
        self.teacher = create_teacher()
        self.student = create_student()
        self.subject = create_subject()
        self.class_obj = create_class()
        now = timezone.now()
        self.contest = Contest.objects.create(
            title='Test Contest',
            created_by=self.teacher,
            subject=self.subject,
            class_obj=self.class_obj,
            duration_minutes=30,
            start_time=now - datetime.timedelta(minutes=5),
            end_time=now + datetime.timedelta(hours=1),
            is_active=True
        )
        self.cq = ContestQuestion.objects.create(
            contest=self.contest,
            question_text='What is 2+2?',
            question_type='MCQ',
            option1='3', option2='4', option3='5', option4='6',
            correct_option=2,
            marks=1
        )

    def test_contest_list_loads(self):
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('contest_list'))
        self.assertEqual(response.status_code, 200)

    def test_student_can_join_contest(self):
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('contest_join', kwargs={'pk': self.contest.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ContestSubmission.objects.filter(
            contest=self.contest, student=self.student
        ).exists())

    def test_student_can_submit_contest(self):
        self.client.login(username='student1', password='testpass123')
        ContestSubmission.objects.create(
            contest=self.contest,
            student=self.student
        )
        response = self.client.post(
            reverse('contest_submit', kwargs={'pk': self.contest.pk}),
            {f'q_{self.cq.pk}': '2'}
        )
        self.assertEqual(response.status_code, 302)
        submission = ContestSubmission.objects.get(contest=self.contest, student=self.student)
        self.assertTrue(submission.is_submitted)
        self.assertEqual(submission.total_marks, 1)

    def test_leaderboard_loads(self):
        self.client.login(username='student1', password='testpass123')
        response = self.client.get(reverse('contest_leaderboard', kwargs={'pk': self.contest.pk}))
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_data_is_me_correct_per_viewer(self):
        """Cached leaderboard rows must not leak one viewer's is_me flag to another."""
        student2 = create_student(username='student2', email='s2@test.com')
        for s in (self.student, student2):
            ContestSubmission.objects.create(
                contest=self.contest, student=s, is_submitted=True,
                total_marks=1, duration_taken=60,
            )
        url = reverse('leaderboard_data', kwargs={'pk': self.contest.pk})
        self.client.login(username='student1', password='testpass123')
        rows1 = self.client.get(url).json()['rows']
        self.client.logout()
        # Second request is served from the cache populated by the first.
        self.client.login(username='student2', password='testpass123')
        rows2 = self.client.get(url).json()['rows']
        self.assertEqual([r['username'] for r in rows1 if r['is_me']], ['student1'])
        self.assertEqual([r['username'] for r in rows2 if r['is_me']], ['student2'])
        self.assertEqual(len(rows1), 2)

    def test_teacher_can_delete_contest(self):
        self.client.login(username='teacher1', password='testpass123')
        response = self.client.post(reverse('contest_delete', kwargs={'pk': self.contest.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Contest.objects.filter(pk=self.contest.pk).exists())


# -------- PROFILE TESTS --------

class ProfileTests(TestCase):

    def setUp(self):
        self.student = create_student()
        self.client.login(username='student1', password='testpass123')

    def test_profile_page_loads(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        response = self.client.post(reverse('profile_update'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@test.com',
        })
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'John')
        self.assertEqual(self.student.email, 'john@test.com')


# -------- SYLLABUS TESTS --------

class SyllabusTests(TestCase):

    def setUp(self):
        self.teacher = create_teacher()
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        self.client.login(username='teacher1', password='testpass123')

    def test_syllabus_list_loads(self):
        response = self.client.get(reverse('syllabus_list'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_can_add_syllabus(self):
        response = self.client.post(reverse('syllabus_add'), {
            'board': self.board.pk,
            'subject': self.subject.pk,
            'class_obj': self.class_obj.pk,
            'content': 'Chapter 1, Chapter 2',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Syllabus.objects.filter(subject=self.subject).exists())

    def test_teacher_can_delete_syllabus(self):
        syllabus = Syllabus.objects.create(
            subject=self.subject,
            class_obj=self.class_obj,
            board=self.board,
            content='Test content'
        )
        response = self.client.post(reverse('syllabus_delete', kwargs={'pk': syllabus.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Syllabus.objects.filter(pk=syllabus.pk).exists())


# -------- SUPERADMIN TESTS --------

class SuperAdminTests(TestCase):

    def setUp(self):
        self.superadmin = create_superadmin()
        self.student = create_student()
        self.client.login(username='superadmin1', password='testpass123')

    def test_superadmin_dashboard_loads(self):
        response = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_superadmin_can_update_user(self):
        profile = self.student.profile
        response = self.client.post(
            reverse('update_user', kwargs={'pk': profile.pk}),
            {'role': 'ADMIN', 'plan': 'PREMIUM'}
        )
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.plan, 'PREMIUM')

    def test_superadmin_can_cancel_subscription(self):
        profile = self.student.profile
        profile.plan = 'PREMIUM'
        profile.save()
        response = self.client.post(
            reverse('cancel_subscription', kwargs={'pk': profile.pk})
        )
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.plan, 'FREE')

    def test_superadmin_can_delete_user(self):
        profile = self.student.profile
        response = self.client.post(
            reverse('delete_user', kwargs={'pk': profile.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='student1').exists())

    def test_update_user_rejects_invalid_role(self):
        profile = self.student.profile
        profile.plan = 'FREE'
        profile.save()
        # An invalid role must reject the whole update — plan stays FREE too.
        self.client.post(reverse('update_user', kwargs={'pk': profile.pk}),
                         {'role': 'HACKER', 'plan': 'PREMIUM'})
        profile.refresh_from_db()
        self.assertEqual(profile.role, 'STUDENT')
        self.assertEqual(profile.plan, 'FREE')

    def test_superadmin_account_protected_from_update_and_delete(self):
        sa_profile = self.superadmin.profile
        self.client.post(reverse('update_user', kwargs={'pk': sa_profile.pk}),
                         {'role': 'STUDENT', 'plan': 'FREE'})
        sa_profile.refresh_from_db()
        self.assertEqual(sa_profile.role, 'ADMIN')
        self.client.post(reverse('delete_user', kwargs={'pk': sa_profile.pk}))
        self.assertTrue(User.objects.filter(username='superadmin1').exists())

    def test_cancel_subscription_clears_expiry(self):
        profile = self.student.profile
        profile.plan = 'PREMIUM'
        profile.plan_expires_at = timezone.now() + datetime.timedelta(days=30)
        profile.save()
        self.client.post(reverse('cancel_subscription', kwargs={'pk': profile.pk}))
        profile.refresh_from_db()
        self.assertEqual(profile.plan, 'FREE')
        self.assertIsNone(profile.plan_expires_at)

    def test_approve_teacher_requires_post(self):
        teacher = create_teacher(username='applicant', email='app@test.com')
        teacher.profile.is_approved = False
        teacher.profile.save()
        self.client.get(reverse('approve_teacher', kwargs={'pk': teacher.profile.pk}))
        teacher.profile.refresh_from_db()
        self.assertFalse(teacher.profile.is_approved)
        self.client.post(reverse('approve_teacher', kwargs={'pk': teacher.profile.pk}))
        teacher.profile.refresh_from_db()
        self.assertTrue(teacher.profile.is_approved)

    def test_dashboard_overview_context(self):
        response = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['signup_series']), 30)
        self.assertIn('total_users', response.context)
        self.assertIn('month_revenue', response.context)
        # the user table moved to its own page — the overview must not carry it
        self.assertNotIn('page_obj', response.context)

    def test_users_page_search_and_filters(self):
        create_student(username='findme', email='findme@test.com', plan='FREE')
        response = self.client.get(reverse('superadmin_users') + '?q=findme')
        self.assertEqual(response.context['total_matched'], 1)
        self.assertEqual(response.context['page_obj'].object_list[0].user.username, 'findme')
        response = self.client.get(reverse('superadmin_users') + '?plan=PREMIUM')
        usernames = [p.user.username for p in response.context['page_obj'].object_list]
        self.assertIn('student1', usernames)
        self.assertNotIn('findme', usernames)

    def test_users_page_pagination(self):
        for i in range(25):
            create_student(username=f'bulk{i}', email=f'bulk{i}@test.com')
        page1 = self.client.get(reverse('superadmin_users'))
        self.assertEqual(len(page1.context['page_obj'].object_list), 20)
        page2 = self.client.get(reverse('superadmin_users') + '?page=2')
        self.assertEqual(page2.context['page_obj'].number, 2)

    def test_revenue_page_stats(self):
        from .models import Payment
        Payment.objects.create(user=self.student, plan='PREMIUM', amount=199,
                               tran_id='t1', status='COMPLETED')
        Payment.objects.create(user=self.student, plan='BASIC', amount=99,
                               tran_id='t2', status='FAILED')
        response = self.client.get(reverse('superadmin_revenue'))
        self.assertEqual(response.context['total_revenue'], 199)
        self.assertEqual(response.context['payment_count'], 1)
        self.assertEqual(len(response.context['revenue_series']), 6)

    def test_export_excel(self):
        response = self.client.get(reverse('export_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

