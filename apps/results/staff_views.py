"""
Staff portal views for the Results domain.
All views use StaffRequiredMixin + explicit permission_required.

Result lifecycle:
  DRAFT → SUBMITTED  (add_result or change_result)
  SUBMITTED → APPROVED  (approve_result)
  APPROVED → PUBLISHED  (publish_result)
  Any non-PUBLISHED → DRAFT  (change_result — reset)
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.mixins import StaffRequiredMixin
from apps.core.audit import audit_log
from apps.core.models import AuditAction
from apps.courses.models import Course, CourseUnit
from apps.enrollments.models import AcademicPeriod, Enrollment, EnrollmentStatus

from .forms import ResultContextForm, BulkScoreForm, ResultStatusForm
from .models import Result, ResultStatus
from .services import create_result, transition_result, bulk_enter_results


class ResultListView(StaffRequiredMixin, View):
    permission_required = 'results.view_result'

    def get(self, request):
        qs = Result.objects.select_related(
            'enrollment__student__user',
            'enrollment__course',
            'enrollment__academic_period',
            'course_unit',
            'entered_by',
        ).order_by('-created_at')

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(enrollment__student__admission_number__icontains=q)
                | Q(enrollment__student__user__first_name__icontains=q)
                | Q(enrollment__student__user__last_name__icontains=q)
                | Q(course_unit__code__icontains=q)
                | Q(course_unit__name__icontains=q)
            )

        status_filter = request.GET.get('status', '')
        if status_filter:
            qs = qs.filter(status=status_filter)

        course_filter = request.GET.get('course', '')
        if course_filter:
            qs = qs.filter(enrollment__course_id=course_filter)

        period_filter = request.GET.get('period', '')
        if period_filter:
            qs = qs.filter(enrollment__academic_period_id=period_filter)

        paginator = Paginator(qs, 30)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        # Status summary counts
        counts = {s: Result.objects.filter(status=s).count() for s in ResultStatus.values}

        return render(request, 'staff/results/list.html', {
            'page_title': 'Results',
            'active_section': 'results',
            'page_obj': page_obj,
            'q': q,
            'status_filter': status_filter,
            'course_filter': course_filter,
            'period_filter': period_filter,
            'status_choices': ResultStatus.choices,
            'courses': Course.objects.filter(is_active=True).order_by('name'),
            'periods': AcademicPeriod.objects.order_by('-start_date'),
            'counts': counts,
            'total': qs.count(),
            'can_enter': request.user.has_perm('results.add_result'),
        })


class ResultDetailView(StaffRequiredMixin, View):
    permission_required = 'results.view_result'

    def get(self, request, pk):
        result = get_object_or_404(
            Result.objects.select_related(
                'enrollment__student__user',
                'enrollment__course',
                'enrollment__academic_period',
                'course_unit',
                'entered_by',
                'approved_by',
            ),
            pk=pk,
        )
        return render(request, 'staff/results/detail.html', {
            'page_title': f'Result — {result.course_unit.code}',
            'active_section': 'results',
            'result': result,
            'ResultStatus': ResultStatus,
            'can_change': request.user.has_perm('results.change_result'),
            'can_approve': request.user.has_perm('results.approve_result'),
            'can_publish': request.user.has_perm('results.publish_result'),
            'status_form': ResultStatusForm(),
        })


class ResultStatusChangeView(StaffRequiredMixin, View):
    """Handle SUBMITTED / APPROVED / PUBLISHED / DRAFT transitions from detail page."""
    permission_required = 'results.change_result'

    def post(self, request, pk):
        result = get_object_or_404(Result, pk=pk)

        new_status = request.POST.get('new_status', '')
        valid = {'SUBMITTED', 'APPROVED', 'PUBLISHED', 'DRAFT'}
        if new_status not in valid:
            messages.error(request, 'Invalid status transition.')
            return redirect('staff:result_detail', pk=pk)

        # Extra permission guards
        if new_status == 'APPROVED' and not request.user.has_perm('results.approve_result'):
            messages.error(request, 'You do not have permission to approve results.')
            return redirect('staff:result_detail', pk=pk)
        if new_status == 'PUBLISHED' and not request.user.has_perm('results.publish_result'):
            messages.error(request, 'You do not have permission to publish results.')
            return redirect('staff:result_detail', pk=pk)

        try:
            transition_result(result=result, new_status=new_status, actor=request.user, request=request)
            messages.success(request, f'Result status updated to {result.get_status_display()}.')
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect('staff:result_detail', pk=pk)


class ResultEnterView(StaffRequiredMixin, View):
    """
    Bulk result entry:
    Step 1 (GET / POST context form): select course, unit, period.
    Step 2 (POST scores form): submit scores for all enrolled students.
    """
    permission_required = 'results.add_result'

    def get(self, request):
        context_form = ResultContextForm()
        return render(request, 'staff/results/enter.html', {
            'page_title': 'Enter Results',
            'active_section': 'results',
            'context_form': context_form,
            'step': 1,
        })

    def post(self, request):
        # Determine which step we're on
        if 'load_students' in request.POST:
            return self._load_students(request)
        return self._save_scores(request)

    def _load_students(self, request):
        """Step 1 submitted: validate context and show score entry table."""
        context_form = ResultContextForm(request.POST)
        if not context_form.is_valid():
            return render(request, 'staff/results/enter.html', {
                'page_title': 'Enter Results',
                'active_section': 'results',
                'context_form': context_form,
                'step': 1,
            })

        course = context_form.cleaned_data['course']
        unit = context_form.cleaned_data['course_unit']
        period = context_form.cleaned_data['academic_period']

        enrollments = Enrollment.objects.filter(
            course=course,
            academic_period=period,
            status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING],
        ).select_related('student__user').order_by(
            'student__user__last_name', 'student__user__first_name'
        )

        # Pre-populate with existing DRAFT results
        existing = {
            r.enrollment_id: r
            for r in Result.objects.filter(
                enrollment__in=enrollments, course_unit=unit
            )
        }

        rows = []
        for e in enrollments:
            existing_result = existing.get(e.pk)
            initial = {}
            if existing_result:
                initial = {
                    'score_cat': existing_result.score_cat,
                    'score_exam': existing_result.score_exam,
                }
            rows.append({
                'enrollment': e,
                'form': BulkScoreForm(initial=initial, prefix=str(e.pk)),
                'existing_result': existing_result,
            })

        return render(request, 'staff/results/enter.html', {
            'page_title': 'Enter Results',
            'active_section': 'results',
            'context_form': context_form,
            'course': course,
            'unit': unit,
            'period': period,
            'rows': rows,
            'step': 2,
        })

    def _save_scores(self, request):
        """Step 2 submitted: save scores for each enrollment row."""
        course_id = request.POST.get('course_id')
        unit_id = request.POST.get('unit_id')
        period_id = request.POST.get('period_id')

        try:
            course = Course.objects.get(pk=course_id)
            unit = CourseUnit.objects.get(pk=unit_id, course=course)
            period = AcademicPeriod.objects.get(pk=period_id)
        except (Course.DoesNotExist, CourseUnit.DoesNotExist, AcademicPeriod.DoesNotExist):
            messages.error(request, 'Invalid context. Please start again.')
            return redirect('staff:results_enter')

        enrollments = Enrollment.objects.filter(
            course=course,
            academic_period=period,
            status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING],
        )

        scores_map = {}
        for e in enrollments:
            form = BulkScoreForm(request.POST, prefix=str(e.pk))
            if form.is_valid():
                scores_map[e.pk] = {
                    'score_cat': form.cleaned_data.get('score_cat'),
                    'score_exam': form.cleaned_data.get('score_exam'),
                }

        bulk_enter_results(
            enrollment_ids=[e.pk for e in enrollments],
            course_unit=unit,
            scores_map=scores_map,
            entered_by=request.user,
            request=request,
        )

        messages.success(
            request,
            f'Results saved for {unit.code} — {period.name}.',
        )
        return redirect('staff:results')
