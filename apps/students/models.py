from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class StudentStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    GRADUATED = 'GRADUATED', 'Graduated'


class StudentProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='studentprofile',
    )
    admission_number = models.CharField(max_length=50, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    county = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=10,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
        help_text='Explicit lifecycle status. Changing status does not delete historical records.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'student profile'
        verbose_name_plural = 'student profiles'
        permissions = [
            ('deactivate_student', 'Can deactivate student'),
        ]

    def is_academically_active(self):
        """Return True only for students who may be treated as active enrollees."""
        return self.status == StudentStatus.ACTIVE

    def clean(self):
        # Req 5.4: linked user must not be a staff member
        if self.user_id and self.user.is_staff:
            raise ValidationError(
                'A staff member cannot have a StudentProfile.'
            )
        # Req 5.5: mutual exclusion with StaffProfile
        if self.user_id and hasattr(self.user, 'staffprofile'):
            raise ValidationError(
                'This user already has a StaffProfile. '
                'A user cannot be both a student and a staff member.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.admission_number})'
