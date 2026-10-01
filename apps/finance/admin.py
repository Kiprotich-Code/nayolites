from django.contrib import admin

from .models import (
    Invoice, InvoiceItem, Payment, PaymentAllocation,
    PaymentProviderTransaction, Receipt, SequenceCounter,
    FeeStructure, FeeItem,
)


class FeeItemInline(admin.TabularInline):
    model = FeeItem
    extra = 1
    fields = ['name', 'amount', 'order']


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'academic_period', 'currency', 'is_active', 'created_at']
    list_filter = ['is_active', 'course', 'academic_period']
    search_fields = ['name', 'course__name', 'course__code']
    inlines = [FeeItemInline]


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ['description', 'quantity', 'unit_amount', 'total_amount', 'fee_item_ref']
    can_delete = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'enrollment', 'status', 'currency', 'issued_at', 'due_date', 'created_at']
    list_filter = ['status', 'currency']
    search_fields = [
        'invoice_number',
        'enrollment__student__user__first_name',
        'enrollment__student__admission_number',
    ]
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    inlines = [InvoiceItemInline]


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    readonly_fields = ['invoice', 'allocated_amount', 'created_at', 'allocated_by']
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_reference', 'enrollment', 'amount', 'method', 'status', 'currency', 'paid_at', 'created_at']
    list_filter = ['status', 'method']
    search_fields = [
        'payment_reference',
        'enrollment__student__user__first_name',
        'enrollment__student__admission_number',
    ]
    readonly_fields = ['payment_reference', 'created_at', 'updated_at']
    inlines = [PaymentAllocationInline]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'payment', 'issued_at']
    search_fields = ['receipt_number', 'payment__payment_reference']
    readonly_fields = ['receipt_number', 'issued_at']


admin.site.register(SequenceCounter)
admin.site.register(PaymentProviderTransaction)
