"""
Modèles de Trésorerie — SakinaFinance
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class BankAccount(models.Model):
    """Compte bancaire réel lié à un compte comptable"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='bank_accounts')
    entity = models.ForeignKey('accounts.Entity', on_delete=models.CASCADE, related_name='bank_accounts')
    
    bank_name = models.CharField(max_length=150)
    account_name = models.CharField(max_length=150)
    iban = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, default='XOF')
    
    # Lien comptable (Classe 521 par exemple)
    accounting_account = models.ForeignKey('accounting.Account', on_delete=models.PROTECT, related_name='bank_accounts')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_name}"

class BankStatement(models.Model):
    """Relevé bancaire importé"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='statements')
    reference = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2)
    
    is_imported = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Relevé {self.reference} ({self.start_date} - {self.end_date})"

class BankStatementLine(models.Model):
    """Ligne de relevé bancaire"""
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='lines')
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    
    # Rapprochement
    is_reconciled = models.BooleanField(default=False)
    reconciled_transaction = models.ForeignKey('accounting.Transaction', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.date} : {self.amount} ({self.description[:30]})"

class BankReconciliation(models.Model):
    """Rapprochement bancaire périodique"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    period_end = models.DateField()
    
    account_balance = models.DecimalField(max_digits=15, decimal_places=2) # Solde comptable
    statement_balance = models.DecimalField(max_digits=15, decimal_places=2) # Solde relevé
    
    difference = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('draft', 'Brouillon'), ('validated', 'Validé')], default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
