"""
Admin configuration for Accounting Module
"""

from django.contrib import admin
from .models import (
    Account, Journal, Transaction, TransactionLine,
    Invoice, InvoiceLine, FinancialStatement, TaxDeclaration,
    AssetCategory, FixedAsset, AssetDepreciation,
    InterCompanyElimination, ConsolidationReport
)


class TransactionLineInline(admin.TabularInline):
    model = TransactionLine
    extra = 1


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_class', 'account_type', 'company', 'current_balance', 'is_active']
    list_filter = ['account_class', 'account_type', 'company', 'is_active']
    search_fields = ['code', 'name']


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'journal_type', 'company', 'is_active']
    list_filter = ['journal_type', 'company', 'is_active']
    search_fields = ['code', 'name']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reference', 'date', 'journal', 'total_debit', 'total_credit', 'status', 'company']
    list_filter = ['status', 'journal', 'company', 'date']
    search_fields = ['reference', 'description']
    inlines = [TransactionLineInline]
    date_hierarchy = 'date'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'partner_name', 'invoice_type', 'invoice_date', 'total', 'status', 'company']
    list_filter = ['invoice_type', 'status', 'company', 'invoice_date']
    search_fields = ['invoice_number', 'partner_name']
    inlines = [InvoiceLineInline]
    date_hierarchy = 'invoice_date'


@admin.register(FinancialStatement)
class FinancialStatementAdmin(admin.ModelAdmin):
    list_display = ['statement_type', 'period_start', 'period_end', 'company', 'is_draft']
    list_filter = ['statement_type', 'company', 'is_draft']
    date_hierarchy = 'period_end'


@admin.register(TaxDeclaration)
class TaxDeclarationAdmin(admin.ModelAdmin):
    list_display = ['tax_type', 'period_start', 'period_end', 'tax_amount', 'status', 'company']
    list_filter = ['tax_type', 'status', 'company']
    date_hierarchy = 'period_end'


# ─── IMMOBILISATIONS ─────────────────────────────────────────────────────────

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'useful_life_years', 'depreciation_method', 'depreciation_rate']
    list_filter = ['company', 'depreciation_method']
    search_fields = ['name', 'code']


class AssetDepreciationInline(admin.TabularInline):
    model = AssetDepreciation
    extra = 0
    fields = ['period', 'amount', 'accumulated', 'net_book_value', 'is_posted']
    readonly_fields = ['accumulated', 'net_book_value']


@admin.register(FixedAsset)
class FixedAssetAdmin(admin.ModelAdmin):
    list_display = [
        'asset_code', 'name', 'category', 'acquisition_date',
        'acquisition_cost', 'accumulated_depreciation', 'net_book_value', 'status'
    ]
    list_filter = ['company', 'status', 'category', 'depreciation_method']
    search_fields = ['asset_code', 'name', 'serial_number']
    readonly_fields = ['net_book_value', 'created_at', 'updated_at']
    inlines = [AssetDepreciationInline]
    fieldsets = (
        ('Identification', {
            'fields': ('company', 'entity', 'category', 'asset_code', 'name', 'description', 'serial_number', 'location')
        }),
        ('Acquisition', {
            'fields': ('acquisition_date', 'acquisition_cost', 'residual_value', 'currency')
        }),
        ('Amortissement', {
            'fields': ('useful_life_years', 'depreciation_method', 'depreciation_start_date',
                       'accumulated_depreciation', 'net_book_value')
        }),
        ('Cession', {
            'fields': ('disposal_date', 'disposal_amount', 'disposal_gain_loss', 'status')
        }),
    )


@admin.register(AssetDepreciation)
class AssetDepreciationAdmin(admin.ModelAdmin):
    list_display = ['asset', 'period', 'amount', 'accumulated', 'net_book_value', 'is_posted']
    list_filter = ['is_posted', 'asset__company']
    search_fields = ['asset__name', 'asset__asset_code']
    date_hierarchy = 'period'


# ─── CONSOLIDATION GROUPE ─────────────────────────────────────────────────────

@admin.register(InterCompanyElimination)
class InterCompanyEliminationAdmin(admin.ModelAdmin):
    list_display = [
        'elimination_type', 'entity_source', 'entity_target',
        'period_start', 'period_end', 'amount', 'currency', 'is_posted'
    ]
    list_filter = ['elimination_type', 'company', 'is_posted']
    search_fields = ['description']
    readonly_fields = ['created_at']


@admin.register(ConsolidationReport)
class ConsolidationReportAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'company', 'period_start', 'period_end',
        'accounting_standard', 'consolidated_revenue', 'consolidated_net_income', 'status'
    ]
    list_filter = ['company', 'status', 'accounting_standard']
    search_fields = ['title']
    filter_horizontal = ['included_entities']
    readonly_fields = ['generated_at']

