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
    answer_hint = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['-year', 'subject', 'chapter']
    def __str__(self):
        return self.chapter


class UserProfile(models.Model):
    ROLE_CHOICES = [('STUDENT','Student'),('ADMIN','Teacher/Tutor/Institution')]
    PLAN_CHOICES = [('FREE','Free'),('BASIC','Basic'),('PREMIUM','Premium')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='FREE')
    is_admin = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)
    def __str__(self):
        return self.user.username
    @property
    def is_premium(self):
        return self.plan in ['BASIC', 'PREMIUM']


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


class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-answered_at']
    def __str__(self):
        return f"{self.user.username} - {self.question.id}"


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
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contests')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='contests')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='contests')
    duration_minutes = models.IntegerField(default=30)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return self.title


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