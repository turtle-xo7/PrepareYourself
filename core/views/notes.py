"""Study notes, comments, bookmarks, note requests, AI note tools.

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
def request_note(request):
    if request.method != 'POST':
        return redirect('study_notes')
    from ..models import NoteRequest, Notification, UserProfile
    topic = request.POST.get('topic', '').strip()
    if not topic:
        messages.error(request, 'Topic দাও।' if request.LANG == 'bn' else 'Please enter a topic.')
        return redirect('study_notes')
    subject_id = request.POST.get('subject')
    subject = Subject.objects.filter(pk=subject_id).first() if subject_id else None
    note_req = NoteRequest.objects.create(
        student=request.user,
        subject=subject,
        topic=topic,
        details=request.POST.get('details', ''),
    )
    admin_ids = UserProfile.objects.filter(is_admin=True).values_list('user_id', flat=True)
    Notification.objects.bulk_create([
        Notification(
            recipient_id=uid,
            notif_type='request',
            title=f'নতুন Note Request: {topic}' if request.LANG == 'bn' else f'New Note Request: {topic}',
            message=f'{request.user.username} একটি note request করেছেন — "{topic}"' if request.LANG == 'bn' else f'{request.user.username} requested a note on "{topic}"',
            link='/manage/note-requests/',
        )
        for uid in admin_ids
    ])
    messages.success(request, 'Request পাঠানো হয়েছে! 📩' if request.LANG == 'bn' else 'Request sent! 📩')
    return redirect('study_notes')


@admin_required
def manage_note_requests(request):
    from ..models import NoteRequest
    note_requests = NoteRequest.objects.select_related('student', 'subject', 'fulfilled_by', 'fulfilled_note').order_by('-created_at')
    subjects = Subject.objects.filter(is_active=True)
    return render(request, 'manage/note_requests.html', {
        'note_requests': note_requests,
        'subjects': subjects,
        'pending_count': note_requests.filter(status='PENDING').count(),
    })


@admin_required
def fulfill_note_request(request, pk):
    from ..models import NoteRequest, Notification
    from django.utils import timezone
    note_req = get_object_or_404(NoteRequest, pk=pk)
    action = request.POST.get('action', 'fulfill')
    if action == 'reject':
        note_req.status = 'REJECTED'
        note_req.fulfilled_at = timezone.now()
        note_req.fulfilled_by = request.user
        note_req.save()
        Notification.objects.create(
            recipient=note_req.student,
            notif_type='request',
            title='Note Request Update',
            message=f'Your request for "{note_req.topic}" could not be fulfilled at this time.',
            title_bn='Note Request আপডেট',
            message_bn=f'"{note_req.topic}" বিষয়ে তোমার request টি এই মুহূর্তে পূরণ করা সম্ভব হয়নি।',
            link='/student/notifications/',
        )
        messages.info(request, 'Request reject করা হয়েছে।' if request.LANG == 'bn' else 'Request rejected.')
    else:
        note_req.status = 'FULFILLED'
        note_req.fulfilled_at = timezone.now()
        note_req.fulfilled_by = request.user
        note_req.save()
        Notification.objects.create(
            recipient=note_req.student,
            notif_type='note',
            title='Your Note Request is Fulfilled! 🎉',
            message=f'A study note on "{note_req.topic}" has been added. Check it out!',
            title_bn='তোমার Note Request পূরণ হয়েছে! 🎉',
            message_bn=f'"{note_req.topic}" বিষয়ে study note যোগ করা হয়েছে। এখনই দেখো!',
            link='/study-notes/',
        )
        messages.success(request, 'Request fulfilled করা হয়েছে।' if request.LANG == 'bn' else 'Request fulfilled.')
    return redirect('manage_note_requests')


@login_required
def notifications(request):
    from ..models import TeacherFeedback, Notification
    feedbacks = TeacherFeedback.objects.filter(
        student=request.user
    ).select_related('teacher', 'progress__question')
    feedbacks.filter(is_read=False).update(is_read=True)

    notifs = Notification.objects.filter(recipient=request.user)
    notifs.filter(is_read=False).update(is_read=True)

    from django.core.paginator import Paginator
    page_obj = Paginator(notifs, 25).get_page(request.GET.get('page'))

    return render(request, 'core/notifications.html', {
        'feedbacks': feedbacks,
        'notifications': page_obj.object_list,
        'page_obj': page_obj,
    })


# -------- STUDY NOTES --------

@premium_required
def study_notes(request):
    from ..models import StudyNote, NoteBookmark
    notes = StudyNote.objects.filter(is_active=True).select_related('subject', 'class_obj', 'created_by')
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()

    subject_filter = request.GET.get('subject')
    class_filter = request.GET.get('class_obj')
    search = request.GET.get('search', '')

    if subject_filter:
        notes = notes.filter(subject__slug=subject_filter)
    if class_filter:
        notes = notes.filter(class_obj__id=class_filter)
    if search:
        notes = notes.filter(title__icontains=search) | notes.filter(chapter__icontains=search)

    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(NoteBookmark.objects.filter(
            user=request.user
        ).values_list('note_id', flat=True))

    return render(request, 'core/study_notes.html', {
        'notes': notes,
        'subjects': subjects,
        'classes': classes,
        'search': search,
        'bookmarked_ids': bookmarked_ids,
    })


@premium_required
def study_note_detail(request, pk):
    from ..models import StudyNote, NoteBookmark, NoteReadProgress, NoteComment

    note = get_object_or_404(StudyNote, pk=pk, is_active=True)
    is_bookmarked = NoteBookmark.objects.filter(user=request.user, note=note).exists()
    read_progress, _ = NoteReadProgress.objects.get_or_create(user=request.user, note=note)
    related_notes = StudyNote.objects.filter(
        subject=note.subject, is_active=True
    ).exclude(pk=note.pk)[:3]

    approved_comments = NoteComment.objects.filter(note=note, is_approved=True).select_related('user')

    try:
        is_teacher = request.user.profile.role == 'ADMIN'
    except:
        is_teacher = False

    pending_comments = NoteComment.objects.filter(
        note=note, is_approved=False
    ).select_related('user') if is_teacher else NoteComment.objects.none()

    return render(request, 'core/study_note_detail.html', {
        'note': note,
        'is_bookmarked': is_bookmarked,
        'read_progress': read_progress,
        'related_notes': related_notes,
        'approved_comments': approved_comments,
        'pending_comments': pending_comments,
        'is_teacher': is_teacher,
    })


@admin_required
def study_note_add(request):
    from ..models import StudyNote, NoteRequest
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    linked_request = None
    req_id = request.GET.get('req') or request.POST.get('note_request_id')
    if req_id:
        linked_request = NoteRequest.objects.filter(pk=req_id, status='PENDING').first()
    if request.method == 'POST':
        err = _upload_error(request.FILES.get('pdf_file'), kind='doc', max_mb=20)
        if err:
            messages.error(request, _L(request, *err))
            return redirect('study_note_add')
        note = StudyNote.objects.create(
            title=request.POST.get('title'),
            subject=get_object_or_404(Subject, pk=request.POST.get('subject')),
            class_obj=get_object_or_404(Class, pk=request.POST.get('class_obj')),
            chapter=request.POST.get('chapter'),
            content=request.POST.get('content', ''),
            created_by=request.user,
            is_active=True
        )
        if request.FILES.get('pdf_file'):
            note.pdf_file = request.FILES['pdf_file']
            note.save()
        _notify_all_students(
            'note',
            f'New Study Note: {note.title}',
            f'{request.user.username} uploaded a new study note — "{note.title}" ({note.subject.name}, {note.class_obj.name})',
            link=f'/study-notes/{note.pk}/',
            title_bn=f'নতুন Study Note: {note.title}',
            message_bn=f'{request.user.username} একটি নতুন study note আপলোড করেছেন — "{note.title}" ({note.subject.name}, {note.class_obj.name})',
        )
        # Fulfill a linked note request if specified
        from ..models import NoteRequest
        from django.utils import timezone
        req_id = request.POST.get('note_request_id')
        if req_id:
            try:
                note_req = NoteRequest.objects.get(pk=req_id, status='PENDING')
                note_req.status = 'FULFILLED'
                note_req.fulfilled_at = timezone.now()
                note_req.fulfilled_by = request.user
                note_req.fulfilled_note = note
                note_req.save()
                from ..models import Notification
                Notification.objects.create(
                    recipient=note_req.student,
                    notif_type='note',
                    title='Your Note Request is Fulfilled! 🎉',
                    message=f'A new study note on "{note_req.topic}" has been added.',
                    title_bn='তোমার Note Request পূরণ হয়েছে! 🎉',
                    message_bn=f'"{note_req.topic}" বিষয়ে একটি নতুন study note যোগ করা হয়েছে।',
                    link=f'/study-notes/{note.pk}/',
                )
            except NoteRequest.DoesNotExist:
                pass
        messages.success(request, 'Note added!')
        return redirect('study_notes')
    return render(request, 'core/study_note_add.html', {
        'subjects': subjects,
        'classes': classes,
        'linked_request': linked_request,
    })


@admin_required
def study_note_edit(request, pk):
    from ..models import StudyNote
    note = get_object_or_404(StudyNote, pk=pk)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    if request.method == 'POST':
        note.title = request.POST.get('title')
        note.subject = get_object_or_404(Subject, pk=request.POST.get('subject'))
        note.class_obj = get_object_or_404(Class, pk=request.POST.get('class_obj'))
        note.chapter = request.POST.get('chapter')
        note.content = request.POST.get('content', '')
        if request.FILES.get('pdf_file'):
            err = _upload_error(request.FILES['pdf_file'], kind='doc', max_mb=20)
            if err:
                messages.error(request, _L(request, *err))
                return redirect('study_note_edit', pk=note.pk)
            note.pdf_file = request.FILES['pdf_file']
        note.save()
        messages.success(request, 'Note updated!')
        return redirect('study_note_detail', pk=note.pk)
    return render(request, 'core/study_note_edit.html', {
        'note': note,
        'subjects': subjects,
        'classes': classes,
    })


@admin_required
def study_note_delete(request, pk):
    from ..models import StudyNote
    note = get_object_or_404(StudyNote, pk=pk)
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted!')
    return redirect('study_notes')


@login_required
def toggle_bookmark(request, pk):
    from ..models import StudyNote, NoteBookmark
    note = get_object_or_404(StudyNote, pk=pk)
    bookmark, created = NoteBookmark.objects.get_or_create(user=request.user, note=note)
    if not created:
        bookmark.delete()
        return JsonResponse({'bookmarked': False})
    return JsonResponse({'bookmarked': True})


@login_required
def update_read_progress(request, pk):
    from ..models import StudyNote, NoteReadProgress
    if request.method == 'POST':
        note = get_object_or_404(StudyNote, pk=pk)
        data = json.loads(request.body)
        scroll_percent = data.get('scroll_percent', 0)
        progress, _ = NoteReadProgress.objects.get_or_create(user=request.user, note=note)
        progress.scroll_percent = scroll_percent
        if scroll_percent >= 90:
            progress.is_completed = True
        progress.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'})


@login_required
def add_comment(request, pk):
    from ..models import StudyNote, NoteComment
    note = get_object_or_404(StudyNote, pk=pk)
    if request.method == 'POST':
        comment_text = request.POST.get('comment', '').strip()
        if comment_text:
            is_approved = request.user.profile.role == 'ADMIN' or request.user.profile.is_superadmin
            NoteComment.objects.create(
                note=note,
                user=request.user,
                comment=comment_text,
                is_approved=is_approved
            )
            messages.success(request, 'Comment posted!' if is_approved else 'Comment submitted for approval!')
    return redirect('study_note_detail', pk=pk)


@admin_required
def approve_comment(request, comment_pk):
    from ..models import NoteComment
    comment = get_object_or_404(NoteComment, pk=comment_pk)
    if request.method == 'POST':
        comment.is_approved = True
        comment.save()
    return redirect('study_note_detail', pk=comment.note.pk)


@admin_required
def delete_comment(request, comment_pk):
    from ..models import NoteComment
    comment = get_object_or_404(NoteComment, pk=comment_pk)
    note_pk = comment.note.pk
    if request.method == 'POST':
        comment.delete()
    return redirect('study_note_detail', pk=note_pk)


@admin_required
def generate_note_ai(request):
    if request.method == 'POST':
        topic = request.POST.get('topic', '')
        subject_id = request.POST.get('subject')
        class_id = request.POST.get('class_obj')
        chapter = request.POST.get('chapter', '')

        prompt = f"এই topic এর উপর একটি সম্পূর্ণ study note বাংলায় লিখো। Note টি SSC/HSC students এর জন্য। Topic: {topic}, Chapter: {chapter}. Note এ heading, subheading, examples, এবং key points থাকবে। HTML format এ দাও। Math/chemistry equation এর জন্য LaTeX delimiter use করো: inline math এর জন্য $...$ এবং display equation এর জন্য $$...$$ (যেমন: $E=mc^2$ অথবা $$\\int_0^1 x\\,dx$$)।"

        try:
            content = ai_svc.anthropic_complete(prompt, max_tokens=2000)
            from ..models import StudyNote
            note = StudyNote.objects.create(
                title=topic,
                subject=get_object_or_404(Subject, pk=subject_id),
                class_obj=get_object_or_404(Class, pk=class_id),
                chapter=chapter,
                content=content,
                created_by=request.user,
                is_active=True
            )
            messages.success(request, _L(request, 'Note generated with AI!', 'AI দিয়ে note তৈরি হয়েছে!'))
            return redirect('study_note_detail', pk=note.pk)
        except ai_svc.AIServiceError as e:
            messages.error(request, f'AI error: {e}')

    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    return render(request, 'core/generate_note.html', {
        'subjects': subjects,
        'classes': classes,
    })


@login_required
def generate_mcq(request, pk):
    if request.method == 'POST':
        from ..models import StudyNote

        note = get_object_or_404(StudyNote, pk=pk)

        prompt = f"এই study note থেকে ১০টি MCQ প্রশ্ন বাংলায় তৈরি করো। প্রতিটি প্রশ্নে ৪টি option এবং সঠিক উত্তর দাও। Math/chemistry equation এর জন্য LaTeX delimiter use করো ($...$ inline এর জন্য, $$...$$ display এর জন্য)। JSON format এ দাও এভাবে: {{\"mcqs\": [{{\"question\": \"...\", \"options\": [\"ক) ...\", \"খ) ...\", \"গ) ...\", \"ঘ) ...\"], \"answer\": \"ক\"}}]}}\n\nNote:\n{note.content[:3000]}"

        try:
            text = ai_svc.anthropic_complete(prompt, max_tokens=2000)
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                mcq_data = json.loads(json_match.group())
                return JsonResponse({'mcqs': mcq_data.get('mcqs', [])})
            return JsonResponse({'mcqs': [], 'error': 'Could not parse MCQs'})
        except ai_svc.AIServiceError as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Invalid request'})


@login_required
def summarize_note(request, pk):
    if request.method == 'POST':
        from ..models import StudyNote

        note = get_object_or_404(StudyNote, pk=pk)

        prompt = f"এই study note টি সহজ বাংলায় সংক্ষেপ করো। Key points bullet points এ দাও। ৩-৫ টি main point এবং একটি summary paragraph লিখো। Math/chemistry equation এর জন্য LaTeX delimiter use করো ($...$ inline, $$...$$ display)।\n\nNote:\n{note.content[:3000]}"

        try:
            summary = ai_svc.anthropic_complete(prompt, max_tokens=1000)
            return JsonResponse({'summary': summary})
        except ai_svc.AIServiceError as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Invalid request'})


@login_required
def ask_ai(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        question = data.get('question', '')
        note_content = data.get('note_content', '')

        prompt = f"Based on this study note, answer in Bengali:\n\nNote:\n{note_content}\n\nQuestion: {question}\n\nPlease respond in Bengali. For any math or chemistry equations, wrap them in LaTeX delimiters: $...$ for inline, $$...$$ for display equations."

        try:
            answer = ai_svc.anthropic_complete(prompt, max_tokens=1000)
            return JsonResponse({'answer': answer})
        except ai_svc.AIServiceError as e:
            return JsonResponse({'answer': f'Error: {e}'})

    return JsonResponse({'error': 'Invalid request'})


# -------- CONTEST --------

