"""Manage panel: question/board/subject/class/video CRUD, user admin.

Split from the original monolithic core/views.py.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction
from datetime import datetime
import json
import uuid

from ..models import Board, Subject, Class, Question, UserProfile, UserProgress
from ..services import ai as ai_svc
from .base import (
    logger, _L, _upload_error, ALLOWED_IMAGE_EXTS, ALLOWED_DOC_EXTS,
    CURRENT_YEAR, YEARS,
    admin_required, superadmin_required, premium_required,
    _is_exam_staff, _notify_all_students,
)

@admin_required
def manage_dashboard(request):
    from ..models import PracticalVideo, ExamPaper, ExamAttempt, NoteRequest
    total_questions = Question.objects.filter(is_active=True).count()
    total_videos = PracticalVideo.objects.filter(is_active=True).count()
    total_boards = Board.objects.filter(is_active=True).count()
    total_subjects = Subject.objects.filter(is_active=True).count()
    total_classes = Class.objects.count()
    recent_questions = Question.objects.select_related('board', 'subject').order_by('-created_at')[:5]
    exam_paper_count = ExamPaper.objects.count()
    pending_cq_count = ExamAttempt.objects.filter(status='CQ_PENDING').count()
    pending_note_requests = NoteRequest.objects.filter(status='PENDING').select_related('student', 'subject').order_by('-created_at')[:5]
    pending_note_request_count = NoteRequest.objects.filter(status='PENDING').count()
    return render(request, 'manage/dashboard.html', {
        'total_questions': total_questions,
        'total_videos': total_videos,
        'total_boards': total_boards,
        'total_subjects': total_subjects,
        'total_classes': total_classes,
        'recent_questions': recent_questions,
        'exam_paper_count': exam_paper_count,
        'pending_cq_count': pending_cq_count,
        'pending_note_requests': pending_note_requests,
        'pending_note_request_count': pending_note_request_count,
    })


@admin_required
def manage_questions(request):
    questions = Question.objects.select_related('board', 'subject', 'class_obj').order_by('-created_at')
    return render(request, 'manage/questions.html', {'questions': questions})


@admin_required
def question_add(request):
    boards = Board.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    if request.method == 'POST':
        board_pk = request.POST.get('board')
        subject_pk = request.POST.get('subject')
        class_pk = request.POST.get('class_obj')
        year_val = request.POST.get('year')
        qtype = request.POST.get('question_type') or 'MCQ'
        difficulty = 'Medium'
        chapter = ''

        def _int_or_default(val, default):
            try: return int(val)
            except (TypeError, ValueError): return default

        try:
            year_int = int(year_val)
        except (TypeError, ValueError):
            year_int = None

        # MCQ branch: handle multiple MCQ rows
        if qtype == 'MCQ':
            mcq_texts = request.POST.getlist('mcq_question_text')
            mcq_opt1 = request.POST.getlist('mcq_option1')
            mcq_opt2 = request.POST.getlist('mcq_option2')
            mcq_opt3 = request.POST.getlist('mcq_option3')
            mcq_opt4 = request.POST.getlist('mcq_option4')
            mcq_correct = request.POST.getlist('mcq_correct_option')

            if not any(t.strip() for t in mcq_texts):
                messages.error(request, _L(request, 'Add at least 1 MCQ.', 'কমপক্ষে ১টি MCQ যোগ করুন।'))
                return render(request, 'manage/question_form.html', {
                    'boards': boards, 'subjects': subjects,
                    'classes': classes, 'years': YEARS, 'action': 'Add',
                })

            # Duplicate check: only one MCQ allowed per (board, subject, class, year)
            if board_pk and year_int and subject_pk and class_pk:
                existing = Question.objects.filter(
                    board_id=board_pk, year=year_int,
                    subject_id=subject_pk, class_obj_id=class_pk,
                    question_type='MCQ',
                ).select_related('board', 'subject').first()
                if existing:
                    messages.error(
                        request,
                        f'এই (Board, Subject, Class, Year) এর জন্য একটি MCQ ইতিমধ্যে যোগ করা আছে। '
                        f'Board: {existing.board.name}, Subject: {existing.subject.name}, Year: {existing.year}. '
                        f'প্রতি Board+Subject+Class+Year এ একটিমাত্র MCQ ও একটিমাত্র CQ যোগ করা যায়।'
                    )
                    return render(request, 'manage/question_form.html', {
                        'boards': boards, 'subjects': subjects,
                        'classes': classes, 'years': YEARS, 'action': 'Add',
                        'post': request.POST,
                    })

            # Single shared file for the whole batch — save once and assign path to every MCQ
            shared_file = request.FILES.get('mcq_question_file')
            shared_file_path = None
            if shared_file:
                from django.core.files.storage import default_storage
                shared_file_path = default_storage.save(
                    f'question_mcq/{shared_file.name}', shared_file
                )

            from django.db import IntegrityError
            added = 0
            last_q = None
            for i, text in enumerate(mcq_texts):
                text = text.strip()
                if not text:
                    continue
                try:
                    correct = int(mcq_correct[i]) if i < len(mcq_correct) else 1
                except (ValueError, IndexError):
                    correct = 1
                try:
                    last_q = Question.objects.create(
                        board_id=board_pk, subject_id=subject_pk,
                        class_obj_id=class_pk, year=year_int,
                        chapter=chapter, question_text=text,
                        question_type='MCQ', difficulty=difficulty,
                        option1=mcq_opt1[i] if i < len(mcq_opt1) else '',
                        option2=mcq_opt2[i] if i < len(mcq_opt2) else '',
                        option3=mcq_opt3[i] if i < len(mcq_opt3) else '',
                        option4=mcq_opt4[i] if i < len(mcq_opt4) else '',
                        correct_option=correct,
                        mcq_question_file=shared_file_path or '',
                    )
                    added += 1
                    # DB rule: only ONE MCQ row per (board, subject, class, year) — stop after first
                    break
                except IntegrityError:
                    messages.error(
                        request,
                        'এই (Board, Subject, Class, Year) এর জন্য একটি MCQ ইতিমধ্যে যোগ করা আছে।'
                    )
                    return render(request, 'manage/question_form.html', {
                        'boards': boards, 'subjects': subjects,
                        'classes': classes, 'years': YEARS, 'action': 'Add',
                        'post': request.POST,
                    })

            if added and last_q:
                _notify_all_students(
                    'question',
                    f'New Question Added — {last_q.subject.name}',
                    f'{last_q.subject.name}, {last_q.class_obj.name} (MCQ)',
                    link='/question-bank/',
                    title_bn=f'নতুন প্রশ্ন যোগ হয়েছে — {last_q.subject.name}',
                    message_bn=f'{last_q.subject.name}, {last_q.class_obj.name} (MCQ)',
                )
                messages.success(request, _L(request, 'MCQ question added.', 'MCQ question যোগ করা হয়েছে।'))
            return redirect('manage_questions')

        # WRITTEN (CQ) branch: single question with stimulus + image + hint + solution
        qtext = (request.POST.get('question_text') or '').strip()

        # Duplicate check: only one CQ allowed per (board, subject, class, year)
        if board_pk and year_int and subject_pk and class_pk:
            existing = Question.objects.filter(
                board_id=board_pk, year=year_int,
                subject_id=subject_pk, class_obj_id=class_pk,
                question_type='WRITTEN',
            ).select_related('board', 'subject').first()
            if existing:
                messages.error(
                    request,
                    f'এই (Board, Subject, Class, Year) এর জন্য একটি CQ ইতিমধ্যে যোগ করা আছে। '
                    f'Board: {existing.board.name}, Subject: {existing.subject.name}, Year: {existing.year}. '
                    f'প্রতি Board+Subject+Class+Year এ একটিমাত্র MCQ ও একটিমাত্র CQ যোগ করা যায়।'
                )
                return render(request, 'manage/question_form.html', {
                    'boards': boards, 'subjects': subjects,
                    'classes': classes, 'years': YEARS, 'action': 'Add',
                    'post': request.POST,
                })

        from django.db import IntegrityError
        try:
            q = Question.objects.create(
                board=get_object_or_404(Board, pk=board_pk),
                subject=get_object_or_404(Subject, pk=subject_pk),
                class_obj=get_object_or_404(Class, pk=class_pk),
                year=year_int,
                chapter=chapter,
                question_text=qtext,
                question_type='WRITTEN',
                difficulty=difficulty,
                answer_hint=request.POST.get('answer_hint', ''),
            )
        except IntegrityError:
            messages.error(
                request,
                'এই (Board, Subject, Class, Year) এর জন্য একটি CQ ইতিমধ্যে যোগ করা আছে।'
            )
            return render(request, 'manage/question_form.html', {
                'boards': boards, 'subjects': subjects,
                'classes': classes, 'years': YEARS, 'action': 'Add',
                'post': request.POST,
            })
        if request.FILES.get('stimulus_image'):
            q.stimulus_image = request.FILES['stimulus_image']
            q.save()
        if request.FILES.get('solution_image'):
            q.solution_image = request.FILES['solution_image']
            q.save()
        _notify_all_students(
            'question',
            f'New Question Added — {q.subject.name}',
            f'{q.subject.name}, {q.class_obj.name} ({q.get_question_type_display()})',
            link='/question-bank/',
            title_bn=f'নতুন প্রশ্ন যোগ হয়েছে — {q.subject.name}',
            message_bn=f'{q.subject.name}, {q.class_obj.name} ({q.get_question_type_display()})',
        )
        messages.success(request, 'Question added successfully!')
        return redirect('manage_questions')
    return render(request, 'manage/question_form.html', {
        'boards': boards, 'subjects': subjects,
        'classes': classes, 'years': YEARS, 'action': 'Add'
    })


@admin_required
def question_add_mcq_bulk(request):
    boards = Board.objects.filter(is_active=True).order_by('name')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    classes = Class.objects.all().order_by('numeric_value')
    years = list(YEARS)

    if request.method == 'POST':
        board_pk = request.POST.get('board')
        subject_pk = request.POST.get('subject')
        class_pk = request.POST.get('class_obj')
        year_val = request.POST.get('year')
        chapter = ''
        difficulty = 'Medium'

        errors = []
        if not board_pk: errors.append(_L(request, 'Select a board.', 'Board বেছে নিন।'))
        if not subject_pk: errors.append(_L(request, 'Select a subject.', 'Subject বেছে নিন।'))
        if not class_pk: errors.append(_L(request, 'Select a class.', 'Class বেছে নিন।'))
        if not year_val: errors.append(_L(request, 'Select a year.', 'Year বেছে নিন।'))

        mcq_texts = request.POST.getlist('mcq_question_text')
        mcq_opt1 = request.POST.getlist('mcq_option1')
        mcq_opt2 = request.POST.getlist('mcq_option2')
        mcq_opt3 = request.POST.getlist('mcq_option3')
        mcq_opt4 = request.POST.getlist('mcq_option4')
        mcq_correct = request.POST.getlist('mcq_correct_option')
        mcq_marks_list = request.POST.getlist('mcq_marks')

        if not any(t.strip() for t in mcq_texts):
            errors.append(_L(request, 'Add at least 1 MCQ.', 'কমপক্ষে ১টি MCQ যোগ করুন।'))

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'manage/question_add_mcq.html', {
                'boards': boards, 'subjects': subjects,
                'classes': classes, 'years': years, 'post': request.POST,
            })

        try:
            year_int = int(year_val)
        except (TypeError, ValueError):
            year_int = None

        # Duplicate check: only one MCQ allowed per (board, subject, class, year)
        existing = Question.objects.filter(
            board_id=board_pk, year=year_int,
            subject_id=subject_pk, class_obj_id=class_pk,
            question_type='MCQ',
        ).select_related('board', 'subject').first()
        if existing:
            messages.error(
                request,
                f'এই (Board, Subject, Class, Year) এর জন্য একটি MCQ ইতিমধ্যে যোগ করা আছে। '
                f'Board: {existing.board.name}, Subject: {existing.subject.name}, Year: {existing.year}. '
                f'প্রতি Board+Subject+Class+Year এ একটিমাত্র MCQ যোগ করা যায়।'
            )
            return render(request, 'manage/question_add_mcq.html', {
                'boards': boards, 'subjects': subjects,
                'classes': classes, 'years': years, 'post': request.POST,
            })

        # Single shared file for the whole batch — save once and assign path to the MCQ row
        shared_file = request.FILES.get('mcq_question_file')
        shared_file_path = None
        if shared_file:
            from django.core.files.storage import default_storage
            shared_file_path = default_storage.save(
                f'question_mcq/{shared_file.name}', shared_file
            )

        from django.db import IntegrityError
        added = 0
        for i, text in enumerate(mcq_texts):
            text = text.strip()
            if not text:
                continue
            try:
                correct = int(mcq_correct[i]) if i < len(mcq_correct) else 1
            except (ValueError, IndexError):
                correct = 1
            try:
                Question.objects.create(
                    board_id=board_pk,
                    subject_id=subject_pk,
                    class_obj_id=class_pk,
                    year=year_int,
                    chapter=chapter,
                    question_text=text,
                    question_type='MCQ',
                    difficulty=difficulty,
                    option1=mcq_opt1[i] if i < len(mcq_opt1) else '',
                    option2=mcq_opt2[i] if i < len(mcq_opt2) else '',
                    option3=mcq_opt3[i] if i < len(mcq_opt3) else '',
                    option4=mcq_opt4[i] if i < len(mcq_opt4) else '',
                    correct_option=correct,
                    mcq_question_file=shared_file_path or '',
                )
                added += 1
                # Only one MCQ row allowed per (board, subject, class, year) — stop after first
                break
            except IntegrityError:
                messages.error(
                    request,
                    'এই (Board, Subject, Class, Year) এর জন্য একটি MCQ ইতিমধ্যে যোগ করা আছে।'
                )
                return render(request, 'manage/question_add_mcq.html', {
                    'boards': boards, 'subjects': subjects,
                    'classes': classes, 'years': years, 'post': request.POST,
                })

        if added:
            messages.success(request, _L(request, 'MCQ question added.', 'MCQ question যোগ করা হয়েছে।'))
        return redirect('manage_questions')

    return render(request, 'manage/question_add_mcq.html', {
        'boards': boards, 'subjects': subjects,
        'classes': classes, 'years': years,
    })


@login_required
def submit_written_solve(request, question_id):
    if request.method != 'POST':
        return redirect('question_bank')
    from ..models import WrittenSolveSubmission
    question = get_object_or_404(Question, pk=question_id, question_type='WRITTEN', is_active=True)
    photos = {
        'photo_ka': request.FILES.get('photo_ka'),
        'photo_kha': request.FILES.get('photo_kha'),
        'photo_ga': request.FILES.get('photo_ga'),
        'photo_gha': request.FILES.get('photo_gha'),
    }
    if not all(photos.values()):
        lang = getattr(request, 'LANG', 'bn')
        messages.error(request, 'All 4 parts (ক, খ, গ, ঘ) must be uploaded.' if lang == 'en' else 'সব ৪টি অংশ (ক, খ, গ, ঘ) আপলোড করো।')
        return redirect('question_bank')
    for photo in photos.values():
        err = _upload_error(photo, kind='image', max_mb=10)
        if err:
            messages.error(request, _L(request, *err))
            return redirect('written_question_practice', question_id=question.pk)
    sub, _ = WrittenSolveSubmission.objects.get_or_create(student=request.user, question=question)
    for field, file in photos.items():
        setattr(sub, field, file)
    sub.save()
    UserProgress.objects.get_or_create(user=request.user, question=question, defaults={'is_correct': True})
    lang = getattr(request, 'LANG', 'bn')
    messages.success(request, '✓ Answer submitted! You earned 10 marks.' if lang == 'en' else '✓ উত্তর জমা হয়েছে! ১০ নম্বর পেয়েছো।')
    return redirect('written_question_practice', question_id=question.pk)


@login_required
def written_question_practice(request, question_id):
    from ..models import WrittenSolveSubmission
    question = get_object_or_404(Question, pk=question_id, question_type='WRITTEN', is_active=True)
    is_teacher = _is_exam_staff(request.user)
    submission = None
    student_submissions = None
    if is_teacher:
        student_submissions = (
            WrittenSolveSubmission.objects
            .filter(question=question)
            .select_related('student')
            .order_by('-submitted_at')
        )
    else:
        submission = WrittenSolveSubmission.objects.filter(student=request.user, question=question).first()
    return render(request, 'core/written_question_practice.html', {
        'question': question,
        'submission': submission,
        'is_teacher': is_teacher,
        'student_submissions': student_submissions,
    })


@login_required
def upload_question_solution(request, question_id):
    question = get_object_or_404(Question, pk=question_id, question_type='WRITTEN', is_active=True)
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers can do this.', 'শুধু Teacher এই কাজটি করতে পারবে।'))
        return redirect('written_question_practice', question_id=question.pk)
    if request.method == 'POST' and request.FILES.get('solution_image'):
        question.solution_image = request.FILES['solution_image']
        question.save()
        lang = getattr(request, 'LANG', 'bn')
        messages.success(request, '✓ Solution uploaded successfully.' if lang == 'en' else '✓ Solution upload হয়েছে।')
    return redirect('written_question_practice', question_id=question.pk)


@login_required
def delete_question_solution(request, question_id):
    question = get_object_or_404(Question, pk=question_id, question_type='WRITTEN', is_active=True)
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers can do this.', 'শুধু Teacher এই কাজটি করতে পারবে।'))
        return redirect('written_question_practice', question_id=question.pk)
    if request.method == 'POST' and question.solution_image:
        question.solution_image.delete(save=False)
        question.solution_image = None
        question.save()
        lang = getattr(request, 'LANG', 'bn')
        messages.success(request, '✓ Solution deleted.' if lang == 'en' else '✓ Solution মুছে ফেলা হয়েছে।')
    return redirect('written_question_practice', question_id=question.pk)


@login_required
def delete_student_submission(request, submission_id):
    from ..models import WrittenSolveSubmission
    sub = get_object_or_404(WrittenSolveSubmission, pk=submission_id)
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers can do this.', 'শুধু Teacher এই কাজটি করতে পারবে।'))
        return redirect('written_question_practice', question_id=sub.question_id)
    question_id = sub.question_id
    if request.method == 'POST':
        for field in ('photo_ka', 'photo_kha', 'photo_ga', 'photo_gha'):
            photo = getattr(sub, field, None)
            if photo:
                photo.delete(save=False)
        UserProgress.objects.filter(user=sub.student, question_id=question_id).delete()
        student_name = sub.student.get_full_name() or sub.student.username
        sub.delete()
        lang = getattr(request, 'LANG', 'bn')
        messages.success(
            request,
            f'✓ Submission of {student_name} deleted.' if lang == 'en'
            else f'✓ {student_name} এর submission মুছে ফেলা হয়েছে।'
        )
    return redirect('written_question_practice', question_id=question_id)


@admin_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk)
    boards = Board.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    if request.method == 'POST':
        question.board = get_object_or_404(Board, pk=request.POST.get('board'))
        question.subject = get_object_or_404(Subject, pk=request.POST.get('subject'))
        question.class_obj = get_object_or_404(Class, pk=request.POST.get('class_obj'))
        question.year = request.POST.get('year')
        question.question_type = request.POST.get('question_type')

        if question.question_type == 'MCQ':
            # Edit form uses the row-based naming (first row of the bulk template)
            mcq_texts = request.POST.getlist('mcq_question_text')
            mcq_opt1 = request.POST.getlist('mcq_option1')
            mcq_opt2 = request.POST.getlist('mcq_option2')
            mcq_opt3 = request.POST.getlist('mcq_option3')
            mcq_opt4 = request.POST.getlist('mcq_option4')
            mcq_correct = request.POST.getlist('mcq_correct_option')
            if mcq_texts:
                question.question_text = (mcq_texts[0] or '').strip()
                question.option1 = mcq_opt1[0] if mcq_opt1 else ''
                question.option2 = mcq_opt2[0] if mcq_opt2 else ''
                question.option3 = mcq_opt3[0] if mcq_opt3 else ''
                question.option4 = mcq_opt4[0] if mcq_opt4 else ''
                try:
                    question.correct_option = int(mcq_correct[0]) if mcq_correct else 1
                except (ValueError, IndexError):
                    question.correct_option = 1
        else:
            question.question_text = (request.POST.get('question_text') or '').strip()
            question.answer_hint = request.POST.get('answer_hint', '')
            if request.FILES.get('stimulus_image'):
                question.stimulus_image = request.FILES['stimulus_image']
            if request.FILES.get('solution_image'):
                question.solution_image = request.FILES['solution_image']
        from django.db import IntegrityError
        try:
            question.save()
        except IntegrityError:
            messages.error(
                request,
                'এই question ইতিমধ্যে যোগ করা আছে — একই Board, Subject, Class, Year এ duplicate allowed না।'
            )
            return render(request, 'manage/question_form.html', {
                'question': question, 'boards': boards,
                'subjects': subjects, 'classes': classes,
                'years': YEARS, 'action': 'Edit'
            })
        messages.success(request, 'Question updated!')
        return redirect('manage_questions')
    return render(request, 'manage/question_form.html', {
        'question': question, 'boards': boards,
        'subjects': subjects, 'classes': classes,
        'years': YEARS, 'action': 'Edit'
    })


@admin_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted!')
    return redirect('manage_questions')


@admin_required
def manage_boards(request):
    boards = Board.objects.all()
    return render(request, 'manage/boards.html', {'boards': boards})


@admin_required
def board_add(request):
    if request.method == 'POST':
        Board.objects.create(
            name=request.POST.get('name'),
            student_count=request.POST.get('student_count', ''),
            is_active=True
        )
        messages.success(request, 'Board added!')
    return redirect('manage_boards')


@admin_required
def board_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(Board, pk=pk).delete()
        messages.success(request, 'Board deleted!')
    return redirect('manage_boards')


@admin_required
def manage_subjects(request):
    subjects = Subject.objects.all()
    return render(request, 'manage/subjects.html', {'subjects': subjects})


@admin_required
def subject_add(request):
    if request.method == 'POST':
        Subject.objects.create(
            name=request.POST.get('name'),
            icon=request.POST.get('icon', ''),
            color=request.POST.get('color', 'blue'),
            is_active=True
        )
        messages.success(request, 'Subject added!')
    return redirect('manage_subjects')


@admin_required
def subject_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(Subject, pk=pk).delete()
        messages.success(request, 'Subject deleted!')
    return redirect('manage_subjects')


@admin_required
def manage_classes(request):
    classes = Class.objects.all()
    return render(request, 'manage/classes.html', {'classes': classes})


@admin_required
def class_add(request):
    if request.method == 'POST':
        Class.objects.create(
            name=request.POST.get('name'),
            numeric_value=request.POST.get('numeric_value'),
        )
        messages.success(request, 'Class added!')
    return redirect('manage_classes')


@admin_required
def class_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(Class, pk=pk).delete()
        messages.success(request, 'Class deleted!')
    return redirect('manage_classes')


@premium_required
def practical_videos(request):
    from ..models import PracticalVideo
    videos = PracticalVideo.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()

    subject_filter = request.GET.get('subject')
    class_filter = request.GET.get('class_obj')

    if subject_filter:
        videos = videos.filter(subject__slug=subject_filter)
    if class_filter:
        videos = videos.filter(class_obj__id=class_filter)

    return render(request, 'core/practical_videos.html', {
        'videos': videos,
        'subjects': subjects,
        'classes': classes,
    })


@admin_required
def video_add(request):
    from ..models import PracticalVideo
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        youtube_url = request.POST.get('youtube_url')
        subject_id = request.POST.get('subject')
        class_id = request.POST.get('class_obj')
        description = request.POST.get('description', '')
        PracticalVideo.objects.create(
            title=title,
            youtube_url=youtube_url,
            subject_id=subject_id,
            class_obj_id=class_id,
            description=description,
            is_active=True
        )
        messages.success(request, 'Video added successfully!')
        return redirect('practical_videos')
    return render(request, 'core/video_add.html', {
        'subjects': subjects,
        'classes': classes,
    })


@admin_required
def video_delete(request, pk):
    from ..models import PracticalVideo
    video = get_object_or_404(PracticalVideo, pk=pk)
    video.delete()
    messages.success(request, 'Video deleted!')
    return redirect('practical_videos')


@superadmin_required
def update_user(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == 'POST':
        profile.role = request.POST.get('role', profile.role)
        profile.plan = request.POST.get('plan', profile.plan)
        profile.save()
        messages.success(request, f'{profile.user.username} updated!')
    return redirect('superadmin_dashboard')


@superadmin_required
def delete_user(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == 'POST':
        user = profile.user
        user.delete()
        messages.success(request, 'User deleted!')
    return redirect('superadmin_dashboard')


@superadmin_required
def cancel_subscription(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == 'POST':
        profile.plan = 'FREE'
        profile.save()
        messages.success(request, f'{profile.user.username} subscription cancelled!')
    return redirect('superadmin_dashboard')


