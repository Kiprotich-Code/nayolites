"""
Custom error handlers for the Nayolites platform.

These replace Django's default error pages to:
- Match the institutional design system
- Never expose stack traces to non-superusers in production
- Return appropriate HTTP status codes

Requirements: 20.1, 20.2, 20.3
"""

from django.shortcuts import render


def permission_denied(request, exception=None):
    """HTTP 403 — Permission Denied handler."""
    return render(request, 'errors/403.html', status=403)


def page_not_found(request, exception=None):
    """HTTP 404 — Page Not Found handler."""
    return render(request, 'errors/404.html', status=404)


def server_error(request):
    """HTTP 500 — Server Error handler."""
    return render(request, 'errors/500.html', status=500)
