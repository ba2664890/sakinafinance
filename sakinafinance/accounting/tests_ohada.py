
from django.test import TestCase
from django.utils import timezone
from .models import Account, Transaction, TransactionLine, Journal
from sakinafinance.accounts.models import Company, Entity
from sakinafinance.accounting.services import post_transaction, refresh_current_balances
from decimal import Decimal

class OHADABackendTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.entity = Entity.objects.create(company=self.company, name="Test Entity")
        self.journal = Journal.objects.create(company=self.company, name="OD", code="OD", journal_type='od')
        
        self.acc_asset = Account.objects.create(
            company=self.company, code="211", name="Matériel", 
            account_type='asset', account_class='class_2'
        )
        self.acc_cash = Account.objects.create(
            company=self.company, code="521", name="Banque", 
            account_type='asset', account_class='class_5'
        )

    def test_automatic_balance_refresh(self):
        """Vérifie que post_transaction recalcule bien les soldes"""
        tx = Transaction.objects.create(
            company=self.company, journal=self.journal, 
            reference="TX001", date=timezone.now().date(),
            status='pending', total_debit=1000, total_credit=1000
        )
        TransactionLine.objects.create(transaction=tx, account=self.acc_asset, debit=1000, credit=0)
        TransactionLine.objects.create(transaction=tx, account=self.acc_cash, debit=0, credit=1000)
        
        # Avant validation
        self.assertEqual(Account.objects.get(id=self.acc_asset.id).current_balance, 0)
        
        # Validation
        post_transaction(tx)
        
        # Après validation
        self.acc_asset.refresh_from_db()
        self.acc_cash.refresh_from_db()
        self.assertEqual(self.acc_asset.current_balance, 1000)
        self.assertEqual(self.acc_cash.current_balance, -1000)
