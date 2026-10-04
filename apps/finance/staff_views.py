"""
Staff portal views for the Finance & Payments module.

All views extend StaffRequiredMixin and declare permission_required.
POST handlers call service-layer functions and catch ValueError to
display user-facing error messages via django.contrib.messages.

Requirements: 9.1–9.8, 10.1–10.5, 11.1–11.7, 12.1–12.5, 13.1–13.3
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.accounts.mixins import StaffRequiredMixin
from apps.core.audit import audit_log
from apps.core.models import AuditAction
from apps.finance.forms import (
    FeeItemFormSet,
    FeeStructureForm,
    InvoiceCreateForm,
    InvoiceDueDateForm,
    InvoiceVoidForm,
    ManualPaymentForm,
    PaymentAllocateForm,
)
from apps.finance.models import (
    FeeStructure,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Payment,
    PaymentAllocation,
    PaymentStatus,
    Receipt,
)
from apps.finance.services import (
    allocate_payment,
    create_invoice,
    get_student_financial_summary,
    issue_invoice,
    mark_overdue_invoices,
    record_manual_payment,
    void_invoice,
)
from apps.students.models import StudentProfile


# ─────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────

class FinanceDashboardView(StaffRequiredMixin, View):
    """
    Finance summary dashboard.

    Calls mark_overdue_invoices() on each load so overdue statuses are
    always current. Computes key financial aggregates and shows recent
    activity.

    Requirements: 9.1–9.8
    """
    permission_required = 'finance.view_invoice'
    template_name = 'staff/finance/dashboard.html'

    def get(self, request):
        mark_overdue_invoices()

        # Total billed: sum of all InvoiceItem amounts on non-VOID invoices
        total_billed = (
            InvoiceItem.objects.filter(
                invoice__status__in=[
                    InvoiceStatus.ISSUED,
                    InvoiceStatus.PARTIALLY_PAID,
                    InvoiceStatus.PAID,
                    InvoiceStatus.OVERDUE,
                    InvoiceStatus.DRAFT,
                ]
            ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
        )

        # Total collected: sum of allocations from SUCCESSFUL payments
        total_collected = (
            PaymentAllocation.objects.filter(
                payment__status=PaymentStatus.SUCCESSFUL
            ).aggregate(t=Sum('allocated_amount'))['t'] or Decimal('0.00')
        )

        outstanding = total_billed - total_collected

        recent_invoices = Invoice.objects.select_related(
            'enrollment__student__user',
        ).order_by('-created_at')[:5]

        recent_payments = Payment.objects.select_related(
            'enrollment__student__user',
        ).order_by('-created_at')[:5]

        pending_count = Payment.objects.filter(status=PaymentStatus.PENDING).count()

        # Successful payments where total allocated < payment.amount
        unallocated_count = 0
        for payment in Payment.objects.filter(status=PaymentStatus.SUCCESSFUL):
            allocated = (
                payment.allocations.aggregate(t=Sum('allocated_amount'))['t']
                or Decimal('0.00')
            )
            if allocated < payment.amount:
                unallocated_count += 1

        context = {
            'total_billed': total_billed,
            'total_collected': total_collected,
            'outstanding': outstanding,
            'recent_invoices': recent_invoices,
            'recent_payments': recent_payments,
            'pending_count': pending_count,
            'unallocated_count': unallocated_count,
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────
# Fee Structure views
# ─────────────────────────────────────────────────────────────

class FinanceFeeStructureListView(StaffRequiredMixin, ListView):
    """
    Paginated list of all fee structures with optional search.

    Requirements: 10.1, 10.5
    """
    permission_required = 'finance.view_feestructure'
    template_name = 'staff/finance/fee_structures/list.html'
    paginate_by = 25
    context_object_name = 'fee_structures'

    def get_queryset(self):
        qs = FeeStructure.objects.select_related(
            'course', 'academic_period'
        ).order_by('-created_at')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(course__name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class FinanceFeeStructureCreateView(StaffRequiredMixin, View):
    """
    Create a new FeeStructure with inline FeeItems.

    Requirements: 10.2, 10.5, 1.6
    """
    permission_required = 'finance.add_feestructure'
    template_name = 'staff/finance/fee_structures/create.html'

    def get(self, request):
        form = FeeStructureForm()
        formset = FeeItemFormSet()
        return render(request, self.template_name, {'form': form, 'formset': formset})

    def post(self, request):
        form = FeeStructureForm(request.POST)
        formset = FeeItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            fee_structure = form.save()
            formset.instance = fee_structure
            formset.save()
            audit_log(
                actor=request.user,
                action=AuditAction.FEE_STRUCTURE_CREATED,
                obj=fee_structure,
                description=f'Fee structure "{fee_structure.name}" created.',
                request=request,
            )
            messages.success(request, f'Fee structure "{fee_structure.name}" created successfully.')
            return redirect('staff:fee_structure_detail', pk=fee_structure.pk)
        return render(request, self.template_name, {'form': form, 'formset': formset})


class FinanceFeeStructureDetailView(StaffRequiredMixin, View):
    """
    Display a FeeStructure's details. POST toggles is_active (requires
    activate_feestructure permission).

    Requirements: 10.3, 10.5, 1.7
    """
    permission_required = 'finance.view_feestructure'
    template_name = 'staff/finance/fee_structures/detail.html'

    def get(self, request, pk):
        fee_structure = get_object_or_404(FeeStructure, pk=pk)
        return render(request, self.template_name, {'fee_structure': fee_structure})

    def post(self, request, pk):
        fee_structure = get_object_or_404(FeeStructure, pk=pk)
        if not request.user.has_perm('finance.activate_feestructure'):
            messages.error(request, 'You do not have permission to activate/deactivate fee structures.')
            return redirect('staff:fee_structure_detail', pk=pk)
        fee_structure.is_active = not fee_structure.is_active
        fee_structure.save(update_fields=['is_active', 'updated_at'])
        audit_log(
            actor=request.user,
            action=AuditAction.FEE_STRUCTURE_ACTIVATED,
            obj=fee_structure,
            description=(
                f'Fee structure "{fee_structure.name}" '
                f'{"activated" if fee_structure.is_active else "deactivated"}.'
            ),
            request=request,
        )
        status_word = 'activated' if fee_structure.is_active else 'deactivated'
        messages.success(request, f'Fee structure "{fee_structure.name}" {status_word}.')
        return redirect('staff:fee_structure_detail', pk=pk)


class FinanceFeeStructureEditView(StaffRequiredMixin, View):
    """
    Edit an existing FeeStructure and its FeeItems.

    Requirements: 10.4, 10.5, 1.6
    """
    permission_required = 'finance.change_feestructure'
    template_name = 'staff/finance/fee_structures/edit.html'

    def get(self, request, pk):
        fee_structure = get_object_or_404(FeeStructure, pk=pk)
        form = FeeStructureForm(instance=fee_structure)
        formset = FeeItemFormSet(instance=fee_structure)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'fee_structure': fee_structure,
        })

    def post(self, request, pk):
        fee_structure = get_object_or_404(FeeStructure, pk=pk)
        form = FeeStructureForm(request.POST, instance=fee_structure)
        formset = FeeItemFormSet(request.POST, instance=fee_structure)
        if form.is_valid() and formset.is_valid():
            fee_structure = form.save()
            formset.save()
            audit_log(
                actor=request.user,
                action=AuditAction.FEE_STRUCTURE_UPDATED,
                obj=fee_structure,
                description=f'Fee structure "{fee_structure.name}" updated.',
                request=request,
            )
            messages.success(request, f'Fee structure "{fee_structure.name}" updated successfully.')
            return redirect('staff:fee_structure_detail', pk=fee_structure.pk)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'fee_structure': fee_structure,
        })


# ─────────────────────────────────────────────────────────────
# Invoice views
# ─────────────────────────────────────────────────────────────

class InvoiceListView(StaffRequiredMixin, ListView):
    """
    Paginated invoice list with search and filters.

    Requirements: 11.1, 11.6
    """
    permission_required = 'finance.view_invoice'
    template_name = 'staff/finance/invoices/list.html'
    paginate_by = 25
    context_object_name = 'invoices'

    def get_queryset(self):
        qs = Invoice.objects.select_related(
            'enrollment__student__user',
            'enrollment__course',
            'enrollment__academic_period',
        ).order_by('-created_at')

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q)
                | Q(enrollment__student__user__first_name__icontains=q)
                | Q(enrollment__student__user__last_name__icontains=q)
                | Q(enrollment__student__admission_number__icontains=q)
            )

        status_filter = self.request.GET.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        course_id = self.request.GET.get('course_id', '').strip()
        if course_id:
            qs = qs.filter(enrollment__course_id=course_id)

        period_id = self.request.GET.get('period_id', '').strip()
        if period_id:
            qs = qs.filter(enrollment__academic_period_id=period_id)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['course_id'] = self.request.GET.get('course_id', '')
        ctx['period_id'] = self.request.GET.get('period_id', '')
        ctx['status_choices'] = InvoiceStatus.choices
        return ctx


class InvoiceCreateView(StaffRequiredMixin, View):
    """
    Create an invoice from an enrollment and fee structure.

    Requirements: 11.2, 11.6
    """
    permission_required = 'finance.add_invoice'
    template_name = 'staff/finance/invoices/create.html'

    def get(self, request):
        form = InvoiceCreateForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = InvoiceCreateForm(request.POST)
        if form.is_valid():
            enrollment = form.cleaned_data['enrollment']
            fee_structure = form.cleaned_data['fee_structure']
            due_date = form.cleaned_data.get('due_date')
            try:
                invoice = create_invoice(
                    enrollment=enrollment,
                    fee_structure=fee_structure,
                    created_by=request.user,
                    due_date=due_date,
                )
                messages.success(request, f'Invoice {invoice.invoice_number} created.')
                return redirect('staff:invoice_detail', pk=invoice.pk)
            except ValueError as exc:
                messages.error(request, str(exc))
        return render(request, self.template_name, {'form': form})


class InvoiceDetailView(StaffRequiredMixin, View):
    """
    Display invoice header, items, allocations, balance, and action flags.

    Requirements: 11.3, 11.6
    """
    permission_required = 'finance.view_invoice'
    template_name = 'staff/finance/invoices/detail.html'

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.select_related(
                'enrollment__student__user',
                'enrollment__course',
                'enrollment__academic_period',
                'created_by',
                'issued_by',
                'voided_by',
            ).prefetch_related('items', 'allocations__payment'),
            pk=pk,
        )
        from apps.finance.services import get_invoice_balance
        balance = get_invoice_balance(invoice)
        can_issue = invoice.status == InvoiceStatus.DRAFT
        can_void = invoice.status != InvoiceStatus.VOID
        can_edit = invoice.status != InvoiceStatus.VOID

        try:
            receipt = invoice.allocations.filter(
                payment__status=PaymentStatus.SUCCESSFUL
            ).first()
        except Exception:
            receipt = None

        context = {
            'invoice': invoice,
            'balance': balance,
            'can_issue': can_issue,
            'can_void': can_void,
            'can_edit': can_edit,
        }
        return render(request, self.template_name, context)


class InvoiceIssueView(StaffRequiredMixin, View):
    """
    POST-only view to transition a DRAFT invoice to ISSUED.

    Requirements: 11.4, 11.6
    """
    permission_required = 'finance.issue_invoice'

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            issue_invoice(invoice=invoice, issued_by=request.user)
            messages.success(request, f'Invoice {invoice.invoice_number} issued.')
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect('staff:invoice_detail', pk=pk)


class InvoiceVoidView(StaffRequiredMixin, View):
    """
    Void an invoice after capturing a mandatory void reason.

    Requirements: 11.5, 11.6, 11.7
    """
    permission_required = 'finance.void_invoice'
    template_name = 'staff/finance/invoices/void.html'

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceVoidForm()
        return render(request, self.template_name, {'invoice': invoice, 'form': form})

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceVoidForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['void_reason']
            try:
                void_invoice(invoice=invoice, voided_by=request.user, reason=reason)
                messages.success(request, f'Invoice {invoice.invoice_number} voided.')
                return redirect('staff:invoice_detail', pk=pk)
            except ValueError as exc:
                messages.error(request, str(exc))
        return render(request, self.template_name, {'invoice': invoice, 'form': form})


class InvoiceEditView(StaffRequiredMixin, View):
    """
    Edit due_date and notes on an invoice (only these two fields are
    mutable after issuance).

    Requirements: 11.6
    """
    permission_required = 'finance.change_invoice'
    template_name = 'staff/finance/invoices/edit.html'

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceDueDateForm(instance=invoice)
        return render(request, self.template_name, {'invoice': invoice, 'form': form})

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceDueDateForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, f'Invoice {invoice.invoice_number} updated.')
            return redirect('staff:invoice_detail', pk=pk)
        return render(request, self.template_name, {'invoice': invoice, 'form': form})


# ─────────────────────────────────────────────────────────────
# Payment views
# ─────────────────────────────────────────────────────────────

class PaymentListView(StaffRequiredMixin, ListView):
    """
    Paginated payment list with search and filters.

    Requirements: 12.1, 12.5
    """
    permission_required = 'finance.view_payment'
    template_name = 'staff/finance/payments/list.html'
    paginate_by = 25
    context_object_name = 'payments'

    def get_queryset(self):
        qs = Payment.objects.select_related(
            'enrollment__student__user',
        ).order_by('-created_at')

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(payment_reference__icontains=q)
                | Q(enrollment__student__user__first_name__icontains=q)
                | Q(enrollment__student__user__last_name__icontains=q)
                | Q(enrollment__student__admission_number__icontains=q)
            )

        status_filter = self.request.GET.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        method_filter = self.request.GET.get('method', '').strip()
        if method_filter:
            qs = qs.filter(method=method_filter)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['method_filter'] = self.request.GET.get('method', '')
        from apps.finance.models import PaymentStatus, PaymentMethod
        ctx['status_choices'] = PaymentStatus.choices
        ctx['method_choices'] = PaymentMethod.choices
        return ctx


class PaymentDetailView(StaffRequiredMixin, View):
    """
    Display payment details, allocations, provider transaction, and receipt.

    Requirements: 12.2, 12.5
    """
    permission_required = 'finance.view_payment'
    template_name = 'staff/finance/payments/detail.html'

    def get(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.select_related(
                'enrollment__student__user',
                'enrollment__course',
                'recorded_by',
            ).prefetch_related('allocations__invoice', 'provider_transactions'),
            pk=pk,
        )
        provider_tx = payment.provider_transactions.first()
        receipt = getattr(payment, 'receipt', None)

        allocated = (
            payment.allocations.aggregate(t=Sum('allocated_amount'))['t']
            or Decimal('0.00')
        )
        unallocated = payment.amount - allocated

        context = {
            'payment': payment,
            'provider_tx': provider_tx,
            'receipt': receipt,
            'unallocated': unallocated,
        }
        return render(request, self.template_name, context)


class ManualPaymentCreateView(StaffRequiredMixin, View):
    """
    Record a manual payment (immediately SUCCESSFUL) for an enrollment.

    Requirements: 12.3, 12.5
    """
    permission_required = 'finance.add_payment'
    template_name = 'staff/finance/payments/record.html'

    def get(self, request):
        form = ManualPaymentForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ManualPaymentForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                payment = record_manual_payment(
                    enrollment=cd['enrollment'],
                    amount=cd['amount'],
                    method=cd['method'],
                    payer_name=cd.get('payer_name', ''),
                    payer_phone=cd.get('payer_phone', ''),
                    notes=cd.get('notes', ''),
                    recorded_by=request.user,
                )
                messages.success(
                    request,
                    f'Payment {payment.payment_reference} recorded successfully.',
                )
                return redirect('staff:payment_detail', pk=payment.pk)
            except ValueError as exc:
                messages.error(request, str(exc))
        return render(request, self.template_name, {'form': form})


class PaymentAllocateView(StaffRequiredMixin, View):
    """
    Manually allocate an amount from a SUCCESSFUL payment to an invoice.

    Requirements: 12.4, 12.5
    """
    permission_required = 'finance.allocate_payment'
    template_name = 'staff/finance/payments/allocate.html'

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        form = PaymentAllocateForm(payment=payment)
        return render(request, self.template_name, {'payment': payment, 'form': form})

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        form = PaymentAllocateForm(request.POST, payment=payment)
        if form.is_valid():
            invoice = form.cleaned_data['invoice']
            amount = form.cleaned_data['amount']
            try:
                allocate_payment(
                    payment=payment,
                    invoice=invoice,
                    amount=amount,
                    allocated_by=request.user,
                )
                messages.success(
                    request,
                    f'Allocated {amount} KES from {payment.payment_reference} '
                    f'to invoice {invoice.invoice_number}.',
                )
                return redirect('staff:payment_detail', pk=pk)
            except ValueError as exc:
                messages.error(request, str(exc))
        return render(request, self.template_name, {'payment': payment, 'form': form})


# ─────────────────────────────────────────────────────────────
# Receipt views
# ─────────────────────────────────────────────────────────────

class ReceiptDetailView(StaffRequiredMixin, View):
    """
    Display all fields of a receipt.

    Requirements: 13.1
    """
    permission_required = 'finance.view_receipt'
    template_name = 'staff/finance/receipts/detail.html'

    def get(self, request, pk):
        receipt = get_object_or_404(
            Receipt.objects.select_related(
                'payment__enrollment__student__user',
                'payment__enrollment__course',
                'payment__recorded_by',
            ),
            pk=pk,
        )
        return render(request, self.template_name, {'receipt': receipt})


class ReceiptPrintView(StaffRequiredMixin, View):
    """
    Print-friendly receipt view (no navigation chrome).

    Requirements: 13.2
    """
    permission_required = 'finance.view_receipt'
    template_name = 'staff/finance/receipts/print.html'

    def get(self, request, pk):
        receipt = get_object_or_404(
            Receipt.objects.select_related(
                'payment__enrollment__student__user',
                'payment__enrollment__course',
                'payment__recorded_by',
            ),
            pk=pk,
        )
        return render(request, self.template_name, {'receipt': receipt})


# ─────────────────────────────────────────────────────────────
# Student financial statement
# ─────────────────────────────────────────────────────────────

class StudentFinancialStatementView(StaffRequiredMixin, View):
    """
    Full financial statement for a given student (all enrollments,
    invoices, payments, receipts, running balance).

    Takes student_pk as a URL parameter.

    Requirements: 13.3
    """
    permission_required = 'finance.view_invoice'
    template_name = 'staff/finance/student_statement.html'

    def get(self, request, student_pk):
        student = get_object_or_404(StudentProfile, pk=student_pk)
        summary = get_student_financial_summary(student)
        return render(request, self.template_name, {
            'student': student,
            'summary': summary,
        })
