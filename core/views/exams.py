"""Exam papers: lifecycle, MCQ/CQ phases, grading queue.

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

@login_required
def exam_paper_list(request):
    from ..models import ExamPaper, ExamAttempt
    papers = ExamPaper.objects.filter(is_active=True).select_related(
        'subject', 'class_obj', 'board'
    ).order_by('-year', 'subject__name')

    attempt_map = {}
    if request.user.is_authenticated:
        for a in ExamAttempt.objects.filter(
            student=request.user, exam_paper__is_active=True
        ).values('exam_paper_id', 'status', 'id'):
            attempt_map[a['exam_paper_id']] = a

    paper_data = []
    for paper in papers:
        attempt = attempt_map.get(paper.id)
        paper_data.append({
            'paper': paper,
            'mcq_count': paper.mcqs.count(),
            'cq_count': paper.cqs.count(),
            'attempt': attempt,
        })

    subjects = ExamPaper.objects.filter(is_active=True).values_list(
        'subject__name', flat=True
    ).distinct().order_by('subject__name')
    classes = ExamPaper.objects.filter(is_active=True).values_list(
        'class_obj__name', flat=True
    ).distinct().order_by('class_obj__numeric_value')

    return render(request, 'core/exam_paper_list.html', {
        'paper_data': paper_data,
        'subjects': subjects,
        'classes': classes,
    })


@login_required
def exam_paper_detail(request, pk):
    from ..models import ExamPaper, ExamAttempt
    paper = get_object_or_404(ExamPaper, pk=pk, is_active=True)

    attempt = ExamAttempt.objects.filter(
        exam_paper=paper, student=request.user
    ).first()

    mcqs = paper.mcqs.all()[:30]
    cqs = paper.cqs.all()

    return render(request, 'core/exam_paper_detail.html', {
        'paper': paper,
        'attempt': attempt,
        'mcq_count': mcqs.count(),
        'cq_count': cqs.count(),
        'mcq_sample': mcqs[:3],
    })


@login_required
def preview_exam(request, pk):
    from ..models import ExamPaper
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers/Admins can view this page.', 'শুধুমাত্র Teacher/Admin এই page দেখতে পারবেন।'))
        return redirect('exam_paper_detail', pk=pk)
    paper = get_object_or_404(ExamPaper, pk=pk, is_active=True)
    mcqs = paper.mcqs.all()
    cqs = paper.cqs.all()
    return render(request, 'manage/preview_exam.html', {
        'paper': paper,
        'mcqs': mcqs,
        'cqs': cqs,
    })


def _calculate_grade(score, max_marks):
    if not max_marks or max_marks <= 0:
        return '—'
    pct = (score / max_marks) * 100
    if pct >= 80:
        return 'A+'
    elif pct >= 70:
        return 'A'
    elif pct >= 60:
        return 'A-'
    elif pct >= 50:
        return 'B'
    elif pct >= 40:
        return 'C'
    elif pct >= 33:
        return 'D'
    return 'F'


EXAM_MCQ_MAX = 30
EXAM_CQ_MAX = 70
EXAM_TOTAL_MAX = 100


def _exam_max_marks(attempt=None):
    return EXAM_TOTAL_MAX


def _auto_submit_mcq(attempt):
    from django.utils import timezone
    mcqs = attempt.exam_paper.mcqs.all()[:30]
    score = 0
    for mcq in mcqs:
        selected = int(attempt.mcq_answers.get(str(mcq.id), 0))
        if selected == mcq.correct_option:
            score += mcq.marks
    attempt.mcq_score = score
    attempt.mcq_submitted_at = timezone.now()
    if attempt.exam_paper.cqs.exists():
        attempt.status = 'MCQ_DONE'
    else:
        attempt.status = 'GRADED'
        attempt.cq_score = 0
        attempt.total_score = score
        attempt.grade = _calculate_grade(score, _exam_max_marks(attempt))
    attempt.save()


@login_required
def start_exam(request, pk):
    from ..models import ExamPaper, ExamAttempt
    try:
        if request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin:
            messages.error(request, _L(request, 'Teachers/Admins cannot take exams.', 'Teacher/Admin রা পরীক্ষা দিতে পারবেন না।'))
            return redirect('exam_paper_detail', pk=pk)
    except Exception:
        pass
    paper = get_object_or_404(ExamPaper, pk=pk, is_active=True)
    attempt = ExamAttempt.objects.filter(exam_paper=paper, student=request.user).first()

    if attempt:
        if attempt.status == 'MCQ_PHASE':
            if attempt.mcq_seconds_remaining == 0:
                _auto_submit_mcq(attempt)
                return redirect('exam_cq_phase', attempt_id=attempt.id)
            mcqs = list(paper.mcqs.all()[:30])
            return render(request, 'core/exam_mcq_phase.html', {
                'paper': paper,
                'attempt': attempt,
                'mcqs': mcqs,
                'seconds_remaining': attempt.mcq_seconds_remaining,
            })
        if attempt.status in ('MCQ_DONE', 'CQ_PHASE'):
            return redirect('exam_cq_phase', attempt_id=attempt.id)
        return redirect('exam_results', attempt_id=attempt.id)

    from django.utils import timezone
    mcqs = list(paper.mcqs.all()[:30])
    if not mcqs:
        attempt = ExamAttempt.objects.create(
            exam_paper=paper, student=request.user,
            status='MCQ_DONE', mcq_score=0, mcq_submitted_at=timezone.now()
        )
        if not paper.cqs.exists():
            attempt.status = 'GRADED'
            attempt.cq_score = 0
            attempt.total_score = 0
            attempt.grade = _calculate_grade(0, _exam_max_marks(attempt))
            attempt.save()
            return redirect('exam_results', attempt_id=attempt.id)
        return redirect('exam_cq_phase', attempt_id=attempt.id)

    attempt = ExamAttempt.objects.create(exam_paper=paper, student=request.user, status='MCQ_PHASE')
    return render(request, 'core/exam_mcq_phase.html', {
        'paper': paper,
        'attempt': attempt,
        'mcqs': mcqs,
        'seconds_remaining': attempt.mcq_seconds_remaining,
    })


@login_required
def submit_mcq(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        if request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin:
            return JsonResponse({'error': 'Not allowed'}, status=403)
    except Exception:
        pass
    try:
        data = json.loads(request.body)
        attempt_id = int(data.get('attempt_id', 0))
        answers = data.get('answers', {})
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    from ..models import ExamAttempt
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user, status='MCQ_PHASE')
    from django.utils import timezone

    mcqs = attempt.exam_paper.mcqs.all()[:30]
    score = 0
    for mcq in mcqs:
        selected = int(answers.get(str(mcq.id), 0))
        if selected == mcq.correct_option:
            score += mcq.marks

    attempt.mcq_answers = {str(k): int(v) for k, v in answers.items() if str(v).isdigit()}
    attempt.mcq_score = score
    attempt.mcq_submitted_at = timezone.now()
    if attempt.exam_paper.cqs.exists():
        attempt.status = 'MCQ_DONE'
        redirect_url = f'/exam/{attempt.id}/cq/'
    else:
        attempt.status = 'GRADED'
        attempt.cq_score = 0
        attempt.total_score = score
        attempt.grade = _calculate_grade(score, _exam_max_marks(attempt))
        redirect_url = f'/exam/{attempt.id}/results/'
    attempt.save()

    return JsonResponse({
        'success': True,
        'score': score,
        'redirect': redirect_url,
    })


@login_required
def exam_cq_phase(request, attempt_id):
    try:
        if request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin:
            messages.error(request, _L(request, 'Teachers/Admins cannot take exams.', 'Teacher/Admin রা পরীক্ষা দিতে পারবেন না।'))
            return redirect('exam_paper_list')
    except Exception:
        pass
    from ..models import ExamAttempt
    from django.utils import timezone
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    if attempt.status == 'MCQ_PHASE':
        return redirect('start_exam', pk=attempt.exam_paper.id)
    if attempt.status in ('CQ_PENDING', 'GRADED'):
        return redirect('exam_results', attempt_id=attempt.id)

    if attempt.status == 'MCQ_DONE':
        attempt.status = 'CQ_PHASE'
        attempt.cq_started_at = timezone.now()
        attempt.save()

    if attempt.cq_seconds_remaining == 0:
        attempt.status = 'CQ_PENDING'
        attempt.cq_submitted_at = timezone.now()
        attempt.save()
        messages.info(request, _L(request, 'CQ time is up. Answers were auto-submitted.', 'CQ সময় শেষ। উত্তর auto-submit হয়েছে।'))
        return redirect('exam_results', attempt_id=attempt.id)

    cqs = attempt.exam_paper.cqs.all()
    existing_subs = {s.cq_question_id: s for s in attempt.cq_submissions.all()}
    selected_ids = set(attempt.selected_cqs)

    return render(request, 'core/exam_cq_phase.html', {
        'attempt': attempt,
        'cqs': cqs,
        'existing_subs': existing_subs,
        'selected_ids': selected_ids,
        'seconds_remaining': attempt.cq_seconds_remaining,
    })


@login_required
def submit_cq(request, attempt_id):
    try:
        if request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin:
            messages.error(request, _L(request, 'Teachers/Admins cannot take exams.', 'Teacher/Admin রা পরীক্ষা দিতে পারবেন না।'))
            return redirect('exam_paper_list')
    except Exception:
        pass
    if request.method != 'POST':
        return redirect('exam_cq_phase', attempt_id=attempt_id)

    from ..models import ExamAttempt, CQQuestion, CQSubmission
    from django.utils import timezone
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    if attempt.status in ('CQ_PENDING', 'GRADED'):
        messages.info(request, _L(request, 'This exam has already been submitted.', 'এই পরীক্ষার উত্তর আগেই জমা হয়েছে।'))
        return redirect('exam_results', attempt_id=attempt.id)
    if attempt.status == 'MCQ_PHASE':
        messages.error(request, _L(request, 'The MCQ phase is not finished yet.', 'এখনো MCQ পর্ব শেষ হয়নি।'))
        return redirect('start_exam', pk=attempt.exam_paper.id)
    if attempt.status not in ('CQ_PHASE', 'MCQ_DONE'):
        messages.error(request, _L(request, 'CQ cannot be submitted right now.', 'এই মুহূর্তে CQ submit করা যাচ্ছে না।'))
        return redirect('exam_results', attempt_id=attempt.id)

    selected_cq_ids = []
    for val in request.POST.getlist('selected_cqs'):
        try:
            selected_cq_ids.append(int(val))
        except ValueError:
            pass
    selected_cq_ids = selected_cq_ids[:7]

    for uploaded in request.FILES.values():
        err = _upload_error(uploaded, kind='image', max_mb=10)
        if err:
            messages.error(request, _L(request, *err))
            return redirect('exam_cq_phase', attempt_id=attempt.id)

    # CQ answer rows and the attempt's CQ_PENDING status must commit together,
    # otherwise a mid-request failure leaves answers saved but the attempt
    # still in CQ_PHASE (or vice versa).
    with transaction.atomic():
        for cq_id in selected_cq_ids:
            try:
                cq = CQQuestion.objects.get(id=cq_id, exam_paper=attempt.exam_paper)
            except CQQuestion.DoesNotExist:
                continue
            sub, _ = CQSubmission.objects.get_or_create(attempt=attempt, cq_question=cq)
            if f'photo_{cq_id}' in request.FILES:
                sub.photo = request.FILES[f'photo_{cq_id}']
            for part in ('a', 'b', 'c', 'd'):
                key = f'photo_{cq_id}_{part}'
                if key in request.FILES:
                    setattr(sub, f'photo_{part}', request.FILES[key])
            sub.save()

        attempt.selected_cqs = selected_cq_ids
        attempt.status = 'CQ_PENDING'
        attempt.cq_submitted_at = timezone.now()
        attempt.save()

    logger.info('CQ submitted: attempt=%s user=%s paper=%s',
                attempt.id, request.user.username, attempt.exam_paper.title)

    # In-app notification — one per (teacher, exam paper) while unread, subject-filtered
    from ..models import Notification, UserProfile, ExamAttempt as _EA
    paper_title = attempt.exam_paper.title
    paper_subject = attempt.exam_paper.subject
    grade_link = '/manage/grade-queue/'

    subject_teachers = UserProfile.objects.filter(
        role='ADMIN', is_approved=True, subjects=paper_subject
    ).select_related('user')
    # Fallback: if no teacher has subjects assigned yet, notify all approved teachers
    if not subject_teachers.exists():
        subject_teachers = UserProfile.objects.filter(
            role='ADMIN', is_approved=True
        ).select_related('user')
    # Grading is teacher work — superadmins are not notified here. They see
    # the grade-queue backlog on the Control Centre "Needs Attention" card.
    notify_users = {p.user for p in subject_teachers if not p.is_superadmin}

    pending_count = _EA.objects.filter(exam_paper=attempt.exam_paper, status='CQ_PENDING').count()

    for teacher in notify_users:
        # Skip if this teacher already has an unread notification for this paper
        already = Notification.objects.filter(
            recipient=teacher, notif_type='exam', is_read=False,
            title__contains=paper_title,
        ).exists()
        if already:
            continue
        Notification.objects.create(
            recipient=teacher,
            notif_type='exam',
            title=f'CQ submissions waiting — {paper_title}',
            title_bn=f'CQ জমা অপেক্ষায় — {paper_title}',
            message=f'{pending_count} student(s) submitted CQ answers for "{paper_title}". Check the grade queue.',
            message_bn=f'"{paper_title}" পরীক্ষায় {pending_count} জন CQ উত্তর জমা দিয়েছে। গ্রেড কিউ দেখুন।',
            link=grade_link,
        )

    messages.success(request, _L(request, 'Your CQ answers were submitted successfully. Please wait for evaluation by the teacher.', 'আপনার CQ উত্তর সফলভাবে জমা হয়েছে। Teacher এর মূল্যায়নের জন্য অপেক্ষা করুন।'))
    return redirect('exam_results', attempt_id=attempt.id)


@login_required
def exam_results(request, attempt_id):
    try:
        if request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin:
            messages.error(request, _L(request, 'Teachers/Admins cannot take exams.', 'Teacher/Admin রা পরীক্ষা দিতে পারবেন না।'))
            return redirect('exam_paper_list')
    except Exception:
        pass
    from ..models import ExamAttempt
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    cq_submissions = attempt.cq_submissions.select_related('cq_question').all()
    max_marks = _exam_max_marks(attempt)
    score = attempt.total_score or 0
    percentage = round((score / max_marks) * 100, 1) if max_marks else 0
    live_grade = _calculate_grade(score, max_marks) if attempt.status == 'GRADED' else attempt.grade
    if attempt.status == 'GRADED' and live_grade != attempt.grade:
        attempt.grade = live_grade
        attempt.save(update_fields=['grade'])
    return render(request, 'core/exam_results.html', {
        'attempt': attempt,
        'cq_submissions': cq_submissions,
        'max_marks': max_marks,
        'percentage': percentage,
        'live_grade': live_grade,
    })


@login_required
def create_exam_paper(request):
    from ..models import ExamPaper, ExamPaperMCQ, CQQuestion
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers/Staff can access this page.', 'Teacher/Staff শুধু এই page access করতে পারবে।'))
        return redirect('home')

    subjects = Subject.objects.filter(is_active=True).order_by('name')
    classes = Class.objects.all().order_by('numeric_value')
    boards = Board.objects.filter(is_active=True).order_by('name')
    years = list(range(CURRENT_YEAR, CURRENT_YEAR - 10, -1))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        subject_id = request.POST.get('subject', '').strip()
        class_id = request.POST.get('class_obj', '').strip()
        board_id = request.POST.get('board', '').strip()
        year = request.POST.get('year', '').strip()

        errors = []
        if not title:
            errors.append(_L(request, 'Enter a title.', 'Title দিন।'))
        if not subject_id:
            errors.append(_L(request, 'Select a subject.', 'Subject বেছে নিন।'))
        if not class_id:
            errors.append(_L(request, 'Select a class.', 'Class বেছে নিন।'))

        # Duplicate check: Board + Year combination must be unique per subject/class
        if board_id and year and subject_id and class_id:
            try:
                year_int = int(year)
            except ValueError:
                year_int = None
            if year_int:
                existing = ExamPaper.objects.filter(
                    board_id=board_id, year=year_int,
                    subject_id=subject_id, class_obj_id=class_id,
                ).select_related('board', 'subject', 'class_obj', 'created_by').first()
                if existing:
                    creator = existing.created_by.get_full_name() or existing.created_by.username
                    errors.append(
                        f'এই Board ({existing.board.name}), Year ({year_int}), '
                        f'Subject ({existing.subject.name}) এবং Class ({existing.class_obj.name}) এর paper '
                        f'ইতিমধ্যে আছে: "{existing.title}" — তৈরি করেছেন {creator}.'
                    )

        mcq_texts = request.POST.getlist('mcq_question_text')
        cq_texts = request.POST.getlist('cq_question_text')
        if not any(t.strip() for t in mcq_texts) and not any(t.strip() for t in cq_texts):
            errors.append(_L(request, 'Add at least 1 MCQ or 1 CQ question.', 'কমপক্ষে ১টি MCQ অথবা ১টি CQ প্রশ্ন দিন।'))

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'manage/create_exam_paper.html', {
                'subjects': subjects, 'classes': classes,
                'boards': boards, 'years': years, 'post': request.POST,
            })

        paper = ExamPaper.objects.create(
            title=title,
            subject_id=subject_id,
            class_obj_id=class_id,
            board_id=board_id if board_id else None,
            year=int(year) if year else None,
            created_by=request.user,
            is_active=True,
        )

        # MCQs
        mcq_opt1 = request.POST.getlist('mcq_option1')
        mcq_opt2 = request.POST.getlist('mcq_option2')
        mcq_opt3 = request.POST.getlist('mcq_option3')
        mcq_opt4 = request.POST.getlist('mcq_option4')
        mcq_correct = request.POST.getlist('mcq_correct_option')
        mcq_marks = request.POST.getlist('mcq_marks')

        order = 0
        for i, text in enumerate(mcq_texts):
            text = text.strip()
            if not text:
                continue
            try:
                correct = int(mcq_correct[i]) if i < len(mcq_correct) else 1
                marks = int(mcq_marks[i]) if i < len(mcq_marks) else 1
            except (ValueError, IndexError):
                correct, marks = 1, 1
            ExamPaperMCQ.objects.create(
                exam_paper=paper,
                question_text=text,
                option1=mcq_opt1[i] if i < len(mcq_opt1) else '',
                option2=mcq_opt2[i] if i < len(mcq_opt2) else '',
                option3=mcq_opt3[i] if i < len(mcq_opt3) else '',
                option4=mcq_opt4[i] if i < len(mcq_opt4) else '',
                correct_option=correct,
                marks=marks,
                order=order,
            )
            order += 1

        # CQs
        cq_part_a = request.POST.getlist('cq_part_a')
        cq_part_b = request.POST.getlist('cq_part_b')
        cq_part_c = request.POST.getlist('cq_part_c')
        cq_part_d = request.POST.getlist('cq_part_d')
        cq_marks_a = request.POST.getlist('cq_marks_a')
        cq_marks_b = request.POST.getlist('cq_marks_b')
        cq_marks_c = request.POST.getlist('cq_marks_c')
        cq_marks_d = request.POST.getlist('cq_marks_d')

        order = 0
        for i, text in enumerate(cq_texts):
            text = text.strip()
            if not text:
                continue
            def _m(lst, idx, default):
                try:
                    return max(0, int(lst[idx])) if idx < len(lst) else default
                except ValueError:
                    return default
            CQQuestion.objects.create(
                exam_paper=paper,
                question_text=text,
                part_a=cq_part_a[i] if i < len(cq_part_a) else '',
                part_b=cq_part_b[i] if i < len(cq_part_b) else '',
                part_c=cq_part_c[i] if i < len(cq_part_c) else '',
                part_d=cq_part_d[i] if i < len(cq_part_d) else '',
                marks_a=_m(cq_marks_a, i, 1),
                marks_b=_m(cq_marks_b, i, 2),
                marks_c=_m(cq_marks_c, i, 3),
                marks_d=_m(cq_marks_d, i, 4),
                order=order,
            )
            order += 1

        _notify_all_students(
            'exam',
            f'New Exam Paper: {paper.title}',
            f'{request.user.username} uploaded a new exam paper — "{paper.title}" ({paper.subject.name}, {paper.class_obj.name})',
            link=f'/exam-papers/{paper.pk}/',
            title_bn=f'নতুন Exam Paper: {paper.title}',
            message_bn=f'{request.user.username} একটি নতুন exam paper আপলোড করেছেন — "{paper.title}" ({paper.subject.name}, {paper.class_obj.name})',
        )
        messages.success(
            request,
            f'"{paper.title}" তৈরি হয়েছে — {paper.mcqs.count()}টি MCQ, {paper.cqs.count()}টি CQ।'
        )
        return redirect('exam_paper_detail', pk=paper.pk)

    return render(request, 'manage/create_exam_paper.html', {
        'subjects': subjects,
        'classes': classes,
        'boards': boards,
        'years': years,
    })


@login_required
def edit_exam_paper(request, pk):
    import json as _json
    from ..models import ExamPaper, ExamPaperMCQ, CQQuestion, ExamAttempt
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers/Staff can access this page.', 'Teacher/Staff শুধু এই page access করতে পারবে।'))
        return redirect('home')

    paper = get_object_or_404(ExamPaper, pk=pk)
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    classes = Class.objects.all().order_by('numeric_value')
    boards = Board.objects.filter(is_active=True).order_by('name')
    years = list(range(CURRENT_YEAR, CURRENT_YEAR - 10, -1))
    active_attempt_count = ExamAttempt.objects.filter(
        exam_paper=paper
    ).exclude(status='GRADED').count()

    def _get_existing():
        mcqs = list(paper.mcqs.order_by('order').values(
            'question_text', 'option1', 'option2', 'option3', 'option4',
            'correct_option', 'marks'
        ))
        cqs = list(paper.cqs.order_by('order').values(
            'question_text', 'part_a', 'part_b', 'part_c', 'part_d',
            'marks_a', 'marks_b', 'marks_c', 'marks_d'
        ))
        return _json.dumps(mcqs), _json.dumps(cqs)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        subject_id = request.POST.get('subject', '').strip()
        class_id = request.POST.get('class_obj', '').strip()
        board_id = request.POST.get('board', '').strip()
        year = request.POST.get('year', '').strip()

        errors = []
        if not title: errors.append(_L(request, 'Enter a title.', 'Title দিন।'))
        if not subject_id: errors.append(_L(request, 'Select a subject.', 'Subject বেছে নিন।'))
        if not class_id: errors.append(_L(request, 'Select a class.', 'Class বেছে নিন।'))

        # Duplicate check: Board + Year combination must be unique (excluding self)
        if board_id and year and subject_id and class_id:
            try:
                year_int = int(year)
            except ValueError:
                year_int = None
            if year_int:
                existing = ExamPaper.objects.filter(
                    board_id=board_id, year=year_int,
                    subject_id=subject_id, class_obj_id=class_id,
                ).exclude(pk=paper.pk).select_related(
                    'board', 'subject', 'class_obj', 'created_by'
                ).first()
                if existing:
                    creator = existing.created_by.get_full_name() or existing.created_by.username
                    errors.append(
                        f'এই Board ({existing.board.name}), Year ({year_int}), '
                        f'Subject ({existing.subject.name}) এবং Class ({existing.class_obj.name}) এর paper '
                        f'ইতিমধ্যে আছে: "{existing.title}" — তৈরি করেছেন {creator}.'
                    )

        mcq_texts = request.POST.getlist('mcq_question_text')
        cq_texts = request.POST.getlist('cq_question_text')
        if not any(t.strip() for t in mcq_texts) and not any(t.strip() for t in cq_texts):
            errors.append(_L(request, 'Add at least 1 MCQ or 1 CQ question.', 'কমপক্ষে ১টি MCQ অথবা ১টি CQ প্রশ্ন দিন।'))

        if errors:
            for err in errors:
                messages.error(request, err)
            mcqs_json, cqs_json = _get_existing()
            return render(request, 'manage/edit_exam_paper.html', {
                'paper': paper, 'subjects': subjects, 'classes': classes,
                'boards': boards, 'years': years,
                'existing_mcqs_json': mcqs_json, 'existing_cqs_json': cqs_json,
                'active_attempt_count': active_attempt_count,
            })

        paper.title = title
        paper.subject_id = subject_id
        paper.class_obj_id = class_id
        paper.board_id = board_id if board_id else None
        paper.year = int(year) if year else None
        paper.save()

        paper.mcqs.all().delete()
        mcq_opt1 = request.POST.getlist('mcq_option1')
        mcq_opt2 = request.POST.getlist('mcq_option2')
        mcq_opt3 = request.POST.getlist('mcq_option3')
        mcq_opt4 = request.POST.getlist('mcq_option4')
        mcq_correct = request.POST.getlist('mcq_correct_option')
        mcq_marks_list = request.POST.getlist('mcq_marks')
        order = 0
        for i, text in enumerate(mcq_texts):
            text = text.strip()
            if not text:
                continue
            try:
                correct = int(mcq_correct[i]) if i < len(mcq_correct) else 1
                marks = int(mcq_marks_list[i]) if i < len(mcq_marks_list) else 1
            except (ValueError, IndexError):
                correct, marks = 1, 1
            ExamPaperMCQ.objects.create(
                exam_paper=paper,
                question_text=text,
                option1=mcq_opt1[i] if i < len(mcq_opt1) else '',
                option2=mcq_opt2[i] if i < len(mcq_opt2) else '',
                option3=mcq_opt3[i] if i < len(mcq_opt3) else '',
                option4=mcq_opt4[i] if i < len(mcq_opt4) else '',
                correct_option=correct,
                marks=marks,
                order=order,
            )
            order += 1

        paper.cqs.all().delete()
        cq_part_a = request.POST.getlist('cq_part_a')
        cq_part_b = request.POST.getlist('cq_part_b')
        cq_part_c = request.POST.getlist('cq_part_c')
        cq_part_d = request.POST.getlist('cq_part_d')
        cq_marks_a = request.POST.getlist('cq_marks_a')
        cq_marks_b = request.POST.getlist('cq_marks_b')
        cq_marks_c = request.POST.getlist('cq_marks_c')
        cq_marks_d = request.POST.getlist('cq_marks_d')
        order = 0
        for i, text in enumerate(cq_texts):
            text = text.strip()
            if not text:
                continue
            def _m(lst, idx, default):
                try:
                    return max(0, int(lst[idx])) if idx < len(lst) else default
                except ValueError:
                    return default
            CQQuestion.objects.create(
                exam_paper=paper,
                question_text=text,
                part_a=cq_part_a[i] if i < len(cq_part_a) else '',
                part_b=cq_part_b[i] if i < len(cq_part_b) else '',
                part_c=cq_part_c[i] if i < len(cq_part_c) else '',
                part_d=cq_part_d[i] if i < len(cq_part_d) else '',
                marks_a=_m(cq_marks_a, i, 1),
                marks_b=_m(cq_marks_b, i, 2),
                marks_c=_m(cq_marks_c, i, 3),
                marks_d=_m(cq_marks_d, i, 4),
                order=order,
            )
            order += 1

        messages.success(
            request,
            f'"{paper.title}" আপডেট হয়েছে — {paper.mcqs.count()}টি MCQ, {paper.cqs.count()}টি CQ।'
        )
        return redirect('exam_paper_detail', pk=paper.pk)

    mcqs_json, cqs_json = _get_existing()
    return render(request, 'manage/edit_exam_paper.html', {
        'paper': paper,
        'subjects': subjects,
        'classes': classes,
        'boards': boards,
        'years': years,
        'existing_mcqs_json': mcqs_json,
        'existing_cqs_json': cqs_json,
        'active_attempt_count': active_attempt_count,
    })


@login_required
def delete_exam_paper(request, pk):
    from ..models import ExamPaper, ExamAttempt
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers/Staff can access this page.', 'Teacher/Staff শুধু এই page access করতে পারবে।'))
        return redirect('home')

    if request.method != 'POST':
        return redirect('exam_paper_detail', pk=pk)

    paper = get_object_or_404(ExamPaper, pk=pk)
    active_attempts = ExamAttempt.objects.filter(
        exam_paper=paper,
        student__profile__role='STUDENT',
    ).exclude(status='GRADED').count()

    if active_attempts > 0:
        messages.error(
            request,
            f'{active_attempts}জন student এই exam-এ active আছে। Delete করা সম্ভব নয়।'
        )
        return redirect('exam_paper_detail', pk=pk)

    paper_title = paper.title
    paper.is_active = False
    paper.save()
    messages.success(request, _L(request, f'"{paper_title}" deleted successfully.', f'"{paper_title}" সফলভাবে মুছে ফেলা হয়েছে।'))
    return redirect('exam_paper_list')


def _parse_exam_questions(text):
    import re

    # Options: English a/b/c/d (any case) OR Bengali ক/খ/গ/ঘ, any bracket/dot/space delimiter
    opt_re = re.compile(r'^[(（]?([aAbBcCdDকখগঘ])[)）\.\s]+(.*)', re.UNICODE)
    # Numbered question prefix (Arabic or Bengali numerals)
    q_num_re = re.compile(r'^[০-৯0-9]{1,2}[।\.)\s]+(.*)')

    OPT_IDX = {
        'a': 1, 'A': 1, 'ক': 1,
        'b': 2, 'B': 2, 'খ': 2,
        'c': 3, 'C': 3, 'গ': 3,
        'd': 4, 'D': 4, 'ঘ': 4,
    }

    mcqs = []
    cqs = []

    def flush(q_parts, opts):
        if not opts:
            # Fallback: no letter prefixes — first line = question, next 4 = options
            if len(q_parts) >= 3:
                q_text = q_parts[0]
                options = q_parts[1:5]
                if len(options) == 4:
                    mcqs.append({
                        'question_text': q_text,
                        'option1': options[0], 'option2': options[1],
                        'option3': options[2], 'option4': options[3],
                        'correct_option': 1, 'marks': 1,
                    })
            return
        q_text = ' '.join(q_parts).strip()
        o1, o2, o3, o4 = opts.get(1,''), opts.get(2,''), opts.get(3,''), opts.get(4,'')
        if o1 and o2 and o3 and o4:
            mcqs.append({
                'question_text': q_text,
                'option1': o1, 'option2': o2, 'option3': o3, 'option4': o4,
                'correct_option': 1, 'marks': 1,
            })
        elif o1 or o2:
            cqs.append({
                'question_text': q_text,
                'part_a': o1, 'part_b': o2, 'part_c': o3, 'part_d': o4,
                'marks_a': 1, 'marks_b': 2, 'marks_c': 3, 'marks_d': 4,
            })

    q_parts = []
    opts = {}
    in_options = False

    for raw in text.splitlines():
        line = raw.strip()

        if not line:
            # Blank line ends the current question block
            if opts:
                flush(q_parts, opts)
                q_parts, opts, in_options = [], {}, False
            continue

        om = opt_re.match(line)
        if om:
            idx = OPT_IDX.get(om.group(1))
            if idx:
                opts[idx] = om.group(2).strip()
                in_options = True
            continue

        # Non-option text line
        qm = q_num_re.match(line)
        if qm:
            # Numbered question — flush previous block first
            if opts or in_options:
                flush(q_parts, opts)
                q_parts, opts, in_options = [], {}, False
            q_parts.append(qm.group(1).strip())
        else:
            if in_options and len(opts) < 4:
                # Already collecting options but this line has no prefix —
                # treat it as the next sequential option
                opts[len(opts) + 1] = line
            elif in_options:
                # All 4 options filled, plain text = new question block
                flush(q_parts, opts)
                q_parts, opts, in_options = [line], {}, False
            else:
                q_parts.append(line)

    flush(q_parts, opts)
    return mcqs, cqs


@login_required
def parse_exam_text(request):
    """Receives raw OCR text (from browser-side Tesseract.js) and parses MCQ/CQ structure."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    if not _is_exam_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'error': _L(request, 'Please provide text.', 'Text দিন।')}, status=400)

    mcqs, cqs = _parse_exam_questions(text)
    return JsonResponse({
        'success': True,
        'data': {'mcqs': mcqs, 'cqs': cqs},
    })


@login_required
def extract_text_from_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    if not _is_exam_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse({'error': _L(request, 'Please provide an image.', 'ছবি দিন।')}, status=400)

    try:
        text = ai_svc.gemini_extract_text(
            image_file.read(),
            mime_type=image_file.content_type or 'image/jpeg',
        )
        return JsonResponse({'success': True, 'text': text})
    except ai_svc.AIServiceError as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def grade_cq_submission(request, attempt_id):
    from ..models import ExamAttempt, CQSubmission
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers/Staff can access this page.', 'শুধু Teacher/Staff এই page access করতে পারবে।'))
        return redirect('home')

    attempt = get_object_or_404(
        ExamAttempt.objects.filter(status__in=['CQ_PENDING', 'GRADED']),
        id=attempt_id,
    )

    is_super = getattr(getattr(request.user, 'profile', None), 'is_superadmin', False)
    if attempt.status == 'CQ_PENDING' and attempt.assigned_teacher != request.user and not is_super:
        messages.error(request, _L(request, 'Claim this answer script before grading it.', 'এই answer script grade করতে হলে আগে Claim করুন।'))
        return redirect('manage_grade_list')

    cq_submissions = attempt.cq_submissions.select_related('cq_question').all()
    is_regrade = (attempt.status == 'GRADED')

    if request.method == 'POST':
        from django.utils import timezone
        # Per-question marks and the attempt's final score/grade must commit
        # together — partially saved marks with an unGRADED attempt would let
        # the script be re-claimed and double-graded.
        with transaction.atomic():
            total_cq = 0
            for sub in cq_submissions:
                q = sub.cq_question
                cq_total = 0
                for part, max_marks in (('a', q.marks_a), ('b', q.marks_b),
                                        ('c', q.marks_c), ('d', q.marks_d)):
                    raw = request.POST.get(f'marks_{sub.id}_{part}', '').strip()
                    try:
                        m = int(raw) if raw else 0
                    except ValueError:
                        m = 0
                    m = max(0, min(m, max_marks))
                    setattr(sub, f'marks_{part}', m)
                    comment = request.POST.get(f'comment_{sub.id}_{part}', '').strip()
                    # Clear comment if student got full marks for this part
                    setattr(sub, f'comment_{part}', '' if m >= max_marks else comment)
                    cq_total += m
                sub.marks_given = cq_total
                sub.save()
                total_cq += cq_total

            attempt.cq_score = total_cq
            attempt.total_score = attempt.mcq_score + total_cq
            attempt.grade = _calculate_grade(attempt.total_score, _exam_max_marks(attempt))
            attempt.status = 'GRADED'
            attempt.graded_by = request.user
            attempt.graded_at = timezone.now()
            attempt.save()

        logger.info('CQ graded: attempt=%s student=%s grader=%s score=%s grade=%s%s',
                    attempt.id, attempt.student.username, request.user.username,
                    attempt.total_score, attempt.grade, ' (regrade)' if is_regrade else '')

        from ..models import Notification
        from django.urls import reverse
        if is_regrade:
            n_title = f'Result updated: {attempt.exam_paper.title}'
            n_title_bn = f'ফলাফল আপডেট: {attempt.exam_paper.title}'
            n_msg = f'Your result has been updated. New score: {attempt.total_score}, Grade: {attempt.grade}.'
            n_msg_bn = f'তোমার ফলাফল আপডেট হয়েছে। নতুন নম্বর: {attempt.total_score}, গ্রেড: {attempt.grade}।'
        else:
            n_title = f'Result published: {attempt.exam_paper.title}'
            n_title_bn = f'ফলাফল প্রকাশিত: {attempt.exam_paper.title}'
            n_msg = f'Your exam has been graded. Score: {attempt.total_score}, Grade: {attempt.grade}.'
            n_msg_bn = f'তোমার পরীক্ষার ফলাফল প্রকাশিত হয়েছে। নম্বর: {attempt.total_score}, গ্রেড: {attempt.grade}।'
        Notification.objects.create(
            recipient=attempt.student,
            notif_type='exam',
            title=n_title,
            message=n_msg,
            title_bn=n_title_bn,
            message_bn=n_msg_bn,
            link=reverse('exam_results', args=[attempt.id]),
        )

        messages.success(request, _L(request, f'{"Re-grading" if is_regrade else "Grading"} complete. Grade: {attempt.grade}', f'{"Re-grading" if is_regrade else "Grading"} সম্পন্ন। Grade: {attempt.grade}'))
        return redirect('manage_grade_list')

    return render(request, 'manage/grade_cq_submission.html', {
        'attempt': attempt,
        'cq_submissions': cq_submissions,
        'is_regrade': is_regrade,
    })


@login_required
def manage_grade_list(request):
    if not _is_exam_staff(request.user):
        messages.error(request, _L(request, 'Only Teachers/Staff can access this page.', 'শুধু Teacher/Staff এই page access করতে পারবে।'))
        return redirect('home')

    from ..models import ExamAttempt
    from django.utils import timezone
    from datetime import timedelta

    is_super = getattr(getattr(request.user, 'profile', None), 'is_superadmin', False)
    try:
        my_subjects = list(request.user.profile.subjects.values_list('id', flat=True))
    except Exception:
        my_subjects = []

    qs_pending = ExamAttempt.objects.filter(status='CQ_PENDING').select_related(
        'student', 'exam_paper', 'exam_paper__subject', 'assigned_teacher'
    ).order_by('cq_submitted_at')

    # Unclaimed: filtered by teacher's current subject
    unclaimed_qs = qs_pending.filter(assigned_teacher=None)
    if not is_super and my_subjects:
        unclaimed_qs = unclaimed_qs.filter(exam_paper__subject__id__in=my_subjects)

    # My queue: always show everything this teacher claimed, even if they changed subject
    my_queue = qs_pending.filter(assigned_teacher=request.user)

    # Graded by me: all attempts I've graded (most recent first)
    graded_by_me = ExamAttempt.objects.filter(
        status='GRADED', graded_by=request.user
    ).select_related(
        'student', 'exam_paper', 'exam_paper__subject'
    ).order_by('-graded_at')[:100]

    total_pending = unclaimed_qs.count() + my_queue.count()
    unclaimed = unclaimed_qs

    cutoff = timezone.now() - timedelta(hours=24)
    for qs in [unclaimed, my_queue]:
        for attempt in qs:
            attempt.is_urgent = bool(attempt.cq_submitted_at and attempt.cq_submitted_at < cutoff)

    return render(request, 'manage/grade_queue.html', {
        'unclaimed': unclaimed,
        'my_queue': my_queue,
        'graded_by_me': graded_by_me,
        'total_pending': total_pending,
    })


@login_required
def claim_cq_attempt(request, attempt_id):
    from ..models import ExamAttempt
    if not _is_exam_staff(request.user):
        return redirect('home')
    if request.method == 'POST':
        from django.utils import timezone
        # Conditional UPDATE so two teachers clicking simultaneously can't both claim.
        claimed = ExamAttempt.objects.filter(
            id=attempt_id, status='CQ_PENDING', assigned_teacher=None,
        ).update(assigned_teacher=request.user, claimed_at=timezone.now())
        if not claimed:
            messages.warning(request, _L(
                request,
                'This script was already claimed by another teacher.',
                'এই খাতা ইতিমধ্যে অন্য teacher claim করেছেন।',
            ))
    return redirect('manage_grade_list')


@login_required
def release_cq_attempt(request, attempt_id):
    from ..models import ExamAttempt
    if not _is_exam_staff(request.user):
        return redirect('home')
    if request.method == 'POST':
        attempt = get_object_or_404(ExamAttempt, id=attempt_id, status='CQ_PENDING')
        is_super = getattr(getattr(request.user, 'profile', None), 'is_superadmin', False)
        if attempt.assigned_teacher == request.user or is_super:
            attempt.assigned_teacher = None
            attempt.claimed_at = None
            attempt.save()
    return redirect('manage_grade_list')


# -------- CONTEST: REGISTRATION, RATINGS, BADGES, COINS --------

