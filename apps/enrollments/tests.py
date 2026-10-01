"""
Tests for AcademicPeriod, Enrollment, and domain services.

Covers:
- AcademicPeriod validation (date range)
- Enrollment creation via service
- Duplicate enrollment protection (DB constraint)
- Enrollment status transitions
- Enrollment history preservation
- Authorization boundaries for staff academic views
- Inactive student cannot be enrolled
- Inactive course cannot be enrolled
"""

import datetime

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.courses.models import Course, CourseUnit
from apps.students.models import StudentProfile, StudentStatus
from .models import AcademicPeriod, Enrollment, EnrollmentStatus
from .services import (
    create_enrollment, change_enrollment_status, approve_enrollment,
    create_student, change_student_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email, is_staff=False, **kwargs):
    kwargs.setdefault('first_name', 'Test')
    kwargs.setdefault('last_name', 'User')
    return User.objects.create_user(
        email=email, password='TestPass123!', is_staff=is_staff, **kwargs
    )


def make_student_user_and_profile(email, admission='ADM001'):
    user = make_user(email)
    profile = StudentProfile.objects.create(user=user, admission_number=admission)
    return user, profile


def make_course(code='TST', name='Test Course', active=True):
    return Course.objects.create(code=code, name=name, duration='1 Year', is_active=active)


def make_period(name='2026 Test', start=None, end=None, active=True):
    start = start or datetime.date(2026, 1, 1)
    end = end or datetime.date(2026, 6, 30)
    return AcademicPeriod.objects.create(name=name, start_date=start, end_date=end, is_active=active)


# ---------------------------------------------------------------------------
# AcademicPeriod tests
# ---------------------------------------------------------------------------

class AcademicPeriodModelTests(TestCase):

    def test_valid_period_saves(self):
        p = make_period()
        self.assertIsNotNone(p.pk)

    def test_invalid_date_range_raises(self):
        with self.assertRaises(ValidationError):
            AcademicPeriod(
                name='Bad Period',
                start_date=datetime.date(2026, 6, 1),
                end_date=datetime.date(2026, 1, 1),
                is_active=True,
            ).full_clean()

    def test_equal_dates_raise(self):
        with self.assertRaises(ValidationError):
            AcademicPeriod(
                name='Same Day',
                start_date=datetime.date(2026, 1, 1),
                end_date=datetime.date(2026, 1, 1),
            ).full_clean()

    def test_name_uniqueness(self):
        make_period(name='Unique Period')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_period(name='Unique Period')

    def test_inactive_period_excluded_from_active_filter(self):
        make_period(name='Open', active=True)
        make_period(name='Closed', active=False)
        active = AcademicPeriod.objects.filter(is_active=True)
        self.assertIn('Open', [p.name for p in active])
        self.assertNotIn('Closed', [p.name for p in active])


# ---------------------------------------------------------------------------
# Enrollment service tests
# ---------------------------------------------------------------------------

class EnrollmentServiceTests(TestCase):

    def setUp(self):
        self.actor = make_user('actor@example.com', is_staff=True)
        _, self.student = make_student_user_and_profile('s1@example.com', 'ADM-001')
        self.course = make_course()
        self.period = make_period()

    def test_create_enrollment_success(self):
        e = create_enrollment(
            student=self.student,
            course=self.course,
            academic_period=self.period,
            created_by=self.actor,
        )
        self.assertEqual(e.status, EnrollmentStatus.PENDING)
        self.assertEqual(e.student, self.student)
        self.assertEqual(e.course, self.course)

    def test_create_enrollment_active_immediately(self):
        e = create_enrollment(
            student=self.student,
            course=self.course,
            academic_period=self.period,
            created_by=self.actor,
            initial_status='ACTIVE',
        )
        self.assertEqual(e.status, EnrollmentStatus.ACTIVE)

    def test_inactive_student_cannot_be_enrolled(self):
        self.student.status = StudentStatus.INACTIVE
        self.student.save(update_fields=['status', 'updated_at'])
        with self.assertRaises(ValidationError):
            create_enrollment(
                student=self.student,
                course=self.course,
                academic_period=self.period,
                created_by=self.actor,
            )

    def test_inactive_course_cannot_be_enrolled(self):
        inactive_course = make_course(code='INA', name='Inactive', active=False)
        with self.assertRaises(ValidationError):
            create_enrollment(
                student=self.student,
                course=inactive_course,
                academic_period=self.period,
                created_by=self.actor,
            )

    def test_inactive_period_cannot_be_enrolled(self):
        closed_period = make_period(name='Closed 2025', active=False)
        with self.assertRaises(ValidationError):
            create_enrollment(
                student=self.student,
                course=self.course,
                academic_period=closed_period,
                created_by=self.actor,
            )

    def test_duplicate_open_enrollment_rejected(self):
        create_enrollment(
            student=self.student,
            course=self.course,
            academic_period=self.period,
            created_by=self.actor,
        )
        with self.assertRaises(ValidationError):
            create_enrollment(
                student=self.student,
                course=self.course,
                academic_period=self.period,
                created_by=self.actor,
            )

    def test_completed_enrollment_does_not_block_new_one(self):
        """
        Historical preservation: a COMPLETED enrollment must not block
        a new enrollment in the same course/period combination.
        """
        e1 = create_enrollment(
            student=self.student,
            course=self.course,
            academic_period=self.period,
            created_by=self.actor,
            initial_status='ACTIVE',
        )
        change_enrollment_status(
            enrollment=e1,
            new_status='COMPLETED',
            changed_by=self.actor,
        )
        # Now a new period for the same course should be fine
        period2 = make_period(name='2026 Sem 2', start=datetime.date(2026, 7, 1), end=datetime.date(2026, 12, 31))
        e2 = create_enrollment(
            student=self.student,
            course=self.course,
            academic_period=period2,
            created_by=self.actor,
        )
        self.assertIsNotNone(e2.pk)

    def test_enrollment_history_preserved(self):
        """Multiple enrollments across periods are all retained."""
        p2 = make_period(name='2026 Sem 2', start=datetime.date(2026, 7, 1), end=datetime.date(2026, 12, 31))
        e1 = create_enrollment(
            student=self.student, course=self.course, academic_period=self.period, created_by=self.actor, initial_status='ACTIVE'
        )
        change_enrollment_status(enrollment=e1, new_status='COMPLETED', changed_by=self.actor)
        create_enrollment(
            student=self.student, course=self.course, academic_period=p2, created_by=self.actor
        )
        total = Enrollment.objects.filter(student=self.student).count()
        self.assertEqual(total, 2)

    def test_status_transition_pending_to_active(self):
        e = create_enrollment(student=self.student, course=self.course, academic_period=self.period, created_by=self.actor)
        approve_enrollment(enrollment=e, approved_by=self.actor)
        e.refresh_from_db()
        self.assertEqual(e.status, EnrollmentStatus.ACTIVE)

    def test_invalid_status_transition_raises(self):
        e = create_enrollment(student=self.student, course=self.course, academic_period=self.period, created_by=self.actor, initial_status='ACTIVE')
        with self.assertRaises(ValueError):
            change_enrollment_status(enrollment=e, new_status='PENDING', changed_by=self.actor)

    def test_terminal_status_cannot_be_changed(self):
        e = create_enrollment(student=self.student, course=self.course, academic_period=self.period, created_by=self.actor, initial_status='ACTIVE')
        change_enrollment_status(enrollment=e, new_status='COMPLETED', changed_by=self.actor)
        with self.assertRaises(ValueError):
            change_enrollment_status(enrollment=e, new_status='ACTIVE', changed_by=self.actor)

    def test_withdrawn_at_timestamp_set(self):
        e = create_enrollment(student=self.student, course=self.course, academic_period=self.period, created_by=self.actor, initial_status='ACTIVE')
        change_enrollment_status(enrollment=e, new_status='WITHDRAWN', changed_by=self.actor)
        e.refresh_from_db()
        self.assertIsNotNone(e.withdrawn_at)

    def test_completed_at_timestamp_set(self):
        e = create_enrollment(student=self.student, course=self.course, academic_period=self.period, created_by=self.actor, initial_status='ACTIVE')
        change_enrollment_status(enrollment=e, new_status='COMPLETED', changed_by=self.actor)
        e.refresh_from_db()
        self.assertIsNotNone(e.completed_at)


# ---------------------------------------------------------------------------
# Enrollment authorization boundary tests
# ---------------------------------------------------------------------------

class EnrollmentAuthorizationTests(TestCase):

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse('staff:enrollments'))
        self.assertRedirects(response, '/auth/login/?next=/staff/enrollments/', fetch_redirect_response=False)

    def test_no_permission_gets_403(self):
        user = make_user('noauth@example.com', is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse('staff:enrollments'))
        self.assertEqual(response.status_code, 403)

    def test_view_permission_can_list(self):
        user = make_user('viewer@example.com', is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='view_enrollment'))
        self.client.force_login(user)
        response = self.client.get(reverse('staff:enrollments'))
        self.assertEqual(response.status_code, 200)

    def test_view_only_cannot_create_enrollment(self):
        user = make_user('viewonly@example.com', is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='view_enrollment'))
        self.client.force_login(user)
        response = self.client.get(reverse('staff:enrollment_create'))
        self.assertEqual(response.status_code, 403)

    def test_approve_permission_required_to_approve(self):
        """
        A user with change_enrollment but NOT approve_enrollment cannot
        approve a PENDING enrollment — the view checks explicitly.
        """
        actor = make_user('changer@example.com', is_staff=True)
        actor.user_permissions.add(Permission.objects.get(codename='change_enrollment'))
        actor.user_permissions.add(Permission.objects.get(codename='view_enrollment'))
        self.client.force_login(actor)

        # Create the enrollment directly (bypassing view)
        _, student = make_student_user_and_profile('s2@example.com', 'ADM-002')
        course = make_course(code='AUT')
        period = make_period(name='Auth Period')
        enrollment = Enrollment.objects.create(
            student=student, course=course, academic_period=period, status='PENDING'
        )

        # POST to status change with new_status=ACTIVE (approve action)
        response = self.client.post(
            reverse('staff:enrollment_status', kwargs={'pk': enrollment.pk}),
            {'new_status': 'ACTIVE', 'notes': ''},
        )
        # Should redirect back to detail with error message (not silently approve)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, 'PENDING',
                         'Enrollment should not be approved without approve_enrollment permission.')


# ---------------------------------------------------------------------------
# Student service / status tests
# ---------------------------------------------------------------------------

class StudentServiceTests(TestCase):

    def setUp(self):
        self.actor = make_user('actor2@example.com', is_staff=True)

    def test_create_student(self):
        user = make_user('new_student@example.com')
        profile = create_student(
            user=user,
            admission_number='NCC/2026/TEST',
            created_by=self.actor,
        )
        self.assertEqual(profile.admission_number, 'NCC/2026/TEST')
        self.assertEqual(profile.status, StudentStatus.ACTIVE)

    def test_admission_number_uniqueness(self):
        user1 = make_user('s_a@example.com')
        user2 = make_user('s_b@example.com')
        create_student(user=user1, admission_number='NCC/DUP', created_by=self.actor)
        with self.assertRaises(ValidationError):
            create_student(user=user2, admission_number='NCC/DUP', created_by=self.actor)

    def test_change_student_status(self):
        user = make_user('status_test@example.com')
        profile = create_student(user=user, admission_number='NCC/ST1', created_by=self.actor)
        change_student_status(student=profile, new_status='SUSPENDED', changed_by=self.actor)
        profile.refresh_from_db()
        self.assertEqual(profile.status, 'SUSPENDED')

    def test_same_status_change_is_noop(self):
        user = make_user('status_noop@example.com')
        profile = create_student(user=user, admission_number='NCC/ST2', created_by=self.actor)
        result = change_student_status(student=profile, new_status='ACTIVE', changed_by=self.actor)
        self.assertEqual(result.status, 'ACTIVE')

    def test_invalid_status_raises(self):
        user = make_user('bad_status@example.com')
        profile = create_student(user=user, admission_number='NCC/ST3', created_by=self.actor)
        with self.assertRaises(ValueError):
            change_student_status(student=profile, new_status='INVALID', changed_by=self.actor)
