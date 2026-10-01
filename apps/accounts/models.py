from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class AccountStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    INACTIVE = 'INACTIVE', 'Inactive'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required.')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('account_status', AccountStatus.ACTIVE)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('account_status', AccountStatus.ACTIVE)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    account_status = models.CharField(
        max_length=10,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    force_password_change = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name

    def __str__(self):
        return self.email


class StaffProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='staffprofile',
    )
    staff_number = models.CharField(max_length=50, unique=True)
    job_title = models.CharField(max_length=150)
    department = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'staff profile'
        verbose_name_plural = 'staff profiles'

    def clean(self):
        from django.core.exceptions import ValidationError
        # Mutual exclusion: a user cannot have both StaffProfile and StudentProfile
        if hasattr(self.user, 'studentprofile'):
            raise ValidationError(
                'This user already has a StudentProfile. '
                'A user cannot be both a student and a staff member.'
            )

    def save(self, *args, **kwargs):
        # Req 6.4: creating a StaffProfile sets is_staff=True on the linked User
        self.full_clean()
        if not self.user.is_staff:
            self.user.is_staff = True
            self.user.save(update_fields=['is_staff'])
        super().save(*args, **kwargs)
        # Req 6.5: deactivating a StaffProfile cascades to INACTIVE account_status
        if not self.is_active:
            if self.user.account_status != AccountStatus.INACTIVE:
                self.user.account_status = AccountStatus.INACTIVE
                self.user.is_active = False
                self.user.save(update_fields=['account_status', 'is_active'])

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.staff_number})'
