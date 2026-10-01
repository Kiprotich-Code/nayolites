"""
Public course application views.

Architecture:
    Public form submission → CourseApplication (SUBMITTED)
    Staff review → Accept/Reject
    If accepted: Staff creates Student + Enrollment

The public applicant never creates an Enrollment or StudentProfile directly.
No internal IDs are exposed to the public at any point.
"""

from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.audit import audit_log
from apps.core.models import AuditAction
from apps.enrollments.application_forms import CourseApplicationForm
from apps.enrollments.applications import ApplicationStatus, CourseApplication
from apps.enrollments.models import AcademicPeriod

from .models import Course


def public_apply(request, slug):
    """
    GET: Show the application form for a specific course.
    POST: Validate and save the CourseApplication; redirect to confirmation.

    Security:
    - Course is identified by slug (not PK) — internal IDs never in the URL.
    - preferred_period is validated server-side against AcademicPeriod.pk.
    - Status always starts at SUBMITTED regardless of form input.
    - CSRF enforced by middleware.
    """
    course = get_object_or_404(Course, slug=slug, is_active=True)
    active_periods = AcademicPeriod.objects.filter(is_active=True).order_by('start_date')

    if request.method == 'POST':
        form = CourseApplicationForm(request.POST, active_periods=active_periods)
        if form.is_valid():
            d = form.cleaned_data

            # Resolve preferred_period safely — never trust raw ID from form
            preferred_period = None
            if d.get('preferred_period'):
                preferred_period = AcademicPeriod.objects.filter(
                    pk=d['preferred_period'],
                    is_active=True,
                ).first()

            try:
                application = CourseApplication.objects.create(
                    first_name=d['first_name'],
                    last_name=d['last_name'],
                    email=d['email'],
                    phone=d.get('phone', ''),
                    message=d.get('message', ''),
                    course=course,
                    preferred_period=preferred_period,
                    # status defaults to SUBMITTED; reference_number auto-generated
                )
            except IntegrityError:
                # Extremely unlikely (UUID collision) — handle gracefully
                form.add_error(None, 'An error occurred. Please try again.')
                return render(request, 'public/apply.html', {
                    'page_title': f'Apply — {course.name}',
                    'course': course,
                    'form': form,
                    'active_periods': active_periods,
                })

            audit_log(
                actor=None,  # unauthenticated public submission
                action=AuditAction.APPLICATION_SUBMITTED,
                obj=application,
                description=(
                    f'Public application submitted: {application.reference_number} '
                    f'for {course.code} by {application.get_full_name()}'
                ),
                request=request,
            )

            return redirect('courses:apply_confirmation', reference=application.reference_number)

    else:
        form = CourseApplicationForm(active_periods=active_periods)

    return render(request, 'public/apply.html', {
        'page_title': f'Apply — {course.name}',
        'course': course,
        'form': form,
        'active_periods': active_periods,
    })


def public_apply_confirmation(request, reference):
    """
    Confirmation page after a successful application submission.

    Only the reference_number (not internal PK) is used to look up the
    application — preventing enumeration of sequential IDs.
    """
    application = get_object_or_404(
        CourseApplication,
        reference_number=reference,
        status=ApplicationStatus.SUBMITTED,
    )
    return render(request, 'public/apply_confirmation.html', {
        'page_title': 'Application Received',
        'application': application,
        'course': application.course,
    })
