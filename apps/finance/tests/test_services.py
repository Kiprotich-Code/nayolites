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
