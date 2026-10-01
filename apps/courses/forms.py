"""
Forms for the Course and CourseUnit domain.
"""

from django import forms
from .models import Course, CourseUnit


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['code', 'name', 'description', 'duration', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'code': 'Short unique identifier, e.g. DCS, DBM. Cannot be changed after courses are enrolled.',
            'duration': 'Human-readable, e.g. "2 Years" or "1 Year".',
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        qs = Course.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'A course with code "{code}" already exists.')
        return code


class CourseUnitForm(forms.ModelForm):
    class Meta:
        model = CourseUnit
        fields = ['code', 'name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._course = course

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if self._course:
            qs = CourseUnit.objects.filter(course=self._course, code__iexact=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'A unit with code "{code}" already exists in this course.'
                )
        return code
