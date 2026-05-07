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


# -------- EXAM MODE --------
from .models import ExamPaper, ExamPaperMCQ, CQQuestion, ExamAttempt, CQSubmission


class ExamPaperMCQInline(admin.TabularInline):
    model = ExamPaperMCQ
    extra = 1
    fields = ('order', 'question_text', 'option1', 'option2', 'option3', 'option4', 'correct_option', 'marks')


class CQQuestionInline(admin.TabularInline):
    model = CQQuestion
    extra = 1
    fields = ('order', 'question_text', 'part_a', 'part_b', 'part_c', 'part_d',
              'marks_a', 'marks_b', 'marks_c', 'marks_d')


@admin.register(ExamPaper)
class ExamPaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'class_obj', 'board', 'year', 'mcq_count', 'cq_count', 'is_active', 'created_at')
    list_filter = ('subject', 'class_obj', 'board', 'is_active')
    search_fields = ('title',)
    list_editable = ('is_active',)
    list_per_page = 20
    inlines = [ExamPaperMCQInline, CQQuestionInline]
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Paper Info', {
            'fields': ('title', 'subject', 'class_obj', 'board', 'year', 'is_active', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='MCQ')
    def mcq_count(self, obj):
        return obj.mcqs.count()

    @admin.display(description='CQ')
    def cq_count(self, obj):
        return obj.cqs.count()


@admin.register(ExamPaperMCQ)
class ExamPaperMCQAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam_paper', 'order', 'question_short', 'correct_option', 'marks')
    list_filter = ('exam_paper',)
    search_fields = ('question_text', 'exam_paper__title')
    list_per_page = 30

    @admin.display(description='প্রশ্ন')
    def question_short(self, obj):
        return obj.question_text[:60] + '…' if len(obj.question_text) > 60 else obj.question_text


@admin.register(CQQuestion)
class CQQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam_paper', 'order', 'stimulus_short', 'total_marks')
    list_filter = ('exam_paper',)
    search_fields = ('question_text', 'exam_paper__title')
    list_per_page = 20

    fieldsets = (
        ('Paper & Order', {'fields': ('exam_paper', 'order')}),
        ('উদ্দীপক', {'fields': ('question_text',)}),
        ('অংশ ও নম্বর', {
            'fields': (
                ('part_a', 'marks_a'),
                ('part_b', 'marks_b'),
                ('part_c', 'marks_c'),
                ('part_d', 'marks_d'),
            )
        }),
    )

    @admin.display(description='উদ্দীপক')
    def stimulus_short(self, obj):
        return obj.question_text[:70] + '…' if len(obj.question_text) > 70 else obj.question_text

    @admin.display(description='মোট নম্বর')
    def total_marks(self, obj):
        return obj.marks_a + obj.marks_b + obj.marks_c + obj.marks_d


class CQSubmissionInline(admin.TabularInline):
    model = CQSubmission
    extra = 0
    readonly_fields = ('cq_question', 'photo', 'photo_a', 'photo_b', 'photo_c', 'photo_d', 'uploaded_at')
    fields = ('cq_question', 'photo', 'marks_given', 'teacher_comment', 'uploaded_at')
    can_delete = False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'student', 'exam_paper', 'status', 'mcq_score',
        'cq_score', 'total_score', 'grade', 'started_at'
    )
    list_filter = ('status', 'exam_paper', 'grade')
    search_fields = ('student__username', 'exam_paper__title')
    readonly_fields = (
        'student', 'exam_paper', 'started_at', 'mcq_submitted_at',
        'cq_started_at', 'cq_submitted_at', 'mcq_answers', 'selected_cqs',
        'graded_by', 'graded_at',
    )
    list_per_page = 25
    inlines = [CQSubmissionInline]

    fieldsets = (
        ('Attempt Info', {
            'fields': ('student', 'exam_paper', 'status')
        }),
        ('Scores & Grade', {
            'fields': ('mcq_score', 'cq_score', 'total_score', 'grade')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'mcq_submitted_at', 'cq_started_at', 'cq_submitted_at', 'graded_at'),
            'classes': ('collapse',),
        }),
        ('Raw Data', {
            'fields': ('mcq_answers', 'selected_cqs', 'graded_by'),
            'classes': ('collapse',),
        }),
    )


@admin.register(CQSubmission)
class CQSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student_name', 'paper_name', 'cq_question', 'marks_given', 'uploaded_at')
    list_filter = ('attempt__exam_paper',)
    search_fields = ('attempt__student__username', 'attempt__exam_paper__title')
    readonly_fields = ('attempt', 'cq_question', 'photo', 'photo_a', 'photo_b', 'photo_c', 'photo_d', 'uploaded_at')
    list_per_page = 25

    @admin.display(description='শিক্ষার্থী')
    def student_name(self, obj):
        return obj.attempt.student.username

    @admin.display(description='Paper')
    def paper_name(self, obj):
        return obj.attempt.exam_paper.title