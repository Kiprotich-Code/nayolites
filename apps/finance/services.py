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


def _update_invoice_status_after_allocation(invoice, invoice_total, total_allocated):
    """
    Set invoice.status based on allocation totals. Does NOT call .save() —
    the caller is responsible for saving inside the surrounding transaction.
    """
    if total_allocated >= invoice_total:
        invoice.status = InvoiceStatus.PAID
    elif total_allocated > Decimal('0.00'):
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    # No change for zero allocation (stays ISSUED/OVERDUE)


def allocate_payment(payment, invoice, amount, allocated_by=None):
    """
    Allocate `amount` from `payment` to `invoice`.

    Uses select_for_update() on both rows to prevent concurrent over-allocation.
    All validation is re-done inside the lock so values are fresh.

    Raises ValueError if:
    - payment.status is not SUCCESSFUL
    - amount > remaining unallocated on payment
    - amount > remaining balance on invoice
    Returns the created PaymentAllocation.
    """
    amount = Decimal(str(amount))  # ensure Decimal

    with transaction.atomic():
        # Lock both rows
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)

        if payment.status != PaymentStatus.SUCCESSFUL:
            raise ValueError(
                f'Payment {payment.payment_reference} is not SUCCESSFUL '
                f'(status: {payment.status}). Only SUCCESSFUL payments can be allocated.'
            )

        # Re-compute inside lock
        existing_payment_allocated = (
            PaymentAllocation.objects.filter(payment=payment)
            .aggregate(t=Sum('allocated_amount'))['t'] or Decimal('0.00')
        )
        payment_remaining = payment.amount - existing_payment_allocated

        if amount > payment_remaining:
            raise ValueError(
                f'Allocation of {amount} exceeds remaining unallocated amount '
                f'({payment_remaining}) on payment {payment.payment_reference}.'
            )

        invoice_total = (
            invoice.items.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
        )
        existing_invoice_allocated = (
            invoice.allocations.filter(
                payment__status=PaymentStatus.SUCCESSFUL
            ).aggregate(a=Sum('allocated_amount'))['a'] or Decimal('0.00')
        )
        invoice_remaining = invoice_total - existing_invoice_allocated

        if amount > invoice_remaining:
            raise ValueError(
                f'Allocation of {amount} exceeds remaining invoice balance '
                f'({invoice_remaining}) on invoice {invoice.invoice_number}.'
            )

        allocation = PaymentAllocation.objects.create(
            payment=payment,
            invoice=invoice,
            allocated_amount=amount,
            allocated_by=allocated_by,
        )

        # Update invoice status
        new_total_allocated = existing_invoice_allocated + amount
        _update_invoice_status_after_allocation(invoice, invoice_total, new_total_allocated)
        invoice.save(update_fields=['status', 'updated_at'])

        audit_log(
            actor=allocated_by,
            action=AuditAction.PAYMENT_ALLOCATED,
            obj=allocation,
            description=(
                f'{amount} allocated from {payment.payment_reference} '
                f'to invoice {invoice.invoice_number}.'
            ),
        )

    return allocation


def auto_allocate_payment(payment):
    """
    Automatically allocate payment to the enrollment's outstanding invoices,
    oldest issued_at first. Stops when payment amount is exhausted.

    Only allocates to ISSUED, PARTIALLY_PAID, and OVERDUE invoices.
    Remaining unallocated amount stays as credit on the Payment object.

    Returns list of created PaymentAllocation instances.
    All allocations executed inside a single transaction.atomic().
    """
    if payment.status != PaymentStatus.SUCCESSFUL:
        raise ValueError(
            f'Cannot auto-allocate non-SUCCESSFUL payment {payment.payment_reference}.'
        )

    with transaction.atomic():
        # Re-read allocatable amount inside transaction
        existing_allocated = (
            PaymentAllocation.objects.filter(payment=payment)
            .aggregate(t=Sum('allocated_amount'))['t'] or Decimal('0.00')
        )
        available = payment.amount - existing_allocated

        if available <= Decimal('0.00'):
            return []

        # Invoices ordered oldest-first; only allocatable statuses
        allocatable_statuses = [
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
            InvoiceStatus.OVERDUE,
        ]
        invoices = Invoice.objects.filter(
            enrollment=payment.enrollment,
            status__in=allocatable_statuses,
        ).order_by('issued_at', 'created_at')

        allocations = []
        for invoice in invoices:
            if available <= Decimal('0.00'):
                break

            invoice_total = (
                invoice.items.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
            )
            invoice_allocated = (
                invoice.allocations.filter(
                    payment__status=PaymentStatus.SUCCESSFUL
                ).aggregate(a=Sum('allocated_amount'))['a'] or Decimal('0.00')
            )
            invoice_balance = invoice_total - invoice_allocated

            if invoice_balance <= Decimal('0.00'):
                continue

            alloc_amount = min(available, invoice_balance)

            allocation = PaymentAllocation.objects.create(
                payment=payment,
                invoice=invoice,
                allocated_amount=alloc_amount,
                allocated_by=None,
            )
            allocations.append(allocation)

            new_total_allocated = invoice_allocated + alloc_amount
            _update_invoice_status_after_allocation(invoice, invoice_total, new_total_allocated)
            invoice.save(update_fields=['status', 'updated_at'])

            available -= alloc_amount

        return allocations


def record_manual_payment(
    enrollment, amount, method, payer_name='', payer_phone='',
    notes='', recorded_by=None
):
    """
    Record a manual payment (CASH, BANK, MPESA, OTHER) immediately as SUCCESSFUL.

    Creates: Payment → auto_allocate_payment() → Receipt.
    All wrapped in transaction.atomic().
    Returns the created Payment instance.
    """
    amount = Decimal(str(amount))

    with transaction.atomic():
        year = timezone.now().year
        ref = generate_payment_reference(year)

        payment = Payment.objects.create(
            payment_reference=ref,
            enrollment=enrollment,
            amount=amount,
            method=method,
            status=PaymentStatus.SUCCESSFUL,
            currency='KES',
            payer_name=payer_name or '',
            payer_phone=payer_phone or '',
            notes=notes or '',
            paid_at=timezone.now(),
            recorded_by=recorded_by,
        )

        audit_log(
            actor=recorded_by,
            action=AuditAction.PAYMENT_CREATED,
            obj=payment,
            description=f'Manual payment {ref} recorded: {amount} KES via {method}.',
        )

        auto_allocate_payment(payment)

        receipt_number = generate_receipt_number(year)
        Receipt.objects.create(
            receipt_number=receipt_number,
            payment=payment,
        )

        audit_log(
            actor=recorded_by,
            action=AuditAction.MANUAL_PAYMENT_RECORDED,
            obj=payment,
            description=(
                f'Manual payment {ref} recorded and receipt {receipt_number} issued. '
                f'Amount: {amount} KES. Method: {method}. Payer: {payer_name or "—"}.'
            ),
        )

    return payment



# ─────────────────────────────────────────────────────────────
# PayHero integration
# ─────────────────────────────────────────────────────────────

def initiate_payhero_payment(enrollment, amount, phone, initiated_by=None):
    """
    Initiate an online M-Pesa STK push payment via PayHero.

    1. Creates a PENDING Payment + PaymentProviderTransaction.
    2. Calls providers.payhero.initiate_stk_push() outside the transaction.
    3. On API success: updates PaymentProviderTransaction with provider_tx_id.
    4. On API failure: sets Payment.status = FAILED, raises PayHeroError.

    Returns the Payment instance (status PENDING or FAILED).
    """
    from django.conf import settings
    from apps.finance.providers import payhero as _payhero

    amount = Decimal(str(amount))
    year = timezone.now().year
    ref = generate_payment_reference(year)

    # Create DB records first (inside transaction)
    with transaction.atomic():
        payment = Payment.objects.create(
            payment_reference=ref,
            enrollment=enrollment,
            amount=amount,
            method=PaymentMethod.MPESA,
            status=PaymentStatus.PENDING,
            currency='KES',
            recorded_by=initiated_by,
        )
        provider_tx = PaymentProviderTransaction.objects.create(
            payment=payment,
            provider='PAYHERO',
            provider_tx_id=f'PENDING-{ref}',  # placeholder until API confirms
            provider_status='PENDING',
        )
        audit_log(
            actor=initiated_by,
            action=AuditAction.PAYMENT_CREATED,
            obj=payment,
            description=f'PayHero STK push initiated for {amount} KES to {phone}.',
        )

    # API call OUTSIDE transaction (network I/O must not hold a DB transaction)
    callback_url = getattr(settings, 'PAYHERO_CALLBACK_URL',
                           'https://example.com/finance/callbacks/payhero/')
    try:
        api_response = _payhero.initiate_stk_push(
            phone=phone,
            amount=amount,
            reference=ref,
            callback_url=callback_url,
        )
        # Update provider transaction with real ID from API response
        real_tx_id = (
            api_response.get('reference')
            or api_response.get('id')
            or f'PAYHERO-{ref}'
        )
        with transaction.atomic():
            provider_tx.provider_tx_id = real_tx_id
            provider_tx.provider_status = api_response.get('status', 'PENDING')
            provider_tx.raw_metadata = api_response
            provider_tx.save(update_fields=['provider_tx_id', 'provider_status', 'raw_metadata', 'updated_at'])

    except PayHeroError:
        with transaction.atomic():
            payment.status = PaymentStatus.FAILED
            payment.save(update_fields=['status', 'updated_at'])
            provider_tx.provider_status = 'FAILED'
            provider_tx.save(update_fields=['provider_status', 'updated_at'])
        raise

    return payment


def process_payhero_callback(
    provider_tx_id: str,
    status: str,
    amount,
    provider_reference: str,
    raw_payload: dict,
):
    """
    Process a PayHero webhook callback. Idempotent.

    If the PaymentProviderTransaction with provider_tx_id is already at a
    terminal status (SUCCESSFUL or FAILED), returns the existing Payment
    unchanged — duplicate callbacks have no effect.

    On success: SUCCESSFUL, paid_at, auto_allocate_payment(), Receipt.
    On failure: FAILED.
    All state changes inside transaction.atomic().
    """
    TERMINAL_STATUSES = {'SUCCESSFUL', 'FAILED'}

    with transaction.atomic():
        try:
            provider_tx = PaymentProviderTransaction.objects.select_for_update().get(
                provider_tx_id=provider_tx_id
            )
        except PaymentProviderTransaction.DoesNotExist:
            raise ValueError(
                f'No PaymentProviderTransaction found for provider_tx_id={provider_tx_id!r}'
            )

        payment = Payment.objects.select_for_update().get(pk=provider_tx.payment_id)

        # Idempotency: already terminal → return unchanged
        if payment.status in TERMINAL_STATUSES:
            return payment

        # Update provider transaction record
        provider_tx.provider_reference = provider_reference or ''
        provider_tx.provider_status = status
        provider_tx.raw_metadata = raw_payload or {}
        provider_tx.save(update_fields=['provider_reference', 'provider_status', 'raw_metadata', 'updated_at'])

        is_success = status.upper() in ('SUCCESS', 'SUCCESSFUL', 'COMPLETE', 'COMPLETED')

        if is_success:
            payment.status = PaymentStatus.SUCCESSFUL
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at', 'updated_at'])

            audit_log(
                actor=None,
                action=AuditAction.PAYMENT_STATUS_CHANGED,
                obj=payment,
                description=f'PayHero callback confirmed success for {payment.payment_reference}.',
            )

            # Auto-allocate to outstanding invoices
            auto_allocate_payment(payment)

            # Issue receipt
            year = timezone.now().year
            receipt_number = generate_receipt_number(year)
            Receipt.objects.create(receipt_number=receipt_number, payment=payment)

            audit_log(
                actor=None,
                action=AuditAction.RECEIPT_ISSUED,
                obj=payment,
                description=f'Receipt {receipt_number} issued for {payment.payment_reference}.',
            )

        else:
            payment.status = PaymentStatus.FAILED
            payment.save(update_fields=['status', 'updated_at'])

            audit_log(
                actor=None,
                action=AuditAction.PAYMENT_STATUS_CHANGED,
                obj=payment,
                description=f'PayHero callback reported failure for {payment.payment_reference}.',
            )

    return payment
