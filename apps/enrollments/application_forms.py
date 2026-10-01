"""
Public course application form.

Security notes:
- Only collects applicant-provided information.
- course and preferred_period are passed as URL/view context, not hidden form fields.
- Status is never set by form input — always defaults to SUBMITTED on the model.
- reference_number is auto-generated server-side.
- CSRF is enforced by Django's CsrfViewMiddleware on all POST requests.
"""

from django import forms


class CourseApplicationForm(forms.Form):
    first_name = forms.CharField(max_length=150, label='First Name')
    last_name = forms.CharField(max_length=150, label='Last Name')
    email = forms.EmailField(label='Email Address')
    phone = forms.CharField(
        max_length=20,
        required=False,
        label='Phone Number (optional)',
    )
    preferred_period = forms.IntegerField(
        required=False,
        widget=forms.Select(),  # choices injected in __init__
        label='Preferred Intake (optional)',
    )
    message = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Additional Notes (optional)',
        help_text='Anything you would like us to know about your application.',
    )

    def __init__(self, *args, active_periods=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [('', '— No preference —')]
        if active_periods:
            choices += [(p.pk, p.name) for p in active_periods]
        self.fields['preferred_period'].widget = forms.Select(choices=choices)
