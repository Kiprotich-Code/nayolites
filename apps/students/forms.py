"""
Forms for the Student domain (staff management side).
"""

from django import forms
from django.contrib.auth import get_user_model

from apps.accounts.models import AccountStatus
from .models import StudentProfile, StudentStatus

User = get_user_model()


class StudentCreateForm(forms.Form):
    """
    Two-part form: creates a User account and a StudentProfile together.
    Used by staff to create a new student record.
    """
    # ---- User fields ----
    email = forms.EmailField(label='Email address')
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=20, required=False)

    # ---- Student profile fields ----
    admission_number = forms.CharField(
        max_length=50,
        help_text='Unique institutional identifier, e.g. NCC/2026/0001',
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    gender = forms.ChoiceField(
        choices=[('', '— Select —')] + StudentProfile.GENDER_CHOICES,
        required=False,
    )
    county = forms.CharField(max_length=100, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    emergency_contact_name = forms.CharField(max_length=200, required=False)
    emergency_contact_phone = forms.CharField(max_length=20, required=False)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_admission_number(self):
        number = self.cleaned_data.get('admission_number', '').strip()
        if StudentProfile.objects.filter(admission_number__iexact=number).exists():
            raise forms.ValidationError(
                f'Admission number "{number}" is already in use.'
            )
        return number


class StudentEditForm(forms.ModelForm):
    """Edit an existing StudentProfile's non-identity fields."""

    class Meta:
        model = StudentProfile
        fields = [
            'date_of_birth', 'gender', 'county', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    # ---- User fields injected separately ----
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=20, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            user = self.instance.user
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['phone'].initial = user.phone


class StudentStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=StudentStatus.choices,
        label='New Status',
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        label='Reason / notes (optional)',
    )
