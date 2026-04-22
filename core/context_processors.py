def user_role(request):
    is_admin = False
    is_superadmin = False
    unread_count = 0
    if request.user.is_authenticated:
        try:
            is_admin = request.user.profile.role == 'ADMIN'
            is_superadmin = request.user.profile.is_superadmin
            if not is_admin and not is_superadmin:
                from core.models import TeacherFeedback
                unread_count = TeacherFeedback.objects.filter(
                    student=request.user, is_read=False
                ).count()
        except:
            pass
    return {'is_admin': is_admin, 'is_superadmin': is_superadmin, 'unread_count': unread_count}