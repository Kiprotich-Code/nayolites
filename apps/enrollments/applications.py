"""
CourseApplication model — public application/admissions workflow.

Architectural decision:
    PUBLIC SUBMISSION ≠ AUTOMATIC TRUSTED ENROLLMENT

A CourseApplication is created when a prospective student submits the
public application form. It is NOT an Enrollment and it does NOT create
a User or StudentProfile automatically.

The lifecycle is:

    Public applicant submits form
            ↓
    CourseApplication (SUBMITTED)
            ↓
    Staff reviews
            ↓
    ACCEPTED → Staff creates User + StudentProfile + Enrollment
    REJECTED → No academic record created
    WITHDRAWN → Applicant withdrew

Security notes:
- The model holds no privileged data beyond what the applicant provided.
- The `status` field is never set by public input — only staff can change it.
- `reference_number` is auto-generated server-side; it is the only safe
  identifier surfaced to the public applicant for tracking.
- No internal IDs, Student PKs, or Enrollment PKs are exposed publicly.

Duplicate protection:
- A soft check on email + course + academic_period combination is applied
  at the application layer. We do NOT use a DB unique constraint on this
  combination because two legitimate applicants could share an email
  (e.g. family members), and we don't want to block them.
- A reference_number unique constraint is used to prevent double-submission
  of the exact same form token.
"""

import uuid

from django.db import models


class ApplicationStatus(models.TextChoices):
    SUBMITTED = 'SUBMITTED', 'Submitted'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    REJECTED = 'REJECTED', 'Rejected'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'


def _generate_reference():
    """Generate a short, human-readable reference number."""
    return 'APP-' + uuid.uuid4().hex[:8].upper()


class CourseApplication(models.Model):
    """
    A prospective student's application for a course.

    This record is created from the public website. It has no FK to
    StudentProfile or Enrollment until staff explicitly converts it.

    Fields collected from the public form:
    - Applicant name / email / phone
    - Desired course and academic period
    - Relevant application note

    Fields set server-side only:
    - reference_number (auto-generated UUID fragment)
    - status (always starts SUBMITTED — never writable by public form)
    - created_at / updated_at
    - reviewed_by / reviewed_at (set by staff on status change)
    - linked_enrollment (set if staff converts to an Enrollment)
    """

    # ---- Applicant-provided information ----
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(
        blank=True,
        help_text='Optional note from the applicant.',
    )

    # ---- Course and period requested ----
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.PROTECT,
        related_name='applications',
        help_text='The course the applicant wishes to enrol in.',
    )
    preferred_period = models.ForeignKey(
        'enrollments.AcademicPeriod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
        help_text='Optional preferred intake period.',
    )

    # ---- Server-side fields (never set by public input) ----
    reference_number = models.CharField(
        max_length=20,
        unique=True,
        default=_generate_reference,
        editable=False,
        help_text='Auto-generated reference given to the applicant for tracking.',
    )
    status = models.CharField(
        max_length=12,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
        help_text='Only staff may change this field.',
    )
    staff_notes = models.TextField(
        blank=True,
        help_text='Internal staff notes — not visible to applicant.',
    )

    # ---- Staff review tracking ----
    reviewed_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_applications',
        help_text='Staff member who last changed status.',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # ---- Link to Enrollment if accepted and converted ----
    linked_enrollment = models.OneToOneField(
        'enrollments.Enrollment',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_application',
        help_text='Set when staff converts this application to an enrollment.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'course application'
        verbose_name_plural = 'course applications'
        ordering = ['-created_at']
        permissions = [
            ('review_courseapplication', 'Can review and process course applications'),
        ]

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def __str__(self):
        return f'{self.reference_number} — {self.get_full_name()} ({self.course.code})'
