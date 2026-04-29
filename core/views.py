from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
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
            profile = request.user.profile
            if profile.role == 'ADMIN' or profile.is_superadmin:
                return view_func(request, *args, **kwargs)
            if not profile.is_premium:
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

        # Email দিয়ে login support
        if '@' in username:
            try:
                from django.contrib.auth.models import User
                user_obj = User.objects.get(email=username)
                username = user_obj.username
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username/Email বা Password ভুল।')
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
    from .models import Board
    boards = Board.objects.filter(is_active=True)
    return render(request, 'core/home.html', {'boards': boards})

def pricing(request):
    return render(request, 'core/pricing.html')


SUBJECT_COLOR_HEX = {
    'blue': '#3b82f6', 'red': '#ef4444', 'green': '#22c55e',
    'purple': '#a855f7', 'orange': '#f97316', 'yellow': '#eab308',
    'pink': '#ec4899', 'teal': '#14b8a6', 'indigo': '#6366f1',
    'cyan': '#06b6d4', 'emerald': '#10b981',
}


def _streak_from_dates(active_dates, today):
    """Walk backwards from today (or yesterday) and count consecutive active days."""
    from datetime import timedelta
    if today in active_dates:
        day = today
    elif (today - timedelta(days=1)) in active_dates:
        day = today - timedelta(days=1)
    else:
        return 0
    count = 0
    while day in active_dates:
        count += 1
        day = day - timedelta(days=1)
    return count


def _longest_streak(active_dates):
    from datetime import timedelta
    if not active_dates:
        return 0
    sorted_dates = sorted(active_dates)
    longest = run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    return max(longest, run)


@login_required
def dashboard(request):
    try:
        if request.user.profile.role == 'ADMIN' and not request.user.profile.is_superadmin:
            return redirect('teacher_dashboard')
    except:
        pass

    try:
        if not request.user.profile.is_premium:
            messages.error(request, 'এই feature শুধু Premium users এর জন্য।')
            return redirect('pricing')
    except:
        return redirect('pricing')

    from .models import UserProgress, TeacherFeedback
    from django.db.models import Count, Q
    from django.db.models.functions import TruncDate
    from datetime import timedelta
    from django.utils import timezone
    from collections import defaultdict, Counter

    user = request.user
    progress = UserProgress.objects.filter(user=user).select_related(
        'question', 'question__subject'
    )

    # ----- Headline stats -----
    total_answered = progress.count()
    total_correct = progress.filter(is_correct=True).count()
    total_wrong = total_answered - total_correct
    accuracy = round((total_correct / total_answered * 100), 1) if total_answered else 0

    # ----- This week vs last week (for trend arrows) -----
    today = timezone.now().date()
    week_start = today - timedelta(days=6)
    last_week_start = today - timedelta(days=13)
    last_week_end = today - timedelta(days=7)

    this_week_qs = progress.filter(answered_at__date__gte=week_start)
    last_week_qs = progress.filter(answered_at__date__range=(last_week_start, last_week_end))
    this_week_count = this_week_qs.count()
    last_week_count = last_week_qs.count()
    this_week_correct = this_week_qs.filter(is_correct=True).count()
    last_week_correct = last_week_qs.filter(is_correct=True).count()

    this_week_acc = round((this_week_correct / this_week_count * 100), 1) if this_week_count else 0
    last_week_acc = round((last_week_correct / last_week_count * 100), 1) if last_week_count else 0
    accuracy_delta = round(this_week_acc - last_week_acc, 1)

    if last_week_count == 0:
        volume_delta_pct = None
    else:
        volume_delta_pct = round(((this_week_count - last_week_count) / last_week_count) * 100, 1)

    # ----- Streak -----
    active_dates = set(
        progress.annotate(d=TruncDate('answered_at'))
                .values_list('d', flat=True).distinct()
    )
    current_streak = _streak_from_dates(active_dates, today)
    longest_streak = _longest_streak(active_dates)

    daily_goal = 10
    today_count = progress.filter(answered_at__date=today).count()
    goal_progress = min(round((today_count / daily_goal) * 100), 100) if daily_goal else 0

    if current_streak >= 30:
        streak_msg = "🔥 দারুণ! তুমি প্রায় unstoppable — keep the fire alive!"
    elif current_streak >= 7:
        streak_msg = "এক সপ্তাহ ধরে চালিয়ে যাচ্ছ। Consistency জেতে — keep going!"
    elif current_streak >= 3:
        streak_msg = "ভালো streak তৈরি হচ্ছে। আজ আরও কয়েকটা প্রশ্ন practice করো।"
    elif current_streak >= 1:
        streak_msg = "শুরু হয়েছে! আগামীকালও log in করে streak ধরে রাখো।"
    else:
        streak_msg = "আজই শুরু করো — একটাই প্রশ্ন answer করো, streak শুরু হবে।"

    # ----- 30-day heatmap -----
    counts_30 = dict(
        progress.filter(answered_at__date__gte=today - timedelta(days=29))
                .annotate(d=TruncDate('answered_at'))
                .values_list('d')
                .annotate(c=Count('id'))
                .values_list('d', 'c')
    )
    heatmap = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        c = counts_30.get(day, 0)
        if c == 0:
            lvl = 0
        elif c < 5:
            lvl = 1
        elif c < 15:
            lvl = 2
        elif c < 30:
            lvl = 3
        else:
            lvl = 4
        heatmap.append({
            'date': day.strftime('%Y-%m-%d'),
            'label': day.strftime('%d %b'),
            'count': c,
            'level': lvl,
        })

    # ----- 7-day daily activity -----
    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        c = progress.filter(answered_at__date=day).count()
        cc = progress.filter(answered_at__date=day, is_correct=True).count()
        daily_data.append({'day': day.strftime('%a'), 'count': c, 'correct': cc})

    # ----- 30-day accuracy trend -----
    by_day = {}
    rows_30 = (
        progress.filter(answered_at__date__gte=today - timedelta(days=29))
                .annotate(d=TruncDate('answered_at'))
                .values('d')
                .annotate(total=Count('id'), correct=Count('id', filter=Q(is_correct=True)))
    )
    for r in rows_30:
        by_day[r['d']] = (r['total'], r['correct'])
    accuracy_trend = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        t, c = by_day.get(day, (0, 0))
        accuracy_trend.append({
            'day': day.strftime('%d %b'),
            'accuracy': round((c / t * 100), 1) if t else None,
        })

    # ----- Subjects (collapsible cards + pie) -----
    subj_agg = list(
        progress.values(
            'question__subject__id',
            'question__subject__name',
            'question__subject__icon',
            'question__subject__color',
        ).annotate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True)),
        ).order_by('-total')
    )
    diff_rows = list(
        progress.values('question__subject__id', 'question__difficulty')
                .annotate(c=Count('id'))
    )
    diff_map = defaultdict(lambda: {'Easy': 0, 'Medium': 0, 'Hard': 0})
    for r in diff_rows:
        diff_map[r['question__subject__id']][r['question__difficulty']] = r['c']

    week_rows = list(
        this_week_qs.annotate(d=TruncDate('answered_at'))
                    .values('question__subject__id', 'd')
                    .annotate(c=Count('id'))
    )
    week_map = defaultdict(dict)
    for r in week_rows:
        week_map[r['question__subject__id']][r['d']] = r['c']

    subjects_data = []
    for s in subj_agg:
        sid = s['question__subject__id']
        total = s['total']
        correct = s['correct']
        wrong = total - correct
        acc = round((correct / total * 100), 1) if total else 0
        weekly = []
        max_in_week = 0
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            c = week_map.get(sid, {}).get(day, 0)
            max_in_week = max(max_in_week, c)
            weekly.append({'day': day.strftime('%a'), 'count': c})
        for w in weekly:
            w['height'] = round((w['count'] / max_in_week) * 100) if max_in_week else 0
        color_name = s['question__subject__color'] or 'blue'
        subjects_data.append({
            'id': sid,
            'name': s['question__subject__name'],
            'icon': s['question__subject__icon'] or '📚',
            'color': color_name,
            'hex': SUBJECT_COLOR_HEX.get(color_name, '#3b82f6'),
            'total': total,
            'correct': correct,
            'wrong': wrong,
            'accuracy': acc,
            'difficulty': diff_map[sid],
            'weekly': weekly,
        })

    # ----- Insights -----
    weekday_total = Counter()
    for ts in progress.values_list('answered_at', flat=True):
        weekday_total[ts.strftime('%A')] += 1
    best_day = max(weekday_total, key=weekday_total.get) if weekday_total else None

    weakest = None
    for s in subjects_data:
        if s['total'] >= 5:
            if weakest is None or s['accuracy'] < weakest['accuracy']:
                weakest = s

    # ----- Rank (among students) by total correct answers -----
    rank = User.objects.filter(profile__role='STUDENT').annotate(
        cc=Count('progress', filter=Q(progress__is_correct=True))
    ).filter(cc__gt=total_correct).count() + 1
    total_students = User.objects.filter(profile__role='STUDENT').count() or 1

    # ----- Teacher feedback -----
    feedbacks = list(
        TeacherFeedback.objects.filter(student=user)
                                .select_related('teacher', 'progress__question__subject')
                                .order_by('-created_at')[:3]
    )
    unread_count = TeacherFeedback.objects.filter(student=user, is_read=False).count()

    return render(request, 'core/dashboard.html', {
        # headline
        'total_answered': total_answered,
        'total_correct': total_correct,
        'total_wrong': total_wrong,
        'accuracy': accuracy,
        # trends
        'this_week_count': this_week_count,
        'last_week_count': last_week_count,
        'volume_delta_pct': volume_delta_pct,
        'this_week_acc': this_week_acc,
        'accuracy_delta': accuracy_delta,
        # streak
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'today_count': today_count,
        'daily_goal': daily_goal,
        'goal_progress': goal_progress,
        'streak_msg': streak_msg,
        'heatmap': heatmap,
        # charts
        'daily_data': daily_data,
        'accuracy_trend': accuracy_trend,
        # subjects
        'subjects_data': subjects_data,
        # insights
        'best_day': best_day,
        'weakest': weakest,
        # rank
        'rank': rank,
        'total_students': total_students,
        # feedback
        'feedbacks': feedbacks,
        'unread_count': unread_count,
    })


@login_required
def progress_history(request):
    try:
        if request.user.profile.role == 'ADMIN' and not request.user.profile.is_superadmin:
            return redirect('teacher_dashboard')
    except:
        pass

    try:
        if not request.user.profile.is_premium:
            messages.error(request, 'এই feature শুধু Premium users এর জন্য।')
            return redirect('pricing')
    except:
        return redirect('pricing')

    from .models import UserProgress
    from django.db.models import Count, Q
    from django.db.models.functions import TruncDate
    from datetime import timedelta, datetime as dt
    from django.utils import timezone
    from django.core.paginator import Paginator

    user = request.user
    base = UserProgress.objects.filter(user=user).select_related(
        'question', 'question__subject', 'question__board'
    )

    # Filters
    subject_filter = request.GET.get('subject') or ''
    result_filter = request.GET.get('result') or ''
    difficulty_filter = request.GET.get('difficulty') or ''
    date_from = request.GET.get('from') or ''
    date_to = request.GET.get('to') or ''

    qs = base
    if subject_filter:
        qs = qs.filter(question__subject_id=subject_filter)
    if result_filter == 'correct':
        qs = qs.filter(is_correct=True)
    elif result_filter == 'wrong':
        qs = qs.filter(is_correct=False)
    if difficulty_filter in ('Easy', 'Medium', 'Hard'):
        qs = qs.filter(question__difficulty=difficulty_filter)
    if date_from:
        try:
            qs = qs.filter(answered_at__date__gte=dt.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(answered_at__date__lte=dt.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    qs = qs.order_by('-answered_at')

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    filtered_count = paginator.count

    # Summary stats — over user's full history (not the filter)
    today = timezone.now().date()
    week_start = today - timedelta(days=6)
    week_qs = base.filter(answered_at__date__gte=week_start)
    week_total = week_qs.count()
    week_correct = week_qs.filter(is_correct=True).count()
    week_accuracy = round((week_correct / week_total * 100), 1) if week_total else 0

    active_dates = set(
        base.annotate(d=TruncDate('answered_at')).values_list('d', flat=True).distinct()
    )
    current_streak = _streak_from_dates(active_dates, today)

    total_all = base.count()
    correct_all = base.filter(is_correct=True).count()
    accuracy_all = round((correct_all / total_all * 100), 1) if total_all else 0

    subjects = Subject.objects.filter(is_active=True).order_by('name')

    params = request.GET.copy()
    params.pop('page', None)
    qs_string = params.urlencode()

    has_filters = any([subject_filter, result_filter, difficulty_filter, date_from, date_to])

    return render(request, 'core/progress_history.html', {
        'page_obj': page_obj,
        'filtered_count': filtered_count,
        'subjects': subjects,
        'subject_filter': subject_filter,
        'result_filter': result_filter,
        'difficulty_filter': difficulty_filter,
        'date_from': date_from,
        'date_to': date_to,
        'has_filters': has_filters,
        'qs_string': qs_string,
        # summary
        'current_streak': current_streak,
        'week_total': week_total,
        'week_correct': week_correct,
        'week_accuracy': week_accuracy,
        'total_all': total_all,
        'accuracy_all': accuracy_all,
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
    total_boards = Board.objects.filter(is_active=True).count()
    total_subjects = Subject.objects.filter(is_active=True).count()
    total_classes = Class.objects.count()
    recent_questions = Question.objects.select_related('board', 'subject').order_by('-created_at')[:5]
    return render(request, 'manage/dashboard.html', {
        'total_questions': total_questions,
        'total_videos': total_videos,
        'total_boards': total_boards,
        'total_subjects': total_subjects,
        'total_classes': total_classes,
        'recent_questions': recent_questions,
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


@admin_required
def teacher_dashboard(request):
    from .models import UserProgress
    from datetime import timedelta
    from django.utils import timezone

    today = timezone.now().date()

    students = UserProfile.objects.filter(
        role='STUDENT', is_superadmin=False
    ).select_related('user').order_by('-user__date_joined')

    student_data = []
    total_answered_all = 0
    active_today = 0
    accuracy_list = []

    for s in students:
        progress = UserProgress.objects.filter(user=s.user)
        total = progress.count()
        correct = progress.filter(is_correct=True).count()
        today_count = progress.filter(answered_at__date=today).count()
        accuracy = round((correct / total * 100), 1) if total > 0 else 0
        total_answered_all += total
        if today_count > 0:
            active_today += 1
        if total > 0:
            accuracy_list.append(accuracy)
        student_data.append({
            'profile': s,
            'total': total,
            'correct': correct,
            'wrong': total - correct,
            'accuracy': accuracy,
            'today_count': today_count,
        })

    avg_accuracy = round(sum(accuracy_list) / len(accuracy_list), 1) if accuracy_list else 0

    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = UserProgress.objects.filter(answered_at__date=day).count()
        correct = UserProgress.objects.filter(answered_at__date=day, is_correct=True).count()
        daily_data.append({
            'day': day.strftime('%a'),
            'count': count,
            'correct': correct,
        })

    return render(request, 'teacher/dashboard.html', {
        'student_data': student_data,
        'total_answered_all': total_answered_all,
        'active_today': active_today,
        'avg_accuracy': avg_accuracy,
        'daily_data': daily_data,
    })


@admin_required
def student_detail(request, pk):
    from .models import UserProgress
    from django.db.models import Count, Q
    from datetime import timedelta
    from django.utils import timezone

    profile = get_object_or_404(UserProfile, pk=pk)
    progress = UserProgress.objects.filter(user=profile.user).select_related('question', 'question__subject')

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
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        count = progress.filter(answered_at__date=day).count()
        correct = progress.filter(answered_at__date=day, is_correct=True).count()
        daily_data.append({
            'day': day.strftime('%d %b'),
            'count': count,
            'correct': correct
        })

    history = progress.order_by('-answered_at')[:30]

    return render(request, 'teacher/student_detail.html', {
        'profile': profile,
        'total_answered': total_answered,
        'total_correct': total_correct,
        'total_wrong': total_wrong,
        'accuracy': accuracy,
        'subject_progress': list(subject_progress),
        'daily_data': daily_data,
        'history': history,
    })


@admin_required
def give_feedback(request, progress_pk):
    from .models import UserProgress, TeacherFeedback
    progress = get_object_or_404(UserProgress, pk=progress_pk)
    if request.method == 'POST':
        comment = request.POST.get('comment', '').strip()
        if comment:
            TeacherFeedback.objects.create(
                teacher=request.user,
                student=progress.user,
                progress=progress,
                comment=comment
            )
            messages.success(request, 'Feedback sent!')
    return redirect('student_detail', pk=progress.user.profile.pk)


@login_required
def notifications(request):
    from .models import TeacherFeedback
    feedbacks = TeacherFeedback.objects.filter(
        student=request.user
    ).select_related('teacher', 'progress__question')
    feedbacks.filter(is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {
        'feedbacks': feedbacks,
    })


# -------- STUDY NOTES --------

@premium_required
def study_notes(request):
    from .models import StudyNote, NoteBookmark
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
    from .models import StudyNote, NoteBookmark, NoteReadProgress, NoteComment

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
    from .models import StudyNote
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    if request.method == 'POST':
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
        messages.success(request, 'Note added!')
        return redirect('study_notes')
    return render(request, 'core/study_note_add.html', {
        'subjects': subjects,
        'classes': classes,
    })


@admin_required
def study_note_edit(request, pk):
    from .models import StudyNote
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
    from .models import StudyNote
    note = get_object_or_404(StudyNote, pk=pk)
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted!')
    return redirect('study_notes')


@login_required
def toggle_bookmark(request, pk):
    from .models import StudyNote, NoteBookmark
    note = get_object_or_404(StudyNote, pk=pk)
    bookmark, created = NoteBookmark.objects.get_or_create(user=request.user, note=note)
    if not created:
        bookmark.delete()
        return JsonResponse({'bookmarked': False})
    return JsonResponse({'bookmarked': True})


@login_required
def update_read_progress(request, pk):
    from .models import StudyNote, NoteReadProgress
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
    from .models import StudyNote, NoteComment
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
    from .models import NoteComment
    comment = get_object_or_404(NoteComment, pk=comment_pk)
    if request.method == 'POST':
        comment.is_approved = True
        comment.save()
    return redirect('study_note_detail', pk=comment.note.pk)


@admin_required
def delete_comment(request, comment_pk):
    from .models import NoteComment
    comment = get_object_or_404(NoteComment, pk=comment_pk)
    note_pk = comment.note.pk
    if request.method == 'POST':
        comment.delete()
    return redirect('study_note_detail', pk=note_pk)


@admin_required
def generate_note_ai(request):
    if request.method == 'POST':
        import urllib.request
        import urllib.error
        topic = request.POST.get('topic', '')
        subject_id = request.POST.get('subject')
        class_id = request.POST.get('class_obj')
        chapter = request.POST.get('chapter', '')

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [{
                "role": "user",
                "content": f"এই topic এর উপর একটি সম্পূর্ণ study note বাংলায় লিখো। Note টি SSC/HSC students এর জন্য। Topic: {topic}, Chapter: {chapter}. Note এ heading, subheading, examples, এবং key points থাকবে। HTML format এ দাও। Math/chemistry equation এর জন্য LaTeX delimiter use করো: inline math এর জন্য $...$ এবং display equation এর জন্য $$...$$ (যেমন: $E=mc^2$ অথবা $$\\int_0^1 x\\,dx$$)।"
            }]
        }, ensure_ascii=False).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'anthropic-version': '2023-06-01',
                'x-api-key': settings.ANTHROPIC_API_KEY,
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result['content'][0]['text']
                from .models import StudyNote
                note = StudyNote.objects.create(
                    title=topic,
                    subject=get_object_or_404(Subject, pk=subject_id),
                    class_obj=get_object_or_404(Class, pk=class_id),
                    chapter=chapter,
                    content=content,
                    created_by=request.user,
                    is_active=True
                )
                messages.success(request, 'AI দিয়ে note তৈরি হয়েছে!')
                return redirect('study_note_detail', pk=note.pk)
        except Exception as e:
            messages.error(request, f'AI error: {str(e)}')

    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    return render(request, 'core/generate_note.html', {
        'subjects': subjects,
        'classes': classes,
    })


@login_required
def generate_mcq(request, pk):
    if request.method == 'POST':
        import urllib.request
        import urllib.error
        from .models import StudyNote

        note = get_object_or_404(StudyNote, pk=pk)

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [{
                "role": "user",
                "content": f"এই study note থেকে ১০টি MCQ প্রশ্ন বাংলায় তৈরি করো। প্রতিটি প্রশ্নে ৪টি option এবং সঠিক উত্তর দাও। Math/chemistry equation এর জন্য LaTeX delimiter use করো ($...$ inline এর জন্য, $$...$$ display এর জন্য)। JSON format এ দাও এভাবে: {{\"mcqs\": [{{\"question\": \"...\", \"options\": [\"ক) ...\", \"খ) ...\", \"গ) ...\", \"ঘ) ...\"], \"answer\": \"ক\"}}]}}\n\nNote:\n{note.content[:3000]}"
            }]
        }, ensure_ascii=False).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'anthropic-version': '2023-06-01',
                'x-api-key': settings.ANTHROPIC_API_KEY,
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                text = result['content'][0]['text']
                import re
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    mcq_data = json.loads(json_match.group())
                    return JsonResponse({'mcqs': mcq_data.get('mcqs', [])})
                return JsonResponse({'mcqs': [], 'error': 'Could not parse MCQs'})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Invalid request'})


@login_required
def summarize_note(request, pk):
    if request.method == 'POST':
        import urllib.request
        import urllib.error
        from .models import StudyNote

        note = get_object_or_404(StudyNote, pk=pk)

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{
                "role": "user",
                "content": f"এই study note টি সহজ বাংলায় সংক্ষেপ করো। Key points bullet points এ দাও। ৩-৫ টি main point এবং একটি summary paragraph লিখো। Math/chemistry equation এর জন্য LaTeX delimiter use করো ($...$ inline, $$...$$ display)।\n\nNote:\n{note.content[:3000]}"
            }]
        }, ensure_ascii=False).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'anthropic-version': '2023-06-01',
                'x-api-key': settings.ANTHROPIC_API_KEY,
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                summary = result['content'][0]['text']
                return JsonResponse({'summary': summary})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Invalid request'})


@login_required
def ask_ai(request):
    if request.method == 'POST':
        import urllib.request
        import urllib.error
        data = json.loads(request.body)
        question = data.get('question', '')
        note_content = data.get('note_content', '')

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": f"Based on this study note, answer in Bengali:\n\nNote:\n{note_content}\n\nQuestion: {question}\n\nPlease respond in Bengali. For any math or chemistry equations, wrap them in LaTeX delimiters: $...$ for inline, $$...$$ for display equations."
                }
            ]
        }, ensure_ascii=False).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'anthropic-version': '2023-06-01',
                'x-api-key': settings.ANTHROPIC_API_KEY,
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                answer = result['content'][0]['text']
                return JsonResponse({'answer': answer})
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            return JsonResponse({'answer': f'Error: {error_body}'})
        except Exception as e:
            return JsonResponse({'answer': f'Error: {str(e)}'})

    return JsonResponse({'error': 'Invalid request'})


# -------- CONTEST --------

@login_required
def contest_list(request):
    from .models import Contest
    from django.utils import timezone
    now = timezone.now()
    active_contests = Contest.objects.filter(is_active=True, end_time__gte=now).select_related('subject', 'class_obj', 'created_by')
    past_contests = Contest.objects.filter(is_active=True, end_time__lt=now).select_related('subject', 'class_obj')[:10]
    return render(request, 'core/contest_list.html', {
        'active_contests': active_contests,
        'past_contests': past_contests,
    })


@admin_required
def contest_create(request):
    from .models import Contest, ContestQuestion
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    if request.method == 'POST':
        from django.utils import timezone
        import datetime
        contest = Contest.objects.create(
            title=request.POST.get('title'),
            created_by=request.user,
            subject=get_object_or_404(Subject, pk=request.POST.get('subject')),
            class_obj=get_object_or_404(Class, pk=request.POST.get('class_obj')),
            duration_minutes=int(request.POST.get('duration_minutes', 30)),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            is_active=True
        )
        question_texts = request.POST.getlist('question_text')
        question_types = request.POST.getlist('question_type')
        marks_list = request.POST.getlist('marks')
        option1s = request.POST.getlist('option1')
        option2s = request.POST.getlist('option2')
        option3s = request.POST.getlist('option3')
        option4s = request.POST.getlist('option4')
        correct_options = request.POST.getlist('correct_option')

        for i, qtext in enumerate(question_texts):
            if qtext.strip():
                ContestQuestion.objects.create(
                    contest=contest,
                    question_text=qtext,
                    question_type=question_types[i] if i < len(question_types) else 'MCQ',
                    marks=int(marks_list[i]) if i < len(marks_list) and marks_list[i] else 1,
                    option1=option1s[i] if i < len(option1s) else '',
                    option2=option2s[i] if i < len(option2s) else '',
                    option3=option3s[i] if i < len(option3s) else '',
                    option4=option4s[i] if i < len(option4s) else '',
                    correct_option=int(correct_options[i]) if i < len(correct_options) and correct_options[i] else None,
                )
        messages.success(request, 'Contest created!')
        return redirect('contest_detail', pk=contest.pk)
    return render(request, 'core/contest_create.html', {
        'subjects': subjects,
        'classes': classes,
    })


@login_required
def contest_detail(request, pk):
    from .models import Contest, ContestSubmission
    from django.utils import timezone
    contest = get_object_or_404(Contest, pk=pk)
    now = timezone.now()
    has_submitted = ContestSubmission.objects.filter(contest=contest, student=request.user, is_submitted=True).exists()
    is_active = contest.start_time <= now <= contest.end_time
    return render(request, 'core/contest_detail.html', {
        'contest': contest,
        'has_submitted': has_submitted,
        'is_active': is_active,
        'now': now,
    })


@login_required
def contest_join(request, pk):
    from .models import Contest, ContestSubmission
    from django.utils import timezone
    contest = get_object_or_404(Contest, pk=pk)
    now = timezone.now()

    if now < contest.start_time:
        messages.error(request, 'Contest এখনো শুরু হয়নি।')
        return redirect('contest_detail', pk=pk)
    if now > contest.end_time:
        messages.error(request, 'Contest শেষ হয়ে গেছে।')
        return redirect('contest_detail', pk=pk)

    submission, created = ContestSubmission.objects.get_or_create(
        contest=contest,
        student=request.user,
    )
    if submission.is_submitted:
        messages.error(request, 'তুমি আগেই submit করেছ।')
        return redirect('contest_leaderboard', pk=pk)

    questions = contest.questions.all()
    return render(request, 'core/contest_exam.html', {
        'contest': contest,
        'questions': questions,
        'submission': submission,
    })


@login_required
def contest_submit(request, pk):
    from .models import Contest, ContestSubmission, ContestAnswer
    from django.utils import timezone
    if request.method != 'POST':
        return redirect('contest_detail', pk=pk)

    contest = get_object_or_404(Contest, pk=pk)
    submission = get_object_or_404(ContestSubmission, contest=contest, student=request.user)

    if submission.is_submitted:
        return redirect('contest_leaderboard', pk=pk)

    total_marks = 0
    questions = contest.questions.all()

    for q in questions:
        if q.question_type == 'MCQ':
            answer_val = request.POST.get(f'q_{q.pk}')
            mcq_answer = int(answer_val) if answer_val else None
            is_correct = mcq_answer == q.correct_option if mcq_answer else False
            marks_obtained = q.marks if is_correct else 0
            total_marks += marks_obtained
            ContestAnswer.objects.create(
                submission=submission,
                question=q,
                mcq_answer=mcq_answer,
                is_correct=is_correct,
                marks_obtained=marks_obtained
            )
        else:
            creative_answer = request.POST.get(f'q_{q.pk}', '')
            ContestAnswer.objects.create(
                submission=submission,
                question=q,
                creative_answer=creative_answer,
                is_correct=None,
                marks_obtained=0
            )

    now = timezone.now()
    duration = int((now - submission.started_at).total_seconds())
    submission.submitted_at = now
    submission.total_marks = total_marks
    submission.duration_taken = duration
    submission.is_submitted = True
    submission.save()

    messages.success(request, f'Submit হয়েছে! তোমার marks: {total_marks}')
    return redirect('contest_leaderboard', pk=pk)


@login_required
def contest_leaderboard(request, pk):
    from .models import Contest, ContestSubmission
    contest = get_object_or_404(Contest, pk=pk)
    submissions = ContestSubmission.objects.filter(
        contest=contest, is_submitted=True
    ).select_related('student').order_by('-total_marks', 'duration_taken')

    my_submission = ContestSubmission.objects.filter(
        contest=contest, student=request.user, is_submitted=True
    ).first()

    return render(request, 'core/contest_leaderboard.html', {
        'contest': contest,
        'submissions': submissions,
        'my_submission': my_submission,
    })


@admin_required
def contest_delete(request, pk):
    from .models import Contest
    contest = get_object_or_404(Contest, pk=pk)
    if request.method == 'POST':
        contest.delete()
        messages.success(request, 'Contest deleted!')
        return redirect('contest_list')
    return redirect('contest_detail', pk=pk)


@login_required
def profile_view(request):
    return render(request, 'core/profile.html', {
        'profile': request.user.profile,
    })


@login_required
def profile_update(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        messages.success(request, 'Profile updated!')
        return redirect('profile')
    return render(request, 'core/profile.html', {
        'profile': request.user.profile,
    })


# -------- SYLLABUS --------

def syllabus_list(request):
    from .models import Syllabus
    syllabi = Syllabus.objects.filter(is_active=True).select_related('subject', 'class_obj', 'board')
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    boards = Board.objects.filter(is_active=True)

    subject_filter = request.GET.get('subject')
    class_filter = request.GET.get('class_obj')
    board_filter = request.GET.get('board')

    if subject_filter:
        syllabi = syllabi.filter(subject__slug=subject_filter)
    if class_filter:
        syllabi = syllabi.filter(class_obj__id=class_filter)
    if board_filter:
        syllabi = syllabi.filter(board__id=board_filter)

    return render(request, 'core/syllabus_list.html', {
        'syllabi': syllabi,
        'subjects': subjects,
        'classes': classes,
        'boards': boards,
    })


def syllabus_detail(request, pk):
    from .models import Syllabus
    syllabus = get_object_or_404(Syllabus, pk=pk, is_active=True)
    return render(request, 'core/syllabus_detail.html', {
        'syllabus': syllabus,
    })


@admin_required
def syllabus_add(request):
    from .models import Syllabus
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    boards = Board.objects.filter(is_active=True)
    if request.method == 'POST':
        Syllabus.objects.create(
            subject=get_object_or_404(Subject, pk=request.POST.get('subject')),
            class_obj=get_object_or_404(Class, pk=request.POST.get('class_obj')),
            board=get_object_or_404(Board, pk=request.POST.get('board')),
            content=request.POST.get('content', ''),
            is_active=True
        )
        messages.success(request, 'Syllabus added!')
        return redirect('syllabus_list')
    return render(request, 'core/syllabus_form.html', {
        'subjects': subjects,
        'classes': classes,
        'boards': boards,
        'action': 'Add',
    })


@admin_required
def syllabus_edit(request, pk):
    from .models import Syllabus
    syllabus = get_object_or_404(Syllabus, pk=pk)
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.all()
    boards = Board.objects.filter(is_active=True)
    if request.method == 'POST':
        syllabus.subject = get_object_or_404(Subject, pk=request.POST.get('subject'))
        syllabus.class_obj = get_object_or_404(Class, pk=request.POST.get('class_obj'))
        syllabus.board = get_object_or_404(Board, pk=request.POST.get('board'))
        syllabus.content = request.POST.get('content', '')
        syllabus.save()
        messages.success(request, 'Syllabus updated!')
        return redirect('syllabus_detail', pk=syllabus.pk)
    return render(request, 'core/syllabus_form.html', {
        'syllabus': syllabus,
        'subjects': subjects,
        'classes': classes,
        'boards': boards,
        'action': 'Edit',
    })


@admin_required
def syllabus_delete(request, pk):
    from .models import Syllabus
    syllabus = get_object_or_404(Syllabus, pk=pk)
    if request.method == 'POST':
        syllabus.delete()
        messages.success(request, 'Syllabus deleted!')
    return redirect('syllabus_list')


@superadmin_required
def export_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from django.http import HttpResponse
    from .models import UserProgress, TeacherFeedback, StudyNote, Contest, ContestSubmission, NoteBookmark

    wb = openpyxl.Workbook()

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1D4ED8', end_color='1D4ED8', fill_type='solid')

    def style_header(ws, headers):
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            ws.column_dimensions[cell.column_letter].width = max(len(header) + 5, 15)

    ws1 = wb.active
    ws1.title = 'Users'
    headers = ['Username', 'Email', 'Role', 'Plan', 'Is Superadmin', 'Joined']
    style_header(ws1, headers)
    for profile in UserProfile.objects.select_related('user').all():
        ws1.append([
            profile.user.username,
            profile.user.email,
            profile.role,
            profile.plan,
            'Yes' if profile.is_superadmin else 'No',
            profile.user.date_joined.strftime('%d-%m-%Y %H:%M'),
        ])

    ws2 = wb.create_sheet('Questions')
    headers2 = ['Board', 'Subject', 'Class', 'Year', 'Chapter', 'Question', 'Type', 'Difficulty', 'Correct Option', 'Answer Hint']
    style_header(ws2, headers2)
    for q in Question.objects.select_related('board', 'subject', 'class_obj').filter(is_active=True):
        ws2.append([
            q.board.name, q.subject.name, q.class_obj.name, q.year,
            q.chapter, q.question_text, q.question_type, q.difficulty,
            q.correct_option, q.answer_hint,
        ])

    ws3 = wb.create_sheet('Progress')
    headers3 = ['Student', 'Question', 'Subject', 'Correct', 'Answered At']
    style_header(ws3, headers3)
    for p in UserProgress.objects.select_related('user', 'question', 'question__subject').all():
        ws3.append([
            p.user.username, p.question.question_text[:50],
            p.question.subject.name, 'Yes' if p.is_correct else 'No',
            p.answered_at.strftime('%d-%m-%Y %H:%M'),
        ])

    ws4 = wb.create_sheet('Study Notes')
    headers4 = ['Title', 'Subject', 'Class', 'Chapter', 'Created By', 'Created At']
    style_header(ws4, headers4)
    for note in StudyNote.objects.select_related('subject', 'class_obj', 'created_by').all():
        ws4.append([
            note.title, note.subject.name, note.class_obj.name,
            note.chapter, note.created_by.username,
            note.created_at.strftime('%d-%m-%Y %H:%M'),
        ])

    ws5 = wb.create_sheet('Contests')
    headers5 = ['Title', 'Subject', 'Class', 'Created By', 'Duration', 'Start', 'End', 'Submissions']
    style_header(ws5, headers5)
    for c in Contest.objects.select_related('subject', 'class_obj', 'created_by').all():
        ws5.append([
            c.title, c.subject.name, c.class_obj.name, c.created_by.username,
            f"{c.duration_minutes} min",
            c.start_time.strftime('%d-%m-%Y %H:%M'),
            c.end_time.strftime('%d-%m-%Y %H:%M'),
            c.submissions.filter(is_submitted=True).count(),
        ])

    ws6 = wb.create_sheet('Contest Results')
    headers6 = ['Contest', 'Student', 'Total Marks', 'Duration (s)', 'Submitted At']
    style_header(ws6, headers6)
    for sub in ContestSubmission.objects.select_related('contest', 'student').filter(is_submitted=True):
        ws6.append([
            sub.contest.title, sub.student.username, sub.total_marks,
            sub.duration_taken,
            sub.submitted_at.strftime('%d-%m-%Y %H:%M') if sub.submitted_at else '',
        ])

    ws7 = wb.create_sheet('Teacher Feedback')
    headers7 = ['Teacher', 'Student', 'Comment', 'Is Read', 'Created At']
    style_header(ws7, headers7)
    for fb in TeacherFeedback.objects.select_related('teacher', 'student').all():
        ws7.append([
            fb.teacher.username, fb.student.username, fb.comment,
            'Yes' if fb.is_read else 'No',
            fb.created_at.strftime('%d-%m-%Y %H:%M'),
        ])

    ws8 = wb.create_sheet('Bookmarks')
    headers8 = ['Student', 'Note Title', 'Bookmarked At']
    style_header(ws8, headers8)
    for bm in NoteBookmark.objects.select_related('user', 'note').all():
        ws8.append([
            bm.user.username, bm.note.title,
            bm.created_at.strftime('%d-%m-%Y %H:%M'),
        ])

    from django.utils import timezone
    filename = f"PrepareYourself_Data_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    from django.http import HttpResponse
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response