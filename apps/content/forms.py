"""
Forms for the CourseContent domain (staff side).
"""

from django import forms

from apps.courses.models import Course, CourseUnit
from .models import CourseContent, ContentType, ContentVisibility


class CourseContentForm(forms.ModelForm):
    class Meta:
        model = CourseContent
        fields = [
            'course', 'course_unit', 'title', 'description',
            'content_type', 'file', 'url', 'visibility',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit course_unit choices to units of the selected course
        self.fields['course'].queryset = Course.objects.filter(
            is_active=True
        ).order_by('name')

        if self.instance.pk and self.instance.course_id:
            self.fields['course_unit'].queryset = CourseUnit.objects.filter(
                course=self.instance.course, is_active=True
            ).order_by('code')
        elif 'course' in self.data:
            try:
                course_id = int(self.data['course'])
                self.fields['course_unit'].queryset = CourseUnit.objects.filter(
                    course_id=course_id, is_active=True
                ).order_by('code')
            except (ValueError, TypeError):
                self.fields['course_unit'].queryset = CourseUnit.objects.none()
        else:
            self.fields['course_unit'].queryset = CourseUnit.objects.none()

        self.fields['course_unit'].required = False
        self.fields['file'].required = False
        self.fields['url'].required = False

    def clean(self):
        cleaned = super().clean()
        file_ = cleaned.get('file')
        url = cleaned.get('url')
        if file_ and url:
            self.add_error('url', 'Provide either a file upload or a URL, not both.')
        course = cleaned.get('course')
        unit = cleaned.get('course_unit')
        if course and unit and unit.course != course:
            self.add_error('course_unit', 'This unit does not belong to the selected course.')
        return cleaned
