from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Board(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    student_count = models.CharField(max_length=20, help_text="e.g., 5M+")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} Board"


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
        verbose_name_plural = "Classes"

    def __str__(self):
        return self.name


class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    QUESTION_TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice'),
        ('WRITTEN', 'Written'),
    ]

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
        return f"{self.board} | Class {self.class_obj.numeric_value} | {self.subject} | {self.chapter[:30]}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({'Admin' if self.is_admin else 'User'})"