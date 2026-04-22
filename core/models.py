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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return self.title