from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AcademicPeriod(models.Model):
    """
    An institutional time boundary for academic activity.

    Examples: "2026 Semester 1", "January 2026 Intake", "2026 Term 2".
    These are data, not code — the institution creates and names them.

    Multiple periods may be active simultaneously (e.g. different intakes
    running in parallel). No global single-active constraint is enforced.
    """

    name = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(
        default=True,
        help_text='Active periods appear in enrollment workflows. Inactive periods are archived.',
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'academic period'
        verbose_name_plural = 'academic periods'
        ordering = ['-start_date']
        permissions = [
            ('manage_academicperiod', 'Can create and modify academic periods'),
        ]

    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError(
                    {'end_date': 'End date must be after start date.'}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class EnrollmentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACTIVE = 'ACTIVE', 'Active'
    COMPLETED = 'COMPLETED', 'Completed'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
    CANCELLED = 'CANCELLED', 'Cancelled'


# Statuses that represent an open/ongoing enrollment — used for duplicate protection
_OPEN_STATUSES = (EnrollmentStatus.PENDING, EnrollmentStatus.ACTIVE)


class Enrollment(models.Model):
    """
    The institutional record of a Student enrolled in a Course for an AcademicPeriod.

    This is NOT a join table. It is a first-class domain entity:
    - It has its own lifecycle (status, dates).
    - Future modules attach directly to it:
        Enrollment → Invoice
        Enrollment → Result
        Enrollment → Attendance

    Uniqueness rule:
    A student may not have two PENDING or ACTIVE enrollments in the same
    course and academic period simultaneously. Completed/Withdrawn/Cancelled
    enrollments are retained as historical records and do not block new ones.

    The database constraint enforces this at the DB level — concurrent
    requests cannot bypass it.
    """

    student = models.ForeignKey(
        'students.StudentProfile',
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    academic_period = models.ForeignKey(
        AcademicPeriod,
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    status = models.CharField(
        max_length=10,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PENDING,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True, null=True)
    # Set by services layer when status transitions — not auto
    completed_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    # Free-text note — staff can record reason for status changes
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'enrollment'
        verbose_name_plural = 'enrollments'
        ordering = ['-enrolled_at']
        permissions = [
            ('approve_enrollment', 'Can approve enrollment'),
        ]
        constraints = [
            # Prevent duplicate open enrollments at the DB level.
            # A student may have at most one PENDING or ACTIVE enrollment
            # per course per academic period.
            #
            # Django 4.2+ UniqueConstraint with condition covers partial uniqueness.
            # SQLite and PostgreSQL both support this.
            models.UniqueConstraint(
                fields=['student', 'course', 'academic_period'],
                condition=models.Q(status__in=['PENDING', 'ACTIVE']),
                name='unique_open_enrollment_per_student_course_period',
            )
        ]

    def clean(self):
        # Validate that the course is active before creating a new enrollment
        if self.pk is None:  # creation only
            if self.course_id and not self.course.is_active:
                raise ValidationError(
                    {'course': 'Cannot enroll in an inactive course.'}
                )
            if self.academic_period_id and not self.academic_period.is_active:
                raise ValidationError(
                    {'academic_period': 'Cannot enroll in an inactive academic period.'}
                )

    def __str__(self):
        return (
            f'{self.student} → {self.course.code} '
            f'[{self.academic_period}] ({self.status})'
        )

    @property
    def is_open(self):
        return self.status in _OPEN_STATUSES
