"""
Context processors for the Nayolites platform.

Injects college-wide constants and (for authenticated staff) navigation
permission flags into every template context.
"""

from datetime import datetime

from django.conf import settings


def college_settings(request):
    """
    Provide institution-level context to all templates.
    For authenticated staff, also injects nav_perms for sidebar visibility.
    """
    ctx = {
        'college': {
            'name': settings.COLLEGE_NAME,
            'short_name': settings.COLLEGE_SHORT_NAME,
            'tagline': settings.COLLEGE_TAGLINE,
            'address': settings.COLLEGE_ADDRESS,
            'phone': settings.COLLEGE_PHONE,
            'email': settings.COLLEGE_EMAIL,
            'website': settings.COLLEGE_WEBSITE,
            'currency': settings.COLLEGE_CURRENCY,
            'currency_symbol': settings.COLLEGE_CURRENCY_SYMBOL,
            'year': datetime.now().year,
        }
    }

    # Inject permission-aware navigation flags for authenticated staff
    if request.user.is_authenticated and request.user.is_staff:
        u = request.user
        ctx['nav_perms'] = {
            'students':         u.has_perm('students.view_studentprofile'),
            'courses':          u.has_perm('courses.view_course'),
            'enrollments':      u.has_perm('enrollments.view_enrollment'),
            'academic_periods': u.has_perm('enrollments.view_academicperiod'),
            'finance':          any(u.has_perm(p) for p in [
                                    'finance.view_invoice',
                                    'finance.view_payment',
                                    'finance.view_feestructure',
                                ]),
            'results':          u.has_perm('results.view_result'),
            'content':          u.has_perm('content.view_coursecontent'),
            'users':            u.has_perm('accounts.view_user'),
            'groups':           u.has_perm('auth.view_group'),
            'audit_log':        u.has_perm('core.view_auditlog'),
            'settings':         u.has_perm('core.change_collegesettings'),
        }
        # Surface current user info for sidebar display
        ctx['sidebar_user'] = {
            'initials': (u.first_name[:1] + u.last_name[:1]).upper() or '?',
            'display_name': u.get_short_name() or u.email,
            'groups': ', '.join(u.groups.values_list('name', flat=True)[:2]) or 'Staff',
        }
    else:
        ctx['nav_perms'] = {}
        ctx['sidebar_user'] = {}

    return ctx
