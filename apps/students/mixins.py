"""
Authorization mixins for the Nayolites student portal.

StudentOwnerMixin enforces object-level ownership for every student
portal view. Students can only access their own records.

Security-critical — Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404

from .models import StudentProfile


class StudentOwnerMixin(LoginRequiredMixin):
    """
    Mixin for student portal views.

    On dispatch():
    - Unauthenticated → redirect to /auth/login/?next=<current path>
    - Authenticated but no StudentProfile → HTTP 404 (not 403, to avoid
      leaking whether a student account exists for this user)
    - Authenticated with StudentProfile → attaches self._student_profile

    All querysets in student portal views MUST filter by the profile:

        def get_queryset(self):
            return Invoice.objects.filter(
                enrollment__student=self.get_student_profile()
            )

    URL parameter manipulation (e.g. /student/invoices/99/) is defeated
    because the queryset filter will return no results for objects that
    don't belong to this student — get_object_or_404 will then return 404.
    """

    login_url = '/auth/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        try:
            self._student_profile = request.user.studentprofile
        except StudentProfile.DoesNotExist:
            raise Http404('No student profile found for this account.')
        return super().dispatch(request, *args, **kwargs)

    def get_student_profile(self) -> StudentProfile:
        """Return the authenticated student's profile. Always safe after dispatch()."""
        return self._student_profile
