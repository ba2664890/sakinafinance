"""
Procurement Admin — FinanceOS IA
"""
from django.contrib import admin
from .models import (
    SupplierCategory, Supplier, PurchaseRFQ,
    PurchaseOrder, PurchaseOrderLine, GoodsReceipt,
    InventoryItem, StockTransaction
)


@admin.register(SupplierCategory)
class SupplierCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company']
    list_filter = ['company']
    search_fields = ['name', 'code']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'country', 'email', 'phone',
        'rating', 'total_spend', 'total_orders', 'status'
    ]
    list_filter = ['company', 'status', 'category', 'country']
    search_fields = ['name', 'tax_id', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'total_spend', 'total_orders']
    fieldsets = (
        ('Identification', {
            'fields': ('company', 'category', 'supplier_code', 'name', 'legal_name', 'status')
        }),
        ('Enregistrement', {
            'fields': ('tax_id', 'trade_register', 'vat_number')
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'website', 'address', 'city', 'country',
                       'contact_name', 'contact_email', 'contact_phone')
        }),
        ('Conditions Commerciales', {
            'fields': ('payment_terms_days', 'currency', 'credit_limit',
                       'bank_name', 'account_number', 'iban')
        }),
        ('Performance', {
            'fields': ('rating', 'on_time_delivery_pct', 'total_spend', 'total_orders')
        }),
    )


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1
    fields = ['product_name', 'quantity', 'unit', 'unit_price', 'discount_pct', 'tax_rate', 'line_total']
    readonly_fields = ['line_total', 'tax_amount']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'supplier', 'order_date', 'expected_delivery',
        'total', 'currency', 'status', 'priority'
    ]
    list_filter = ['company', 'status', 'priority', 'currency']
    search_fields = ['reference', 'supplier__name']
    readonly_fields = ['created_at', 'updated_at', 'subtotal', 'tax_amount', 'total']
    inlines = [PurchaseOrderLineInline]
    actions = ['approve_orders']

    def approve_orders(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', approved_by=request.user, approved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} commande(s) approuvée(s).")
    approve_orders.short_description = "Approuver les commandes sélectionnées"


@admin.register(PurchaseRFQ)
class PurchaseRFQAdmin(admin.ModelAdmin):
    list_display = ['reference', 'title', 'estimated_budget', 'deadline', 'responses_count', 'status']
    list_filter = ['company', 'status']
    search_fields = ['reference', 'title']
    filter_horizontal = ['invited_suppliers']


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ['reference', 'purchase_order', 'receipt_date', 'received_by', 'status']
    list_filter = ['status']
    search_fields = ['reference']
    readonly_fields = ['created_at']


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'item_type', 'current_stock', 'unit_measure', 'unit_cost', 'is_active']
    list_filter = ['company', 'item_type', 'is_active']
    search_fields = ['sku', 'name']
    readonly_fields = ['current_stock', 'created_at', 'updated_at']


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'item', 'transaction_type', 'quantity', 'unit_cost', 'reference']
    list_filter = ['transaction_type']
    search_fields = ['item__name', 'reference']
    readonly_fields = ['timestamp']
