"""
Forms for AcademicPeriod and Enrollment staff management.
"""

from django import forms
from django.core.exceptions import ValidationError

from apps.students.models import StudentProfile
from .models import AcademicPeriod, Enrollment, EnrollmentStatus


class AcademicPeriodForm(forms.ModelForm):
    class Meta:
        model = AcademicPeriod
        fields = ['name', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and start >= end:
            self.add_error('end_date', 'End date must be after start date.')
        return cleaned


class EnrollmentCreateForm(forms.Form):
    """
    Form for staff to enroll a student.
    student is pre-filled from context in some flows but also selectable here.
    """
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.select_related('user').order_by(
            'user__last_name', 'user__first_name'
        ),
        label='Student',
        help_text='Only active students are shown.',
    )
    course = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        label='Course',
    )
    academic_period = forms.ModelChoiceField(
        queryset=AcademicPeriod.objects.filter(is_active=True).order_by('-start_date'),
        label='Academic Period',
    )
    initial_status = forms.ChoiceField(
        choices=[
            (EnrollmentStatus.PENDING, 'Pending — requires approval'),
            (EnrollmentStatus.ACTIVE, 'Active — enroll immediately'),
        ],
        initial=EnrollmentStatus.PENDING,
        label='Initial Status',
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        label='Notes (optional)',
    )

    def __init__(self, *args, **kwargs):
        from apps.courses.models import Course
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = StudentProfile.objects.filter(
            status='ACTIVE'
        ).select_related('user').order_by('user__last_name', 'user__first_name')
        self.fields['course'].queryset = Course.objects.filter(
            is_active=True
        ).order_by('name')


class EnrollmentStatusForm(forms.Form):
    """Change an enrollment's status."""
    new_status = forms.ChoiceField(
        choices=EnrollmentStatus.choices,
        label='New Status',
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        label='Reason / notes (optional)',
    )
