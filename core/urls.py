from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('question-bank/', views.question_bank, name='question_bank'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('checkout/', views.checkout, name='checkout'),
    path('pricing/', views.pricing, name='pricing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('practical-lab/', views.practical_lab, name='practical_lab'),
    path('track-progress/', views.track_progress, name='track_progress'),
    path('progress/', views.progress_history, name='progress_history'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),

    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='core/password_reset.html',
        email_template_name='core/password_reset_email.html',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='core/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='core/password_reset_confirm.html',
        success_url='/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='core/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Practical Videos
    path('practical-videos/', views.practical_videos, name='practical_videos'),
    path('practical-videos/add/', views.video_add, name='video_add'),
    path('practical-videos/<int:pk>/delete/', views.video_delete, name='video_delete'),

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

    # Superadmin
    path('superadmin/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/user/<int:pk>/update/', views.update_user, name='update_user'),
    path('superadmin/user/<int:pk>/delete/', views.delete_user, name='delete_user'),
    path('superadmin/user/<int:pk>/cancel-subscription/', views.cancel_subscription, name='cancel_subscription'),

    # Teacher
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/student/<int:pk>/', views.student_detail, name='student_detail'),
    path('teacher/feedback/<int:progress_pk>/', views.give_feedback, name='give_feedback'),
    path('student/notifications/', views.notifications, name='notifications'),

    # Study Notes
    path('study-notes/', views.study_notes, name='study_notes'),
    path('study-notes/add/', views.study_note_add, name='study_note_add'),
    path('study-notes/ask-ai/', views.ask_ai, name='ask_ai'),
    path('study-notes/generate/', views.generate_note_ai, name='generate_note_ai'),
    path('study-notes/comment/<int:comment_pk>/approve/', views.approve_comment, name='approve_comment'),
    path('study-notes/comment/<int:comment_pk>/delete/', views.delete_comment, name='delete_comment'),
    path('study-notes/<int:pk>/', views.study_note_detail, name='study_note_detail'),
    path('study-notes/<int:pk>/edit/', views.study_note_edit, name='study_note_edit'),
    path('study-notes/<int:pk>/delete/', views.study_note_delete, name='study_note_delete'),
    path('study-notes/<int:pk>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('study-notes/<int:pk>/read-progress/', views.update_read_progress, name='update_read_progress'),
    path('study-notes/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('study-notes/<int:pk>/generate-mcq/', views.generate_mcq, name='generate_mcq'),
    path('study-notes/<int:pk>/summarize/', views.summarize_note, name='summarize_note'),

    # Contests
    path('contests/', views.contest_list, name='contest_list'),
    path('contests/create/', views.contest_create, name='contest_create'),
    path('contests/<int:pk>/', views.contest_detail, name='contest_detail'),
    path('contests/<int:pk>/join/', views.contest_join, name='contest_join'),
    path('contests/<int:pk>/submit/', views.contest_submit, name='contest_submit'),
    path('contests/<int:pk>/leaderboard/', views.contest_leaderboard, name='contest_leaderboard'),
    path('contests/<int:pk>/delete/', views.contest_delete, name='contest_delete'),

    # Syllabus
    path('syllabus/', views.syllabus_list, name='syllabus_list'),
    path('syllabus/add/', views.syllabus_add, name='syllabus_add'),
    path('syllabus/<int:pk>/', views.syllabus_detail, name='syllabus_detail'),
    path('syllabus/<int:pk>/edit/', views.syllabus_edit, name='syllabus_edit'),
    path('syllabus/<int:pk>/delete/', views.syllabus_delete, name='syllabus_delete'),

    #admin database
    path('superadmin/export/', views.export_excel, name='export_excel'),
]