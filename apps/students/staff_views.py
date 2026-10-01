"""
Staff portal views for Student management.
All views use StaffRequiredMixin + explicit permission_required.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.mixins import StaffRequiredMixin
from apps.core.audit import audit_log
from apps.core.models import AuditAction
from apps.enrollments.services import create_student, change_student_status

from .forms import StudentCreateForm, StudentEditForm, StudentStatusForm
from .models import StudentProfile, StudentStatus

User = get_user_model()


class StudentListView(StaffRequiredMixin, View):
    permission_required = 'students.view_studentprofile'

    def get(self, request):
        from apps.courses.models import Course
        from apps.enrollments.models import AcademicPeriod, EnrollmentStatus

        qs = StudentProfile.objects.select_related('user').order_by(
            'user__last_name', 'user__first_name'
        )

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(admission_number__icontains=q)
                | Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q)
            )

        status_filter = request.GET.get('status', '')
        if status_filter:
            qs = qs.filter(status=status_filter)

        course_filter = request.GET.get('course', '')
        if course_filter:
            qs = qs.filter(
                enrollments__course_id=course_filter,
                enrollments__status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING],
            ).distinct()

        period_filter = request.GET.get('period', '')
        if period_filter:
            qs = qs.filter(
                enrollments__academic_period_id=period_filter,
            ).distinct()

        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'staff/students/list.html', {
            'page_title': 'Students',
            'active_section': 'students',
            'page_obj': page_obj,
            'q': q,
            'status_filter': status_filter,
            'course_filter': course_filter,
            'period_filter': period_filter,
            'status_choices': StudentStatus.choices,
            'courses': Course.objects.filter(is_active=True).order_by('name'),
            'periods': AcademicPeriod.objects.filter(is_active=True).order_by('-start_date'),
            'total': qs.count(),
            'can_add': request.user.has_perm('students.add_studentprofile'),
        })


class StudentCreateView(StaffRequiredMixin, View):
    permission_required = 'students.add_studentprofile'

    def get(self, request):
        return render(request, 'staff/students/form.html', {
            'page_title': 'Add Student',
            'active_section': 'students',
            'form': StudentCreateForm(),
            'action': 'create',
        })

    def post(self, request):
        form = StudentCreateForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            with transaction.atomic():
                user = User.objects.create_user(
                    email=d['email'],
                    password=None,
                    first_name=d['first_name'],
                    last_name=d['last_name'],
                    phone=d.get('phone', ''),
                    force_password_change=True,
                )
                profile = create_student(
                    user=user,
                    admission_number=d['admission_number'],
                    created_by=request.user,
                    request=request,
                    date_of_birth=d.get('date_of_birth'),
                    gender=d.get('gender', ''),
                    county=d.get('county', ''),
                    address=d.get('address', ''),
                    emergency_contact_name=d.get('emergency_contact_name', ''),
                    emergency_contact_phone=d.get('emergency_contact_phone', ''),
                )
            messages.success(
                request,
                f'Student record created for {profile.user.get_full_name()} '
                f'({profile.admission_number}).',
            )
            return redirect('staff:student_detail', pk=profile.pk)

        return render(request, 'staff/students/form.html', {
            'page_title': 'Add Student',
            'active_section': 'students',
            'form': form,
            'action': 'create',
        })


class StudentDetailView(StaffRequiredMixin, View):
    permission_required = 'students.view_studentprofile'

    def get(self, request, pk):
        student = get_object_or_404(
            StudentProfile.objects.select_related('user'),
            pk=pk,
        )
        enrollments = student.enrollments.select_related(
            'course', 'academic_period'
        ).order_by('-enrolled_at')

        return render(request, 'staff/students/detail.html', {
            'page_title': student.user.get_full_name(),
            'active_section': 'students',
            'student': student,
            'enrollments': enrollments,
            'can_edit': request.user.has_perm('students.change_studentprofile'),
            'can_change_status': request.user.has_perm('students.deactivate_student'),
            'can_enroll': request.user.has_perm('enrollments.add_enrollment'),
            'StudentStatus': StudentStatus,
        })


class StudentEditView(StaffRequiredMixin, View):
    permission_required = 'students.change_studentprofile'

    def get(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related('user'), pk=pk)
        return render(request, 'staff/students/form.html', {
            'page_title': f'Edit: {student.user.get_full_name()}',
            'active_section': 'students',
            'form': StudentEditForm(instance=student),
            'student': student,
            'action': 'edit',
        })

    def post(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related('user'), pk=pk)
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            with transaction.atomic():
                # Update the linked User fields
                user = student.user
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.phone = form.cleaned_data.get('phone', '')
                user.save(update_fields=['first_name', 'last_name', 'phone'])
                form.save()
            audit_log(
                actor=request.user,
                action=AuditAction.STUDENT_UPDATED,
                obj=student,
                description=f'Student record updated: {student}',
                request=request,
            )
            messages.success(request, 'Student record updated.')
            return redirect('staff:student_detail', pk=student.pk)

        return render(request, 'staff/students/form.html', {
            'page_title': f'Edit: {student.user.get_full_name()}',
            'active_section': 'students',
            'form': form,
            'student': student,
            'action': 'edit',
        })


class StudentStatusChangeView(StaffRequiredMixin, View):
    permission_required = 'students.deactivate_student'

    def get(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related('user'), pk=pk)
        form = StudentStatusForm(initial={'status': student.status})
        return render(request, 'staff/students/status_change.html', {
            'page_title': f'Change Status: {student.user.get_full_name()}',
            'active_section': 'students',
            'student': student,
            'form': form,
        })

    def post(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related('user'), pk=pk)
        form = StudentStatusForm(request.POST)
        if form.is_valid():
            change_student_status(
                student=student,
                new_status=form.cleaned_data['status'],
                changed_by=request.user,
                notes=form.cleaned_data.get('notes', ''),
                request=request,
            )
            messages.success(
                request,
                f'Student status updated to {student.get_status_display()}.',
            )
            return redirect('staff:student_detail', pk=student.pk)
        return render(request, 'staff/students/status_change.html', {
            'page_title': f'Change Status: {student.user.get_full_name()}',
            'active_section': 'students',
            'student': student,
            'form': form,
        })
