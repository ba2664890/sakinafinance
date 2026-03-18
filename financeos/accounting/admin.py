"""
Admin configuration for Accounting Module
"""

from django.contrib import admin
from .models import Account, Journal, Transaction, TransactionLine, Invoice, InvoiceLine, FinancialStatement, TaxDeclaration

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
    hierarchy_fields = ['parent']

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
