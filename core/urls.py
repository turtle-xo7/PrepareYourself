from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('question-bank/', views.question_bank, name='question_bank'),
    path('login/', views.login_view, name='login'),
    path('study-notes/', views.study_notes, name='study_notes'),
    path('pricing/', views.pricing, name='pricing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('practical-lab/', views.practical_lab, name='practical_lab'),

    # Manage Panel
    path('manage/', views.manage_dashboard, name='manage_dashboard'),
    path('manage/questions/', views.manage_questions, name='manage_questions'),
    path('manage/questions/add/', views.question_add, name='question_add'),
    path('manage/questions/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('manage/questions/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('manage/boards/', views.manage_boards, name='manage_boards'),
    path('manage/boards/add/', views.board_add, name='board_add'),
    path('manage/boards/<int:pk>/delete/', views.board_delete, name='board_delete'),
    path('manage/subjects/', views.manage_subjects, name='manage_subjects'),
    path('manage/subjects/add/', views.subject_add, name='subject_add'),
    path('manage/subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),
    path('manage/classes/', views.manage_classes, name='manage_classes'),
    path('manage/classes/add/', views.class_add, name='class_add'),
    path('manage/classes/<int:pk>/delete/', views.class_delete, name='class_delete'),
    path('signup/', views.signup_view, name='signup'),
    path('checkout/', views.checkout, name='checkout'),
    path('logout/', views.logout_view, name='logout'),
    path('practical-videos/', views.practical_videos, name='practical_videos'),
    path('practical-videos/add/', views.video_add, name='video_add'),
    path('practical-videos/<int:pk>/delete/', views.video_delete, name='video_delete'),
    path('superadmin/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/user/<int:pk>/update/', views.update_user, name='update_user'),
    ]