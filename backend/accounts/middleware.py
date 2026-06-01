from accounts.models import User


class CustomUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.custom_user = None
        uid = request.session.get('user_id')
        if uid:
            user = User.objects.filter(user_id=uid, is_active=True).first()
            if user:
                request.custom_user = user
            else:
                # Session from before DB reseed — drop stale auth keys
                for key in ('user_id', 'username', 'role'):
                    request.session.pop(key, None)
        return self.get_response(request)
