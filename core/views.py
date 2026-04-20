from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Board, Subject, Class, Question, UserProfile
from datetime import datetime
import json

CURRENT_YEAR = datetime.now().year
YEARS = list(range(CURRENT_YEAR, CURRENT_YEAR - 6, -1))


# -------- DECORATORS --------

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if request.user.profile.role != 'ADMIN':
                messages.error(request, 'শুধু Teacher/Tutor/Institution এই page access করতে পারবে।')
                return redirect('home')
        except UserProfile.DoesNotExist:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def superadmin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if not request.user.profile.is_superadmin:
                return redirect('home')
        except:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def premium_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if not request.user.profile.is_premium:
                messages.error(request, 'এই feature শুধু Premium users এর জন্য।')
                return redirect('pricing')
        except UserProfile.DoesNotExist:
            return redirect('pricing')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# -------- AUTH VIEWS --------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username বা Password ভুল।')
    return render(request, 'core/login.html')


def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'STUDENT')
        plan = request.POST.get('plan', 'FREE')
        admin_code = request.POST.get('admin_code', '')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return redirect('login')

        user = User.objects.create_user(username=username, email=email, password=password)

        is_superadmin = False
        if admin_code == 'PY2026ADMIN':
            role = 'ADMIN'
            is_superadmin = True

        UserProfile.objects.create(
            user=user,
            role=role,
            plan=plan,
            is_superadmin=is_superadmin
        )

        login(request, user)

        if plan != 'FREE':
            return redirect(f'/checkout/?plan={plan}')

        return redirect('home')

    return redirect('login')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def checkout(request):
    if request.method == 'POST':
        request.user.profile.plan = request.POST.get('plan', 'BASIC')
        request.user.profile.save()
        messages.success(request, f'{request.user.profile.plan} plan activated!')
        return redirect('home')
    return render(request, 'core/checkout.html')


# -------- FRONTEND VIEWS --------

def home(request):
    return render(request, 'core/home.html')

def pricing(request):
    return render(request, 'core/pricing.html')

@premium_required
def study_notes(request):
    return render(request, 'core/study_notes.html')

@premium_required
def dashboard(request):
    from .models import UserProgress
    from django.db.models import Count, Q
    from datetime import timedelta
    from django.utils import timezone

    user = request.user
    progress = UserProgress.objects.filter(user=user)
    total_answered = progress.count()
    total_correct = progress.filter(is_correct=True).count()
    total_wrong = total_answered - total_correct
    accuracy = round((total_correct / total_answered * 100), 1) if total_answered > 0 else 0

    subject_progress = progress.values('question__subject__name').annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True))
    ).order_by('-total')[:5]

    today = timezone.now().date()
    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = progress.filter(answered_at__date=day).count()
        daily_data.append({'day': day.strftime('%a'), 'count': count})

    return render(request, 'core/dashboard.html', {
        'total_answered': total_answered,
        'total_correct': total_correct,
        'total_wrong': total_wrong,
        'accuracy': accuracy,
        'subject_progress': list(subject_progress),
        'daily_data': daily_data,
    })


@premium_required
def progress_history(request):
    from .models import UserProgress
    from django.db.models import Count, Q
    from datetime import timedelta
    from django.utils import timezone

    user = request.user
    progress = UserProgress.objects.filter(user=user).select_related('question', 'question__subject')

    total_answered = progress.count()
    total_correct = progress.filter(is_correct=True).count()
    total_wrong = total_answered - total_correct
    accuracy = round((total_correct / total_answered * 100), 1) if total_answered > 0 else 0

    subject_progress = progress.values('question__subject__name').annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True))
    ).order_by('-total')

    today = timezone.now().date()
    daily_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        count = progress.filter(answered_at__date=day).count()
        correct = progress.filter(answered_at__date=day, is_correct=True).count()
        daily_data.append({
            'day': day.strftime('%d %b'),
            'count': count,
            'correct': correct
        })

    history = progress.order_by('-answered_at')[:50]

    return render(request, 'core/progress_history.html', {
        'total_answered': total_answered,
        'total_correct': total_correct,
        'total_wrong': total_wrong,
        'accuracy': accuracy,
        'subject_progress': list(subject_progress),
        'daily_data': daily_data,
        'history': history,
    })


@premium_required
def practical_lab(request):
    from .models import PracticalVideo
    videos = PracticalVideo.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()

    subject_filter = request.GET.get('subject')
    class_filter = request.GET.get('class_obj')

    if subject_filter:
        videos = videos.filter(subject__slug=subject_filter)
    if class_filter:
        videos = videos.filter(class_obj__id=class_filter)

    return render(request, 'core/practical_lab.html', {
        'videos': videos,
        'subjects': subjects,
        'classes': classes,
    })


def question_bank(request):
    boards = Board.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    questions = Question.objects.select_related('board', 'subject', 'class_obj').filter(is_active=True)

    board = request.GET.get('board')
    subject = request.GET.get('subject')
    class_id = request.GET.get('class')
    year = request.GET.get('year')

    if board:
        questions = questions.filter(board_id=board)
    if subject:
        questions = questions.filter(subject_id=subject)
    if class_id:
        questions = questions.filter(class_obj_id=class_id)
    if year:
        questions = questions.filter(year=year)

    is_premium = False
    if request.user.is_authenticated:
        try:
            is_premium = request.user.profile.is_premium
        except UserProfile.DoesNotExist:
            pass

    if not is_premium:
        questions = questions[:10]

    return render(request, 'core/question_bank.html', {
        'boards': boards,
        'subjects': subjects,
        'classes': classes,
        'questions': questions,
        'years': YEARS,
        'is_premium': is_premium,
    })


@login_required
def track_progress(request):
    if request.method == 'POST':
        from .models import UserProgress
        data = json.loads(request.body)
        question_id = data.get('question_id')
        is_correct = data.get('is_correct', False)
        question_obj = Question.objects.filter(pk=question_id).first()
        if question_obj:
            UserProgress.objects.get_or_create(
                user=request.user,
                question=question_obj,
                defaults={'is_correct': is_correct}
            )
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'})


# -------- SUPERADMIN DASHBOARD --------

@superadmin_required
def superadmin_dashboard(request):
    from .models import PracticalVideo

    total_superadmins = UserProfile.objects.filter(is_superadmin=True).count()
    total_users = UserProfile.objects.filter(is_superadmin=False).count()
    total_students = UserProfile.objects.filter(role='STUDENT', is_superadmin=False).count()
    total_teachers = UserProfile.objects.filter(role='ADMIN', is_superadmin=False).count()
    free_users = UserProfile.objects.filter(plan='FREE', is_superadmin=False).count()
    basic_users = UserProfile.objects.filter(plan='BASIC', is_superadmin=False).count()
    premium_users = UserProfile.objects.filter(plan='PREMIUM', is_superadmin=False).count()
    paid_users = basic_users + premium_users
    total_questions = Question.objects.filter(is_active=True).count()
    total_boards = Board.objects.filter(is_active=True).count()
    total_subjects = Subject.objects.filter(is_active=True).count()
    total_videos = PracticalVideo.objects.filter(is_active=True).count()
    recent_users = UserProfile.objects.filter(is_superadmin=False).select_related('user').order_by('-user__date_joined')[:10]

    return render(request, 'core/superadmin_dashboard.html', {
        'total_superadmins': total_superadmins,
        'total_users': total_users,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'free_users': free_users,
        'basic_users': basic_users,
        'premium_users': premium_users,
        'paid_users': paid_users,
        'total_questions': total_questions,
        'total_boards': total_boards,
        'total_subjects': total_subjects,
        'total_videos': total_videos,
        'recent_users': recent_users,
    })


# -------- MANAGE PANEL (ADMIN ONLY) --------

@admin_required
def manage_dashboard(request):
    from .models import PracticalVideo
    total_questions = Question.objects.filter(is_active=True).count()
    total_videos = PracticalVideo.objects.filter(is_active=True).count()
    return render(request, 'manage/dashboard.html', {
        'total_questions': total_questions,
        'total_videos': total_videos,
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
        Question.objects.create(
            board=get_object_or_404(Board, pk=request.POST.get('board')),
            subject=get_object_or_404(Subject, pk=request.POST.get('subject')),
            class_obj=get_object_or_404(Class, pk=request.POST.get('class_obj')),
            year=request.POST.get('year'),
            chapter=request.POST.get('chapter'),
            question_text=request.POST.get('question_text'),
            question_type=request.POST.get('question_type'),
            difficulty=request.POST.get('difficulty'),
            option1=request.POST.get('option1', ''),
            option2=request.POST.get('option2', ''),
            option3=request.POST.get('option3', ''),
            option4=request.POST.get('option4', ''),
            correct_option=request.POST.get('correct_option') or None,
            answer_hint=request.POST.get('answer_hint', ''),
        )
        messages.success(request, 'Question added successfully!')
        return redirect('manage_questions')
    return render(request, 'manage/question_form.html', {
        'boards': boards, 'subjects': subjects,
        'classes': classes, 'years': YEARS, 'action': 'Add'
    })

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
        question.chapter = request.POST.get('chapter')
        question.question_text = request.POST.get('question_text')
        question.question_type = request.POST.get('question_type')
        question.difficulty = request.POST.get('difficulty')
        question.option1 = request.POST.get('option1', '')
        question.option2 = request.POST.get('option2', '')
        question.option3 = request.POST.get('option3', '')
        question.option4 = request.POST.get('option4', '')
        question.correct_option = request.POST.get('correct_option') or None
        question.answer_hint = request.POST.get('answer_hint', '')
        question.save()
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
    from .models import PracticalVideo
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
    from .models import PracticalVideo
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
    from .models import PracticalVideo
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


@premium_required
def progress_history(request):
    from .models import UserProgress
    from django.db.models import Count
    from datetime import timedelta
    from django.utils import timezone

    user = request.user
    progress = UserProgress.objects.filter(user=user).select_related('question', 'question__subject')

    total_answered = progress.count()
    total_correct = progress.filter(is_correct=True).count()
    total_wrong = total_answered - total_correct
    accuracy = round((total_correct / total_answered * 100), 1) if total_answered > 0 else 0

    # Subject wise progress
    subject_progress = progress.values(
        'question__subject__name'
    ).annotate(
        total=Count('id'),
        correct=Count('id', filter=__import__('django.db.models', fromlist=['Q']).Q(is_correct=True))
    ).order_by('-total')

    # Last 30 days activity
    today = timezone.now().date()
    daily_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        count = progress.filter(answered_at__date=day).count()
        correct = progress.filter(answered_at__date=day, is_correct=True).count()
        daily_data.append({
            'day': day.strftime('%d %b'),
            'count': count,
            'correct': correct
        })

    # Question history
    history = progress.order_by('-answered_at')[:50]

    return render(request, 'core/progress_history.html', {
        'total_answered': total_answered,
        'total_correct': total_correct,
        'total_wrong': total_wrong,
        'accuracy': accuracy,
        'subject_progress': list(subject_progress),
        'daily_data': daily_data,
        'history': history,
    })