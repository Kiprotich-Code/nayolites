"""
Unit tests for finance model field definitions and Meta permissions.

These tests use model introspection (_meta API) so no database fixtures
are required for most assertions.

Requirements: 20.1
"""
from django.db import models as django_models
from django.test import TestCase

from apps.finance.models import (
    FeeItem,
    FeeStructure,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    PaymentProviderTransaction,
    PaymentStatus,
    Receipt,
    SequenceCounter,
)


# ─────────────────────────────────────────────────────────────
# FeeStructure
# ─────────────────────────────────────────────────────────────

class FeeStructureModelTest(TestCase):

    def test_custom_permissions(self):
        perms = dict(FeeStructure._meta.permissions)
        self.assertIn('activate_feestructure', perms)
        self.assertEqual(perms['activate_feestructure'], 'Can activate/deactivate fee structure')

    def test_ordering(self):
        self.assertEqual(FeeStructure._meta.ordering, ['-created_at'])

    def test_verbose_name(self):
        self.assertEqual(FeeStructure._meta.verbose_name, 'fee structure')
        self.assertEqual(FeeStructure._meta.verbose_name_plural, 'fee structures')


# ─────────────────────────────────────────────────────────────
# FeeItem
# ─────────────────────────────────────────────────────────────

class FeeItemModelTest(TestCase):

    def test_ordering(self):
        self.assertEqual(FeeItem._meta.ordering, ['order', 'id'])

    def test_amount_is_decimal_field(self):
        field = FeeItem._meta.get_field('amount')
        self.assertIsInstance(field, django_models.DecimalField)
        self.assertEqual(field.max_digits, 12)
        self.assertEqual(field.decimal_places, 2)

    def test_name_max_length(self):
        field = FeeItem._meta.get_field('name')
        self.assertEqual(field.max_length, 200)

    def test_order_default(self):
        field = FeeItem._meta.get_field('order')
        self.assertIsInstance(field, django_models.PositiveIntegerField)
        self.assertEqual(field.default, 0)


# ─────────────────────────────────────────────────────────────
# InvoiceStatus choices
# ─────────────────────────────────────────────────────────────

class InvoiceStatusChoicesTest(TestCase):

    def test_all_required_choices_present(self):
        values = [choice[0] for choice in InvoiceStatus.choices]
        self.assertIn('DRAFT', values)
        self.assertIn('ISSUED', values)
        self.assertIn('PARTIALLY_PAID', values)
        self.assertIn('PAID', values)
        self.assertIn('OVERDUE', values)
        self.assertIn('VOID', values)

    def test_choice_count(self):
        self.assertEqual(len(InvoiceStatus.choices), 6)


# ─────────────────────────────────────────────────────────────
# Invoice
# ─────────────────────────────────────────────────────────────

class InvoiceModelTest(TestCase):

    def test_custom_permissions(self):
        perms = dict(Invoice._meta.permissions)
        self.assertIn('issue_invoice', perms)
        self.assertIn('void_invoice', perms)
        self.assertEqual(perms['issue_invoice'], 'Can issue invoice')
        self.assertEqual(perms['void_invoice'], 'Can void invoice')

    def test_invoice_number_is_unique(self):
        field = Invoice._meta.get_field('invoice_number')
        self.assertTrue(field.unique)

    def test_invoice_number_max_length(self):
        field = Invoice._meta.get_field('invoice_number')
        self.assertEqual(field.max_length, 20)

    def test_status_max_length(self):
        field = Invoice._meta.get_field('status')
        self.assertEqual(field.max_length, 15)

    def test_status_default(self):
        field = Invoice._meta.get_field('status')
        self.assertEqual(field.default, InvoiceStatus.DRAFT)

    def test_ordering(self):
        self.assertEqual(Invoice._meta.ordering, ['-created_at'])


# ─────────────────────────────────────────────────────────────
# PaymentStatus choices
# ─────────────────────────────────────────────────────────────

class PaymentStatusChoicesTest(TestCase):

    def test_all_required_choices_present(self):
        values = [choice[0] for choice in PaymentStatus.choices]
        self.assertIn('PENDING', values)
        self.assertIn('SUCCESSFUL', values)
        self.assertIn('FAILED', values)
        self.assertIn('CANCELLED', values)
        self.assertIn('REVERSED', values)

    def test_choice_count(self):
        self.assertEqual(len(PaymentStatus.choices), 5)


# ─────────────────────────────────────────────────────────────
# PaymentMethod choices
# ─────────────────────────────────────────────────────────────

class PaymentMethodChoicesTest(TestCase):

    def test_all_required_choices_present(self):
        values = [choice[0] for choice in PaymentMethod.choices]
        self.assertIn('MPESA', values)
        self.assertIn('BANK', values)
        self.assertIn('CASH', values)
        self.assertIn('OTHER', values)

    def test_choice_count(self):
        self.assertEqual(len(PaymentMethod.choices), 4)


# ─────────────────────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────────────────────

class PaymentModelTest(TestCase):

    def test_custom_permissions(self):
        perms = dict(Payment._meta.permissions)
        self.assertIn('reverse_payment', perms)
        self.assertIn('allocate_payment', perms)
        self.assertEqual(perms['reverse_payment'], 'Can reverse payment')
        self.assertEqual(perms['allocate_payment'], 'Can allocate payment')

    def test_amount_is_decimal_field(self):
        field = Payment._meta.get_field('amount')
        self.assertIsInstance(field, django_models.DecimalField)
        self.assertEqual(field.max_digits, 12)
        self.assertEqual(field.decimal_places, 2)

    def test_payment_reference_is_unique(self):
        field = Payment._meta.get_field('payment_reference')
        self.assertTrue(field.unique)

    def test_payment_reference_max_length(self):
        field = Payment._meta.get_field('payment_reference')
        self.assertEqual(field.max_length, 20)

    def test_status_default(self):
        field = Payment._meta.get_field('status')
        self.assertEqual(field.default, PaymentStatus.PENDING)

    def test_ordering(self):
        self.assertEqual(Payment._meta.ordering, ['-created_at'])


# ─────────────────────────────────────────────────────────────
# Receipt
# ─────────────────────────────────────────────────────────────

class ReceiptModelTest(TestCase):

    def test_payment_is_one_to_one(self):
        field = Receipt._meta.get_field('payment')
        self.assertIsInstance(field, django_models.OneToOneField)

    def test_receipt_number_is_unique(self):
        field = Receipt._meta.get_field('receipt_number')
        self.assertTrue(field.unique)

    def test_receipt_number_max_length(self):
        field = Receipt._meta.get_field('receipt_number')
        self.assertEqual(field.max_length, 20)

    def test_ordering(self):
        self.assertEqual(Receipt._meta.ordering, ['-issued_at'])


# ─────────────────────────────────────────────────────────────
# PaymentProviderTransaction
# ─────────────────────────────────────────────────────────────

class PaymentProviderTransactionModelTest(TestCase):

    def test_provider_tx_id_is_unique(self):
        field = PaymentProviderTransaction._meta.get_field('provider_tx_id')
        self.assertTrue(field.unique)

    def test_provider_tx_id_max_length(self):
        field = PaymentProviderTransaction._meta.get_field('provider_tx_id')
        self.assertEqual(field.max_length, 100)

    def test_raw_metadata_is_json_field(self):
        field = PaymentProviderTransaction._meta.get_field('raw_metadata')
        self.assertIsInstance(field, django_models.JSONField)


# ─────────────────────────────────────────────────────────────
# SequenceCounter
# ─────────────────────────────────────────────────────────────

class SequenceCounterModelTest(TestCase):

    def test_unique_together_includes_prefix_year(self):
        unique_together = SequenceCounter._meta.unique_together
        self.assertIn(('prefix', 'year'), unique_together)

    def test_prefix_max_length(self):
        field = SequenceCounter._meta.get_field('prefix')
        self.assertEqual(field.max_length, 10)

    def test_last_value_default(self):
        field = SequenceCounter._meta.get_field('last_value')
        self.assertIsInstance(field, django_models.PositiveIntegerField)
        self.assertEqual(field.default, 0)

    def test_verbose_name(self):
        self.assertEqual(SequenceCounter._meta.verbose_name, 'sequence counter')
        self.assertEqual(SequenceCounter._meta.verbose_name_plural, 'sequence counters')
