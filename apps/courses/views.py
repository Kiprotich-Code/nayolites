"""
Public-facing course views — database-driven.

Replaces the mock-data catalogue in apps/core/views.py.
These views are intentionally read-only and expose only what is safe
for public consumption: active courses and their units.

No internal IDs, staff information, or enrollment records are exposed.
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Course


def public_courses(request):
    """Active course catalogue with optional search."""
    qs = (
        Course.objects
        .filter(is_active=True)
        .prefetch_related('units')
        .order_by('name')
    )

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(code__icontains=q)
            | Q(description__icontains=q)
        )

    return render(request, 'public/courses.html', {
        'page_title': 'Our Programmes',
        'courses': qs,
        'total': qs.count(),
        'q': q,
    })


def public_course_detail(request, slug):
    """
    Single active course detail — units, description, and application CTA.
    The slug is the public URL identifier; internal PKs are never surfaced.
    """
    from apps.enrollments.models import AcademicPeriod

    course = get_object_or_404(Course, slug=slug, is_active=True)
    units = course.units.filter(is_active=True).order_by('code')
    active_periods = AcademicPeriod.objects.filter(is_active=True).order_by('start_date')

    return render(request, 'public/course_detail.html', {
        'page_title': course.name,
        'course': course,
        'units': units,
        'active_periods': active_periods,
    })
