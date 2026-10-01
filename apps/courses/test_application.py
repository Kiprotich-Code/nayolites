"""
Tests for the public CourseApplication flow.

Covers:
- Valid application submission creates CourseApplication
- Reference number is auto-generated (not from form input)
- Status is always SUBMITTED after submission (never from form input)
- Invalid input is rejected
- CSRF protection (Django's test client enforces this via enforce_csrf_checks)
- Internal fields cannot be manipulated via the public form
- Confirmation page uses reference number not PK
- Inactive course cannot accept applications (returns 404)
- Audit log entry created on submission
"""

import datetime

from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import AuditAction, AuditLog
from apps.courses.models import Course
from apps.enrollments.applications import ApplicationStatus, CourseApplication
from apps.enrollments.models import AcademicPeriod


def make_course(code='APP', name='Application Course', active=True):
    return Course.objects.create(code=code, name=name, duration='1 Year', is_active=active)


def make_period(active=True):
    return AcademicPeriod.objects.create(
        name='2026 Test Intake',
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 6, 30),
        is_active=active,
    )


class PublicApplicationTests(TestCase):

    def setUp(self):
        self.course = make_course()
        self.period = make_period()
        self.apply_url = reverse('courses:apply', kwargs={'slug': self.course.slug})

    def _valid_post_data(self, **overrides):
        data = {
            'first_name': 'Amina',
            'last_name': 'Kariuki',
            'email': 'amina@example.com',
            'phone': '+254712345678',
            'preferred_period': self.period.pk,
            'message': 'I am very interested.',
        }
        data.update(overrides)
        return data

    def test_get_application_form(self):
        response = self.client.get(self.apply_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.name)

    def test_valid_submission_creates_application(self):
        before = CourseApplication.objects.count()
        response = self.client.post(self.apply_url, self._valid_post_data())
        self.assertEqual(CourseApplication.objects.count(), before + 1)

    def test_valid_submission_redirects_to_confirmation(self):
        response = self.client.post(self.apply_url, self._valid_post_data())
        app = CourseApplication.objects.last()
        self.assertRedirects(
            response,
            reverse('courses:apply_confirmation', kwargs={
                'slug': self.course.slug,
                'reference': app.reference_number,
            }),
            fetch_redirect_response=False,
        )

    def test_status_always_submitted_not_manipulatable(self):
        """Public user cannot set status to ACCEPTED via form data."""
        data = self._valid_post_data()
        data['status'] = 'ACCEPTED'  # injected — must be ignored
        self.client.post(self.apply_url, data)
        app = CourseApplication.objects.last()
        self.assertEqual(app.status, ApplicationStatus.SUBMITTED,
                         'Status must always be SUBMITTED regardless of form input.')

    def test_reference_number_is_server_generated(self):
        """Injecting a custom reference_number via form must have no effect."""
        data = self._valid_post_data()
        data['reference_number'] = 'HACK-0000'
        self.client.post(self.apply_url, data)
        app = CourseApplication.objects.last()
        self.assertNotEqual(app.reference_number, 'HACK-0000',
                            'reference_number must be server-generated.')
        self.assertTrue(app.reference_number.startswith('APP-'))

    def test_internal_fields_not_set_by_form(self):
        """staff_notes and reviewed_by must be blank/null after public submission."""
        self.client.post(self.apply_url, self._valid_post_data())
        app = CourseApplication.objects.last()
        self.assertEqual(app.staff_notes, '')
        self.assertIsNone(app.reviewed_by)
        self.assertIsNone(app.reviewed_at)

    def test_inactive_course_returns_404(self):
        inactive = make_course(code='INACT', name='Inactive', active=False)
        url = reverse('courses:apply', kwargs={'slug': inactive.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_missing_required_fields_rejected(self):
        response = self.client.post(self.apply_url, {
            'first_name': '',
            'last_name': '',
            'email': 'not-an-email',
        })
        self.assertEqual(response.status_code, 200)  # re-rendered form
        self.assertEqual(CourseApplication.objects.count(), 0)

    def test_invalid_email_rejected(self):
        data = self._valid_post_data(email='not-valid')
        response = self.client.post(self.apply_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CourseApplication.objects.count(), 0)

    def test_course_set_from_url_not_form(self):
        """The course FK is set from the URL slug, not from form data."""
        other_course = make_course(code='OTH', name='Other')
        data = self._valid_post_data()
        # Attempt to inject a different course ID
        data['course'] = other_course.pk
        self.client.post(self.apply_url, data)
        app = CourseApplication.objects.last()
        self.assertEqual(app.course, self.course,
                         'Course must come from the URL, not form fields.')

    def test_preferred_period_validated_server_side(self):
        """An invalid period PK injected from the form is ignored gracefully."""
        data = self._valid_post_data(preferred_period=99999)
        response = self.client.post(self.apply_url, data)
        # Either rejected (200) or period is None — must not crash or blindly use 99999
        if response.status_code == 302:
            app = CourseApplication.objects.last()
            self.assertIsNone(app.preferred_period,
                              'Invalid period PK must result in null preferred_period.')

    def test_audit_log_created_on_submission(self):
        before = AuditLog.objects.filter(action=AuditAction.APPLICATION_SUBMITTED).count()
        self.client.post(self.apply_url, self._valid_post_data())
        after = AuditLog.objects.filter(action=AuditAction.APPLICATION_SUBMITTED).count()
        self.assertEqual(after, before + 1)

    def test_confirmation_page_accessible_via_reference(self):
        self.client.post(self.apply_url, self._valid_post_data())
        app = CourseApplication.objects.last()
        url = reverse('courses:apply_confirmation', kwargs={
            'slug': self.course.slug,
            'reference': app.reference_number,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, app.reference_number)

    def test_confirmation_page_does_not_expose_pk(self):
        """The confirmation page must show reference_number, not the internal PK."""
        self.client.post(self.apply_url, self._valid_post_data())
        app = CourseApplication.objects.last()
        url = reverse('courses:apply_confirmation', kwargs={
            'slug': self.course.slug,
            'reference': app.reference_number,
        })
        response = self.client.get(url)
        content = response.content.decode()
        # The raw integer PK should not appear in the page
        self.assertNotIn(f'/{app.pk}/', content,
                         'Internal PK must not be exposed on the confirmation page.')

    def test_csrf_enforced_on_application_form(self):
        """POST without CSRF token must be rejected."""
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(self.apply_url, self._valid_post_data())
        self.assertEqual(response.status_code, 403,
                         'CSRF protection must be active on the application form.')


class PublicCatalogueTests(TestCase):

    def test_public_courses_shows_only_active(self):
        Course.objects.create(code='VIS', name='Visible', duration='1 Year', is_active=True)
        Course.objects.create(code='HID', name='Hidden', duration='1 Year', is_active=False)
        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Visible')
        self.assertNotContains(response, 'Hidden')

    def test_inactive_course_detail_returns_404(self):
        c = Course.objects.create(code='OLD', name='Old Course', duration='1 Year', is_active=False)
        response = self.client.get(reverse('courses:detail', kwargs={'slug': c.slug}))
        self.assertEqual(response.status_code, 404)

    def test_active_course_detail_accessible(self):
        c = Course.objects.create(code='NEW', name='New Course', duration='1 Year', is_active=True)
        response = self.client.get(reverse('courses:detail', kwargs={'slug': c.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Course')
