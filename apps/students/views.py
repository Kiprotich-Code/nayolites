"""
Student portal views — database-driven.

All views use StudentOwnerMixin (or LoginRequiredMixin + studentprofile check)
to enforce ownership. A student can only access their own records.

Security: URL parameter manipulation is defeated because all querysets
filter by the authenticated student's profile. Accessing another student's
URL returns 404 — not 403 — to avoid confirming whether a record exists.
"""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from .mixins import StudentOwnerMixin
from .models import StudentProfile


def _get_student_profile(request):
    """
    Retrieve the StudentProfile for the authenticated user.
    Raises Http404 if the user has no student profile.
    This mirrors StudentOwnerMixin for function-based views.
    """
    try:
        return request.user.studentprofile
    except StudentProfile.DoesNotExist:
        raise Http404('No student profile found for this account.')


@login_required(login_url='/auth/login/')
def student_dashboard(request):
    student = _get_student_profile(request)

    # Current/most recent enrollment
    current_enrollment = (
        student.enrollments
        .select_related('course', 'academic_period')
        .filter(status__in=['ACTIVE', 'PENDING'])
        .order_by('-enrolled_at')
        .first()
    )

    # Enrollment history (recent 5)
    all_enrollments = (
        student.enrollments
        .select_related('course', 'academic_period')
        .order_by('-enrolled_at')[:5]
    )

    # Recent published results (latest 4)
    from apps.results.models import Result, ResultStatus
    recent_results = (
        Result.objects
        .filter(enrollment__student=student, status=ResultStatus.PUBLISHED)
        .select_related('course_unit', 'enrollment__academic_period')
        .order_by('-published_at')[:4]
    )

    # Recent content for enrolled courses (latest 4 items)
    from apps.enrollments.models import EnrollmentStatus
    from apps.content.models import CourseContent, ContentVisibility
    enrolled_course_ids = (
        student.enrollments
        .filter(status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING])
        .values_list('course_id', flat=True)
    )
    recent_content = (
        CourseContent.objects
        .filter(
            course_id__in=enrolled_course_ids,
            visibility__in=[ContentVisibility.ENROLLED, ContentVisibility.ALL],
        )
        .select_related('course', 'course_unit')
        .order_by('-created_at')[:4]
    )

    return render(request, 'student/dashboard.html', {
        'page_title': 'Dashboard',
        'student': student,
        'current_enrollment': current_enrollment,
        'recent_enrollments': all_enrollments,
        'recent_results': recent_results,
        'recent_content': recent_content,
    })


@login_required(login_url='/auth/login/')
def student_profile(request):
    student = _get_student_profile(request)
    return render(request, 'student/profile.html', {
        'page_title': 'My Profile',
        'student': student,
    })


@login_required(login_url='/auth/login/')
def student_course(request):
    student = _get_student_profile(request)

    # Current active/pending enrollment
    current_enrollment = (
        student.enrollments
        .select_related('course', 'academic_period')
        .filter(status__in=['ACTIVE', 'PENDING'])
        .order_by('-enrolled_at')
        .first()
    )

    units = []
    if current_enrollment:
        units = (
            current_enrollment.course.units
            .filter(is_active=True)
            .order_by('code')
        )

    return render(request, 'student/course.html', {
        'page_title': 'My Course',
        'student': student,
        'current_enrollment': current_enrollment,
        'units': units,
    })


@login_required(login_url='/auth/login/')
def student_enrollments(request):
    student = _get_student_profile(request)

    enrollments = (
        student.enrollments
        .select_related('course', 'academic_period')
        .order_by('-enrolled_at')
    )

    return render(request, 'student/enrollments.html', {
        'page_title': 'My Enrollments',
        'student': student,
        'enrollments': enrollments,
    })


# ---------------------------------------------------------------------------
# Finance / Results / Documents / Content — still served as stubs
# (These depend on Finance and Results modules not yet implemented)
# ---------------------------------------------------------------------------

@login_required(login_url='/auth/login/')
def student_fees(request):
    student = _get_student_profile(request)
    return render(request, 'student/fees.html', {
        'page_title': 'Fees and Payments',
        'student': student,
        'placeholder': True,
    })


@login_required(login_url='/auth/login/')
def student_invoice_detail(request, invoice_number):
    _get_student_profile(request)
    # Finance module not yet implemented
    raise Http404('Finance module not yet implemented.')


@login_required(login_url='/auth/login/')
def student_receipt(request, receipt_number):
    _get_student_profile(request)
    raise Http404('Finance module not yet implemented.')


@login_required(login_url='/auth/login/')
def student_results(request):
    student = _get_student_profile(request)

    # Only published results for the authenticated student's own enrollments
    from apps.results.models import Result, ResultStatus
    results_qs = (
        Result.objects
        .filter(
            enrollment__student=student,
            status=ResultStatus.PUBLISHED,
        )
        .select_related(
            'enrollment__course',
            'enrollment__academic_period',
            'course_unit',
        )
        .order_by('-enrollment__academic_period__start_date', 'course_unit__code')
    )

    # Group by academic period for display
    from collections import defaultdict
    by_period = defaultdict(list)
    for r in results_qs:
        key = r.enrollment.academic_period.name
        by_period[key].append(r)

    return render(request, 'student/results.html', {
        'page_title': 'My Results',
        'student': student,
        'results_by_period': dict(by_period),
        'has_results': results_qs.exists(),
    })


@login_required(login_url='/auth/login/')
def student_documents(request):
    student = _get_student_profile(request)
    return render(request, 'student/documents.html', {
        'page_title': 'My Documents',
        'student': student,
        'placeholder': True,
    })


@login_required(login_url='/auth/login/')
def student_content(request):
    student = _get_student_profile(request)

    # Get the student's active/pending enrollments
    from apps.enrollments.models import Enrollment, EnrollmentStatus
    from apps.content.models import CourseContent, ContentVisibility

    enrolled_course_ids = (
        Enrollment.objects
        .filter(
            student=student,
            status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING],
        )
        .values_list('course_id', flat=True)
    )

    # Return ENROLLED-visibility content for courses the student is in,
    # plus ALL-visibility content for any course.
    # STAFF-only content is never returned.
    content_qs = (
        CourseContent.objects
        .filter(
            course_id__in=enrolled_course_ids,
            visibility__in=[ContentVisibility.ENROLLED, ContentVisibility.ALL],
        )
        .select_related('course', 'course_unit')
        .order_by('course__code', 'course_unit__code', '-created_at')
    )

    # Group by course then unit for display
    from collections import defaultdict
    by_course = defaultdict(lambda: defaultdict(list))
    for item in content_qs:
        unit_label = (
            f'{item.course_unit.code} — {item.course_unit.name}'
            if item.course_unit_id
            else 'General'
        )
        by_course[item.course.name][unit_label].append(item)

    return render(request, 'student/content.html', {
        'page_title': 'Course Content',
        'student': student,
        'content_by_course': {k: dict(v) for k, v in by_course.items()},
        'total_items': content_qs.count(),
        'has_content': content_qs.exists(),
    })
