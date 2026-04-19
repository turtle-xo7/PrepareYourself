def user_role(request):
    is_admin = False
    is_superadmin = False
    if request.user.is_authenticated:
        try:
            is_admin = request.user.profile.role == 'ADMIN'
            is_superadmin = request.user.profile.is_superadmin
        except:
            pass
    return {'is_admin': is_admin, 'is_superadmin': is_superadmin}