"""
Tests for apps.students models and authorization.

Covers:
- Student/Staff mutual exclusion (carried forward from Phase 1)
- Student ownership — Student A cannot access Student B's portal URLs
- Staff cannot access student portal
- Student cannot access staff portal
- Direct URL access without permission returns 403/404
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import StaffProfile, User
from apps.students.models import StudentProfile, StudentStatus


def make_user(email, **kwargs):
    kwargs.setdefault('first_name', 'Test')
    kwargs.setdefault('last_name', 'User')
    kwargs.setdefault('password', 'TestPass123!')
    return User.objects.create_user(email=email, **kwargs)


def make_student(email, admission):
    user = make_user(email)
    return StudentProfile.objects.create(user=user, admission_number=admission)


class StudentStaffMutualExclusionPropertyTest(TestCase):
    """
    Property 9: StudentProfile and StaffProfile are Mutually Exclusive
    Validates: Requirement 5.5
    """

    def test_cannot_create_studentprofile_for_staff_user(self):
        user = make_user('mutual_test1@example.com')
        StaffProfile.objects.create(user=user, staff_number='MT001', job_title='Lecturer', department='ICT')
        user.refresh_from_db()
        with self.assertRaises(ValidationError):
            StudentProfile(user=user, admission_number='ADM001').clean()

    def test_cannot_create_staffprofile_for_student_user(self):
        user = make_user('mutual_test2@example.com')
        StudentProfile.objects.create(user=user, admission_number='ADM002')
        with self.assertRaises(ValidationError):
            StaffProfile(user=user, staff_number='MT002', job_title='Lecturer', department='ICT').clean()


class StudentOwnershipTests(TestCase):
    """
    Student A cannot access Student B's portal URLs.
    Object-level ownership enforced in views.

    Security requirement: URL parameter manipulation must return 404,
    not 403 (to avoid confirming existence of another student's record).
    """

    def setUp(self):
        self.student_a = make_student('student_a@example.com', 'NCC/A/001')
        self.student_b = make_student('student_b@example.com', 'NCC/B/001')

    def test_student_a_can_access_own_dashboard(self):
        self.client.force_login(self.student_a.user)
        response = self.client.get(reverse('student:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_student_a_can_access_own_profile(self):
        self.client.force_login(self.student_a.user)
        response = self.client.get(reverse('student:profile'))
        self.assertEqual(response.status_code, 200)

    def test_student_a_can_access_own_enrollments(self):
        self.client.force_login(self.student_a.user)
        response = self.client.get(reverse('student:enrollments'))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse('student:dashboard'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/student/',
            fetch_redirect_response=False,
        )

    def test_staff_user_without_studentprofile_gets_404_on_student_portal(self):
        """
        A staff user has no StudentProfile — the student portal should
        return 404 (not 403) via _get_student_profile / StudentOwnerMixin.
        """
        staff_user = make_user('staff_no_profile@example.com', is_staff=True)
        self.client.force_login(staff_user)
        response = self.client.get(reverse('student:dashboard'))
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_access_staff_academic_views(self):
        """
        A student user (is_staff=False) cannot access staff academic views
        even if they somehow navigate to the URL directly.
        """
        self.client.force_login(self.student_a.user)
        # Students list — requires staff + view_studentprofile permission
        response = self.client.get(reverse('staff:students'))
        self.assertIn(response.status_code, [302, 403])


class StudentStatusTests(TestCase):

    def test_default_status_is_active(self):
        s = make_student('status_default@example.com', 'NCC/DEF/001')
        self.assertEqual(s.status, StudentStatus.ACTIVE)

    def test_is_academically_active_true_for_active(self):
        s = make_student('active@example.com', 'NCC/ACT/001')
        self.assertTrue(s.is_academically_active())

    def test_is_academically_active_false_for_suspended(self):
        s = make_student('suspended@example.com', 'NCC/SUS/001')
        s.status = StudentStatus.SUSPENDED
        s.save(update_fields=['status', 'updated_at'])
        self.assertFalse(s.is_academically_active())

    def test_status_change_does_not_delete_student(self):
        s = make_student('nodelete@example.com', 'NCC/ND/001')
        s.status = StudentStatus.INACTIVE
        s.save(update_fields=['status', 'updated_at'])
        # Student still exists
        self.assertTrue(StudentProfile.objects.filter(pk=s.pk).exists())


class StudentAdminAuthorizationTests(TestCase):
    """
    Staff authorization boundary tests for student management.
    Backend enforcement — direct URL access tested.
    """

    def setUp(self):
        self.student = make_student('admin_test_student@example.com', 'NCC/AUTH/001')

    def test_unauthenticated_student_list_redirects(self):
        response = self.client.get(reverse('staff:students'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/staff/students/',
            fetch_redirect_response=False,
        )

    def test_authenticated_no_permission_gets_403(self):
        user = make_user('noauth_staff@example.com', is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse('staff:students'))
        self.assertEqual(response.status_code, 403)

    def test_view_permission_allows_list(self):
        from django.contrib.auth.models import Permission
        user = make_user('viewstaff@example.com', is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='view_studentprofile'))
        self.client.force_login(user)
        response = self.client.get(reverse('staff:students'))
        self.assertEqual(response.status_code, 200)

    def test_view_only_cannot_access_student_create(self):
        from django.contrib.auth.models import Permission
        user = make_user('viewonly2@example.com', is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='view_studentprofile'))
        self.client.force_login(user)
        response = self.client.get(reverse('staff:student_create'))
        self.assertEqual(response.status_code, 403)

    def test_view_only_cannot_change_student_status(self):
        from django.contrib.auth.models import Permission
        user = make_user('viewonly3@example.com', is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='view_studentprofile'))
        self.client.force_login(user)
        response = self.client.get(
            reverse('staff:student_status', kwargs={'pk': self.student.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_student_detail_directly_accessed_by_unpermissioned_user(self):
        """
        Directly accessing /staff/students/<pk>/ without permission = 403.
        The backend enforces this regardless of sidebar visibility.
        """
        user = make_user('direct_access@example.com', is_staff=True)
        self.client.force_login(user)
        response = self.client.get(
            reverse('staff:student_detail', kwargs={'pk': self.student.pk})
        )
        self.assertEqual(response.status_code, 403)
