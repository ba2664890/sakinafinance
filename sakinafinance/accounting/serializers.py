"""
Serializers for Accounting Module
"""

from rest_framework import serializers
from .models import Account, Journal, Transaction, TransactionLine, Invoice, InvoiceLine, FinancialStatement, TaxDeclaration


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Chart of Accounts"""
    account_class_display = serializers.CharField(source='get_account_class_display', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    
    class Meta:
        model = Account
        fields = [
            'id', 'code', 'name', 'name_en', 'account_class', 'account_class_display',
            'account_type', 'account_type_display', 'parent', 'level',
            'opening_balance', 'current_balance', 'is_active', 'description'
        ]
        read_only_fields = ['id', 'current_balance']


class JournalSerializer(serializers.ModelSerializer):
    """Serializer for Accounting Journals"""
    journal_type_display = serializers.CharField(source='get_journal_type_display', read_only=True)
    default_debit_account_name = serializers.CharField(source='default_debit_account.name', read_only=True)
    default_credit_account_name = serializers.CharField(source='default_credit_account.name', read_only=True)
    
    class Meta:
        model = Journal
        fields = [
            'id', 'code', 'name', 'journal_type', 'journal_type_display',
            'default_debit_account', 'default_debit_account_name',
            'default_credit_account', 'default_credit_account_name', 'is_active'
        ]


class TransactionLineSerializer(serializers.ModelSerializer):
    """Serializer for Transaction Lines"""
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    
    class Meta:
        model = TransactionLine
        fields = [
            'id', 'transaction', 'account', 'account_code', 'account_name',
            'debit', 'credit', 'description', 'partner_name'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transactions"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    journal_name = serializers.CharField(source='journal.name', read_only=True)
    lines = TransactionLineSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_balanced = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'reference', 'date', 'description', 'journal', 'journal_name',
            'total_debit', 'total_credit', 'currency', 'status', 'status_display',
            'lines', 'created_by', 'created_by_name', 'posted_by', 'posted_at',
            'source_document', 'created_at', 'is_balanced'
        ]
        read_only_fields = ['id', 'created_at', 'posted_at']


class InvoiceLineSerializer(serializers.ModelSerializer):
    """Serializer for Invoice Lines"""
    revenue_account_name = serializers.CharField(source='revenue_account.name', read_only=True)
    
    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'invoice', 'description', 'quantity', 'unit_price',
            'discount', 'tax_rate', 'tax_amount', 'total', 'revenue_account', 'revenue_account_name'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoices"""
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    days_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_type', 'invoice_type_display',
            'partner_name', 'partner_email', 'partner_address', 'partner_tax_id',
            'invoice_date', 'due_date', 'paid_date',
            'subtotal', 'tax_amount', 'total', 'amount_due', 'currency',
            'status', 'status_display', 'lines', 'notes', 'days_overdue'
        ]
        read_only_fields = ['id', 'amount_due']
    
    def get_days_overdue(self, obj):
        from django.utils import timezone
        if obj.status == Invoice.InvoiceStatus.SENT and obj.due_date:
            days = (timezone.now().date() - obj.due_date).days
            return max(0, days)
        return 0


class FinancialStatementSerializer(serializers.ModelSerializer):
    """Serializer for Financial Statements"""
    statement_type_display = serializers.CharField(source='get_statement_type_display', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = FinancialStatement
        fields = [
            'id', 'statement_type', 'statement_type_display',
            'period_start', 'period_end', 'data',
            'is_draft', 'is_consolidated',
            'generated_by', 'generated_by_name', 'generated_at'
        ]
        read_only_fields = ['id', 'generated_at']


class TaxDeclarationSerializer(serializers.ModelSerializer):
    """Serializer for Tax Declarations"""
    tax_type_display = serializers.CharField(source='get_tax_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TaxDeclaration
        fields = [
            'id', 'tax_type', 'tax_type_display', 'period_start', 'period_end',
            'tax_base', 'tax_rate', 'tax_amount',
            'status', 'status_display', 'submitted_at', 'paid_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
