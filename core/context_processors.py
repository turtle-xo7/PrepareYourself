def user_role(request):
    is_admin = False
    if request.user.is_authenticated:
        try:
            is_admin = request.user.profile.role == 'ADMIN'
        except:
            is_admin = False
    return {'is_admin': is_admin}