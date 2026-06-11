import re

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Board(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    student_count = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['name']
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=10, blank=True)
    color = models.CharField(max_length=20, default='blue')
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['name']
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name


class Class(models.Model):
    name = models.CharField(max_length=20, unique=True)
    numeric_value = models.IntegerField(unique=True)
    class Meta:
        ordering = ['numeric_value']
        verbose_name_plural = 'Classes'
    def __str__(self):
        return self.name


class Question(models.Model):
    DIFFICULTY_CHOICES = [('Easy','Easy'),('Medium','Medium'),('Hard','Hard')]
    QUESTION_TYPE_CHOICES = [('MCQ','Multiple Choice'),('WRITTEN','Written')]
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='questions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='questions')
    year = models.IntegerField()
    chapter = models.CharField(max_length=200)
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='MCQ')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    option1 = models.CharField(max_length=500, blank=True)
    option2 = models.CharField(max_length=500, blank=True)
    option3 = models.CharField(max_length=500, blank=True)
    option4 = models.CharField(max_length=500, blank=True)
    correct_option = models.PositiveSmallIntegerField(null=True, blank=True)
    part_a = models.TextField(blank=True)
    part_b = models.TextField(blank=True)
    part_c = models.TextField(blank=True)
    part_d = models.TextField(blank=True)
    marks_a = models.IntegerField(default=1)
    marks_b = models.IntegerField(default=2)
    marks_c = models.IntegerField(default=3)
    marks_d = models.IntegerField(default=4)
    answer_hint = models.TextField(blank=True)
    stimulus_image = models.FileField(upload_to='question_stimuli/', null=True, blank=True)
    solution_image = models.FileField(upload_to='question_solutions/', null=True, blank=True)
    mcq_question_file = models.FileField(upload_to='question_mcq/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['-year', 'subject', 'chapter']
        constraints = [
            models.UniqueConstraint(
                fields=['board', 'subject', 'class_obj', 'year', 'question_type'],
                name='unique_question_per_board_subject_class_year_type',
            ),
        ]

    def __str__(self):
        return self.chapter

    IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')

    @property
    def stimulus_is_image(self):
        return bool(self.stimulus_image) and self.stimulus_image.name.lower().endswith(self.IMAGE_EXTS)

    @property
    def solution_is_image(self):
        return bool(self.solution_image) and self.solution_image.name.lower().endswith(self.IMAGE_EXTS)

    @property
    def mcq_question_is_image(self):
        return bool(self.mcq_question_file) and self.mcq_question_file.name.lower().endswith(self.IMAGE_EXTS)


class UserProfile(models.Model):
    ROLE_CHOICES = [('STUDENT','Student'),('ADMIN','Teacher/Tutor/Institution')]
    PLAN_CHOICES = [('FREE','Free'),('BASIC','Basic'),('PREMIUM','Premium')]
    LANG_CHOICES = [('bn', 'বাংলা'), ('en', 'English')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='FREE')
    plan_expires_at = models.DateTimeField(null=True, blank=True)
    # Onboarding / personalization
    board = models.ForeignKey('Board', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    class_obj = models.ForeignKey('Class', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    study_subjects = models.ManyToManyField('Subject', blank=True, related_name='enrolled_students')
    exam_goal = models.CharField(max_length=120, blank=True)
    onboarded = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=5, choices=LANG_CHOICES, default='bn')
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_approved = models.BooleanField(default=True)
    teacher_bio = models.TextField(blank=True)
    subject_expertise = models.CharField(max_length=200, blank=True)
    subjects = models.ManyToManyField('Subject', blank=True, related_name='teachers')
    nid_document = models.FileField(upload_to='teacher_docs/nid/', blank=True, null=True)
    qualification_document = models.FileField(upload_to='teacher_docs/qual/', blank=True, null=True)
    rejection_reason = models.TextField(blank=True)
    def __str__(self):
        return self.user.username
    @property
    def is_premium(self):
        if self.plan not in ['BASIC', 'PREMIUM']:
            return False
        # No expiry set = lifetime/admin-granted; otherwise must be in the future
        if self.plan_expires_at is None:
            return True
        from django.utils import timezone
        return self.plan_expires_at > timezone.now()


class Payment(models.Model):
    """Audit record for every subscription payment attempt.
    Gateway-agnostic: gateway='simulation' for now; swap in 'sslcommerz' etc. later."""
    STATUS_CHOICES = [('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')]
    PLAN_CHOICES = [('BASIC', 'Basic'), ('PREMIUM', 'Premium')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES)
    amount = models.PositiveIntegerField()                      # in BDT (৳)
    method = models.CharField(max_length=20, blank=True)        # bkash / nagad / rocket / card
    tran_id = models.CharField(max_length=64, unique=True)      # our transaction id
    gateway = models.CharField(max_length=30, default='simulation')
    val_id = models.CharField(max_length=120, blank=True)       # gateway validation id (real gateway)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} · {self.plan} · ৳{self.amount} · {self.status}"


class PracticalVideo(models.Model):
    title = models.CharField(max_length=200)
    youtube_url = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='videos')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='videos')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return self.title

    @property
    def video_id(self):
        raw = (self.youtube_url or '').strip()
        m = re.search(
            r'(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|v/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})',
            raw,
        )
        if m:
            return m.group(1)
        m = re.match(r'([A-Za-z0-9_-]{11})', raw)
        return m.group(1) if m else raw

    @property
    def thumbnail_url(self):
        return f'https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg'


class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-answered_at']
    def __str__(self):
        return f"{self.user.username} - {self.question.id}"


class WrittenSolveSubmission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='written_solves')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='written_submissions')
    photo_ka = models.ImageField(upload_to='written_solves/', null=True, blank=True)
    photo_kha = models.ImageField(upload_to='written_solves/', null=True, blank=True)
    photo_ga = models.ImageField(upload_to='written_solves/', null=True, blank=True)
    photo_gha = models.ImageField(upload_to='written_solves/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'question']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} — Q{self.question.id}"

    @property
    def is_complete(self):
        return bool(self.photo_ka and self.photo_kha and self.photo_ga and self.photo_gha)


class TeacherFeedback(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks_given')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks_received')
    progress = models.ForeignKey(UserProgress, on_delete=models.CASCADE, related_name='feedbacks')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.teacher.username} → {self.student.username}"


class StudyNote(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='notes')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='notes')
    chapter = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='notes/pdfs/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return self.title


class NoteBookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    note = models.ForeignKey(StudyNote, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ['user', 'note']
    def __str__(self):
        return f"{self.user.username} → {self.note.title}"


class NoteReadProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='note_progress')
    note = models.ForeignKey(StudyNote, on_delete=models.CASCADE, related_name='read_progress')
    scroll_percent = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    last_read = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ['user', 'note']
    def __str__(self):
        return f"{self.user.username} → {self.note.title} ({self.scroll_percent}%)"


class Syllabus(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='syllabi')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='syllabi')
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='syllabi')
    content = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ['subject', 'class_obj', 'board']
        ordering = ['subject__name']
    def __str__(self):
        return f"{self.subject.name} - {self.class_obj.name} - {self.board.name}"


class NoteComment(models.Model):
    note = models.ForeignKey(StudyNote, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='note_comments')
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.user.username} → {self.note.title}"


class Contest(models.Model):
    CONTEST_TYPE = [
        ('standard',  'Standard Timed'),
        ('long',      'Long Challenge'),
        ('marathon',  'Marathon'),
        ('subject',   'Subject Sprint'),
        ('grand',     'Grand Contest'),
        ('practice',  'Practice / Unrated'),
    ]
    DIFFICULTY = [
        ('beginner',     'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced',     'Advanced'),
        ('open',         'Open for All'),
    ]
    ENTRY_REQ = [
        ('open',     'Open to All'),
        ('premium',  'Premium Members Only'),
        ('class_9',  'Class 9 Only'),
        ('class_10', 'Class 10 Only'),
        ('class_11', 'Class 11 Only'),
        ('class_12', 'Class 12 Only'),
    ]

    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contests')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='contests')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='contests')
    duration_minutes = models.IntegerField(default=30)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    description = models.TextField(blank=True)
    contest_type = models.CharField(max_length=20, choices=CONTEST_TYPE, default='standard')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY, default='open')
    entry_requirement = models.CharField(max_length=20, choices=ENTRY_REQ, default='open')
    is_featured = models.BooleanField(default=False)
    is_rated = models.BooleanField(default=True)
    allow_unrated_join = models.BooleanField(default=True)
    max_participants = models.IntegerField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    prize_description = models.TextField(blank=True)
    sponsor_name = models.CharField(max_length=200, blank=True)
    tags = models.CharField(max_length=500, blank=True)
    view_count = models.IntegerField(default=0)
    hide_leaderboard_until_end = models.BooleanField(default=False)
    is_multi_stage = models.BooleanField(default=False)
    stage_number = models.IntegerField(default=1)
    parent_contest = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='stages'
    )
    allows_virtual = models.BooleanField(default=True)
    ratings_calculated = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_live(self):
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    @property
    def is_upcoming(self):
        from django.utils import timezone
        return self.is_active and timezone.now() < self.start_time

    @property
    def is_past(self):
        from django.utils import timezone
        return timezone.now() > self.end_time

    @property
    def tag_list(self):
        return [t.strip() for t in (self.tags or '').split(',') if t.strip()]


class ContestQuestion(models.Model):
    QUESTION_TYPE = [('MCQ', 'MCQ'), ('CREATIVE', 'Creative/Written')]
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE, default='MCQ')
    option1 = models.CharField(max_length=500, blank=True)
    option2 = models.CharField(max_length=500, blank=True)
    option3 = models.CharField(max_length=500, blank=True)
    option4 = models.CharField(max_length=500, blank=True)
    correct_option = models.PositiveSmallIntegerField(null=True, blank=True)
    marks = models.IntegerField(default=1)
    def __str__(self):
        return f"{self.contest.title} - Q{self.id}"


class ContestSubmission(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contest_submissions')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    total_marks = models.IntegerField(default=0)
    is_submitted = models.BooleanField(default=False)
    duration_taken = models.IntegerField(default=0)
    is_virtual = models.BooleanField(default=False)
    is_rated_participant = models.BooleanField(default=True)
    rating_before = models.IntegerField(null=True, blank=True)
    rating_after = models.IntegerField(null=True, blank=True)
    rating_change = models.IntegerField(null=True, blank=True)
    rank_in_contest = models.IntegerField(null=True, blank=True)
    percentile = models.FloatField(null=True, blank=True)
    time_taken_seconds = models.IntegerField(null=True, blank=True)
    class Meta:
        unique_together = ['contest', 'student']
        ordering = ['-total_marks', 'duration_taken']
    def __str__(self):
        return f"{self.student.username} - {self.contest.title}"


class ContestAnswer(models.Model):
    submission = models.ForeignKey(ContestSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ContestQuestion, on_delete=models.CASCADE)
    mcq_answer = models.PositiveSmallIntegerField(null=True, blank=True)
    creative_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    marks_obtained = models.IntegerField(default=0)
    def __str__(self):
        return f"{self.submission.student.username} - Q{self.question.id}"


# -------- EXAM MODE MODELS --------

class ExamPaper(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exam_papers')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='exam_papers')
    board = models.ForeignKey(Board, on_delete=models.SET_NULL, null=True, blank=True, related_name='exam_papers')
    year = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_papers')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return self.title


class ExamPaperMCQ(models.Model):
    exam_paper = models.ForeignKey(ExamPaper, on_delete=models.CASCADE, related_name='mcqs')
    question_text = models.TextField()
    option1 = models.CharField(max_length=500)
    option2 = models.CharField(max_length=500)
    option3 = models.CharField(max_length=500)
    option4 = models.CharField(max_length=500)
    correct_option = models.PositiveSmallIntegerField()
    marks = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    class Meta:
        ordering = ['order', 'id']
    def __str__(self):
        return f"{self.exam_paper.title} - MCQ {self.id}"


class CQQuestion(models.Model):
    exam_paper = models.ForeignKey(ExamPaper, on_delete=models.CASCADE, related_name='cqs')
    question_text = models.TextField()
    part_a = models.TextField(blank=True)
    part_b = models.TextField(blank=True)
    part_c = models.TextField(blank=True)
    part_d = models.TextField(blank=True)
    marks_a = models.IntegerField(default=1)
    marks_b = models.IntegerField(default=2)
    marks_c = models.IntegerField(default=3)
    marks_d = models.IntegerField(default=4)
    order = models.IntegerField(default=0)
    class Meta:
        ordering = ['order', 'id']
    def __str__(self):
        return f"{self.exam_paper.title} - CQ {self.id}"


class ExamAttempt(models.Model):
    STATUS_CHOICES = [
        ('MCQ_PHASE', 'MCQ Phase'),
        ('MCQ_DONE', 'MCQ Done'),
        ('CQ_PHASE', 'CQ Phase'),
        ('CQ_PENDING', 'Pending Review'),
        ('GRADED', 'Graded'),
    ]
    exam_paper = models.ForeignKey(ExamPaper, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_attempts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='MCQ_PHASE')
    started_at = models.DateTimeField(auto_now_add=True)
    mcq_submitted_at = models.DateTimeField(null=True, blank=True)
    cq_started_at = models.DateTimeField(null=True, blank=True)
    cq_submitted_at = models.DateTimeField(null=True, blank=True)
    mcq_score = models.IntegerField(default=0)
    cq_score = models.IntegerField(null=True, blank=True)
    total_score = models.IntegerField(null=True, blank=True)
    grade = models.CharField(max_length=5, blank=True)
    mcq_answers = models.JSONField(default=dict)
    selected_cqs = models.JSONField(default=list)
    graded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='graded_attempts')
    graded_at = models.DateTimeField(null=True, blank=True)
    assigned_teacher = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='claimed_attempts')
    claimed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        unique_together = ['exam_paper', 'student']
        ordering = ['-started_at']
    def __str__(self):
        return f"{self.student.username} - {self.exam_paper.title}"

    @property
    def mcq_seconds_remaining(self):
        from django.utils import timezone
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return max(0, int(1800 - elapsed))

    @property
    def cq_seconds_remaining(self):
        from django.utils import timezone
        if not self.cq_started_at:
            return 9000
        elapsed = (timezone.now() - self.cq_started_at).total_seconds()
        return max(0, int(9000 - elapsed))


class CQSubmission(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='cq_submissions')
    cq_question = models.ForeignKey(CQQuestion, on_delete=models.CASCADE, related_name='submissions')
    photo = models.ImageField(upload_to='exam/cq_answers/', blank=True, null=True)
    photo_a = models.ImageField(upload_to='exam/cq_answers/', blank=True, null=True)
    photo_b = models.ImageField(upload_to='exam/cq_answers/', blank=True, null=True)
    photo_c = models.ImageField(upload_to='exam/cq_answers/', blank=True, null=True)
    photo_d = models.ImageField(upload_to='exam/cq_answers/', blank=True, null=True)
    marks_given = models.IntegerField(null=True, blank=True)
    teacher_comment = models.TextField(blank=True)
    marks_a = models.IntegerField(null=True, blank=True)
    marks_b = models.IntegerField(null=True, blank=True)
    marks_c = models.IntegerField(null=True, blank=True)
    marks_d = models.IntegerField(null=True, blank=True)
    comment_a = models.TextField(blank=True)
    comment_b = models.TextField(blank=True)
    comment_c = models.TextField(blank=True)
    comment_d = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ['attempt', 'cq_question']
    def __str__(self):
        return f"{self.attempt.student.username} - CQ{self.cq_question.id}"


class NoteRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('FULFILLED', 'Fulfilled'),
        ('REJECTED', 'Rejected'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='note_requests')
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='note_requests')
    topic = models.CharField(max_length=300)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_note = models.ForeignKey('StudyNote', on_delete=models.SET_NULL, null=True, blank=True, related_name='from_requests')
    fulfilled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='fulfilled_requests')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} — {self.topic}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('exam', 'Exam Paper'),
        ('contest', 'Contest'),
        ('note', 'Study Note'),
        ('request', 'Note Request'),
        ('question', 'New Question'),
        ('payment', 'Payment'),
    ]
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notif_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    title = models.CharField(max_length=300)
    message = models.TextField()
    title_bn = models.CharField(max_length=300, blank=True)
    message_bn = models.TextField(blank=True)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"


# -------- CONTEST RATING / BADGES / COINS --------

class UserRating(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rating_profile')
    rating = models.IntegerField(default=1000)
    peak_rating = models.IntegerField(default=1000)
    contests_entered = models.IntegerField(default=0)
    contests_rated = models.IntegerField(default=0)
    best_rank = models.IntegerField(null=True, blank=True)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_contest_date = models.DateField(null=True, blank=True)
    total_score_earned = models.IntegerField(default=0)
    coin_balance = models.IntegerField(default=0)
    last_checkin_date = models.DateField(null=True, blank=True)
    checkin_streak = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} ({self.rating})"

    @property
    def rank_title(self):
        thresholds = [
            (1800, "Legend",      "#FF0000", "★★★★★★★"),
            (1600, "Grandmaster", "#FF8C00", "★★★★★★"),
            (1400, "Master",      "#AA00AA", "★★★★★"),
            (1200, "Expert",      "#0000FF", "★★★★"),
            (1000, "Skilled",     "#008080", "★★★"),
            (800,  "Beginner",    "#008000", "★★"),
            (0,    "Newcomer",    "#808080", "★"),
        ]
        for threshold, title, color, stars in thresholds:
            if self.rating >= threshold:
                return {"title": title, "color": color, "stars": stars}
        return {"title": "Newcomer", "color": "#808080", "stars": "★"}

    @property
    def next_rank_info(self):
        thresholds = [800, 1000, 1200, 1400, 1600, 1800]
        for t in thresholds:
            if self.rating < t:
                return {"points_needed": t - self.rating, "next_threshold": t}
        return None


class Badge(models.Model):
    BADGE_TYPE = [
        ('contest',   'Contest Performance'),
        ('streak',    'Consistency Streak'),
        ('milestone', 'Participation Milestone'),
        ('rank',      'Rank Achievement'),
        ('subject',   'Subject Mastery'),
        ('special',   'Special / Seasonal'),
        ('early',     'Early Bird'),
        ('social',    'Community'),
    ]
    RARITY = [
        ('common',    'Common'),
        ('rare',      'Rare'),
        ('epic',      'Epic'),
        ('legendary', 'Legendary'),
    ]
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=100)
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPE)
    rarity = models.CharField(max_length=20, choices=RARITY)
    color_hex = models.CharField(max_length=7, default='#6c757d')
    earn_condition = models.TextField()
    earned_by_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['badge_type', 'rarity']

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earned_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    contest = models.ForeignKey(Contest, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


class ContestRatingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rating_history')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    old_rating = models.IntegerField()
    new_rating = models.IntegerField()
    change = models.IntegerField()
    rank = models.IntegerField()
    percentile = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['recorded_at']

    def __str__(self):
        return f"{self.user.username} {self.old_rating}->{self.new_rating}"


class VirtualContest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='virtual_contests')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='virtual_attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    virtual_rank = models.IntegerField(null=True, blank=True)
    score = models.IntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} virtual {self.contest.title}"


class ContestCoinLedger(models.Model):
    ACTION = [
        ('contest_participate', 'Contest Participation'),
        ('contest_top10pct',    'Top 10% Finish'),
        ('contest_top25pct',    'Top 25% Finish'),
        ('contest_top50pct',    'Top 50% Finish'),
        ('contest_win',         'Contest Win'),
        ('daily_checkin',       'Daily Check-in'),
        ('streak_7',            'Weekly Streak Bonus'),
        ('streak_30',           'Monthly Streak Bonus'),
        ('badge_earned',        'Badge Earned'),
        ('first_contest',       'First Contest'),
        ('early_bird',          'Early Registration'),
        ('virtual_complete',    'Virtual Contest Complete'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coin_ledger')
    action = models.CharField(max_length=40, choices=ACTION)
    amount = models.IntegerField()
    balance = models.IntegerField()
    contest = models.ForeignKey(Contest, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount >= 0 else ''
        return f"{self.user.username} {sign}{self.amount} ({self.action})"


class ContestRegistration(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contest_registrations')
    is_rated = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    is_early_bird = models.BooleanField(default=False)
    notified_start = models.BooleanField(default=False)

    class Meta:
        unique_together = ('contest', 'user')
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.user.username} -> {self.contest.title}"