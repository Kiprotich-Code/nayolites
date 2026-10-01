"""
Finance domain models for the Nayolites College Management System.

Financial invariants enforced here:
- All monetary fields use DecimalField(max_digits=12, decimal_places=2)
- No float arithmetic anywhere in this module
- FeeStructure.academic_period is optional (null = applies to all periods)
- FeeItem.CASCADE under FeeStructure (fee items belong to their structure)
- Invoice balance is NEVER stored — computed from records by services.get_invoice_balance()
- Only SUCCESSFUL payments reduce invoice balances
- See services.py for all business logic and state transitions
"""
from decimal import Decimal

from django.conf import settings
from django.db import models


# ─────────────────────────────────────────────────────────────
# Utility: Collision-free sequential reference number generator
# ─────────────────────────────────────────────────────────────

class SequenceCounter(models.Model):
    """
    Tracks the last-issued sequential number for reference number generation.

    Used by services._next_sequence() with select_for_update() to prevent
    duplicate reference numbers under concurrent load.
    Works with both SQLite (tests) and PostgreSQL (production).
    """
    prefix = models.CharField(max_length=10)
    year = models.IntegerField()
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('prefix', 'year')]
        verbose_name = 'sequence counter'
        verbose_name_plural = 'sequence counters'

    def __str__(self):
        return f'{self.prefix}-{self.year}: {self.last_value}'


# ─────────────────────────────────────────────────────────────
# Fee structures
# ─────────────────────────────────────────────────────────────

class FeeStructure(models.Model):
    """
    A named set of fee items for a course, optionally scoped to one academic period.

    When academic_period is null, this structure applies to all periods for the course.
    When both a period-specific and a course-only structure exist, the period-specific
    one takes precedence (enforced in services.resolve_fee_structure()).

    Historical note: changing a FeeStructure after invoices have been issued does NOT
    affect those invoices. InvoiceItems are snapshots captured at invoice creation time.
    """
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.PROTECT,
        related_name='fee_structures',
    )
    academic_period = models.ForeignKey(
        'enrollments.AcademicPeriod',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='fee_structures',
        help_text='Leave blank to apply to all periods for this course.',
    )
    name = models.CharField(max_length=200)
    currency = models.CharField(
        max_length=10,
        default='KES',
        help_text='ISO 4217 currency code, e.g. KES',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Only active fee structures are available for invoice generation.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'fee structure'
        verbose_name_plural = 'fee structures'
        ordering = ['-created_at']
        permissions = [
            ('activate_feestructure', 'Can activate/deactivate fee structure'),
        ]

    @property
    def total_amount(self):
        """Sum of all fee item amounts. Returns Decimal."""
        from django.db.models import Sum
        result = self.items.aggregate(total=Sum('amount'))['total']
        return result if result is not None else Decimal('0.00')

    def __str__(self):
        period = f' — {self.academic_period}' if self.academic_period else ''
        return f'{self.name} ({self.course.code}{period})'


class FeeItem(models.Model):
    """
    An individual charge within a FeeStructure.

    Examples: Tuition Fee, Registration Fee, Examination Fee, Materials Fee.
    These are templates for invoice items — the actual charges are snapshotted
    into InvoiceItems when an invoice is created.
    """
    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.CASCADE,
        related_name='items',
    )
    name = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Amount in the fee structure currency. Must be a Decimal value.',
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order. Lower numbers appear first.',
    )

    class Meta:
        verbose_name = 'fee item'
        verbose_name_plural = 'fee items'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.name}: {self.amount} ({self.fee_structure.currency})'


# ─────────────────────────────────────────────────────────────
# Invoices
# ─────────────────────────────────────────────────────────────

class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ISSUED = 'ISSUED', 'Issued'
    PARTIALLY_PAID = 'PARTIALLY_PAID', 'Partially Paid'
    PAID = 'PAID', 'Paid'
    OVERDUE = 'OVERDUE', 'Overdue'
    VOID = 'VOID', 'Void'


class Invoice(models.Model):
    """
    A financial document issued to a student enrollment.

    Invoice numbers follow the format INV-YYYY-NNNNN and are unique.
    They are generated atomically by services.generate_invoice_number().

    Historical integrity: once issued, invoice_number, enrollment, currency,
    and InvoiceItems are immutable. Only notes and due_date may be changed.
    Status is managed by service functions — do not mutate status directly.

    Balance is NEVER stored — it is computed from InvoiceItems and PaymentAllocations
    by services.get_invoice_balance().
    """
    enrollment = models.ForeignKey(
        'enrollments.Enrollment',
        on_delete=models.PROTECT,
        related_name='invoices',
    )
    invoice_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Auto-generated: INV-YYYY-NNNNN. Never edit manually.',
    )
    status = models.CharField(
        max_length=15,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='KES')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='invoices_created',
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='invoices_issued',
    )
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='invoices_voided',
    )
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = 'invoice'
        verbose_name_plural = 'invoices'
        ordering = ['-created_at']
        permissions = [
            ('issue_invoice', 'Can issue invoice'),
            ('void_invoice', 'Can void invoice'),
        ]

    def __str__(self):
        return f'{self.invoice_number} — {self.enrollment.student} ({self.status})'


class InvoiceItem(models.Model):
    """
    A historical snapshot of a single charge on an Invoice.

    These are created from FeeItems at invoice creation time and are immutable
    once the invoice is issued. They must never be regenerated from the current
    FeeStructure — they represent what was actually charged.

    fee_item_ref preserves the name of the original FeeItem for audit purposes
    even if the FeeItem is later renamed or deleted.
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
    )
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee_item_ref = models.CharField(
        max_length=200,
        blank=True,
        help_text='Name of the original FeeItem at snapshot time.',
    )

    class Meta:
        verbose_name = 'invoice item'
        verbose_name_plural = 'invoice items'

    def __str__(self):
        return f'{self.description} × {self.quantity} = {self.total_amount}'


# ─────────────────────────────────────────────────────────────
# Payments
# ─────────────────────────────────────────────────────────────

class PaymentMethod(models.TextChoices):
    MPESA = 'MPESA', 'M-Pesa'
    BANK = 'BANK', 'Bank Transfer'
    CASH = 'CASH', 'Cash'
    OTHER = 'OTHER', 'Other'


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SUCCESSFUL = 'SUCCESSFUL', 'Successful'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    REVERSED = 'REVERSED', 'Reversed'


class Payment(models.Model):
    """
    Records a financial transaction associated with a student enrollment.

    Payment references follow the format PAY-YYYY-NNNNN.
    Manual payments (method != online) are immediately SUCCESSFUL.
    Online payments (PayHero) start as PENDING and are confirmed via webhook.

    IMPORTANT: Only SUCCESSFUL payments reduce invoice balances.
    PENDING, FAILED, CANCELLED, and REVERSED payments have no financial effect.

    Balance is never stored on Payment — use services.get_enrollment_outstanding().
    payer_name/payer_phone may differ from the student (parent, sponsor, etc.).
    """
    payment_reference = models.CharField(
        max_length=20,
        unique=True,
        help_text='Auto-generated: PAY-YYYY-NNNNN.',
    )
    enrollment = models.ForeignKey(
        'enrollments.Enrollment',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    currency = models.CharField(max_length=10, default='KES')
    payer_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Person who made the payment (may differ from student).',
    )
    payer_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Set when payment reaches SUCCESSFUL status.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payments_recorded',
        help_text='Staff member who recorded a manual payment.',
    )

    class Meta:
        verbose_name = 'payment'
        verbose_name_plural = 'payments'
        ordering = ['-created_at']
        permissions = [
            ('reverse_payment', 'Can reverse payment'),   # preserved from placeholder
            ('allocate_payment', 'Can allocate payment'),
        ]

    def __str__(self):
        return f'{self.payment_reference} — {self.amount} {self.currency} ({self.status})'


class PaymentAllocation(models.Model):
    """
    Links a SUCCESSFUL Payment to a specific Invoice for a portion of the amount.

    This is the core financial mechanism for tracking partial payments,
    multiple payments against one invoice, and one payment across multiple invoices.

    Invariants (enforced by services.allocate_payment()):
    - payment.status must be SUCCESSFUL
    - sum(allocations for payment) <= payment.amount
    - sum(allocations for invoice from SUCCESSFUL payments) <= invoice total
    """
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='allocations',
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='allocations',
    )
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='allocations_made',
    )

    class Meta:
        verbose_name = 'payment allocation'
        verbose_name_plural = 'payment allocations'
        ordering = ['created_at']

    def __str__(self):
        return (
            f'{self.payment.payment_reference} → '
            f'{self.invoice.invoice_number}: {self.allocated_amount}'
        )


class PaymentProviderTransaction(models.Model):
    """
    Raw provider-side record for a PayHero (or other gateway) STK push transaction.

    Isolated from the core Payment model so that PayHero-specific fields
    do not pollute the financial domain. One payment may have at most one
    provider transaction (one-to-many FK with cardinality-1 intent).

    provider_tx_id must be unique — used for idempotent callback processing.
    """
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='provider_transactions',
    )
    provider = models.CharField(
        max_length=50,
        help_text='Provider code, e.g. PAYHERO.',
    )
    provider_tx_id = models.CharField(
        max_length=100,
        unique=True,
        help_text='Provider-assigned transaction ID. Used for idempotent callback handling.',
    )
    provider_reference = models.CharField(max_length=200, blank=True)
    provider_status = models.CharField(max_length=50)
    raw_metadata = models.JSONField(
        blank=True,
        default=dict,
        help_text='Raw provider payload for debugging and reconciliation.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'payment provider transaction'
        verbose_name_plural = 'payment provider transactions'

    def __str__(self):
        return f'{self.provider}:{self.provider_tx_id} ({self.provider_status})'


class Receipt(models.Model):
    """
    A formal acknowledgment of a SUCCESSFUL Payment.

    Receipt numbers follow the format RCP-YYYY-NNNNN and are unique.
    A receipt is a historical financial document — never mutate it.
    One receipt per payment (OneToOneField).
    """
    receipt_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Auto-generated: RCP-YYYY-NNNNN.',
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name='receipt',
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'receipt'
        verbose_name_plural = 'receipts'
        ordering = ['-issued_at']
        # view_receipt is a Django-generated built-in permission; no custom
        # permissions are needed on this model.

    def __str__(self):
        return f'{self.receipt_number} — {self.payment.payment_reference}'
