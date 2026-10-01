"""
Forms for the Results domain (staff side).
"""

from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.courses.models import Course, CourseUnit
from apps.enrollments.models import AcademicPeriod, Enrollment, EnrollmentStatus


class ResultContextForm(forms.Form):
    """
    Step 1: select course, unit, and academic period before entering scores.
    Used to populate the bulk entry table.
    """
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True).order_by('name'),
        label='Course',
    )
    course_unit = forms.ModelChoiceField(
        queryset=CourseUnit.objects.none(),
        label='Course Unit',
    )
    academic_period = forms.ModelChoiceField(
        queryset=AcademicPeriod.objects.order_by('-start_date'),
        label='Academic Period',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If a course was posted, populate the unit queryset
        if 'course' in self.data:
            try:
                course_id = int(self.data.get('course'))
                self.fields['course_unit'].queryset = (
                    CourseUnit.objects.filter(course_id=course_id, is_active=True)
                    .order_by('code')
                )
            except (ValueError, TypeError):
                pass


class BulkScoreForm(forms.Form):
    """
    Score entry for a single enrollment row in the bulk entry table.
    Instantiated dynamically — one per enrollment in the context queryset.
    """
    score_cat = forms.DecimalField(
        max_digits=5, decimal_places=2,
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        widget=forms.NumberInput(attrs={'min': 0, 'max': 40, 'step': '0.5'}),
        label='CAT (0–40)',
    )
    score_exam = forms.DecimalField(
        max_digits=5, decimal_places=2,
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        widget=forms.NumberInput(attrs={'min': 0, 'max': 60, 'step': '0.5'}),
        label='Exam (0–60)',
    )


class ResultStatusForm(forms.Form):
    """Change a single result's status."""
    NEW_STATUS_CHOICES = [
        ('SUBMITTED', 'Submit for Review'),
        ('APPROVED', 'Approve'),
        ('PUBLISHED', 'Publish'),
        ('DRAFT', 'Reset to Draft'),
    ]
    new_status = forms.ChoiceField(choices=NEW_STATUS_CHOICES, label='Action')
