"""
Force Password Change Middleware.

Intercepts every authenticated request and redirects to the
password-change page when force_password_change is True.

Security-critical: this enforces the first-login password change
requirement and prevents portal access until password is changed.

Requirements: 3.2
"""

from django.shortcuts import redirect
from django.urls import reverse_lazy

# URLs that are always allowed even when force_password_change is True
EXEMPT_PATHS = frozenset([
    '/auth/password-change/',
    '/auth/logout/',
    '/admin/password_change/',
    '/admin/password_change/done/',
])


class ForcePasswordChangeMiddleware:
    """
    Redirects authenticated users with force_password_change=True
    to the password change page on every request, except exempt paths.

    Must be placed in MIDDLEWARE after AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, 'force_password_change', False)
            and request.path not in EXEMPT_PATHS
            and not request.path.startswith('/admin/')
        ):
            return redirect('/auth/password-change/')
        return self.get_response(request)
