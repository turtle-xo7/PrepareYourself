from django.contrib import admin
from .models import Board, Subject, Class, Question, UserProfile
from django.contrib import admin
from .models import Board, Subject, Class, Question, UserProfile, PracticalVideo
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_admin')
    list_editable = ('is_admin',)

# ---------- BOARD ----------
@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'student_count', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)


# ---------- SUBJECT ----------
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'color', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)


# ---------- CLASS ----------
@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# ---------- QUESTION ----------
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'chapter', 'subject', 'board',
        'class_obj', 'year', 'question_type', 'difficulty'
    )
    list_filter = ('board', 'subject', 'class_obj', 'question_type', 'difficulty')
    search_fields = ('chapter', 'question_text')
    list_per_page = 20

    fieldsets = (
        ('Basic Info', {
            'fields': ('board', 'subject', 'class_obj', 'year', 'chapter')
        }),
        ('Question', {
            'fields': ('question_text', 'question_type', 'difficulty')
        }),
        ('MCQ Options', {
            'fields': ('option1', 'option2', 'option3', 'option4', 'correct_option')
        }),
        ('Written Answer', {
            'fields': ('answer_hint',)
        }),
    )

@admin.register(PracticalVideo)
class PracticalVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'class_obj', 'is_active')
    list_filter = ('subject', 'class_obj', 'is_active')
    list_editable = ('is_active',)