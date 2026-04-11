from django.contrib import admin
from .models import Question, MCQOption

class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 4

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [MCQOptionInline]
    list_filter = ['subject', 'board', 'difficulty', 'is_mcq']