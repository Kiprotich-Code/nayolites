"""
Audit logging utility for the Nayolites platform.

Use audit_log() throughout the application to record security-sensitive events.
This utility never raises — a failed audit write is logged to Python's logger
but never aborts the calling transaction.

Requirements: 17.1, 17.2, 17.3, 17.4
"""

import logging

from .models import AuditAction, AuditLog

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """Extract client IP, preferring X-Forwarded-For header."""
    if request is None:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def audit_log(*, actor, action, obj=None, description='', request=None):
    """
    Record a security-sensitive event to the AuditLog.

    Parameters:
        actor:       User instance (or None for unauthenticated events)
        action:      AuditAction choice string (e.g. AuditAction.LOGIN_SUCCESS)
        obj:         The affected model instance (optional)
        description: Human-readable summary of the event
        request:     Django HttpRequest — used to extract IP address (optional)

    Never raises. Failures are caught and logged to the Python logger so
    audit failures never abort legitimate business operations.
    """
    try:
        AuditLog.objects.create(
            actor=actor,
            action=action,
            model_name=obj.__class__.__name__ if obj else '',
            object_id=str(obj.pk) if obj and obj.pk else '',
            description=description,
            ip_address=_get_client_ip(request),
        )
    except Exception:
        logger.exception(
            'audit_log: failed to record entry (action=%s, actor=%s)',
            action,
            actor,
        )
