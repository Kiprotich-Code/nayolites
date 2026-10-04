"""
Student portal views for the Finance module.

Ownership enforced: every queryset filters by enrollment__student=request.user.studentprofile.
Accessing another student's financial data returns HTTP 404, not 403.
Uses @login_required decorator (students are not staff, so StaffRequiredMixin is not used).
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from apps.enrollments.models import Enrollment
from apps.finance.forms import PaymentInitiateForm
from apps.finance.models import Invoice, InvoiceStatus, Payment, PaymentStatus, Receipt
from apps.finance.services import (
    PayHeroError,
    get_enrollment_outstanding,
    get_invoice_balance,
    get_student_financial_summary,
    initiate_payhero_payment,
)


def _get_student_profile(request):
    """Return the studentprofile for the logged-in user, or None."""
    try:
        return request.user.studentprofile
    except Exception:
        return None


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class StudentFinanceSummaryView(View):
    """Financial overview for the student — own data only. student:finance"""

    def get(self, request):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        summary = get_student_financial_summary(profile)
        return render(request, 'student/finance/summary.html', {
            'page_title': 'My Finances',
            'summary': summary,
        })


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class StudentInvoiceListView(View):
    """List all invoices for the student. student:my_invoices"""

    def get(self, request):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        invoices = (
            Invoice.objects
            .filter(enrollment__student=profile)
            .select_related('enrollment__course', 'enrollment__academic_period')
            .order_by('-created_at')
        )
        return render(request, 'student/finance/invoice_list.html', {
            'page_title': 'My Invoices',
            'invoices': invoices,
        })


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class StudentInvoiceDetailView(View):
    """Invoice detail — ownership enforced via enrollment__student filter. student:my_invoice_detail"""

    def get(self, request, pk):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        invoice = get_object_or_404(
            Invoice.objects
            .select_related('enrollment__course', 'enrollment__academic_period')
            .prefetch_related('items', 'allocations__payment'),
            pk=pk,
            enrollment__student=profile,
        )
        balance = get_invoice_balance(invoice)
        return render(request, 'student/finance/invoice_detail.html', {
            'page_title': f'Invoice {invoice.invoice_number}',
            'invoice': invoice,
            'balance': balance,
        })


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class StudentPaymentListView(View):
    """List all payments for the student. student:my_payments"""

    def get(self, request):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        payments = (
            Payment.objects
            .filter(enrollment__student=profile)
            .select_related('enrollment__course')
            .order_by('-created_at')
        )
        return render(request, 'student/finance/payment_list.html', {
            'page_title': 'My Payments',
            'payments': payments,
        })


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class StudentReceiptListView(View):
    """List all receipts for the student. student:my_receipts"""

    def get(self, request):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        receipts = (
            Receipt.objects
            .filter(payment__enrollment__student=profile)
            .select_related('payment__enrollment__course')
            .order_by('-issued_at')
        )
        return render(request, 'student/finance/receipt_list.html', {
            'page_title': 'My Receipts',
            'receipts': receipts,
        })


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class StudentReceiptDetailView(View):
    """Receipt detail — ownership enforced. student:my_receipt_detail"""

    def get(self, request, pk):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        receipt = get_object_or_404(
            Receipt.objects
            .select_related(
                'payment__enrollment__student__user',
                'payment__enrollment__course',
                'payment__enrollment__academic_period',
                'payment__recorded_by',
            )
            .prefetch_related('payment__allocations__invoice'),
            pk=pk,
            payment__enrollment__student=profile,
        )
        return render(request, 'student/finance/receipt_detail.html', {
            'page_title': f'Receipt {receipt.receipt_number}',
            'receipt': receipt,
        })


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class StudentStatementView(View):
    """Full financial statement for the student. student:my_statement"""

    def get(self, request):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        summary = get_student_financial_summary(profile)
        return render(request, 'student/finance/statement.html', {
            'page_title': 'My Financial Statement',
            'summary': summary,
        })


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class StudentPaymentInitiateView(View):
    """Initiate PayHero STK push for an enrollment. student:pay"""

    def get(self, request, enrollment_pk):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, student=profile)
        outstanding = get_enrollment_outstanding(enrollment)
        form = PaymentInitiateForm(enrollment=enrollment)
        return render(request, 'student/finance/pay.html', {
            'page_title': 'Make Payment',
            'enrollment': enrollment,
            'outstanding': outstanding,
            'form': form,
        })

    def post(self, request, enrollment_pk):
        profile = _get_student_profile(request)
        if not profile:
            return redirect('student:dashboard')
        enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, student=profile)
        form = PaymentInitiateForm(request.POST, enrollment=enrollment)
        if form.is_valid():
            try:
                payment = initiate_payhero_payment(
                    enrollment=enrollment,
                    amount=form.cleaned_data['amount'],
                    phone=form.cleaned_data['phone'],
                    initiated_by=request.user,
                )
                return render(request, 'student/finance/pay.html', {
                    'page_title': 'Payment Initiated',
                    'enrollment': enrollment,
                    'payment': payment,
                    'initiated': True,
                })
            except PayHeroError:
                messages.error(request, 'Payment initiation failed. Please try again or contact the finance office.')
        outstanding = get_enrollment_outstanding(enrollment)
        return render(request, 'student/finance/pay.html', {
            'page_title': 'Make Payment',
            'enrollment': enrollment,
            'outstanding': outstanding,
            'form': form,
        })
