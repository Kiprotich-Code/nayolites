"""
Django forms for the Finance module.

All server-side validation. Frontend validation is secondary.
"""
from decimal import Decimal

from django import forms
from django.conf import settings
from django.forms import inlineformset_factory

from apps.finance.models import (
    FeeItem, FeeStructure, Invoice, InvoiceItem,
    Payment, PaymentAllocation, PaymentMethod,
)


# ─────────────────────────────────────────────────────────────
# Fee Structure forms
# ─────────────────────────────────────────────────────────────

class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ['course', 'academic_period', 'name', 'currency', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'academic_period': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'academic_period': 'Academic Period (leave blank for all periods)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_period'].required = False
        self.fields['academic_period'].empty_label = '— All periods —'


FeeItemFormSet = inlineformset_factory(
    FeeStructure,
    FeeItem,
    fields=['name', 'amount', 'order'],
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        'order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
    },
)


# ─────────────────────────────────────────────────────────────
# Invoice forms
# ─────────────────────────────────────────────────────────────

class InvoiceCreateForm(forms.Form):
    """
    Select enrollment and fee structure to create an invoice.
    Validation that fee_structure belongs to the enrollment's course
    is done in the view/service layer.
    """
    enrollment = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Enrollment',
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Fee Structure',
    )
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Due Date (optional)',
    )

    def __init__(self, *args, **kwargs):
        from apps.enrollments.models import Enrollment
        super().__init__(*args, **kwargs)
        self.fields['enrollment'].queryset = (
            Enrollment.objects.select_related('student__user', 'course', 'academic_period')
            .order_by('student__admission_number')
        )


class InvoiceDueDateForm(forms.ModelForm):
    """Edit due_date and notes on an issued invoice."""
    class Meta:
        model = Invoice
        fields = ['due_date', 'notes']
        widgets = {
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InvoiceVoidForm(forms.Form):
    """Capture a mandatory void reason before voiding an invoice."""
    void_reason = forms.CharField(
        required=True,
        min_length=5,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Void Reason',
        help_text='Minimum 5 characters. This is a permanent action.',
    )

    def clean_void_reason(self):
        reason = self.cleaned_data.get('void_reason', '').strip()
        if not reason:
            raise forms.ValidationError('A void reason is required.')
        return reason


# ─────────────────────────────────────────────────────────────
# Payment forms
# ─────────────────────────────────────────────────────────────

class ManualPaymentForm(forms.Form):
    """Record a manual payment against an enrollment."""
    enrollment = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'min': '1',
        }),
    )
    method = forms.ChoiceField(
        choices=PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    payer_name = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Payer Name (if different from student)',
    )
    payer_phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def __init__(self, *args, **kwargs):
        from apps.enrollments.models import Enrollment
        super().__init__(*args, **kwargs)
        self.fields['enrollment'].queryset = (
            Enrollment.objects.select_related('student__user', 'course', 'academic_period')
            .order_by('student__admission_number')
        )


class PaymentAllocateForm(forms.Form):
    """Manually allocate an amount from a payment to an invoice."""
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.exclude(status__in=['VOID', 'PAID']),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Invoice',
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'min': '0.01',
        }),
    )

    def __init__(self, *args, payment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment = payment
        if payment:
            # Only show invoices belonging to the same enrollment
            self.fields['invoice'].queryset = Invoice.objects.filter(
                enrollment=payment.enrollment,
            ).exclude(status__in=['VOID', 'PAID'])


# ─────────────────────────────────────────────────────────────
# Student payment initiation form
# ─────────────────────────────────────────────────────────────

class PaymentInitiateForm(forms.Form):
    """
    Student-facing form to initiate a PayHero STK push.
    Validates amount against enrollment outstanding and minimum floor.
    """
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0712345678',
        }),
        label='M-Pesa Phone Number',
        help_text='The phone number to receive the STK push.',
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01',
        }),
    )

    def __init__(self, *args, enrollment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.enrollment = enrollment

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            return amount

        floor = getattr(settings, 'FINANCE_MINIMUM_PAYMENT_FLOOR', Decimal('500.00'))

        if amount < floor:
            raise forms.ValidationError(
                f'Minimum payment is {floor} KES.'
            )

        if self.enrollment:
            from apps.finance.services import get_enrollment_outstanding
            outstanding = get_enrollment_outstanding(self.enrollment)
            if amount > outstanding:
                raise forms.ValidationError(
                    f'Amount ({amount}) exceeds outstanding balance ({outstanding} KES).'
                )

        return amount
