"""
Tests for the Course and CourseUnit domain.

Covers:
- Course creation and uniqueness
- Course activation/deactivation
- CourseUnit creation and uniqueness within a course
- Authorization: staff without permission cannot access academic views
- Authorization: staff with view cannot perform change actions
"""

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from .models import Course, CourseUnit


def make_user(email, password='TestPass123!', is_staff=False, **kwargs):
    kwargs.setdefault('first_name', 'Test')
    kwargs.setdefault('last_name', 'User')
    u = User.objects.create_user(email=email, password=password, is_staff=is_staff, **kwargs)
    return u


def make_course(**kwargs):
    kwargs.setdefault('code', 'TST')
    kwargs.setdefault('name', 'Test Course')
    kwargs.setdefault('duration', '1 Year')
    kwargs.setdefault('is_active', True)
    return Course.objects.create(**kwargs)


class CourseModelTests(TestCase):

    def test_course_creation(self):
        c = make_course()
        self.assertEqual(c.code, 'TST')
        self.assertTrue(c.is_active)
        self.assertIsNotNone(c.slug)

    def test_slug_auto_generated(self):
        c = make_course(code='DCS', name='Diploma in Computer Science', duration='2 Years')
        self.assertIn('diploma', c.slug)

    def test_course_code_uniqueness(self):
        make_course(code='UNIQ', name='First', duration='1 Year')
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_course(code='UNIQ', name='Second', duration='1 Year')

    def test_course_str(self):
        c = make_course()
        self.assertIn('TST', str(c))

    def test_course_activation_toggle(self):
        c = make_course(is_active=True)
        c.is_active = False
        c.save(update_fields=['is_active', 'updated_at'])
        c.refresh_from_db()
        self.assertFalse(c.is_active)

    def test_inactive_course_not_in_active_list(self):
        make_course(code='ACT', name='Active', duration='1 Year', is_active=True)
        make_course(code='INACT', name='Inactive', duration='1 Year', is_active=False)
        active = Course.objects.filter(is_active=True)
        codes = list(active.values_list('code', flat=True))
        self.assertIn('ACT', codes)
        self.assertNotIn('INACT', codes)


class CourseUnitModelTests(TestCase):

    def setUp(self):
        self.course = make_course(code='DCS', name='Diploma CS', duration='2 Years')

    def test_unit_creation(self):
        u = CourseUnit.objects.create(course=self.course, code='DCS 101', name='Intro to Programming')
        self.assertEqual(u.course, self.course)
        self.assertTrue(u.is_active)

    def test_unit_code_unique_within_course(self):
        CourseUnit.objects.create(course=self.course, code='DCS 101', name='Unit 1')
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CourseUnit.objects.create(course=self.course, code='DCS 101', name='Duplicate')

    def test_unit_code_can_repeat_across_courses(self):
        other = make_course(code='DBM', name='Broadcast Media', duration='2 Years')
        CourseUnit.objects.create(course=self.course, code='101', name='Unit A')
        # Same code in different course is valid
        u2 = CourseUnit.objects.create(course=other, code='101', name='Unit B')
        self.assertEqual(u2.course, other)

    def test_unit_str(self):
        u = CourseUnit.objects.create(course=self.course, code='DCS 101', name='Intro')
        self.assertIn('DCS 101', str(u))


class CourseAuthorizationTests(TestCase):
    """
    Authorization boundary tests for Course staff views.
    Backend enforcement — not just sidebar visibility.
    """

    def setUp(self):
        self.course = make_course(code='TST', name='Test', duration='1 Year')

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse('staff:courses'))
        self.assertRedirects(response, '/auth/login/?next=/staff/courses/', fetch_redirect_response=False)

    def test_authenticated_without_permission_gets_403(self):
        user = make_user('noauth@example.com', is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse('staff:courses'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_with_view_permission_can_list(self):
        user = make_user('viewer@example.com', is_staff=True)
        perm = Permission.objects.get(codename='view_course')
        user.user_permissions.add(perm)
        self.client.force_login(user)
        response = self.client.get(reverse('staff:courses'))
        self.assertEqual(response.status_code, 200)

    def test_view_permission_cannot_create(self):
        user = make_user('viewonly@example.com', is_staff=True)
        perm = Permission.objects.get(codename='view_course')
        user.user_permissions.add(perm)
        self.client.force_login(user)
        response = self.client.get(reverse('staff:course_create'))
        self.assertEqual(response.status_code, 403)

    def test_non_staff_user_cannot_access_staff_course_views(self):
        user = make_user('student@example.com', is_staff=False)
        # Add the permission anyway — is_staff=False means handle_no_permission redirects
        perm = Permission.objects.get(codename='view_course')
        user.user_permissions.add(perm)
        self.client.force_login(user)
        response = self.client.get(reverse('staff:courses'))
        # PermissionRequiredMixin raises → 403 for authenticated; redirect for anon
        self.assertIn(response.status_code, [302, 403])
