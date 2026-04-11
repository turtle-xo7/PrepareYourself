from django.shortcuts import render

def home(request):
    return render(request, 'core/home.html')

def question_bank(request):
    return render(request, 'core/question_bank.html')

def login_view(request):
    return render(request, 'core/login.html')


def study_notes(request):
    # Sample data for study notes
    subjects = [
        {
            'name': 'Physics',
            'icon': '⚡',
            'color': 'blue',
            'chapters': [
                {'title': 'Electrostatics', 'pages': 12, 'downloads': 1200, 'rating': 4.8},
                {'title': 'Current Electricity', 'pages': 15, 'downloads': 980, 'rating': 4.7},
                {'title': 'Magnetism', 'pages': 10, 'downloads': 750, 'rating': 4.6},
                {'title': 'Optics', 'pages': 18, 'downloads': 1100, 'rating': 4.9},
            ]
        },
        {
            'name': 'Chemistry',
            'icon': '🧪',
            'color': 'green',
            'chapters': [
                {'title': 'Acids & Bases', 'pages': 14, 'downloads': 1500, 'rating': 4.9},
                {'title': 'Periodic Table', 'pages': 20, 'downloads': 2100, 'rating': 4.8},
                {'title': 'Chemical Bonding', 'pages': 16, 'downloads': 1300, 'rating': 4.7},
                {'title': 'Organic Chemistry', 'pages': 25, 'downloads': 1800, 'rating': 4.9},
            ]
        },
        {
            'name': 'Biology',
            'icon': '🧬',
            'color': 'purple',
            'chapters': [
                {'title': 'Genetics', 'pages': 18, 'downloads': 950, 'rating': 4.6},
                {'title': 'Cell Structure', 'pages': 12, 'downloads': 1100, 'rating': 4.8},
                {'title': 'Human Physiology', 'pages': 22, 'downloads': 1400, 'rating': 4.7},
                {'title': 'Ecology', 'pages': 15, 'downloads': 800, 'rating': 4.5},
            ]
        },
        {
            'name': 'Mathematics',
            'icon': '📐',
            'color': 'yellow',
            'chapters': [
                {'title': 'Integration', 'pages': 20, 'downloads': 2200, 'rating': 4.9},
                {'title': 'Differentiation', 'pages': 18, 'downloads': 1900, 'rating': 4.8},
                {'title': 'Trigonometry', 'pages': 15, 'downloads': 1600, 'rating': 4.7},
                {'title': 'Vectors', 'pages': 12, 'downloads': 1200, 'rating': 4.6},
            ]
        },
        {
            'name': 'English',
            'icon': '📖',
            'color': 'red',
            'chapters': [
                {'title': 'Grammar Rules', 'pages': 25, 'downloads': 3000, 'rating': 4.8},
                {'title': 'Comprehension', 'pages': 15, 'downloads': 1800, 'rating': 4.6},
                {'title': 'Essay Writing', 'pages': 10, 'downloads': 1500, 'rating': 4.7},
                {'title': 'Vocabulary', 'pages': 20, 'downloads': 2000, 'rating': 4.9},
            ]
        },
        {
            'name': 'Bangla',
            'icon': '🇧🇩',
            'color': 'indigo',
            'chapters': [
                {'title': 'ব্যাকরণ', 'pages': 22, 'downloads': 2500, 'rating': 4.8},
                {'title': 'রচনা', 'pages': 12, 'downloads': 1400, 'rating': 4.6},
                {'title': 'সারাংশ', 'pages': 8, 'downloads': 1000, 'rating': 4.5},
                {'title': 'পত্র লিখন', 'pages': 10, 'downloads': 1200, 'rating': 4.7},
            ]
        }
    ]

    # Featured/Popular notes
    popular_notes = [
        {'title': 'Electrostatics Formulas', 'subject': 'Physics', 'rating': 4.8, 'downloads': '1.2k', 'icon': '⚡'},
        {'title': 'Acid-Base Titration', 'subject': 'Chemistry', 'rating': 4.9, 'downloads': '980', 'icon': '🧪'},
        {'title': 'Integration Cheat Sheet', 'subject': 'Mathematics', 'rating': 4.9, 'downloads': '2.1k', 'icon': '📐'},
        {'title': 'Genetics Key Terms', 'subject': 'Biology', 'rating': 4.6, 'downloads': '750', 'icon': '🧬'},
        {'title': 'Grammar Quick Guide', 'subject': 'English', 'rating': 4.8, 'downloads': '3k', 'icon': '📖'},
        {'title': 'Periodic Table Trends', 'subject': 'Chemistry', 'rating': 4.9, 'downloads': '1.5k', 'icon': '🧪'},
    ]

    context = {
        'subjects': subjects,
        'popular_notes': popular_notes,
    }
    return render(request, 'core/study_notes.html', context)

def pricing(request):
    return render(request, 'core/pricing.html')

def dashboard(request):
    return render(request, 'core/dashboard.html')

def home(request):
    boards = ['Dhaka', 'Chittagong', 'Rajshahi', 'Comilla', 'Sylhet', 'Jessore', 'Barisal', 'Dinajpur']
    context = {
        'boards': boards,
    }
    return render(request, 'core/home.html', context)

def practical_lab(request):
    return render(request, 'core/practical_lab.html')