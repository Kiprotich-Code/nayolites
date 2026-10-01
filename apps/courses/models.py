"""
Course and CourseUnit domain models.

Course is a first-class academic entity — the source of truth for what
the college offers. CourseUnit belongs to a Course and represents the
units of study within that course.

Design notes:
- Course codes are unique across the entire system (DB constraint).
- CourseUnit codes are unique within their Course (DB constraint).
- Deactivation is preferred over deletion. A Course with Enrollments
  cannot be deleted (PROTECT is enforced at the Enrollment FK level).
- The slug field supports clean public URLs without exposing internal PKs.
"""

from django.db import models
from django.utils.text import slugify


class Course(models.Model):
    """
    A programme offered by the college.

    Future extension points:
    - Finance: FeeStructure → Course
    - Results: Result → Enrollment → Course
    - Content: CourseContent → Course / CourseUnit
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text='Short programme code, e.g. DCS, DBM. Must be unique.',
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        help_text='Auto-generated from name for public URLs.',
    )
    description = models.TextField(blank=True)
    duration = models.CharField(
        max_length=50,
        help_text='Human-readable duration, e.g. "2 Years" or "1 Year".',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive courses are hidden from public catalogue and cannot accept new enrollments.',
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'course'
        verbose_name_plural = 'courses'
        ordering = ['name']
        permissions = [
            ('activate_course', 'Can activate/deactivate course'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def active_units(self):
        return self.units.filter(is_active=True)

    @property
    def unit_count(self):
        return self.units.count()

    @property
    def active_enrollment_count(self):
        """Number of active enrollments. Avoids import cycle — uses string reference."""
        from apps.enrollments.models import EnrollmentStatus
        return self.enrollments.filter(status=EnrollmentStatus.ACTIVE).count()

    def __str__(self):
        return f'{self.code} — {self.name}'


class CourseUnit(models.Model):
    """
    A unit of study within a Course.

    Constraint: code is unique within a Course (enforced at DB level).

    Future extension points:
    - Results: Result → CourseUnit (validated: unit.course == enrollment.course)
    - Content: CourseContent → CourseUnit
    - Lecturer assignment: CourseUnitInstructor → CourseUnit → StaffProfile
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='units',
    )
    code = models.CharField(
        max_length=30,
        help_text='Unit code, e.g. DCS 101. Must be unique within the course.',
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'course unit'
        verbose_name_plural = 'course units'
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'code'],
                name='unique_unit_code_within_course',
            )
        ]

    def __str__(self):
        return f'{self.code} — {self.name}'
