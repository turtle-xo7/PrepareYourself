from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Board, Subject, Class, Question, UserProfile
from datetime import datetime

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
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'STUDENT')
        plan = request.POST.get('plan', 'FREE')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'এই username আগে থেকে আছে।')
            return render(request, 'core/signup.html')

        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(
            user=user,
            role=role,
            plan=plan,
            is_admin=(role == 'ADMIN')
        )
        login(request, user)

        if plan != 'FREE':
            return redirect('checkout')

        messages.success(request, 'Account created successfully!')
        return redirect('home')
    return render(request, 'core/signup.html')


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
    return render(request, 'core/dashboard.html')

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

    # Premium check
    is_premium = False
    if request.user.is_authenticated:
        try:
            is_premium = request.user.profile.is_premium
        except UserProfile.DoesNotExist:
            pass

    # Free user দের জন্য শুধু প্রথম 10 টা
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


# -------- MANAGE PANEL (ADMIN ONLY) --------

@admin_required
def manage_dashboard(request):
    context = {
        'total_questions': Question.objects.count(),
        'total_boards': Board.objects.count(),
        'total_subjects': Subject.objects.count(),
        'total_classes': Class.objects.count(),
        'recent_questions': Question.objects.select_related(
            'board', 'subject', 'class_obj'
        ).order_by('-created_at')[:5],
    }
    return render(request, 'manage/dashboard.html', context)

@admin_required
def manage_questions(request):
    questions = Question.objects.select_related(
        'board', 'subject', 'class_obj'
    ).order_by('-created_at')
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