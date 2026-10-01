"""
Forms for authentication and user management in the Nayolites platform.

Requirements: 12.1, 12.3, 12.4, 16.3
"""

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from .models import AccountStatus, StaffProfile, User


# ---------------------------------------------------------------------------
# Staff account creation
# ---------------------------------------------------------------------------

class StaffCreateForm(forms.Form):
    """
    Form for administrators to create a new staff account.
    Validates duplicate email (Req 12.3) and duplicate staff_number (Req 12.4)
    at the form level before any database write.
    """

    first_name = forms.CharField(max_length=150, label='First Name')
    last_name = forms.CharField(max_length=150, label='Last Name')
    email = forms.EmailField(label='Email Address')
    phone = forms.CharField(max_length=20, required=False, label='Phone')
    staff_number = forms.CharField(max_length=50, label='Staff Number')
    job_title = forms.CharField(max_length=150, label='Job Title')
    department = forms.CharField(max_length=150, label='Department')
    initial_password = forms.CharField(
        widget=forms.PasswordInput,
        label='Initial Password',
        help_text='Staff will be required to change this on first login.',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label='Confirm Password',
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Assign Groups',
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                'A user with this email address already exists.'
            )
        return email

    def clean_staff_number(self):
        staff_number = self.cleaned_data['staff_number']
        if StaffProfile.objects.filter(staff_number=staff_number).exists():
            raise ValidationError(
                'A staff member with this staff number already exists.'
            )
        return staff_number

    def clean_initial_password(self):
        password = self.cleaned_data.get('initial_password')
        if password:
            password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get('initial_password')
        pw2 = cleaned_data.get('confirm_password')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data


# ---------------------------------------------------------------------------
# Admin-initiated password set
# ---------------------------------------------------------------------------

class AdminPasswordSetForm(forms.Form):
    """
    Form for administrators to set a new password for any user.
    Runs all four configured password validators.
    """

    new_password = forms.CharField(
        widget=forms.PasswordInput,
        label='New Password',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label='Confirm New Password',
    )

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password:
            password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get('new_password')
        pw2 = cleaned_data.get('confirm_password')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data


# ---------------------------------------------------------------------------
# Account status change
# ---------------------------------------------------------------------------

class AccountStatusForm(forms.Form):
    """
    Form for administrators to change a user's account status.
    """

    account_status = forms.ChoiceField(
        choices=AccountStatus.choices,
        label='Account Status',
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='Reason (optional)',
        help_text='Explain why the status is being changed.',
    )


# ---------------------------------------------------------------------------
# Group assignment
# ---------------------------------------------------------------------------

class GroupAssignmentForm(forms.Form):
    """
    Form for adding or removing a user from a group.
    """

    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label='Group',
    )
    action = forms.ChoiceField(
        choices=[('add', 'Add to group'), ('remove', 'Remove from group')],
        label='Action',
    )


# ---------------------------------------------------------------------------
# Student self-registration
# ---------------------------------------------------------------------------

class StudentSignupForm(forms.Form):
    """
    Self-registration form for new students.
    Creates a User account and minimal StudentProfile.
    The StudentProfile will be completed by the Registrar later.
    """
    first_name = forms.CharField(max_length=150, label='First Name')
    last_name = forms.CharField(max_length=150, label='Last Name')
    email = forms.EmailField(label='Email Address')
    phone = forms.CharField(max_length=20, required=False, label='Phone (optional)')
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Password',
        help_text='At least 8 characters.',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label='Confirm Password',
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            from django.contrib.auth import password_validation as pv
            pv.validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get('password')
        pw2 = cleaned_data.get('confirm_password')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data
