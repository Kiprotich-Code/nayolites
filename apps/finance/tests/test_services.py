"""
Service layer tests for the Finance module.

Covers: reference number generation, fee structure resolution,
invoice lifecycle, payment allocation, and Decimal precision.
Requirements: 20.2–20.8, 20.13, 20.14
"""
import re
from decimal import Decimal

from django.test import TestCase
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from apps.finance.services import (
    generate_invoice_number,
    generate_payment_reference,
    generate_receipt_number,
)


# ─────────────────────────────────────────────────────────────
# Property 1: Reference Number Format Invariant
# ─────────────────────────────────────────────────────────────

INVOICE_PATTERN = re.compile(r'^INV-\d{4}-\d{5}$')
RECEIPT_PATTERN = re.compile(r'^RCP-\d{4}-\d{5}$')
PAYMENT_PATTERN = re.compile(r'^PAY-\d{4}-\d{5}$')


class ReferenceNumberFormatTest(HypothesisTestCase):
    """
    Property 1: For any call to a generator with any year, the returned
    string matches {PREFIX}-YYYY-NNNNN where YYYY is 4 digits and NNNNN
    is 5 zero-padded digits.
    """

    @given(year=st.integers(min_value=2020, max_value=2099))
    @hyp_settings(max_examples=20)
    def test_invoice_number_format(self, year):
        ref = generate_invoice_number(year)
        self.assertRegex(ref, INVOICE_PATTERN,
                         f'Invoice number {ref!r} does not match INV-YYYY-NNNNN')
        # Year embedded in reference matches the input year
        self.assertIn(str(year), ref)

    @given(year=st.integers(min_value=2020, max_value=2099))
    @hyp_settings(max_examples=20)
    def test_receipt_number_format(self, year):
        ref = generate_receipt_number(year)
        self.assertRegex(ref, RECEIPT_PATTERN,
                         f'Receipt number {ref!r} does not match RCP-YYYY-NNNNN')
        self.assertIn(str(year), ref)

    @given(year=st.integers(min_value=2020, max_value=2099))
    @hyp_settings(max_examples=20)
    def test_payment_reference_format(self, year):
        ref = generate_payment_reference(year)
        self.assertRegex(ref, PAYMENT_PATTERN,
                         f'Payment reference {ref!r} does not match PAY-YYYY-NNNNN')
        self.assertIn(str(year), ref)


# ─────────────────────────────────────────────────────────────
# Property 2: Reference Number Global Uniqueness
# ─────────────────────────────────────────────────────────────

class ReferenceNumberUniquenessTest(TestCase):
    """
    Property 2: N sequential calls to the same generator for the same year
    produce N distinct strings with no duplicates.
    """

    def _generate_n(self, generator_fn, year, n):
        return [generator_fn(year) for _ in range(n)]

    def test_invoice_numbers_unique(self):
        refs = self._generate_n(generate_invoice_number, 2026, 50)
        self.assertEqual(len(refs), len(set(refs)),
                         'Duplicate invoice numbers generated')

    def test_receipt_numbers_unique(self):
        refs = self._generate_n(generate_receipt_number, 2026, 50)
        self.assertEqual(len(refs), len(set(refs)),
                         'Duplicate receipt numbers generated')

    def test_payment_references_unique(self):
        refs = self._generate_n(generate_payment_reference, 2026, 50)
        self.assertEqual(len(refs), len(set(refs)),
                         'Duplicate payment references generated')

    def test_counters_independent_across_years(self):
        """Numbers from different years must not collide."""
        refs_2025 = self._generate_n(generate_invoice_number, 2025, 5)
        refs_2026 = self._generate_n(generate_invoice_number, 2026, 5)
        all_refs = refs_2025 + refs_2026
        self.assertEqual(len(all_refs), len(set(all_refs)),
                         'Invoice numbers collided across years')

    def test_invoice_numbers_sequential(self):
        """Numbers for the same year must be strictly increasing."""
        refs = self._generate_n(generate_invoice_number, 2030, 10)
        sequences = [int(r.split('-')[2]) for r in refs]
        self.assertEqual(sequences, sorted(sequences),
                         'Invoice sequence numbers are not monotonically increasing')


# ─────────────────────────────────────────────────────────────
# Property 3: FeeStructure Resolution Priority
# ─────────────────────────────────────────────────────────────

class FeeStructureResolutionTest(TestCase):
    """
    Property 3: When both a period-specific and a course-only active
    FeeStructure exist for the same course, resolve_fee_structure()
    returns the period-specific one.

    Validates: Requirements 1.3, 1.4
    """

    def setUp(self):
        from apps.courses.models import Course
        from apps.enrollments.models import AcademicPeriod
        from apps.finance.models import FeeStructure

        self.course_a = Course.objects.create(
            code='TST01', name='Test Course A', is_active=True,
            duration='1 Year',
        )
        self.course_b = Course.objects.create(
            code='TST02', name='Test Course B', is_active=True,
            duration='1 Year',
        )
        self.period = AcademicPeriod.objects.create(
            name='2026 Semester 1',
            start_date='2026-01-01',
            end_date='2026-06-30',
            is_active=True,
        )

        # Course-only structure (no period)
        self.course_only = FeeStructure.objects.create(
            course=self.course_a,
            academic_period=None,
            name='Course A General',
            currency='KES',
            is_active=True,
        )
        # Period-specific structure
        self.period_specific = FeeStructure.objects.create(
            course=self.course_a,
            academic_period=self.period,
            name='Course A 2026 S1',
            currency='KES',
            is_active=True,
        )

    def test_period_specific_wins_over_course_only(self):
        """Period-specific structure takes precedence over course-only."""
        from apps.finance.services import resolve_fee_structure
        result = resolve_fee_structure(self.course_a, self.period)
        self.assertEqual(result, self.period_specific,
                         'Period-specific structure should take precedence over course-only')

    def test_course_only_returned_when_no_period_specific(self):
        """Falls back to course-only when no period-specific structure exists."""
        from apps.finance.services import resolve_fee_structure
        from apps.finance.models import FeeStructure
        # course_b only has a course-only structure (none created for it yet)
        course_only_b = FeeStructure.objects.create(
            course=self.course_b,
            academic_period=None,
            name='Course B General',
            currency='KES',
            is_active=True,
        )
        result = resolve_fee_structure(self.course_b, self.period)
        self.assertEqual(result, course_only_b,
                         'Should fall back to course-only when no period-specific exists')

    def test_inactive_period_specific_not_returned(self):
        """An inactive period-specific structure is ignored; course-only is returned."""
        from apps.finance.services import resolve_fee_structure
        self.period_specific.is_active = False
        self.period_specific.save()
        result = resolve_fee_structure(self.course_a, self.period)
        self.assertEqual(result, self.course_only,
                         'Inactive period-specific structure should be ignored')

    def test_no_structure_returns_none(self):
        """Returns None when no active structure exists for the course."""
        from apps.finance.services import resolve_fee_structure
        from apps.courses.models import Course
        empty_course = Course.objects.create(
            code='EMPTY', name='Empty Course', is_active=True, duration='1 Year',
        )
        result = resolve_fee_structure(empty_course, self.period)
        self.assertIsNone(result, 'Should return None when no active structure exists')

    def test_none_period_returns_course_only(self):
        """Passing None as period returns the course-only structure."""
        from apps.finance.services import resolve_fee_structure
        result = resolve_fee_structure(self.course_a, None)
        self.assertEqual(result, self.course_only,
                         'Passing None as period should return course-only structure')


# ─────────────────────────────────────────────────────────────
# Shared test helper — used by Property 4 and later tests
# ─────────────────────────────────────────────────────────────

class FinanceTestMixin:
    """
    Mixin that creates a minimal but complete fixture set used across multiple
    finance service tests: User, StudentProfile, Course, AcademicPeriod,
    Enrollment, FeeStructure with two FeeItems.

    Subclasses must inherit from django.test.TestCase (or equivalent) so
    that setUp() is called in a transaction that is rolled back between tests.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.courses.models import Course
        from apps.enrollments.models import AcademicPeriod, Enrollment
        from apps.students.models import StudentProfile
        from apps.finance.models import FeeStructure, FeeItem

        User = get_user_model()

        # ── Staff user (created_by for invoices) ──────────────────────────
        self.staff_user = User.objects.create_user(
            email='finance.staff@test.example',
            password='testpass123',
            first_name='Finance',
            last_name='Staff',
            is_staff=True,
        )

        # ── Student user + profile ─────────────────────────────────────────
        self.student_user = User.objects.create_user(
            email='student.one@test.example',
            password='testpass123',
            first_name='Student',
            last_name='One',
            is_staff=False,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            admission_number='ADM-TEST-001',
        )

        # ── Course ────────────────────────────────────────────────────────
        self.course = Course.objects.create(
            code='FIN01',
            name='Finance Test Course',
            duration='1 Year',
            is_active=True,
        )

        # ── Academic period ───────────────────────────────────────────────
        self.period = AcademicPeriod.objects.create(
            name='2026 Finance Test Semester',
            start_date='2026-01-01',
            end_date='2026-06-30',
            is_active=True,
        )

        # ── Enrollment ────────────────────────────────────────────────────
        self.enrollment = Enrollment.objects.create(
            student=self.student_profile,
            course=self.course,
            academic_period=self.period,
        )

        # ── Fee structure with two items ──────────────────────────────────
        self.fee_structure = FeeStructure.objects.create(
            course=self.course,
            academic_period=self.period,
            name='Finance Test Fee Structure',
            currency='KES',
            is_active=True,
        )
        self.fee_item_tuition = FeeItem.objects.create(
            fee_structure=self.fee_structure,
            name='Tuition Fee',
            amount=Decimal('30000.00'),
            order=1,
        )
        self.fee_item_exam = FeeItem.objects.create(
            fee_structure=self.fee_structure,
            name='Examination Fee',
            amount=Decimal('3000.00'),
            order=2,
        )


# ─────────────────────────────────────────────────────────────
# Property 4: Invoice Snapshot Immutability
# ─────────────────────────────────────────────────────────────

class InvoiceSnapshotImmutabilityTest(FinanceTestMixin, TestCase):
    """
    Property 4: After create_invoice(), modifying the source FeeItem does NOT
    change InvoiceItem.fee_item_ref or unit_amount.

    Validates: Requirements 2.2, 5.1, 5.2, 20.3
    """

    def _create_test_invoice(self):
        """Helper: create and return a fresh invoice from self.fee_structure."""
        from apps.finance.services import create_invoice
        return create_invoice(
            enrollment=self.enrollment,
            fee_structure=self.fee_structure,
            created_by=self.staff_user,
        )

    def test_invoice_items_created_from_fee_items(self):
        """create_invoice() produces one InvoiceItem per FeeItem."""
        invoice = self._create_test_invoice()
        self.assertEqual(
            invoice.items.count(), 2,
            'Invoice should have exactly 2 items matching the 2 FeeItems',
        )

    def test_fee_item_ref_matches_fee_item_name_at_snapshot_time(self):
        """InvoiceItem.fee_item_ref is set to the FeeItem name at creation time."""
        invoice = self._create_test_invoice()
        refs = set(invoice.items.values_list('fee_item_ref', flat=True))
        self.assertIn('Tuition Fee', refs)
        self.assertIn('Examination Fee', refs)

    def test_unit_amount_matches_fee_item_amount_at_snapshot_time(self):
        """InvoiceItem.unit_amount equals the FeeItem.amount at creation time."""
        invoice = self._create_test_invoice()
        item_tuition = invoice.items.get(fee_item_ref='Tuition Fee')
        item_exam = invoice.items.get(fee_item_ref='Examination Fee')
        self.assertEqual(item_tuition.unit_amount, Decimal('30000.00'))
        self.assertEqual(item_exam.unit_amount, Decimal('3000.00'))

    def test_modifying_fee_item_name_does_not_change_fee_item_ref(self):
        """
        Core snapshot invariant: changing FeeItem.name after invoice creation
        does NOT alter the InvoiceItem.fee_item_ref that was snapshotted.
        """
        invoice = self._create_test_invoice()

        # Capture snapshot values before mutation
        item_tuition = invoice.items.get(fee_item_ref='Tuition Fee')
        original_ref = item_tuition.fee_item_ref  # 'Tuition Fee'
        original_unit_amount = item_tuition.unit_amount  # 30000.00

        # Mutate the source FeeItem
        self.fee_item_tuition.name = 'RENAMED Tuition Fee'
        self.fee_item_tuition.save()

        # Re-fetch InvoiceItem from the database — must be unchanged
        item_tuition.refresh_from_db()
        self.assertEqual(
            item_tuition.fee_item_ref, original_ref,
            f'fee_item_ref should remain {original_ref!r} after FeeItem rename; '
            f'got {item_tuition.fee_item_ref!r}',
        )
        self.assertEqual(
            item_tuition.unit_amount, original_unit_amount,
            'unit_amount should be unchanged after FeeItem rename',
        )

    def test_modifying_fee_item_amount_does_not_change_unit_amount(self):
        """
        Changing FeeItem.amount after invoice creation does NOT alter
        InvoiceItem.unit_amount — the snapshot is frozen.
        """
        invoice = self._create_test_invoice()
        item_exam = invoice.items.get(fee_item_ref='Examination Fee')
        original_unit_amount = item_exam.unit_amount  # 3000.00

        # Raise the fee after the invoice was created
        self.fee_item_exam.amount = Decimal('5000.00')
        self.fee_item_exam.save()

        item_exam.refresh_from_db()
        self.assertEqual(
            item_exam.unit_amount, original_unit_amount,
            f'unit_amount should remain {original_unit_amount} after FeeItem amount '
            f'change; got {item_exam.unit_amount}',
        )

    def test_deleting_fee_item_does_not_affect_invoice_item(self):
        """
        Deleting a FeeItem after invoice creation does NOT cascade to
        the InvoiceItem — the snapshot row persists independently.
        """
        invoice = self._create_test_invoice()
        invoice_item_pk = invoice.items.get(fee_item_ref='Examination Fee').pk

        # Delete the source FeeItem
        self.fee_item_exam.delete()

        # The InvoiceItem must still exist with the original values
        from apps.finance.models import InvoiceItem
        surviving_item = InvoiceItem.objects.get(pk=invoice_item_pk)
        self.assertEqual(surviving_item.fee_item_ref, 'Examination Fee')
        self.assertEqual(surviving_item.unit_amount, Decimal('3000.00'))

    def test_second_invoice_from_same_structure_is_independent_snapshot(self):
        """
        Two invoices created from the same FeeStructure are independent
        snapshots — modifying between the two calls does not affect the first.
        """
        from apps.finance.services import create_invoice

        invoice_one = self._create_test_invoice()

        # Modify FeeItem between invoice creations
        self.fee_item_tuition.amount = Decimal('35000.00')
        self.fee_item_tuition.save()

        invoice_two = create_invoice(
            enrollment=self.enrollment,
            fee_structure=self.fee_structure,
            created_by=self.staff_user,
        )

        item_one = invoice_one.items.get(fee_item_ref='Tuition Fee')
        item_two = invoice_two.items.get(fee_item_ref='Tuition Fee')

        # First invoice retains original amount
        item_one.refresh_from_db()
        self.assertEqual(item_one.unit_amount, Decimal('30000.00'),
                         'First invoice snapshot must not be affected by later FeeItem change')
        # Second invoice captures the updated amount
        self.assertEqual(item_two.unit_amount, Decimal('35000.00'),
                         'Second invoice snapshot should capture the new FeeItem amount')


# ─────────────────────────────────────────────────────────────
# Property 5: InvoiceItem Total Computation
# ─────────────────────────────────────────────────────────────

class InvoiceItemTotalComputationTest(FinanceTestMixin, HypothesisTestCase):
    """
    Property 5: For any InvoiceItem, total_amount == quantity × unit_amount
    with exact Decimal arithmetic — no floating-point drift allowed.

    Validates: Requirements 2.7, 5.3, 17.3
    """

    @given(
        unit_amount=st.decimals(
            min_value='1.00', max_value='99999.99',
            allow_nan=False, allow_infinity=False, places=2,
        ),
        quantity=st.integers(min_value=1, max_value=10),
    )
    @hyp_settings(max_examples=5)
    def test_total_amount_exact_decimal_arithmetic(self, unit_amount, quantity):
        """total_amount stored on InvoiceItem must equal qty × unit_amount exactly."""
        from apps.finance.models import InvoiceItem
        from apps.finance.services import generate_invoice_number, create_invoice
        from apps.finance.models import Invoice, InvoiceStatus

        # Create a bare invoice (not via fee_structure to control unit_amount directly)
        inv_num = generate_invoice_number(2099)
        invoice = Invoice.objects.create(
            enrollment=self.enrollment,
            invoice_number=inv_num,
            status=InvoiceStatus.DRAFT,
            currency='KES',
            created_by=self.staff_user,
        )
        expected_total = unit_amount * Decimal(quantity)
        item = InvoiceItem.objects.create(
            invoice=invoice,
            description='Hypothesis Test Item',
            quantity=quantity,
            unit_amount=unit_amount,
            total_amount=expected_total,
            fee_item_ref='Hypothesis Test Item',
        )
        # Reload from DB to verify persistence
        item.refresh_from_db()
        self.assertEqual(
            item.total_amount, expected_total,
            f'total_amount {item.total_amount} != {quantity} × {unit_amount} = {expected_total}',
        )
        self.assertIsInstance(
            item.total_amount, Decimal,
            'total_amount must be a Decimal instance, not float',
        )
        self.assertNotIsInstance(
            float(item.total_amount) if False else item.total_amount,
            float,
            'total_amount must never be a Python float',
        )

    def test_create_invoice_total_amount_computed_correctly(self):
        """create_invoice() sets total_amount = qty(1) × unit_amount for each item."""
        from apps.finance.services import create_invoice
        invoice = create_invoice(
            enrollment=self.enrollment,
            fee_structure=self.fee_structure,
            created_by=self.staff_user,
        )
        for item in invoice.items.all():
            expected = item.unit_amount * Decimal(item.quantity)
            self.assertEqual(
                item.total_amount, expected,
                f'Item "{item.description}": total_amount {item.total_amount} '
                f'!= {item.quantity} × {item.unit_amount} = {expected}',
            )

    def test_invoice_total_is_sum_of_item_totals(self):
        """The sum of all InvoiceItem.total_amount values equals the expected invoice total."""
        from apps.finance.services import create_invoice
        invoice = create_invoice(
            enrollment=self.enrollment,
            fee_structure=self.fee_structure,
            created_by=self.staff_user,
        )
        expected_total = Decimal('30000.00') + Decimal('3000.00')  # tuition + exam
        actual_total = sum(item.total_amount for item in invoice.items.all())
        self.assertEqual(actual_total, expected_total)
        self.assertIsInstance(actual_total, Decimal)


# ─────────────────────────────────────────────────────────────
# Property 13: Invalid Invoice Transitions Raise ValueError
# ─────────────────────────────────────────────────────────────

class InvalidInvoiceTransitionTest(FinanceTestMixin, TestCase):
    """
    Property 13: issue_invoice() raises ValueError for any non-DRAFT status.
    void_invoice() raises ValueError when status is already VOID.

    Validates: Requirements 5.5, 5.7
    """

    def _make_invoice(self, status=None):
        from apps.finance.services import create_invoice, issue_invoice
        from apps.finance.models import InvoiceStatus
        invoice = create_invoice(self.enrollment, self.fee_structure, self.staff_user)
        if status and status != InvoiceStatus.DRAFT:
            issue_invoice(invoice, self.staff_user)
            if status == InvoiceStatus.VOID:
                from apps.finance.services import void_invoice
                void_invoice(invoice, self.staff_user, 'Test void')
        return invoice

    def test_issue_draft_succeeds(self):
        from apps.finance.services import create_invoice, issue_invoice
        from apps.finance.models import InvoiceStatus
        invoice = create_invoice(self.enrollment, self.fee_structure, self.staff_user)
        issued = issue_invoice(invoice, self.staff_user)
        self.assertEqual(issued.status, InvoiceStatus.ISSUED)

    def test_issue_already_issued_raises(self):
        from apps.finance.services import create_invoice, issue_invoice
        invoice = create_invoice(self.enrollment, self.fee_structure, self.staff_user)
        issue_invoice(invoice, self.staff_user)
        with self.assertRaises(ValueError):
            issue_invoice(invoice, self.staff_user)

    def test_issue_void_invoice_raises(self):
        from apps.finance.services import create_invoice, issue_invoice, void_invoice
        invoice = create_invoice(self.enrollment, self.fee_structure, self.staff_user)
        issue_invoice(invoice, self.staff_user)
        void_invoice(invoice, self.staff_user, 'Testing')
        with self.assertRaises(ValueError):
            issue_invoice(invoice, self.staff_user)

    def test_void_already_void_raises(self):
        from apps.finance.services import create_invoice, issue_invoice, void_invoice
        invoice = create_invoice(self.enrollment, self.fee_structure, self.staff_user)
        issue_invoice(invoice, self.staff_user)
        void_invoice(invoice, self.staff_user, 'First void')
        with self.assertRaises(ValueError):
            void_invoice(invoice, self.staff_user, 'Second void attempt')

    def test_void_requires_reason(self):
        from apps.finance.services import create_invoice, issue_invoice, void_invoice
        invoice = create_invoice(self.enrollment, self.fee_structure, self.staff_user)
        issue_invoice(invoice, self.staff_user)
        with self.assertRaises(ValueError):
            void_invoice(invoice, self.staff_user, '')

    def test_void_whitespace_reason_raises(self):
        from apps.finance.services import create_invoice, issue_invoice, void_invoice
        invoice = create_invoice(self.enrollment, self.fee_structure, self.staff_user)
        issue_invoice(invoice, self.staff_user)
        with self.assertRaises(ValueError):
            void_invoice(invoice, self.staff_user, '   ')


# ─────────────────────────────────────────────────────────────
# Property 6: Invoice Balance Correctness
# ─────────────────────────────────────────────────────────────

class InvoiceBalanceCorrectnessTest(FinanceTestMixin, TestCase):
    """
    Property 6: get_invoice_balance() == sum(total_amount) - sum(allocated_amount
    from SUCCESSFUL payments). Never involves float arithmetic.

    Validates: Requirements 2.8, 5.8, 17.3
    """

    def _make_issued_invoice(self):
        from apps.finance.services import create_invoice, issue_invoice
        inv = create_invoice(self.enrollment, self.fee_structure, self.staff_user)
        return issue_invoice(inv, self.staff_user)

    def _make_successful_payment(self, amount, ref_suffix=''):
        from apps.finance.models import Payment, PaymentStatus, PaymentMethod
        return Payment.objects.create(
            payment_reference=f'PAY-TEST-{ref_suffix or "00001"}',
            enrollment=self.enrollment,
            amount=Decimal(str(amount)),
            method=PaymentMethod.CASH,
            status=PaymentStatus.SUCCESSFUL,
            currency='KES',
        )

    def test_balance_equals_total_when_no_payments(self):
        from apps.finance.services import get_invoice_balance
        invoice = self._make_issued_invoice()
        expected = Decimal('30000.00') + Decimal('3000.00')
        self.assertEqual(get_invoice_balance(invoice), expected)

    def test_balance_reduces_after_partial_allocation(self):
        from apps.finance.services import get_invoice_balance
        from apps.finance.models import PaymentAllocation
        invoice = self._make_issued_invoice()
        payment = self._make_successful_payment('10000.00', '00001')
        PaymentAllocation.objects.create(
            payment=payment, invoice=invoice, allocated_amount=Decimal('10000.00'),
        )
        self.assertEqual(get_invoice_balance(invoice), Decimal('23000.00'))

    def test_pending_payment_does_not_reduce_balance(self):
        from apps.finance.services import get_invoice_balance
        from apps.finance.models import Payment, PaymentStatus, PaymentMethod
        invoice = self._make_issued_invoice()
        Payment.objects.create(
            payment_reference='PAY-TEST-PEND1',
            enrollment=self.enrollment,
            amount=Decimal('10000.00'),
            method=PaymentMethod.MPESA,
            status=PaymentStatus.PENDING,
            currency='KES',
        )
        self.assertEqual(get_invoice_balance(invoice), Decimal('33000.00'))

    def test_balance_zero_when_fully_allocated(self):
        from apps.finance.services import get_invoice_balance
        from apps.finance.models import PaymentAllocation
        invoice = self._make_issued_invoice()
        payment = self._make_successful_payment('33000.00', '00002')
        PaymentAllocation.objects.create(
            payment=payment, invoice=invoice, allocated_amount=Decimal('33000.00'),
        )
        self.assertEqual(get_invoice_balance(invoice), Decimal('0.00'))

    def test_multiple_allocations_reduce_balance_correctly(self):
        from apps.finance.services import get_invoice_balance
        from apps.finance.models import PaymentAllocation
        invoice = self._make_issued_invoice()
        p1 = self._make_successful_payment('10000.00', 'A0001')
        p2 = self._make_successful_payment('8000.00', 'A0002')
        PaymentAllocation.objects.create(payment=p1, invoice=invoice, allocated_amount=Decimal('10000.00'))
        PaymentAllocation.objects.create(payment=p2, invoice=invoice, allocated_amount=Decimal('8000.00'))
        self.assertEqual(get_invoice_balance(invoice), Decimal('15000.00'))

    def test_balance_returns_decimal_type(self):
        from apps.finance.services import get_invoice_balance
        invoice = self._make_issued_invoice()
        balance = get_invoice_balance(invoice)
        self.assertIsInstance(balance, Decimal,
                              'get_invoice_balance() must return Decimal, not float')


# ─────────────────────────────────────────────────────────────
# Property 8: Enrollment Outstanding = Sum of Invoice Balances
# ─────────────────────────────────────────────────────────────

class EnrollmentOutstandingTest(FinanceTestMixin, TestCase):
    """
    Property 8: get_enrollment_outstanding() == sum(get_invoice_balance())
    for all non-VOID invoices on the enrollment.

    Validates: Requirement 5.9
    """

    def test_outstanding_is_sum_of_invoice_balances(self):
        from apps.finance.services import (
            create_invoice, issue_invoice,
            get_invoice_balance, get_enrollment_outstanding,
        )
        inv1 = issue_invoice(create_invoice(self.enrollment, self.fee_structure, self.staff_user), self.staff_user)
        inv2 = issue_invoice(create_invoice(self.enrollment, self.fee_structure, self.staff_user), self.staff_user)
        expected = get_invoice_balance(inv1) + get_invoice_balance(inv2)
        self.assertEqual(get_enrollment_outstanding(self.enrollment), expected)

    def test_void_invoices_excluded_from_outstanding(self):
        from apps.finance.services import (
            create_invoice, issue_invoice, void_invoice,
            get_invoice_balance, get_enrollment_outstanding,
        )
        inv1 = issue_invoice(create_invoice(self.enrollment, self.fee_structure, self.staff_user), self.staff_user)
        inv2 = issue_invoice(create_invoice(self.enrollment, self.fee_structure, self.staff_user), self.staff_user)
        void_invoice(inv2, self.staff_user, 'Testing exclusion')
        self.assertEqual(get_enrollment_outstanding(self.enrollment), get_invoice_balance(inv1))

    def test_no_invoices_returns_zero(self):
        from apps.finance.services import get_enrollment_outstanding
        self.assertEqual(get_enrollment_outstanding(self.enrollment), Decimal('0.00'))

    def test_outstanding_returns_decimal_type(self):
        from apps.finance.services import get_enrollment_outstanding
        result = get_enrollment_outstanding(self.enrollment)
        self.assertIsInstance(result, Decimal)


from django.db.models import Sum  # needed by payment allocation tests

# ─────────────────────────────────────────────────────────────
# Helpers shared by payment tests
# ─────────────────────────────────────────────────────────────

class PaymentTestMixin(FinanceTestMixin):
    """Extends FinanceTestMixin with payment/invoice helpers."""

    def _issued_invoice(self):
        from apps.finance.services import create_invoice, issue_invoice
        return issue_invoice(
            create_invoice(self.enrollment, self.fee_structure, self.staff_user),
            self.staff_user,
        )

    def _successful_payment(self, amount, suffix='X0001'):
        from apps.finance.models import Payment, PaymentStatus, PaymentMethod
        from django.utils import timezone
        return Payment.objects.create(
            payment_reference=f'PAY-TST-{suffix}',
            enrollment=self.enrollment,
            amount=Decimal(str(amount)),
            method=PaymentMethod.CASH,
            status=PaymentStatus.SUCCESSFUL,
            currency='KES',
            paid_at=timezone.now(),
        )

    def _pending_payment(self, amount, suffix='P0001'):
        from apps.finance.models import Payment, PaymentStatus, PaymentMethod
        return Payment.objects.create(
            payment_reference=f'PAY-PND-{suffix}',
            enrollment=self.enrollment,
            amount=Decimal(str(amount)),
            method=PaymentMethod.MPESA,
            status=PaymentStatus.PENDING,
            currency='KES',
        )


# ─────────────────────────────────────────────────────────────
# Property 11: Allocation Does Not Exceed Payment Amount
# ─────────────────────────────────────────────────────────────

class AllocationDoesNotExceedPaymentTest(PaymentTestMixin, TestCase):
    """Property 11. Validates: Requirements 3.6, 6.4, 17.1, 17.2"""

    def test_allocation_up_to_payment_amount_succeeds(self):
        from apps.finance.services import allocate_payment
        invoice = self._issued_invoice()
        payment = self._successful_payment('33000.00')
        alloc = allocate_payment(payment, invoice, Decimal('33000.00'), self.staff_user)
        self.assertEqual(alloc.allocated_amount, Decimal('33000.00'))

    def test_over_allocation_raises(self):
        from apps.finance.services import allocate_payment
        invoice = self._issued_invoice()
        payment = self._successful_payment('10000.00')
        with self.assertRaises(ValueError):
            allocate_payment(payment, invoice, Decimal('10001.00'), self.staff_user)

    def test_partial_then_over_allocation_raises(self):
        from apps.finance.services import allocate_payment
        invoice = self._issued_invoice()
        payment = self._successful_payment('33000.00')
        allocate_payment(payment, invoice, Decimal('20000.00'), self.staff_user)
        with self.assertRaises(ValueError):
            allocate_payment(payment, invoice, Decimal('15000.00'), self.staff_user)

    def test_sum_of_allocations_never_exceeds_payment(self):
        from apps.finance.services import allocate_payment
        from apps.finance.models import PaymentAllocation
        invoice1 = self._issued_invoice()
        invoice2 = self._issued_invoice()
        payment = self._successful_payment('33000.00')
        allocate_payment(payment, invoice1, Decimal('20000.00'), self.staff_user)
        allocate_payment(payment, invoice2, Decimal('13000.00'), self.staff_user)
        total = PaymentAllocation.objects.filter(payment=payment).aggregate(
            t=Sum('allocated_amount')
        )['t']
        self.assertLessEqual(total, payment.amount)


# ─────────────────────────────────────────────────────────────
# Property 12: Allocation Does Not Exceed Invoice Total
# ─────────────────────────────────────────────────────────────

class AllocationDoesNotExceedInvoiceTotalTest(PaymentTestMixin, TestCase):
    """Property 12. Validates: Requirements 3.7, 6.5, 17.1, 17.2"""

    def test_over_allocating_invoice_raises(self):
        from apps.finance.services import allocate_payment
        invoice = self._issued_invoice()  # total = 33,000
        payment = self._successful_payment('50000.00')
        with self.assertRaises(ValueError):
            allocate_payment(payment, invoice, Decimal('40000.00'), self.staff_user)

    def test_two_payments_over_allocating_invoice_raises(self):
        from apps.finance.services import allocate_payment
        invoice = self._issued_invoice()  # total = 33,000
        p1 = self._successful_payment('20000.00', 'B0001')
        p2 = self._successful_payment('20000.00', 'B0002')
        allocate_payment(p1, invoice, Decimal('20000.00'), self.staff_user)
        with self.assertRaises(ValueError):
            allocate_payment(p2, invoice, Decimal('15000.00'), self.staff_user)


# ─────────────────────────────────────────────────────────────
# Property 14: Only SUCCESSFUL Payments Can Be Allocated
# ─────────────────────────────────────────────────────────────

class OnlySuccessfulPaymentsAllocatableTest(PaymentTestMixin, TestCase):
    """Property 14. Validates: Requirement 3.5"""

    def test_pending_payment_raises(self):
        from apps.finance.services import allocate_payment
        invoice = self._issued_invoice()
        payment = self._pending_payment('10000.00')
        with self.assertRaises(ValueError):
            allocate_payment(payment, invoice, Decimal('10000.00'), self.staff_user)

    def test_failed_payment_raises(self):
        from apps.finance.services import allocate_payment
        from apps.finance.models import Payment, PaymentStatus, PaymentMethod
        invoice = self._issued_invoice()
        payment = Payment.objects.create(
            payment_reference='PAY-FAIL-00001',
            enrollment=self.enrollment,
            amount=Decimal('10000.00'),
            method=PaymentMethod.MPESA,
            status=PaymentStatus.FAILED,
            currency='KES',
        )
        with self.assertRaises(ValueError):
            allocate_payment(payment, invoice, Decimal('5000.00'), self.staff_user)

    def test_successful_payment_allocates(self):
        from apps.finance.services import allocate_payment
        invoice = self._issued_invoice()
        payment = self._successful_payment('10000.00', 'C0001')
        alloc = allocate_payment(payment, invoice, Decimal('10000.00'), self.staff_user)
        self.assertEqual(alloc.allocated_amount, Decimal('10000.00'))


# ─────────────────────────────────────────────────────────────
# Property 7: Invoice Status After Allocation
# ─────────────────────────────────────────────────────────────

class InvoiceStatusAfterAllocationTest(PaymentTestMixin, TestCase):
    """Property 7. Validates: Requirements 16.3, 16.4"""

    def test_partial_payment_sets_partially_paid(self):
        from apps.finance.services import allocate_payment
        from apps.finance.models import InvoiceStatus
        invoice = self._issued_invoice()
        payment = self._successful_payment('10000.00', 'D0001')
        allocate_payment(payment, invoice, Decimal('10000.00'), self.staff_user)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.PARTIALLY_PAID)

    def test_full_payment_sets_paid(self):
        from apps.finance.services import allocate_payment
        from apps.finance.models import InvoiceStatus
        invoice = self._issued_invoice()
        payment = self._successful_payment('33000.00', 'D0002')
        allocate_payment(payment, invoice, Decimal('33000.00'), self.staff_user)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.PAID)


# ─────────────────────────────────────────────────────────────
# Property 9: Overpayment Credit Preservation
# ─────────────────────────────────────────────────────────────

class OverpaymentCreditPreservationTest(PaymentTestMixin, TestCase):
    """Property 9. Validates: Requirements 6.7, 16.1"""

    def test_overpayment_allocates_full_invoice_leaves_credit(self):
        from apps.finance.services import auto_allocate_payment, get_invoice_balance
        from apps.finance.models import PaymentAllocation
        invoice = self._issued_invoice()   # total = 33,000
        payment = self._successful_payment('50000.00', 'E0001')
        allocations = auto_allocate_payment(payment)
        self.assertEqual(len(allocations), 1)
        # Invoice fully paid
        invoice.refresh_from_db()
        self.assertEqual(get_invoice_balance(invoice), Decimal('0.00'))
        # Total allocated = invoice total, not payment amount
        total_alloc = PaymentAllocation.objects.filter(payment=payment).aggregate(
            t=Sum('allocated_amount')
        )['t']
        self.assertEqual(total_alloc, Decimal('33000.00'))
        # Credit = 50,000 - 33,000 = 17,000 (unallocated, stays on payment)
        self.assertEqual(payment.amount - total_alloc, Decimal('17000.00'))

    def test_no_invoices_leaves_payment_unallocated(self):
        from apps.finance.services import auto_allocate_payment
        from apps.finance.models import PaymentAllocation
        payment = self._successful_payment('10000.00', 'E0002')
        allocations = auto_allocate_payment(payment)
        self.assertEqual(allocations, [])
        self.assertEqual(
            PaymentAllocation.objects.filter(payment=payment).count(), 0
        )


# ─────────────────────────────────────────────────────────────
# Property 10: Auto-Allocation Oldest-First Ordering
# ─────────────────────────────────────────────────────────────

class AutoAllocationOldestFirstTest(PaymentTestMixin, TestCase):
    """Property 10. Validates: Requirements 6.6, 16.2"""

    def test_oldest_invoice_allocated_first(self):
        from apps.finance.services import auto_allocate_payment, get_invoice_balance
        from apps.finance.models import PaymentAllocation
        import time

        inv1 = self._issued_invoice()
        time.sleep(0.01)  # ensure different timestamps
        inv2 = self._issued_invoice()

        # Payment enough for inv1 but not both
        payment = self._successful_payment('20000.00', 'F0001')
        auto_allocate_payment(payment)

        inv1.refresh_from_db()
        inv2.refresh_from_db()

        # inv1 (older) should be partially or fully paid
        self.assertIn(inv1.status, ['PARTIALLY_PAID', 'PAID'],
                      'Older invoice should receive allocation first')
        # inv2 (newer) should still be issued or get remainder
        alloc_inv1 = PaymentAllocation.objects.filter(
            payment=payment, invoice=inv1
        ).aggregate(t=Sum('allocated_amount'))['t'] or Decimal('0.00')
        alloc_inv2 = PaymentAllocation.objects.filter(
            payment=payment, invoice=inv2
        ).aggregate(t=Sum('allocated_amount'))['t'] or Decimal('0.00')
        # inv1 gets at least as much as inv2
        self.assertGreaterEqual(alloc_inv1, alloc_inv2,
                                'Older invoice must be allocated first')


# ─────────────────────────────────────────────────────────────
# Property 19: Decimal Arithmetic Precision
# ─────────────────────────────────────────────────────────────

class DecimalArithmeticPrecisionTest(PaymentTestMixin, TestCase):
    """Property 19. Validates: Requirement 17.3"""

    def test_balance_result_is_decimal(self):
        from apps.finance.services import get_invoice_balance
        invoice = self._issued_invoice()
        balance = get_invoice_balance(invoice)
        self.assertIsInstance(balance, Decimal)
        self.assertNotIsInstance(balance, float)

    def test_outstanding_result_is_decimal(self):
        from apps.finance.services import get_enrollment_outstanding
        result = get_enrollment_outstanding(self.enrollment)
        self.assertIsInstance(result, Decimal)

    def test_allocation_amount_stored_as_decimal(self):
        from apps.finance.services import allocate_payment
        from apps.finance.models import PaymentAllocation
        invoice = self._issued_invoice()
        payment = self._successful_payment('10000.00', 'G0001')
        allocate_payment(payment, invoice, Decimal('10000.00'), self.staff_user)
        alloc = PaymentAllocation.objects.get(payment=payment, invoice=invoice)
        self.assertIsInstance(alloc.allocated_amount, Decimal)

    def test_decimal_150_50_calculation(self):
        """Explicit: Decimal('100.00') + Decimal('50.50') == Decimal('150.50')"""
        result = Decimal('100.00') + Decimal('50.50')
        self.assertEqual(result, Decimal('150.50'))
        self.assertIsInstance(result, Decimal)

    def test_record_manual_payment_creates_receipt(self):
        from apps.finance.services import record_manual_payment
        from apps.finance.models import Receipt, PaymentMethod
        invoice = self._issued_invoice()
        payment = record_manual_payment(
            enrollment=self.enrollment,
            amount=Decimal('33000.00'),
            method=PaymentMethod.CASH,
            payer_name='Test Payer',
            recorded_by=self.staff_user,
        )
        self.assertTrue(hasattr(payment, 'receipt'))
        self.assertTrue(payment.receipt.receipt_number.startswith('RCP-'))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'PAID')
