from django.shortcuts import render

def home(request):
    return render(request, 'core/home.html')

def question_bank(request):
    return render(request, 'core/question_bank.html')

def login_view(request):
    return render(request, 'core/login.html')

def study_notes(request):
    return render(request, 'core/study_notes.html')

def pricing(request):
    return render(request, 'core/pricing.html')

def dashboard(request):
    return render(request, 'core/dashboard.html')