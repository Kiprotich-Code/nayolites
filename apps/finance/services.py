"""
Finance service layer for the Nayolites College Management System.

All financial business logic lives here. Views and management commands
should call these functions rather than manipulating models directly.

Financial invariants:
- All monetary values are Decimal — never float
- Invoice balance derived from records, never stored
- Only SUCCESSFUL payments reduce invoice balances
- Allocation ops use select_for_update() for concurrency safety
- Multi-step ops wrapped in transaction.atomic()
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.audit import audit_log
from apps.core.models import AuditAction
from apps.finance.models import (
    FeeStructure, Invoice, InvoiceItem, InvoiceStatus,
    Payment, PaymentAllocation, PaymentProviderTransaction,
    PaymentMethod, PaymentStatus, Receipt, SequenceCounter,
)


# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────

class PayHeroError(Exception):
    """Raised when the PayHero API returns an error or is unreachable."""
    pass


class FinanceError(ValueError):
    """Base class for finance domain validation errors."""
    pass


# ─────────────────────────────────────────────────────────────
# Reference number generation (collision-free, not gap-free)
# ─────────────────────────────────────────────────────────────

def _next_sequence(prefix: str, year: int) -> str:
    """
    Atomically increment and return the next sequence number.
    Uses select_for_update() to prevent duplicates under concurrent load.
    Numbers may have gaps on transaction rollback — this is expected.
    """
    with transaction.atomic():
        counter, _ = SequenceCounter.objects.select_for_update().get_or_create(
            prefix=prefix,
            year=year,
            defaults={'last_value': 0},
        )
        counter.last_value += 1
        counter.save(update_fields=['last_value'])
        return f'{prefix}-{year}-{counter.last_value:05d}'


def generate_invoice_number(year: int) -> str:
    """Return the next invoice number: INV-YYYY-NNNNN."""
    return _next_sequence('INV', year)


def generate_receipt_number(year: int) -> str:
    """Return the next receipt number: RCP-YYYY-NNNNN."""
    return _next_sequence('RCP', year)


def generate_payment_reference(year: int) -> str:
    """Return the next payment reference: PAY-YYYY-NNNNN."""
    return _next_sequence('PAY', year)


# ─────────────────────────────────────────────────────────────
# Fee structure resolution
# ─────────────────────────────────────────────────────────────

def resolve_fee_structure(course, academic_period):
    """
    Return the best matching active FeeStructure for (course, period).

    Resolution order:
      1. Period-specific (course + academic_period, is_active=True)
      2. Course-only (course + academic_period=None, is_active=True)
      3. None if no active structure exists
    """
    if academic_period is not None:
        period_specific = FeeStructure.objects.filter(
            course=course,
            academic_period=academic_period,
            is_active=True,
        ).first()
        if period_specific:
            return period_specific
    return FeeStructure.objects.filter(
        course=course,
        academic_period__isnull=True,
        is_active=True,
    ).first()


# ─────────────────────────────────────────────────────────────
# Invoice lifecycle
# ─────────────────────────────────────────────────────────────

def create_invoice(enrollment, fee_structure, created_by, due_date=None):
    """
    Create a DRAFT Invoice from a FeeStructure snapshot.

    All FeeItems are copied into InvoiceItems at this moment. Subsequent
    changes to the FeeStructure do NOT affect this invoice.

    Returns the created Invoice instance.
    """
    with transaction.atomic():
        year = timezone.now().year
        invoice_number = generate_invoice_number(year)

        invoice = Invoice.objects.create(
            enrollment=enrollment,
            invoice_number=invoice_number,
            status=InvoiceStatus.DRAFT,
            currency=fee_structure.currency,
            due_date=due_date,
            created_by=created_by,
        )

        # Snapshot each FeeItem as an InvoiceItem
        for fee_item in fee_structure.items.all():
            qty = 1
            total = fee_item.amount * Decimal(qty)
            InvoiceItem.objects.create(
                invoice=invoice,
                description=fee_item.name,
                quantity=qty,
                unit_amount=fee_item.amount,
                total_amount=total,
                fee_item_ref=fee_item.name,
            )

        audit_log(
            actor=created_by,
            action=AuditAction.INVOICE_CREATED,
            obj=invoice,
            description=f'Invoice {invoice.invoice_number} created for {enrollment}',
        )

    return invoice


def issue_invoice(invoice, issued_by):
    """
    Transition an Invoice from DRAFT → ISSUED.

    Sets issued_at to the current UTC time and records who issued it.
    Raises ValueError if the invoice is not in DRAFT status.
    Returns the updated Invoice instance.
    """
    if invoice.status != InvoiceStatus.DRAFT:
        raise ValueError(
            f'Cannot issue invoice {invoice.invoice_number}: '
            f'status is {invoice.status}, expected DRAFT.'
        )
    with transaction.atomic():
        invoice.status = InvoiceStatus.ISSUED
        invoice.issued_at = timezone.now()
        invoice.issued_by = issued_by
        invoice.save(update_fields=['status', 'issued_at', 'issued_by', 'updated_at'])

        audit_log(
            actor=issued_by,
            action=AuditAction.INVOICE_ISSUED,
            obj=invoice,
            description=f'Invoice {invoice.invoice_number} issued.',
        )
    return invoice


def void_invoice(invoice, voided_by, reason):
    """
    Transition an Invoice to VOID status.

    Records who voided it, when, and why. Raises ValueError if already VOID.
    Returns the updated Invoice instance.
    """
    if invoice.status == InvoiceStatus.VOID:
        raise ValueError(
            f'Invoice {invoice.invoice_number} is already VOID.'
        )
    if not reason or not str(reason).strip():
        raise ValueError('A void reason is required.')
    with transaction.atomic():
        invoice.status = InvoiceStatus.VOID
        invoice.voided_by = voided_by
        invoice.voided_at = timezone.now()
        invoice.void_reason = str(reason).strip()
        invoice.save(update_fields=[
            'status', 'voided_by', 'voided_at', 'void_reason', 'updated_at'
        ])

        audit_log(
            actor=voided_by,
            action=AuditAction.INVOICE_VOIDED,
            obj=invoice,
            description=f'Invoice {invoice.invoice_number} voided. Reason: {reason}',
        )
    return invoice


def mark_overdue_invoices():
    """
    Update status to OVERDUE for any issued/partially-paid invoice whose
    due_date has passed and which still has an outstanding balance.

    Called from the finance dashboard view on each load (lightweight query).
    Returns the count of invoices updated.
    """
    from django.utils.timezone import now
    from django.db.models import Q
    today = now().date()

    candidates = Invoice.objects.filter(
        due_date__lt=today,
        status__in=[InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID],
    )
    updated = 0
    for invoice in candidates:
        if get_invoice_balance(invoice) > Decimal('0.00'):
            invoice.status = InvoiceStatus.OVERDUE
            invoice.save(update_fields=['status', 'updated_at'])
            updated += 1
    return updated


def get_invoice_balance(invoice):
    """
    Compute and return the current balance of an Invoice as a Decimal.

    Balance = sum(InvoiceItem.total_amount)
              - sum(PaymentAllocation.allocated_amount for SUCCESSFUL payments)

    Never stores or modifies any field. Always computed from records.
    Returns Decimal('0.00') if no items exist.
    """
    total = invoice.items.aggregate(t=Sum('total_amount'))['t']
    if total is None:
        return Decimal('0.00')
    allocated = invoice.allocations.filter(
        payment__status=PaymentStatus.SUCCESSFUL
    ).aggregate(a=Sum('allocated_amount'))['a']
    return total - (allocated or Decimal('0.00'))


def get_enrollment_outstanding(enrollment):
    """
    Return the total outstanding balance across all non-VOID Invoices
    for the given Enrollment. Returns Decimal('0.00') if none exist.
    """
    invoices = Invoice.objects.filter(
        enrollment=enrollment,
    ).exclude(status=InvoiceStatus.VOID)
    total = Decimal('0.00')
    for inv in invoices:
        total += get_invoice_balance(inv)
    return total


def get_student_financial_summary(student):
    """
    Return a dict summarising the financial position of a student across
    all their enrollments.

    Returns:
    {
        'total_billed':      Decimal,
        'total_paid':        Decimal,
        'total_outstanding': Decimal,
        'enrollments': [
            {
                'enrollment': Enrollment,
                'invoices':   [Invoice, ...],
                'payments':   [Payment, ...],
                'balance':    Decimal,
            }, ...
        ]
    }
    """
    from apps.enrollments.models import Enrollment
    enrollments = Enrollment.objects.filter(
        student=student
    ).select_related('course', 'academic_period').order_by('-enrolled_at')

    total_billed = Decimal('0.00')
    total_paid = Decimal('0.00')
    enrollment_data = []

    for enrollment in enrollments:
        invoices = list(
            Invoice.objects.filter(enrollment=enrollment)
            .exclude(status=InvoiceStatus.VOID)
            .prefetch_related('items', 'allocations')
            .order_by('-created_at')
        )
        payments = list(
            Payment.objects.filter(
                enrollment=enrollment,
                status=PaymentStatus.SUCCESSFUL,
            ).order_by('-created_at')
        )
        e_billed = sum(
            (inv.items.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00'))
            for inv in invoices
        )
        e_paid = sum(
            (inv.allocations.filter(
                payment__status=PaymentStatus.SUCCESSFUL
            ).aggregate(a=Sum('allocated_amount'))['a'] or Decimal('0.00'))
            for inv in invoices
        )
        total_billed += e_billed
        total_paid += e_paid
        enrollment_data.append({
            'enrollment': enrollment,
            'invoices': invoices,
            'payments': payments,
            'balance': e_billed - e_paid,
        })

    return {
        'total_billed': total_billed,
        'total_paid': total_paid,
        'total_outstanding': total_billed - total_paid,
        'enrollments': enrollment_data,
    }


# ─────────────────────────────────────────────────────────────
# Payment functions — filled in by tasks 5.1, 5.5, 5.9, 6.3, 6.4
# ─────────────────────────────────────────────────────────────
