"""
Custom authentication backend for the Nayolites platform.

Authenticates by email + password, then checks account_status.
Suspended and inactive accounts are denied authentication
even if their password is correct.
"""

import logging

from django.contrib.auth.backends import ModelBackend

from .models import AccountStatus, User

logger = logging.getLogger(__name__)


class AccountStatusBackend(ModelBackend):
    """
    Authentication backend that:
    1. Accepts 'email' kwarg (in addition to the default 'username')
    2. Queries User case-insensitively by email
    3. Returns None (not raises) for non-ACTIVE accounts
    4. Stores request._auth_denied_status so the login view can show a targeted message

    Security-critical: this is the sole authentication gate for the application.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Accept email kwarg as the primary identifier
        email = kwargs.get('email') or username
        if not email:
            return None

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Run the hasher to prevent timing attacks
            User().set_password(password)
            return None

        if not user.check_password(password):
            return None

        # Account status gate (Req 1.6, 2.3, 2.4)
        # Return None but store the reason so the view can show the right message
        if user.account_status != AccountStatus.ACTIVE:
            if request is not None:
                request._auth_denied_status = user.account_status
            logger.warning(
                'Login denied for %s: account_status=%s',
                email,
                user.account_status,
            )
            return None

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
