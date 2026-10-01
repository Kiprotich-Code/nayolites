"""
Authorization mixins for the Nayolites staff portal.

StaffRequiredMixin is the single reusable authorization gate for all
staff views. It ensures:
  - Unauthenticated users are redirected to /auth/login/?next=<url>
  - Authenticated users lacking the required permission receive HTTP 403
  - No view code ever uses 'if user.role == "x"' patterns

Security-critical — Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied


class StaffRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Base mixin for all staff portal views.

    Subclasses MUST declare permission_required. Example:

        class UserListView(StaffRequiredMixin, ListView):
            permission_required = 'accounts.view_user'

    Behaviour:
    - Unauthenticated → redirect to /auth/login/?next=<current path>
    - Authenticated, no permission → HTTP 403 (PermissionDenied)
    - Authenticated, has permission → proceed normally

    The same check applies to every HTTP method (GET, POST, etc.) because
    Django's PermissionRequiredMixin runs in dispatch(), before the
    method handler.
    """

    login_url = '/auth/login/'
    raise_exception = True  # raises PermissionDenied → 403 for authenticated users

    def handle_no_permission(self):
        """
        Unauthenticated users → redirect to login with next= preserved.
        Authenticated without permission → 403.
        """
        if not self.request.user.is_authenticated:
            # Let LoginRequiredMixin handle the redirect
            return super(LoginRequiredMixin, self).handle_no_permission()
        raise PermissionDenied
