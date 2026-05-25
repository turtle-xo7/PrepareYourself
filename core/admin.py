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

from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notif_type', 'title', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')
    search_fields = ('recipient__username', 'title')
    readonly_fields = ('recipient', 'notif_type', 'title', 'message', 'link', 'created_at')
    list_per_page = 50


# -------- CONTEST SYSTEM --------
from .models import (
    Contest, ContestQuestion, ContestSubmission,
    UserRating, Badge, UserBadge, ContestRatingHistory,
    ContestCoinLedger, VirtualContest, ContestRegistration,
)


class ContestQuestionInline(admin.TabularInline):
    model = ContestQuestion
    extra = 0
    fields = ('question_text', 'question_type', 'option1', 'option2',
              'option3', 'option4', 'correct_option', 'marks')


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'class_obj', 'contest_type', 'difficulty',
                    'is_featured', 'is_rated', 'start_time', 'end_time',
                    'ratings_calculated', 'view_count')
    list_filter = ('contest_type', 'difficulty', 'is_featured', 'is_rated',
                   'entry_requirement', 'is_active', 'ratings_calculated')
    search_fields = ('title', 'description', 'tags', 'sponsor_name')
    readonly_fields = ('view_count', 'created_at', 'ratings_calculated')
    actions = ['recalculate_ratings', 'mark_featured', 'unmark_featured']
    inlines = [ContestQuestionInline]

    @admin.action(description='Recalculate ratings + award coins/badges')
    def recalculate_ratings(self, request, queryset):
        from .services.rating import calculate_contest_ratings
        done = 0
        for c in queryset:
            calculate_contest_ratings(c.pk, force=True)
            done += 1
        self.message_user(request, f'Recalculated ratings for {done} contest(s).')

    @admin.action(description='Mark as featured')
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description='Remove featured flag')
    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)


@admin.register(ContestSubmission)
class ContestSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'contest', 'total_marks', 'rank_in_contest',
                    'rating_change', 'is_virtual', 'is_rated_participant',
                    'is_submitted', 'submitted_at')
    list_filter = ('is_submitted', 'is_virtual', 'is_rated_participant', 'contest')
    search_fields = ('student__username', 'contest__title')


@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'peak_rating', 'contests_entered',
                    'contests_rated', 'current_streak', 'coin_balance',
                    'last_contest_date')
    list_filter = ('last_contest_date',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('rating', 'peak_rating', 'contests_entered',
                       'contests_rated', 'best_rank', 'current_streak',
                       'longest_streak', 'coin_balance')


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'badge_type', 'rarity', 'earned_by_count', 'is_active')
    list_filter = ('badge_type', 'rarity', 'is_active')
    search_fields = ('name', 'description')


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'earned_at', 'contest')
    list_filter = ('badge__rarity', 'badge__badge_type')
    search_fields = ('user__username', 'badge__name')
    autocomplete_fields = ('user', 'badge', 'contest')


@admin.register(ContestRatingHistory)
class ContestRatingHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'old_rating', 'new_rating', 'change',
                    'rank', 'percentile', 'recorded_at')
    list_filter = ('contest', 'recorded_at')
    search_fields = ('user__username',)


@admin.register(ContestCoinLedger)
class ContestCoinLedgerAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'amount', 'balance', 'contest', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'note')


@admin.register(VirtualContest)
class VirtualContestAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'score', 'virtual_rank', 'started_at', 'finished_at')
    list_filter = ('contest',)
    search_fields = ('user__username', 'contest__title')


@admin.register(ContestRegistration)
class ContestRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'is_rated', 'is_early_bird', 'registered_at')
    list_filter = ('is_rated', 'is_early_bird', 'contest')
    search_fields = ('user__username', 'contest__title')
