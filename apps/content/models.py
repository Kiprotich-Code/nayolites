"""
CourseContent domain model.

Lightweight content management — not a full LMS.

Content belongs to a Course and optionally to a specific CourseUnit.
Access is controlled by the visibility field.

File uploads and URL links are both supported.
Only one of (file, url) should be populated for a given item — enforced
in clean(). Both may be blank for items created as placeholders before
a file is ready.

Student visibility:
    ENROLLED  — only students actively enrolled in this course
    ALL       — any authenticated student (e.g. prospectus materials)
    STAFF     — staff only; students cannot see this item
"""

import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ContentVisibility(models.TextChoices):
    ENROLLED = 'ENROLLED', 'Enrolled Students'
    ALL = 'ALL', 'All Students'
    STAFF = 'STAFF', 'Staff Only'


class ContentType(models.TextChoices):
    PDF = 'PDF', 'PDF Document'
    VIDEO_URL = 'VIDEO_URL', 'Video URL'
    LINK = 'LINK', 'External Link'
    FILE = 'FILE', 'Other File'


def content_upload_path(instance, filename):
    """Store uploads under media/content/<course_code>/<filename>."""
    code = instance.course.code if instance.course_id else 'misc'
    return os.path.join('content', code, filename)


class CourseContent(models.Model):
    """
    A piece of content attached to a Course (and optionally a CourseUnit).

    Students can access items where:
    - visibility == ENROLLED and they have an active enrollment in the course
    - visibility == ALL and they are authenticated students

    Staff can always access all items (subject to view_coursecontent permission).
    """

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.PROTECT,
        related_name='content_items',
    )
    course_unit = models.ForeignKey(
        'courses.CourseUnit',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='content_items',
        help_text='Optional — attach to a specific unit within the course.',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(
        max_length=10,
        choices=ContentType.choices,
        default=ContentType.PDF,
    )
    file = models.FileField(
        upload_to=content_upload_path,
        null=True, blank=True,
        help_text='Upload a file. Use this or a URL, not both.',
    )
    url = models.URLField(
        blank=True,
        help_text='External link (YouTube, Google Drive, etc.). Use this or a file, not both.',
    )
    visibility = models.CharField(
        max_length=10,
        choices=ContentVisibility.choices,
        default=ContentVisibility.ENROLLED,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_content',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'course content'
        verbose_name_plural = 'course content'
        ordering = ['-created_at']

    def clean(self):
        # A CourseUnit must belong to the Course it is attached to
        if self.course_unit_id and self.course_id:
            if self.course_unit.course_id != self.course_id:
                raise ValidationError(
                    'The selected course unit does not belong to the selected course.'
                )
        # Warn if both file and url are provided
        if self.file and self.url:
            raise ValidationError(
                'Provide either a file upload or a URL, not both.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def has_file(self):
        return bool(self.file)

    @property
    def has_url(self):
        return bool(self.url)

    def __str__(self):
        unit_part = f' [{self.course_unit.code}]' if self.course_unit_id else ''
        return f'{self.course.code}{unit_part} — {self.title}'
