from django.utils.cache import add_never_cache_headers


class NeverCacheAuthenticatedMiddleware:
    """Prevent browsers/proxies from reusing pages rendered for a user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            add_never_cache_headers(response)

        return response
