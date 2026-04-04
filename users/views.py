from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect


def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # user create
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})

        user = User.objects.create_user(username=username, password=password)
        user.save()

        return redirect('login')

    return render(request, 'register.html')


from django.contrib.auth import authenticate, login

def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('home')

        return render(request, 'login.html', {'error': 'Invalid credentials'})

    return render(request, 'login.html')


def dashboard(request):
    return render(request, 'home.html')