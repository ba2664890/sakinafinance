"""
Accounting Models - Comptabilité OHADA/IFRS
FinanceOS IA - Système d'Intelligence Financière Universel
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Account(models.Model):
    """Chart of Accounts - Plan Comptable"""
    
    class AccountClass(models.TextChoices):
        CLASS_1 = '1', _('Comptes de ressources durables')
        CLASS_2 = '2', _('Comptes d\'actif immobilisé')
        CLASS_3 = '3', _('Comptes de stocks')
        CLASS_4 = '4', _('Comptes de tiers')
        CLASS_5 = '5', _('Comptes de trésorerie')
        CLASS_6 = '6', _('Comptes de charges')
        CLASS_7 = '7', _('Comptes de produits')
        CLASS_8 = '8', _('Comptes de résultat')
    
    class AccountType(models.TextChoices):
        ASSET = 'asset', _('Actif')
        LIABILITY = 'liability', _('Passif')
        EQUITY = 'equity', _('Capitaux propres')
        INCOME = 'income', _('Produits')
        EXPENSE = 'expense', _('Charges')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    entity = models.ForeignKey(
        'accounts.Entity',
        on_delete=models.CASCADE,
        related_name='accounts',
        null=True,
        blank=True
    )
    
    # Account Details
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True)
    
    # Classification
    account_class = models.CharField(max_length=1, choices=AccountClass.choices)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    
    # Hierarchy
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    level = models.IntegerField(default=1)
    
    # Balance
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    
    # Metadata
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_full_code(self):
        return self.code


class Journal(models.Model):
    """Accounting Journal"""
    
    class JournalType(models.TextChoices):
        PURCHASES = 'purchases', _('Achats')
        SALES = 'sales', _('Ventes')
        BANK = 'bank', _('Banque')
        CASH = 'cash', _('Caisse')
        OD = 'od', _('Opérations Diverses')
        PAYROLL = 'payroll', _('Paie')
        INVENTORY = 'inventory', _('Stocks')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='journals'
    )
    entity = models.ForeignKey(
        'accounts.Entity',
        on_delete=models.CASCADE,
        related_name='journals',
        null=True,
        blank=True
    )
    
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    journal_type = models.CharField(max_length=20, choices=JournalType.choices)
    
    # Default accounts
    default_debit_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_debit_journal'
    )
    default_credit_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_credit_journal'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Transaction(models.Model):
    """Accounting Transaction"""
    
    class TransactionStatus(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        PENDING = 'pending', _('En attente')
        POSTED = 'posted', _('Validé')
        CANCELLED = 'cancelled', _('Annulé')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    entity = models.ForeignKey(
        'accounts.Entity',
        on_delete=models.CASCADE,
        related_name='transactions',
        null=True,
        blank=True
    )
    journal = models.ForeignKey(
        Journal,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    # Transaction Details
    reference = models.CharField(max_length=50)
    date = models.DateField()
    description = models.TextField()
    
    # Amounts
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.DRAFT
    )
    
    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_transactions'
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_transactions'
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    source_document = models.CharField(max_length=100, blank=True)
    source_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.reference} - {self.date} - {self.description[:50]}"
    
    def is_balanced(self):
        return self.total_debit == self.total_credit


class TransactionLine(models.Model):
    """Transaction Line Item"""
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='transaction_lines'
    )
    
    # Amounts
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Description
    description = models.TextField(blank=True)
    
    # Third party
    partner_type = models.CharField(max_length=50, blank=True)
    partner_id = models.CharField(max_length=100, blank=True)
    partner_name = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.account.code} - D:{self.debit} C:{self.credit}"


class Invoice(models.Model):
    """Customer/Supplier Invoice"""
    
    class InvoiceType(models.TextChoices):
        CUSTOMER = 'customer', _('Client')
        SUPPLIER = 'supplier', _('Fournisseur')
    
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        SENT = 'sent', _('Envoyée')
        PAID = 'paid', _('Payée')
        OVERDUE = 'overdue', _('En retard')
        CANCELLED = 'cancelled', _('Annulée')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    entity = models.ForeignKey(
        'accounts.Entity',
        on_delete=models.CASCADE,
        related_name='invoices',
        null=True,
        blank=True
    )
    
    # Invoice Details
    invoice_number = models.CharField(max_length=50)
    invoice_type = models.CharField(max_length=20, choices=InvoiceType.choices)
    
    # Partner
    partner_name = models.CharField(max_length=255)
    partner_email = models.EmailField(blank=True)
    partner_address = models.TextField(blank=True)
    partner_tax_id = models.CharField(max_length=50, blank=True)
    
    # Dates
    invoice_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_due = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT
    )
    
    # Linked Transaction
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice'
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['company', 'invoice_number']
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"{self.invoice_number} - {self.partner_name} - {self.total}"


class InvoiceLine(models.Model):
    """Invoice Line Item"""
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Tax
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Total
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Account
    revenue_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['id']


class FinancialStatement(models.Model):
    """Financial Statement (Bilan, CR, TFT)"""
    
    class StatementType(models.TextChoices):
        BALANCE_SHEET = 'balance_sheet', _('Bilan')
        INCOME_STATEMENT = 'income_statement', _('Compte de Résultat')
        CASH_FLOW = 'cash_flow', _('Tableau des Flux de Trésorerie')
        EQUITY = 'equity', _('Tableau des Capitaux Propres')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='financial_statements'
    )
    entity = models.ForeignKey(
        'accounts.Entity',
        on_delete=models.CASCADE,
        related_name='financial_statements',
        null=True,
        blank=True
    )
    
    statement_type = models.CharField(max_length=30, choices=StatementType.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Data
    data = models.JSONField(default=dict)
    
    # Status
    is_draft = models.BooleanField(default=True)
    is_consolidated = models.BooleanField(default=False)
    
    # Audit
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-period_end']
    
    def __str__(self):
        return f"{self.get_statement_type_display()} - {self.period_start} to {self.period_end}"


class TaxDeclaration(models.Model):
    """Tax Declaration"""
    
    class TaxType(models.TextChoices):
        VAT = 'vat', _('TVA')
        INCOME = 'income', _('Impôt sur les Bénéfices')
        PAYROLL = 'payroll', _('Impôt sur les Salaires')
        WITHHOLDING = 'withholding', _('Retenue à la source')
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        SUBMITTED = 'submitted', _('Soumise')
        PAID = 'paid', _('Payée')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='tax_declarations'
    )
    entity = models.ForeignKey(
        'accounts.Entity',
        on_delete=models.CASCADE,
        related_name='tax_declarations',
        null=True,
        blank=True
    )
    
    tax_type = models.CharField(max_length=20, choices=TaxType.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Amounts
    tax_base = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Submission
    submitted_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-period_end']
    
    def __str__(self):
        return f"{self.get_tax_type_display()} - {self.period_start} to {self.period_end}"
