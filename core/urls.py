from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('question-bank/', views.question_bank, name='question_bank'),
    path('login/', views.login_view, name='login'),
    path('study-notes/', views.study_notes, name='study_notes'),
    path('pricing/', views.pricing, name='pricing'),
    path('dashboard/', views.dashboard, name='dashboard'),
]