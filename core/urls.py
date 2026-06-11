from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('set-language/', views.toggle_language, name='toggle_language'),
    path('question-bank/', views.question_bank, name='question_bank'),
    path('search/', views.search_page, name='search_page'),
    path('api/search/', views.search_api, name='search_api'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('logout/', views.logout_view, name='logout'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/simulate/<str:tran_id>/', views.payment_simulate, name='payment_simulate'),
    path('payment/process/<str:tran_id>/', views.payment_process, name='payment_process'),
    path('payment/success/<str:tran_id>/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    path('pricing/', views.pricing, name='pricing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('practical-lab/', views.practical_lab, name='practical_lab'),
    path('track-progress/', views.track_progress, name='track_progress'),
    path('progress/', views.progress_history, name='progress_history'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/delete-picture/', views.profile_picture_delete, name='profile_picture_delete'),

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

    # Note Requests
    path('note-requests/submit/', views.request_note, name='request_note'),
    path('manage/note-requests/', views.manage_note_requests, name='manage_note_requests'),
    path('manage/note-requests/<int:pk>/action/', views.fulfill_note_request, name='fulfill_note_request'),

    # Manage Panel
    path('manage/', views.manage_dashboard, name='manage_dashboard'),
    path('manage/questions/', views.manage_questions, name='manage_questions'),
    path('manage/questions/add/', views.question_add, name='question_add'),
    path('manage/questions/add-mcq-bulk/', views.question_add_mcq_bulk, name='question_add_mcq_bulk'),
    path('question-bank/written/<int:question_id>/', views.written_question_practice, name='written_question_practice'),
    path('question-bank/<int:question_id>/submit-solve/', views.submit_written_solve, name='submit_written_solve'),
    path('question-bank/<int:question_id>/upload-solution/', views.upload_question_solution, name='upload_question_solution'),
    path('question-bank/<int:question_id>/delete-solution/', views.delete_question_solution, name='delete_question_solution'),
    path('written-submission/<int:submission_id>/delete/', views.delete_student_submission, name='delete_student_submission'),
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
    path('superadmin/users/', views.superadmin_users, name='superadmin_users'),
    path('superadmin/revenue/', views.superadmin_revenue, name='superadmin_revenue'),
    path('superadmin/user/<int:pk>/update/', views.update_user, name='update_user'),
    path('superadmin/user/<int:pk>/delete/', views.delete_user, name='delete_user'),
    path('superadmin/user/<int:pk>/cancel-subscription/', views.cancel_subscription, name='cancel_subscription'),
    path('superadmin/export/', views.export_excel, name='export_excel'),
    path('superadmin/teacher-applications/', views.teacher_applications, name='teacher_applications'),
    path('superadmin/teacher/<int:pk>/approve/', views.approve_teacher, name='approve_teacher'),
    path('superadmin/teacher/<int:pk>/reject/', views.reject_teacher, name='reject_teacher'),
    path('superadmin/teacher/<int:pk>/assign-subjects/', views.assign_teacher_subjects, name='assign_teacher_subjects'),

    # Teacher
    path('teacher/pending/', views.teacher_pending, name='teacher_pending'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/student/<int:pk>/', views.student_detail, name='student_detail'),
    path('teacher/feedback/<int:progress_pk>/', views.give_feedback, name='give_feedback'),
    path('teacher/student/<int:student_pk>/send-feedback/', views.send_general_feedback, name='send_general_feedback'),
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
    path('contests/bank-questions/', views.contest_bank_questions, name='contest_bank_questions'),
    path('contests/<int:pk>/', views.contest_detail, name='contest_detail'),
    path('contests/<int:pk>/join/', views.contest_join, name='contest_join'),
    path('contests/<int:pk>/submit/', views.contest_submit, name='contest_submit'),
    path('contests/<int:pk>/result/', views.contest_result, name='contest_result'),
    path('contests/<int:pk>/leaderboard/', views.contest_leaderboard, name='contest_leaderboard'),
    path('contests/<int:pk>/leaderboard/data/', views.leaderboard_data, name='leaderboard_data'),
    path('contests/<int:pk>/register/', views.contest_register, name='contest_register'),
    path('contests/<int:pk>/set-rated/', views.contest_set_rated, name='contest_set_rated'),
    path('contests/<int:pk>/virtual/', views.virtual_contest, name='virtual_contest'),
    path('contests/<int:pk>/stats/', views.contest_stats, name='contest_stats'),
    path('contests/<int:pk>/delete/', views.contest_delete, name='contest_delete'),
    path('badges/', views.badge_gallery, name='badge_gallery'),
    path('profile/contests/', views.profile_contests, name='profile_contests'),
    path('api/coins/balance/', views.coin_balance_api, name='coin_balance_api'),
    path('api/badges/check/', views.check_badges_api, name='check_badges_api'),

    # Exam Mode
    path('exam-papers/', views.exam_paper_list, name='exam_paper_list'),
    path('exam-papers/<int:pk>/', views.exam_paper_detail, name='exam_paper_detail'),
    path('exam-papers/<int:pk>/exam/', views.start_exam, name='start_exam'),
    path('exam/submit-mcq/', views.submit_mcq, name='submit_mcq'),
    path('exam/<int:attempt_id>/cq/', views.exam_cq_phase, name='exam_cq_phase'),
    path('exam/<int:attempt_id>/cq/submit/', views.submit_cq, name='submit_cq'),
    path('exam/<int:attempt_id>/results/', views.exam_results, name='exam_results'),
    path('manage/grade-queue/', views.manage_grade_list, name='manage_grade_list'),
    path('manage/grade-cq/<int:attempt_id>/', views.grade_cq_submission, name='grade_cq_submission'),
    path('manage/grade-cq/<int:attempt_id>/claim/', views.claim_cq_attempt, name='claim_cq_attempt'),
    path('manage/grade-cq/<int:attempt_id>/release/', views.release_cq_attempt, name='release_cq_attempt'),
    path('manage/exam-paper/create/', views.create_exam_paper, name='create_exam_paper'),
    path('manage/exam-paper/<int:pk>/preview/', views.preview_exam, name='preview_exam'),
    path('manage/exam-paper/<int:pk>/edit/', views.edit_exam_paper, name='edit_exam_paper'),
    path('manage/exam-paper/<int:pk>/delete/', views.delete_exam_paper, name='delete_exam_paper'),
    path('manage/parse-exam-text/', views.parse_exam_text, name='parse_exam_text'),
    path('manage/extract-image-text/', views.extract_text_from_image, name='extract_image_text'),

    # Syllabus
    path('syllabus/', views.syllabus_list, name='syllabus_list'),
    path('syllabus/add/', views.syllabus_add, name='syllabus_add'),
    path('syllabus/<int:pk>/', views.syllabus_detail, name='syllabus_detail'),
    path('syllabus/<int:pk>/edit/', views.syllabus_edit, name='syllabus_edit'),
    path('syllabus/<int:pk>/delete/', views.syllabus_delete, name='syllabus_delete'),
]

from django.conf import settings
from django.conf.urls.static import static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)