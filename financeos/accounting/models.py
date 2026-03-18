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


# ─────────────────────────────────────────────────────────────────────────────
# IMMOBILISATIONS (FIXED ASSETS)
# ─────────────────────────────────────────────────────────────────────────────

class AssetCategory(models.Model):
    """Catégorie d'immobilisation"""

    class DepreciationMethod(models.TextChoices):
        LINEAR = 'linear', _('Linéaire')
        DECLINING = 'declining', _('Dégressif')
        UNITS = 'units', _('Unités de production')

    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='asset_categories'
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    useful_life_years = models.IntegerField(default=5)
    depreciation_method = models.CharField(
        max_length=20, choices=DepreciationMethod.choices, default=DepreciationMethod.LINEAR
    )
    depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20)

    # Default accounts
    asset_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='category_asset'
    )
    depreciation_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='category_depreciation'
    )
    accumulated_depreciation_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='category_accum_depreciation'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} — {self.name}"


class FixedAsset(models.Model):
    """Immobilisation"""

    class Status(models.TextChoices):
        ACTIVE = 'active', _('En service')
        IDLE = 'idle', _('Non utilisé')
        UNDER_REPAIR = 'under_repair', _('En réparation')
        DISPOSED = 'disposed', _('Cédé')
        FULLY_DEPRECIATED = 'fully_depreciated', _('Totalement amorti')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='fixed_assets'
    )
    entity = models.ForeignKey(
        'accounts.Entity', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fixed_assets'
    )
    category = models.ForeignKey(
        AssetCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assets'
    )

    # Identification
    asset_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)

    # Acquisition
    acquisition_date = models.DateField()
    acquisition_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    residual_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')

    # Depreciation
    useful_life_years = models.IntegerField(default=5)
    depreciation_method = models.CharField(
        max_length=20,
        choices=AssetCategory.DepreciationMethod.choices,
        default=AssetCategory.DepreciationMethod.LINEAR
    )
    depreciation_start_date = models.DateField()
    accumulated_depreciation = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_book_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Disposal
    disposal_date = models.DateField(null=True, blank=True)
    disposal_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    disposal_gain_loss = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    linked_transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['asset_code']

    def __str__(self):
        return f"{self.asset_code} — {self.name}"

    def depreciable_amount(self):
        return self.acquisition_cost - self.residual_value

    def annual_depreciation(self):
        """Calcule l'amortissement annuel selon la méthode"""
        if self.useful_life_years <= 0:
            return 0
        if self.depreciation_method == 'linear':
            return round(self.depreciable_amount() / self.useful_life_years, 2)
        elif self.depreciation_method == 'declining':
            rate = 2 / self.useful_life_years  # Double declining
            return round(float(self.net_book_value) * rate, 2)
        return 0

    def monthly_depreciation(self):
        return round(float(self.annual_depreciation()) / 12, 2)

    def save(self, *args, **kwargs):
        self.net_book_value = self.acquisition_cost - self.accumulated_depreciation
        super().save(*args, **kwargs)


class AssetDepreciation(models.Model):
    """Ligne d'amortissement mensuel"""

    asset = models.ForeignKey(
        FixedAsset, on_delete=models.CASCADE, related_name='depreciations'
    )
    period = models.DateField()  # Premier jour du mois
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    accumulated = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_book_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    linked_transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_posted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['asset', 'period']
        ordering = ['period']

    def __str__(self):
        return f"{self.asset} — {self.period} — {self.amount}"


# ─────────────────────────────────────────────────────────────────────────────
# CONSOLIDATION GROUPE (IFRS 10)
# ─────────────────────────────────────────────────────────────────────────────

class InterCompanyElimination(models.Model):
    """Élimination des flux inter-compagnies (IFRS 10)"""

    class EliminationType(models.TextChoices):
        RECEIVABLE_PAYABLE = 'receivable_payable', _('Créances / Dettes intra-groupe')
        REVENUE_EXPENSE = 'revenue_expense', _('Produits / Charges intra-groupe')
        INVESTMENT = 'investment', _('Titres de participation')
        DIVIDEND = 'dividend', _('Dividendes intra-groupe')
        UNREALIZED_PROFIT = 'unrealized_profit', _('Bénéfices non réalisés')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='eliminations'
    )
    elimination_type = models.CharField(max_length=30, choices=EliminationType.choices)

    # Entities involved
    entity_source = models.ForeignKey(
        'accounts.Entity', on_delete=models.CASCADE, related_name='eliminations_source'
    )
    entity_target = models.ForeignKey(
        'accounts.Entity', on_delete=models.CASCADE, related_name='eliminations_target'
    )

    # Period
    period_start = models.DateField()
    period_end = models.DateField()

    # Amount
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')

    # Accounts
    debit_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='elimination_debit'
    )
    credit_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='elimination_credit'
    )

    description = models.TextField(blank=True)
    is_posted = models.BooleanField(default=False)
    linked_transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_end', 'elimination_type']

    def __str__(self):
        return (
            f"{self.get_elimination_type_display()} — "
            f"{self.entity_source} → {self.entity_target} — {self.amount}"
        )


class ConsolidationReport(models.Model):
    """Rapport de consolidation groupe"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        IN_REVIEW = 'in_review', _('En revue')
        APPROVED = 'approved', _('Approuvé')
        PUBLISHED = 'published', _('Publié')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='consolidation_reports'
    )
    period_start = models.DateField()
    period_end = models.DateField()
    title = models.CharField(max_length=255)

    # Scope
    included_entities = models.ManyToManyField(
        'accounts.Entity', blank=True, related_name='consolidation_reports'
    )
    accounting_standard = models.CharField(
        max_length=20,
        choices=[
            ('ifrs', 'IFRS'), ('ohada', 'OHADA'), ('syscohada', 'SYSCOHADA')
        ],
        default='ifrs'
    )

    # Financial data
    consolidated_data = models.JSONField(default=dict, blank=True)
    eliminations_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    consolidated_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    consolidated_net_income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    consolidated_total_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_consolidations'
    )

    class Meta:
        ordering = ['-period_end']

    def __str__(self):
        return f"{self.title} — {self.period_start} → {self.period_end}"
