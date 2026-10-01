"""
Staff portal views for Course and CourseUnit management.
All views use StaffRequiredMixin + explicit permission_required.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.mixins import StaffRequiredMixin
from apps.core.audit import audit_log
from apps.core.models import AuditAction

from .forms import CourseForm, CourseUnitForm
from .models import Course, CourseUnit


class CourseListView(StaffRequiredMixin, View):
    permission_required = 'courses.view_course'

    def get(self, request):
        qs = Course.objects.annotate(
            annotated_unit_count=Count('units', distinct=True),
            annotated_enrollment_count=Count('enrollments', distinct=True),
        ).order_by('name')

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))

        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'staff/courses/list.html', {
            'page_title': 'Courses',
            'active_section': 'courses',
            'page_obj': page_obj,
            'q': q,
            'status_filter': status_filter,
            'total': qs.count(),
            'can_add': request.user.has_perm('courses.add_course'),
        })


class CourseCreateView(StaffRequiredMixin, View):
    permission_required = 'courses.add_course'

    def get(self, request):
        return render(request, 'staff/courses/form.html', {
            'page_title': 'Add Course',
            'active_section': 'courses',
            'form': CourseForm(),
            'action': 'create',
        })

    def post(self, request):
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            audit_log(
                actor=request.user,
                action=AuditAction.COURSE_CREATED,
                obj=course,
                description=f'Course created: {course}',
                request=request,
            )
            messages.success(request, f'Course "{course.name}" created successfully.')
            return redirect('staff:course_detail', pk=course.pk)
        return render(request, 'staff/courses/form.html', {
            'page_title': 'Add Course',
            'active_section': 'courses',
            'form': form,
            'action': 'create',
        })


class CourseDetailView(StaffRequiredMixin, View):
    permission_required = 'courses.view_course'

    def get(self, request, pk):
        course = get_object_or_404(
            Course.objects.annotate(
                annotated_enrollment_count=Count('enrollments', distinct=True)
            ),
            pk=pk,
        )
        units = course.units.order_by('code')
        return render(request, 'staff/courses/detail.html', {
            'page_title': course.name,
            'active_section': 'courses',
            'course': course,
            'units': units,
            'can_edit': request.user.has_perm('courses.change_course'),
            'can_activate': request.user.has_perm('courses.activate_course'),
            'can_add_unit': request.user.has_perm('courses.add_courseunit'),
        })


class CourseEditView(StaffRequiredMixin, View):
    permission_required = 'courses.change_course'

    def get(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        return render(request, 'staff/courses/form.html', {
            'page_title': f'Edit: {course.name}',
            'active_section': 'courses',
            'form': CourseForm(instance=course),
            'course': course,
            'action': 'edit',
        })

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            audit_log(
                actor=request.user,
                action=AuditAction.COURSE_UPDATED,
                obj=course,
                description=f'Course updated: {course}',
                request=request,
            )
            messages.success(request, f'Course "{course.name}" updated.')
            return redirect('staff:course_detail', pk=course.pk)
        return render(request, 'staff/courses/form.html', {
            'page_title': f'Edit: {course.name}',
            'active_section': 'courses',
            'form': form,
            'course': course,
            'action': 'edit',
        })


class CourseActivateView(StaffRequiredMixin, View):
    permission_required = 'courses.activate_course'

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        new_status = not course.is_active
        course.is_active = new_status
        course.save(update_fields=['is_active', 'updated_at'])
        audit_log(
            actor=request.user,
            action=AuditAction.COURSE_STATUS_CHANGED,
            obj=course,
            description=f'Course {"activated" if new_status else "deactivated"}: {course}',
            request=request,
        )
        label = 'activated' if new_status else 'deactivated'
        messages.success(request, f'Course "{course.name}" {label}.')
        return redirect('staff:course_detail', pk=course.pk)


# ---------------------------------------------------------------------------
# Course Units
# ---------------------------------------------------------------------------

class CourseUnitListView(StaffRequiredMixin, View):
    permission_required = 'courses.view_courseunit'

    def get(self, request, course_pk):
        course = get_object_or_404(Course, pk=course_pk)
        units = course.units.order_by('code')
        return render(request, 'staff/courses/units.html', {
            'page_title': f'{course.code} — Units',
            'active_section': 'courses',
            'course': course,
            'units': units,
            'can_add': request.user.has_perm('courses.add_courseunit'),
            'can_edit': request.user.has_perm('courses.change_courseunit'),
        })


class CourseUnitCreateView(StaffRequiredMixin, View):
    permission_required = 'courses.add_courseunit'

    def get(self, request, course_pk):
        course = get_object_or_404(Course, pk=course_pk)
        return render(request, 'staff/courses/unit_form.html', {
            'page_title': f'Add Unit to {course.code}',
            'active_section': 'courses',
            'course': course,
            'form': CourseUnitForm(course=course),
            'action': 'create',
        })

    def post(self, request, course_pk):
        course = get_object_or_404(Course, pk=course_pk)
        form = CourseUnitForm(request.POST, course=course)
        if form.is_valid():
            unit = form.save(commit=False)
            unit.course = course
            unit.save()
            audit_log(
                actor=request.user,
                action=AuditAction.COURSE_UNIT_CREATED,
                obj=unit,
                description=f'Course unit created: {unit} in {course}',
                request=request,
            )
            messages.success(request, f'Unit "{unit.name}" added to {course.code}.')
            return redirect('staff:course_units', course_pk=course.pk)
        return render(request, 'staff/courses/unit_form.html', {
            'page_title': f'Add Unit to {course.code}',
            'active_section': 'courses',
            'course': course,
            'form': form,
            'action': 'create',
        })


class CourseUnitEditView(StaffRequiredMixin, View):
    permission_required = 'courses.change_courseunit'

    def get(self, request, course_pk, pk):
        course = get_object_or_404(Course, pk=course_pk)
        unit = get_object_or_404(CourseUnit, pk=pk, course=course)
        return render(request, 'staff/courses/unit_form.html', {
            'page_title': f'Edit Unit: {unit.code}',
            'active_section': 'courses',
            'course': course,
            'unit': unit,
            'form': CourseUnitForm(instance=unit, course=course),
            'action': 'edit',
        })

    def post(self, request, course_pk, pk):
        course = get_object_or_404(Course, pk=course_pk)
        unit = get_object_or_404(CourseUnit, pk=pk, course=course)
        form = CourseUnitForm(request.POST, instance=unit, course=course)
        if form.is_valid():
            unit = form.save()
            audit_log(
                actor=request.user,
                action=AuditAction.COURSE_UNIT_UPDATED,
                obj=unit,
                description=f'Course unit updated: {unit}',
                request=request,
            )
            messages.success(request, f'Unit "{unit.name}" updated.')
            return redirect('staff:course_units', course_pk=course.pk)
        return render(request, 'staff/courses/unit_form.html', {
            'page_title': f'Edit Unit: {unit.code}',
            'active_section': 'courses',
            'course': course,
            'unit': unit,
            'form': form,
            'action': 'edit',
        })
