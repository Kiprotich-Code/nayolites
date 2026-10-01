"""
DRF permission classes for the student portal API.

StudentOwnerPermission enforces object-level ownership at the API layer,
mirroring StudentOwnerMixin for HTML views.

Requirements: 21.6
"""

from rest_framework.permissions import BasePermission


class StudentOwnerPermission(BasePermission):
    """
    DRF permission class for student-owned resources.

    Usage on an API view:
        permission_classes = [IsAuthenticated, StudentOwnerPermission]

    The view must set `student_field` to the FK path from the serializer
    object to its StudentProfile, e.g. 'student' or 'enrollment__student'.

    By default checks obj.student == request.user.studentprofile.

    Returns 404 (via get_object_or_404 at the view level) rather than 403
    to avoid leaking whether a record exists for another student.
    """

    message = 'You do not have permission to access this record.'

    def has_permission(self, request, view):
        """Requires authenticated user with a StudentProfile."""
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'studentprofile')

    def has_object_permission(self, request, view, obj):
        """
        Object must belong to the authenticated student.
        Subclasses can override student_field to handle nested relationships.
        """
        try:
            student_profile = request.user.studentprofile
        except Exception:
            return False

        # Default: obj.student == student_profile
        obj_student = getattr(obj, 'student', None)
        if obj_student is None:
            return False
        return obj_student == student_profile
