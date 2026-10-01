"""
Result domain model.

A Result belongs to an Enrollment and a CourseUnit.
The central invariant: result.course_unit.course == result.enrollment.course
This is enforced in clean() and in the service layer.

Lifecycle:
    DRAFT → SUBMITTED → APPROVED → PUBLISHED
    Any state can transition to DRAFT (reset) by the original entrant.

Only PUBLISHED results are visible to students.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class ResultStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted for Review'
    APPROVED = 'APPROVED', 'Approved'
    PUBLISHED = 'PUBLISHED', 'Published'


class Result(models.Model):
    """
    The academic result for one student in one course unit for one enrollment.

    score_cat  : Continuous Assessment Test score (0–40)
    score_exam : Examination score (0–60)
    total      : Derived — score_cat + score_exam (stored for query efficiency)
    grade      : Letter grade computed from total
    status     : Lifecycle state

    The cross-validation rule (unit belongs to enrollment course) is enforced
    in clean() so it cannot be bypassed via the ORM save() path.

    Future: a Result may gain sub-scores, remarks, retake tracking.
    """

    enrollment = models.ForeignKey(
        'enrollments.Enrollment',
        on_delete=models.PROTECT,
        related_name='results',
    )
    course_unit = models.ForeignKey(
        'courses.CourseUnit',
        on_delete=models.PROTECT,
        related_name='results',
    )
    score_cat = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        help_text='Continuous Assessment Test score (0–40).',
    )
    score_exam = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        help_text='Examination score (0–60).',
    )
    total = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text='Computed total (CAT + Exam). Stored for filtering.',
    )
    grade = models.CharField(
        max_length=3, blank=True,
        help_text='Letter grade computed from total.',
    )
    status = models.CharField(
        max_length=10,
        choices=ResultStatus.choices,
        default=ResultStatus.DRAFT,
    )
    # Tracks who entered and approved
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='results_entered',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='results_approved',
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'result'
        verbose_name_plural = 'results'
        ordering = ['-created_at']
        permissions = [
            ('publish_result', 'Can publish result'),
            ('approve_result', 'Can approve result'),
        ]
        constraints = [
            # A student can only have one result per unit per enrollment
            models.UniqueConstraint(
                fields=['enrollment', 'course_unit'],
                name='unique_result_per_enrollment_unit',
            )
        ]

    def clean(self):
        # Core invariant: the course unit must belong to the enrollment's course
        if self.enrollment_id and self.course_unit_id:
            if self.course_unit.course_id != self.enrollment.course_id:
                raise ValidationError(
                    'The course unit does not belong to the course '
                    'associated with this enrollment.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        # Recompute total and grade before every save
        if self.score_cat is not None and self.score_exam is not None:
            self.total = self.score_cat + self.score_exam
            self.grade = self._compute_grade(float(self.total))
        elif self.score_cat is not None or self.score_exam is not None:
            # Partial — don't compute grade yet
            cat = float(self.score_cat) if self.score_cat is not None else 0
            exam = float(self.score_exam) if self.score_exam is not None else 0
            self.total = cat + exam
            self.grade = ''
        else:
            self.total = None
            self.grade = ''
        super().save(*args, **kwargs)

    @staticmethod
    def _compute_grade(total: float) -> str:
        if total >= 70:
            return 'A'
        if total >= 60:
            return 'B'
        if total >= 50:
            return 'C'
        if total >= 40:
            return 'D'
        return 'E'

    @property
    def is_visible_to_students(self):
        return self.status == ResultStatus.PUBLISHED

    def __str__(self):
        return (
            f'{self.enrollment.student.admission_number} — '
            f'{self.course_unit.code} ({self.status})'
        )
