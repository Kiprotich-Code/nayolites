"""
Academic domain services for the Nayolites platform.

These functions contain the important business operations for the academic
domain. Views orchestrate request/response; these functions own the rules.

Design principles:
- Each function is atomic (wrapped in transaction.atomic where appropriate).
- All functions write to the audit log on significant state changes.
- These functions are the single authoritative path for:
    - Creating students
    - Creating enrollments
    - Changing enrollment status
    - Approving enrollments
- Views must never bypass these functions for those operations.
- Functions raise ValueError or ValidationError with clear messages on
  invalid input — callers translate those to user-facing errors.
"""

import logging
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.audit import audit_log
from apps.core.models import AuditAction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Student services
# ---------------------------------------------------------------------------

def create_student(*, user, admission_number, created_by, request=None, **profile_fields):
    """
    Create a StudentProfile for an existing User.

    Parameters:
        user              : User instance — must not already have a student/staff profile
        admission_number  : Unique institutional identifier
        created_by        : Staff User performing the action (for audit log)
        request           : HttpRequest (optional, for IP logging)
        **profile_fields  : Additional StudentProfile fields (date_of_birth, gender, etc.)

    Returns:
        StudentProfile instance

    Raises:
        ValidationError   : If the user already has a profile or admission number is taken
        IntegrityError    : If a concurrent request creates the same admission number
    """
    from apps.students.models import StudentProfile

    with transaction.atomic():
        profile = StudentProfile(
            user=user,
            admission_number=admission_number,
            **profile_fields,
        )
        try:
            profile.full_clean()
            profile.save()
        except ValidationError:
            raise
        except IntegrityError as exc:
            raise ValidationError(
                f'Admission number "{admission_number}" is already in use.'
            ) from exc

        audit_log(
            actor=created_by,
            action=AuditAction.STUDENT_CREATED,
            obj=profile,
            description=f'Student record created: {profile} (by {created_by})',
            request=request,
        )

    return profile


def change_student_status(*, student, new_status, changed_by, notes='', request=None):
    """
    Change a StudentProfile's status with audit trail.

    Does NOT delete historical enrollment records — changing status is a
    lifecycle event, not a data purge.

    Parameters:
        student     : StudentProfile instance
        new_status  : StudentStatus value
        changed_by  : Staff User performing the action
        notes       : Optional reason for the change
        request     : HttpRequest (optional)

    Returns:
        Updated StudentProfile instance
    """
    from apps.students.models import StudentStatus

    old_status = student.status
    if old_status == new_status:
        return student

    valid = [s.value for s in StudentStatus]
    if new_status not in valid:
        raise ValueError(f'Invalid student status: {new_status}')

    with transaction.atomic():
        student.status = new_status
        student.save(update_fields=['status', 'updated_at'])

        audit_log(
            actor=changed_by,
            action=AuditAction.STUDENT_STATUS_CHANGED,
            obj=student,
            description=(
                f'Student status changed: {student.admission_number} '
                f'{old_status} → {new_status}'
                + (f'. Notes: {notes}' if notes else '')
            ),
            request=request,
        )

    return student


# ---------------------------------------------------------------------------
# Enrollment services
# ---------------------------------------------------------------------------

# Valid status transitions — the domain rule for enrollment lifecycle
_VALID_TRANSITIONS = {
    'PENDING':   {'ACTIVE', 'CANCELLED', 'WITHDRAWN'},
    'ACTIVE':    {'COMPLETED', 'WITHDRAWN', 'CANCELLED'},
    'COMPLETED': set(),   # terminal
    'WITHDRAWN': set(),   # terminal
    'CANCELLED': set(),   # terminal
}


def create_enrollment(*, student, course, academic_period, created_by,
                      initial_status='PENDING', notes='', request=None):
    """
    Create an Enrollment, enforcing all domain invariants.

    Invariants enforced:
    1. Student must be ACTIVE.
    2. Course must be active.
    3. AcademicPeriod must be active.
    4. No duplicate PENDING/ACTIVE enrollment for student+course+period (DB constraint).

    Parameters:
        student         : StudentProfile instance
        course          : Course instance
        academic_period : AcademicPeriod instance
        created_by      : User performing the action (for audit)
        initial_status  : 'PENDING' (default) or 'ACTIVE' if approved immediately
        notes           : Optional notes
        request         : HttpRequest (optional)

    Returns:
        Enrollment instance

    Raises:
        ValidationError : Business rule violation
        IntegrityError  : Duplicate open enrollment caught at DB level
    """
    from apps.enrollments.models import Enrollment, EnrollmentStatus
    from apps.students.models import StudentStatus

    # Business rule: only ACTIVE students may be enrolled
    if student.status != StudentStatus.ACTIVE:
        raise ValidationError(
            f'Student {student.admission_number} has status '
            f'"{student.get_status_display()}" and cannot be enrolled. '
            f'Only ACTIVE students may receive new enrollments.'
        )

    with transaction.atomic():
        enrollment = Enrollment(
            student=student,
            course=course,
            academic_period=academic_period,
            status=initial_status,
            notes=notes,
        )
        try:
            enrollment.full_clean()
            enrollment.save()
        except ValidationError:
            raise
        except IntegrityError:
            raise ValidationError(
                f'{student} already has an open enrollment in '
                f'{course.code} for {academic_period}.'
            )

        audit_log(
            actor=created_by,
            action=AuditAction.ENROLLMENT_CREATED,
            obj=enrollment,
            description=(
                f'Enrollment created: {student.admission_number} → '
                f'{course.code} [{academic_period}] status={initial_status}'
            ),
            request=request,
        )

    return enrollment


def change_enrollment_status(*, enrollment, new_status, changed_by,
                              notes='', request=None):
    """
    Transition an Enrollment to a new status, enforcing valid transitions.

    Parameters:
        enrollment  : Enrollment instance
        new_status  : Target EnrollmentStatus value (string)
        changed_by  : User performing the action
        notes       : Optional reason
        request     : HttpRequest (optional)

    Returns:
        Updated Enrollment instance

    Raises:
        ValueError  : Invalid or disallowed transition
    """
    from apps.enrollments.models import EnrollmentStatus

    old_status = enrollment.status
    if old_status == new_status:
        return enrollment

    allowed = _VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise ValueError(
            f'Cannot transition enrollment from {old_status} to {new_status}. '
            f'Allowed transitions: {allowed or "none (terminal state)"}.'
        )

    now = timezone.now()
    update_fields = ['status', 'updated_at']

    if notes:
        enrollment.notes = (enrollment.notes + f'\n[{now}] {notes}').strip()
        update_fields.append('notes')

    if new_status == 'COMPLETED':
        enrollment.completed_at = now
        update_fields.append('completed_at')
    elif new_status == 'WITHDRAWN':
        enrollment.withdrawn_at = now
        update_fields.append('withdrawn_at')

    action = AuditAction.ENROLLMENT_STATUS_CHANGED
    if new_status == 'ACTIVE' and old_status == 'PENDING':
        action = AuditAction.ENROLLMENT_APPROVED

    with transaction.atomic():
        enrollment.status = new_status
        enrollment.save(update_fields=update_fields)

        audit_log(
            actor=changed_by,
            action=action,
            obj=enrollment,
            description=(
                f'Enrollment status changed: {enrollment.student.admission_number} '
                f'[{enrollment.course.code}] {old_status} → {new_status}'
                + (f'. Notes: {notes}' if notes else '')
            ),
            request=request,
        )

    return enrollment


def approve_enrollment(*, enrollment, approved_by, notes='', request=None):
    """
    Approve a PENDING enrollment, setting it to ACTIVE.
    Convenience wrapper around change_enrollment_status.
    """
    return change_enrollment_status(
        enrollment=enrollment,
        new_status='ACTIVE',
        changed_by=approved_by,
        notes=notes,
        request=request,
    )
