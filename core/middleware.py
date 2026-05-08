class UserLanguageMiddleware:
    """Activates the user's preferred language from their profile or session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = 'bn'
        if request.user.is_authenticated:
            try:
                lang = request.user.profile.preferred_language or 'bn'
            except Exception:
                lang = request.session.get('preferred_language', 'bn')
        else:
            lang = request.session.get('preferred_language', 'bn')

        request.LANG = lang
        response = self.get_response(request)
        return response
