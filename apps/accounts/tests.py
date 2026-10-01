"""
Tests for apps.accounts models.

Property tests use Hypothesis for generative testing.
Each property test is tagged with the requirement it validates.
"""

from django.db import IntegrityError, transaction
from django.test import TestCase
from hypothesis import given, settings as hyp_settings
from hypothesis import HealthCheck
from hypothesis.extra.django import TestCase as HypothesisTestCase
from hypothesis.strategies import emails

from .models import AccountStatus, StaffProfile, User


def make_user(email, password='TestPass123!', **kwargs):
    """Helper to create a test user."""
    kwargs.setdefault('first_name', 'Test')
    kwargs.setdefault('last_name', 'User')
    return User.objects.create_user(email=email, password=password, **kwargs)


class UserModelTests(TestCase):
    """Basic unit tests for the custom User model."""

    def test_create_user_with_email(self):
        user = make_user('alice@example.com')
        self.assertEqual(user.email, 'alice@example.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.account_status, AccountStatus.ACTIVE)
        self.assertFalse(user.force_password_change)

    def test_create_user_normalises_email(self):
        user = make_user('Alice@EXAMPLE.COM')
        self.assertEqual(user.email, 'Alice@example.com')  # domain is lowercased

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='TestPass123!')

    def test_create_superuser_sets_flags(self):
        user = User.objects.create_superuser(
            email='admin@nayolites.ac.ke',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.account_status, AccountStatus.ACTIVE)

    def test_email_uniqueness_enforced(self):
        """Duplicate email at the database level raises IntegrityError."""
        make_user('bob@example.com')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_user('bob@example.com')

    def test_get_full_name(self):
        user = make_user('carol@example.com', first_name='Carol', last_name='Njeri')
        self.assertEqual(user.get_full_name(), 'Carol Njeri')

    def test_str_returns_email(self):
        user = make_user('dave@example.com')
        self.assertEqual(str(user), 'dave@example.com')


class EmailUniquenessPropertyTest(HypothesisTestCase):
    """
    Property 1: Email Uniqueness Invariant
    Validates: Requirements 1.2, 1.4

    For any email address, creating two User instances with the same email
    (after normalisation) SHALL raise an IntegrityError.
    """

    @given(email=emails())
    @hyp_settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_email_uniqueness_is_enforced(self, email):
        """Property 1: Email Uniqueness Invariant — Validates Req 1.2, 1.4"""
        User.objects.create_user(
            email=email,
            password='TestPass123!',
            first_name='A',
            last_name='B',
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email=email,
                    password='OtherPass1!',
                    first_name='C',
                    last_name='D',
                )


class StaffProfileIsStaffPropertyTest(TestCase):
    """
    Property 7: StaffProfile Creation Sets is_staff on Linked User
    Validates: Requirement 6.4

    For any StaffProfile created with a valid User, the linked User.is_staff
    SHALL be True immediately after the profile is saved.
    """

    def test_creating_staffprofile_sets_is_staff(self):
        """Property 7: StaffProfile Creation Sets is_staff — Validates Req 6.4"""
        user = User.objects.create_user(
            email='staff_test@example.com',
            password='TestPass123!',
            first_name='Staff',
            last_name='Test',
            is_staff=False,  # explicitly False before profile creation
        )
        self.assertFalse(user.is_staff)

        StaffProfile.objects.create(
            user=user,
            staff_number='ST001',
            job_title='Lecturer',
            department='Computing',
        )
        user.refresh_from_db()
        self.assertTrue(user.is_staff, 'Creating StaffProfile must set is_staff=True')


class InactiveStaffProfileCascadePropertyTest(TestCase):
    """
    Property 8: Inactive StaffProfile Cascades Account Status
    Validates: Requirement 6.5

    For any StaffProfile whose is_active is set to False, the linked
    User.account_status SHALL become INACTIVE.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email='cascade_test@example.com',
            password='TestPass123!',
            first_name='Cascade',
            last_name='Test',
        )
        self.profile = StaffProfile.objects.create(
            user=self.user,
            staff_number='ST002',
            job_title='Admin',
            department='Finance',
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_status, AccountStatus.ACTIVE)

    def test_deactivating_staffprofile_cascades_account_status(self):
        """Property 8: Inactive StaffProfile Cascades — Validates Req 6.5"""
        self.profile.is_active = False
        self.profile.save()

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.account_status,
            AccountStatus.INACTIVE,
            'Setting StaffProfile.is_active=False must set User.account_status=INACTIVE',
        )
        self.assertFalse(self.user.is_active)


class AccountStatusBackendPropertyTest(TestCase):
    """
    Property 2: Account Status Blocks Authentication
    Validates: Requirements 1.6, 2.3, 2.4

    For any User whose account_status is SUSPENDED or INACTIVE,
    authenticate() with valid credentials SHALL return None,
    regardless of password, group memberships, or any other field.
    """

    def setUp(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()

    def _make_request(self):
        return self.factory.post('/auth/login/')

    def test_active_user_can_authenticate(self):
        """Active users with correct credentials can authenticate."""
        user = make_user('active_auth@example.com')
        from django.contrib.auth import authenticate
        result = authenticate(
            self._make_request(),
            username='active_auth@example.com',
            password='TestPass123!',
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.pk, user.pk)

    def test_suspended_user_cannot_authenticate(self):
        """
        Property 2: Account Status Blocks Authentication — SUSPENDED
        Validates: Requirements 1.6, 2.3
        """
        user = make_user('suspended@example.com')
        user.account_status = AccountStatus.SUSPENDED
        user.save(update_fields=['account_status'])

        from django.contrib.auth import authenticate
        request = self._make_request()
        result = authenticate(request, username='suspended@example.com', password='TestPass123!')
        self.assertIsNone(result)
        # The backend should have stored the denial reason on the request
        self.assertEqual(getattr(request, '_auth_denied_status', None), AccountStatus.SUSPENDED)

    def test_inactive_user_cannot_authenticate(self):
        """
        Property 2: Account Status Blocks Authentication — INACTIVE
        Validates: Requirements 1.6, 2.4
        """
        user = make_user('inactive@example.com')
        user.account_status = AccountStatus.INACTIVE
        user.save(update_fields=['account_status'])

        from django.contrib.auth import authenticate
        request = self._make_request()
        result = authenticate(request, username='inactive@example.com', password='TestPass123!')
        self.assertIsNone(result)
        self.assertEqual(getattr(request, '_auth_denied_status', None), AccountStatus.INACTIVE)

    def test_wrong_password_returns_none(self):
        """Wrong password always returns None regardless of account status."""
        make_user('wrongpw@example.com')
        from django.contrib.auth import authenticate
        result = authenticate(self._make_request(), username='wrongpw@example.com', password='WrongPass!')
        self.assertIsNone(result)

    def test_nonexistent_email_returns_none(self):
        """Non-existent email returns None without raising an exception."""
        from django.contrib.auth import authenticate
        result = authenticate(self._make_request(), username='nobody@example.com', password='TestPass123!')
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Phase 2 Property Tests — Tasks 9.3, 10.2, 11.2, 12.2
# ---------------------------------------------------------------------------

from apps.core.models import AuditAction, AuditLog
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


class LoginAuditLogPropertyTest(TestCase):
    """
    Property 5: Successful Authentication Always Produces an AuditLog Entry
    Validates: Requirements 2.5, 17.2

    For any User that successfully authenticates via the login form,
    an AuditLog entry with action=login_success SHALL be created.
    """

    def test_successful_login_creates_audit_entry(self):
        """Property 5: Successful login → AuditLog entry — Validates Req 2.5, 17.2"""
        user = make_user('login_audit@example.com')
        initial_count = AuditLog.objects.filter(action=AuditAction.LOGIN_SUCCESS).count()

        self.client.post('/auth/login/', {
            'email': 'login_audit@example.com',
            'password': 'TestPass123!',
        })

        new_count = AuditLog.objects.filter(action=AuditAction.LOGIN_SUCCESS).count()
        self.assertEqual(new_count, initial_count + 1)

        entry = AuditLog.objects.filter(
            action=AuditAction.LOGIN_SUCCESS,
            actor=user,
        ).last()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.actor, user)

    def test_failed_login_creates_audit_entry(self):
        """Failed login creates AuditLog(LOGIN_FAILED) entry with null actor — Validates Req 2.2, 17.3"""
        make_user('fail_audit@example.com')
        initial_count = AuditLog.objects.filter(action=AuditAction.LOGIN_FAILED).count()

        self.client.post('/auth/login/', {
            'email': 'fail_audit@example.com',
            'password': 'WrongPassword!',
        })

        new_count = AuditLog.objects.filter(action=AuditAction.LOGIN_FAILED).count()
        self.assertEqual(new_count, initial_count + 1)

        entry = AuditLog.objects.filter(action=AuditAction.LOGIN_FAILED).last()
        self.assertIsNone(entry.actor)
        self.assertIn('fail_audit@example.com', entry.description)


class PasswordValidatorPropertyTest(TestCase):
    """
    Property 19: Password Validators Reject Invalid Passwords
    Validates: Requirement 2.11

    Any password string that violates one of the four configured validators
    SHALL be rejected with a ValidationError.
    """

    def _assert_password_rejected(self, password, user=None):
        with self.assertRaises(DjangoValidationError):
            validate_password(password, user=user)

    def test_short_password_rejected(self):
        """Passwords shorter than 8 characters are rejected."""
        self._assert_password_rejected('Ab1!')

    def test_numeric_only_password_rejected(self):
        """All-numeric passwords are rejected."""
        self._assert_password_rejected('12345678')

    def test_common_password_rejected(self):
        """Common passwords are rejected."""
        self._assert_password_rejected('password')

    def test_valid_password_passes(self):
        """A strong password passes all validators."""
        # Should not raise
        validate_password('Nayolites2025!')

    def test_similarity_validator_rejects_similar_to_email(self):
        """Password similar to user email is rejected."""
        user = make_user('similar@example.com')
        with self.assertRaises(DjangoValidationError):
            validate_password('similar1234', user=user)


class ForcePasswordChangeMiddlewarePropertyTest(TestCase):
    """
    Property 4: Force Password Change Intercepts All Portal Requests
    Validates: Requirement 3.2

    For any authenticated User with force_password_change=True,
    a request to any URL that is not the change-password endpoint or logout
    SHALL receive a redirect to the change-password page.
    """

    def setUp(self):
        self.user = make_user('force_pw@example.com', force_password_change=True)
        self.client.force_login(self.user)

    def test_staff_portal_redirects_to_password_change(self):
        """Property 4: force_password_change=True → redirect — Validates Req 3.2"""
        response = self.client.get('/staff/', follow=False)
        self.assertRedirects(response, '/auth/password-change/', fetch_redirect_response=False)

    def test_student_portal_redirects_to_password_change(self):
        """Property 4: force_password_change=True → redirect (student) — Validates Req 3.2"""
        response = self.client.get('/student/', follow=False)
        self.assertRedirects(response, '/auth/password-change/', fetch_redirect_response=False)

    def test_password_change_page_not_redirected(self):
        """The change-password page itself is exempt from the redirect."""
        response = self.client.get('/auth/password-change/')
        # Should return 200 (the form), not redirect
        self.assertEqual(response.status_code, 200)

    def test_after_password_change_flag_cleared(self):
        """After successfully changing password, force_password_change is set to False."""
        response = self.client.post('/auth/password-change/', {
            'old_password': 'TestPass123!',
            'new_password1': 'NewSecure2025!',
            'new_password2': 'NewSecure2025!',
        })
        self.user.refresh_from_db()
        self.assertFalse(self.user.force_password_change)


class PasswordChangeAuditLogPropertyTest(TestCase):
    """
    Property 6: Password Change Always Produces an AuditLog Entry
    Validates: Requirements 3.4, 17.2

    For any User that successfully changes their password,
    an AuditLog entry with action=password_changed SHALL be created.
    """

    def test_password_change_creates_audit_entry(self):
        """Property 6: Password change → AuditLog entry — Validates Req 3.4, 17.2"""
        user = make_user('pw_change_audit@example.com')
        self.client.force_login(user)

        initial_count = AuditLog.objects.filter(action=AuditAction.PASSWORD_CHANGED).count()

        self.client.post('/auth/password-change/', {
            'old_password': 'TestPass123!',
            'new_password1': 'NewSecure2025!',
            'new_password2': 'NewSecure2025!',
        })

        new_count = AuditLog.objects.filter(action=AuditAction.PASSWORD_CHANGED).count()
        self.assertEqual(new_count, initial_count + 1)

        entry = AuditLog.objects.filter(
            action=AuditAction.PASSWORD_CHANGED,
            actor=user,
        ).last()
        self.assertIsNotNone(entry)
