"""
Staff portal views for AcademicPeriod and Enrollment management.
All views use StaffRequiredMixin + explicit permission_required.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.mixins import StaffRequiredMixin
from apps.core.audit import audit_log
from apps.core.models import AuditAction

from .forms import AcademicPeriodForm, EnrollmentCreateForm, EnrollmentStatusForm
from .models import AcademicPeriod, Enrollment, EnrollmentStatus
from .services import create_enrollment, change_enrollment_status, approve_enrollment


# ---------------------------------------------------------------------------
# Academic Period views
# ---------------------------------------------------------------------------

class AcademicPeriodListView(StaffRequiredMixin, View):
    permission_required = 'enrollments.view_academicperiod'

    def get(self, request):
        qs = AcademicPeriod.objects.annotate(
            enrollment_count=Count('enrollments', distinct=True)
        ).order_by('-start_date')

        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        return render(request, 'staff/academic_periods/list.html', {
            'page_title': 'Academic Periods',
            'active_section': 'academic_periods',
            'periods': qs,
            'status_filter': status_filter,
            'can_add': request.user.has_perm('enrollments.add_academicperiod'),
        })


class AcademicPeriodCreateView(StaffRequiredMixin, View):
    permission_required = 'enrollments.add_academicperiod'

    def get(self, request):
        return render(request, 'staff/academic_periods/form.html', {
            'page_title': 'Create Academic Period',
            'active_section': 'academic_periods',
            'form': AcademicPeriodForm(),
            'action': 'create',
        })

    def post(self, request):
        form = AcademicPeriodForm(request.POST)
        if form.is_valid():
            period = form.save()
            audit_log(
                actor=request.user,
                action=AuditAction.ACADEMIC_PERIOD_CREATED,
                obj=period,
                description=f'Academic period created: {period}',
                request=request,
            )
            messages.success(request, f'Academic period "{period.name}" created.')
            return redirect('staff:academic_periods')
        return render(request, 'staff/academic_periods/form.html', {
            'page_title': 'Create Academic Period',
            'active_section': 'academic_periods',
            'form': form,
            'action': 'create',
        })


class AcademicPeriodEditView(StaffRequiredMixin, View):
    permission_required = 'enrollments.change_academicperiod'

    def get(self, request, pk):
        period = get_object_or_404(AcademicPeriod, pk=pk)
        return render(request, 'staff/academic_periods/form.html', {
            'page_title': f'Edit: {period.name}',
            'active_section': 'academic_periods',
            'form': AcademicPeriodForm(instance=period),
            'period': period,
            'action': 'edit',
        })

    def post(self, request, pk):
        period = get_object_or_404(AcademicPeriod, pk=pk)
        form = AcademicPeriodForm(request.POST, instance=period)
        if form.is_valid():
            period = form.save()
            audit_log(
                actor=request.user,
                action=AuditAction.ACADEMIC_PERIOD_UPDATED,
                obj=period,
                description=f'Academic period updated: {period}',
                request=request,
            )
            messages.success(request, f'Academic period "{period.name}" updated.')
            return redirect('staff:academic_periods')
        return render(request, 'staff/academic_periods/form.html', {
            'page_title': f'Edit: {period.name}',
            'active_section': 'academic_periods',
            'form': form,
            'period': period,
            'action': 'edit',
        })


class AcademicPeriodStatusView(StaffRequiredMixin, View):
    permission_required = 'enrollments.change_academicperiod'

    def post(self, request, pk):
        period = get_object_or_404(AcademicPeriod, pk=pk)
        period.is_active = not period.is_active
        period.save(update_fields=['is_active', 'updated_at'])
        audit_log(
            actor=request.user,
            action=AuditAction.ACADEMIC_PERIOD_STATUS_CHANGED,
            obj=period,
            description=f'Period {"activated" if period.is_active else "closed"}: {period}',
            request=request,
        )
        label = 'activated' if period.is_active else 'closed'
        messages.success(request, f'Period "{period.name}" {label}.')
        return redirect('staff:academic_periods')


# ---------------------------------------------------------------------------
# Enrollment views
# ---------------------------------------------------------------------------

class EnrollmentListView(StaffRequiredMixin, View):
    permission_required = 'enrollments.view_enrollment'

    def get(self, request):
        from apps.courses.models import Course

        qs = Enrollment.objects.select_related(
            'student__user', 'course', 'academic_period'
        ).order_by('-enrolled_at')

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(student__admission_number__icontains=q)
                | Q(student__user__first_name__icontains=q)
                | Q(student__user__last_name__icontains=q)
                | Q(course__code__icontains=q)
                | Q(course__name__icontains=q)
            )

        status_filter = request.GET.get('status', '')
        if status_filter:
            qs = qs.filter(status=status_filter)

        course_filter = request.GET.get('course', '')
        if course_filter:
            qs = qs.filter(course_id=course_filter)

        period_filter = request.GET.get('period', '')
        if period_filter:
            qs = qs.filter(academic_period_id=period_filter)

        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'staff/enrollments/list.html', {
            'page_title': 'Enrollments',
            'active_section': 'enrollments',
            'page_obj': page_obj,
            'q': q,
            'status_filter': status_filter,
            'course_filter': course_filter,
            'period_filter': period_filter,
            'status_choices': EnrollmentStatus.choices,
            'courses': Course.objects.filter(is_active=True).order_by('name'),
            'periods': AcademicPeriod.objects.order_by('-start_date'),
            'total': qs.count(),
            'can_add': request.user.has_perm('enrollments.add_enrollment'),
        })


class EnrollmentCreateView(StaffRequiredMixin, View):
    permission_required = 'enrollments.add_enrollment'

    def get(self, request):
        initial = {}
        # Pre-fill student if coming from student detail page
        student_pk = request.GET.get('student')
        if student_pk:
            from apps.students.models import StudentProfile
            try:
                initial['student'] = StudentProfile.objects.get(pk=student_pk)
            except StudentProfile.DoesNotExist:
                pass
        return render(request, 'staff/enrollments/form.html', {
            'page_title': 'Enroll Student',
            'active_section': 'enrollments',
            'form': EnrollmentCreateForm(initial=initial),
        })

    def post(self, request):
        form = EnrollmentCreateForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                enrollment = create_enrollment(
                    student=d['student'],
                    course=d['course'],
                    academic_period=d['academic_period'],
                    created_by=request.user,
                    initial_status=d['initial_status'],
                    notes=d.get('notes', ''),
                    request=request,
                )
            except (ValidationError, ValueError) as exc:
                messages.error(request, str(exc))
                return render(request, 'staff/enrollments/form.html', {
                    'page_title': 'Enroll Student',
                    'active_section': 'enrollments',
                    'form': form,
                })
            messages.success(
                request,
                f'Enrollment created: {enrollment.student.user.get_full_name()} '
                f'→ {enrollment.course.code} [{enrollment.academic_period}].',
            )
            return redirect('staff:enrollment_detail', pk=enrollment.pk)
        return render(request, 'staff/enrollments/form.html', {
            'page_title': 'Enroll Student',
            'active_section': 'enrollments',
            'form': form,
        })


class EnrollmentDetailView(StaffRequiredMixin, View):
    permission_required = 'enrollments.view_enrollment'

    def get(self, request, pk):
        enrollment = get_object_or_404(
            Enrollment.objects.select_related(
                'student__user', 'course', 'academic_period'
            ),
            pk=pk,
        )
        return render(request, 'staff/enrollments/detail.html', {
            'page_title': f'Enrollment — {enrollment.student.user.get_full_name()}',
            'active_section': 'enrollments',
            'enrollment': enrollment,
            'can_change_status': request.user.has_perm('enrollments.change_enrollment'),
            'can_approve': request.user.has_perm('enrollments.approve_enrollment'),
            'EnrollmentStatus': EnrollmentStatus,
        })


class EnrollmentStatusChangeView(StaffRequiredMixin, View):
    permission_required = 'enrollments.change_enrollment'

    def get(self, request, pk):
        enrollment = get_object_or_404(
            Enrollment.objects.select_related('student__user', 'course', 'academic_period'),
            pk=pk,
        )
        form = EnrollmentStatusForm(initial={'new_status': enrollment.status})
        return render(request, 'staff/enrollments/status_change.html', {
            'page_title': 'Change Enrollment Status',
            'active_section': 'enrollments',
            'enrollment': enrollment,
            'form': form,
        })

    def post(self, request, pk):
        enrollment = get_object_or_404(
            Enrollment.objects.select_related('student__user', 'course', 'academic_period'),
            pk=pk,
        )
        form = EnrollmentStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['new_status']
            # Approve action requires specific permission
            if (new_status == EnrollmentStatus.ACTIVE
                    and enrollment.status == EnrollmentStatus.PENDING
                    and not request.user.has_perm('enrollments.approve_enrollment')):
                messages.error(request, 'You do not have permission to approve enrollments.')
                return redirect('staff:enrollment_detail', pk=enrollment.pk)
            try:
                change_enrollment_status(
                    enrollment=enrollment,
                    new_status=new_status,
                    changed_by=request.user,
                    notes=form.cleaned_data.get('notes', ''),
                    request=request,
                )
            except (ValueError, ValidationError) as exc:
                messages.error(request, str(exc))
                return redirect('staff:enrollment_detail', pk=enrollment.pk)
            messages.success(request, f'Enrollment status updated to {enrollment.get_status_display()}.')
            return redirect('staff:enrollment_detail', pk=enrollment.pk)
        return render(request, 'staff/enrollments/status_change.html', {
            'page_title': 'Change Enrollment Status',
            'active_section': 'enrollments',
            'enrollment': enrollment,
            'form': form,
        })
