import json
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from sakinafinance.accounting.models import Account, Journal, Transaction, TransactionLine
from sakinafinance.accounts.models import Company, User


class AccountingSecurityAndDataTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Alpha')
        self.other_company = Company.objects.create(name='Beta')
        self.user = User.objects.create_user(
            email='finance@alpha.test',
            password='testpass123',
            first_name='Alpha',
            last_name='Finance',
            company=self.company,
            role=User.Role.CFO,
        )
        self.client.force_login(self.user)

        self.cash = Account.objects.create(
            company=self.company,
            code='521000',
            name='Banque',
            account_class=Account.AccountClass.CLASS_5,
            account_type=Account.AccountType.ASSET,
            opening_balance=Decimal('1000.00'),
        )
        self.equity = Account.objects.create(
            company=self.company,
            code='101000',
            name='Capital',
            account_class=Account.AccountClass.CLASS_1,
            account_type=Account.AccountType.EQUITY,
            opening_balance=Decimal('1000.00'),
        )
        self.revenue = Account.objects.create(
            company=self.company,
            code='701000',
            name='Ventes',
            account_class=Account.AccountClass.CLASS_7,
            account_type=Account.AccountType.INCOME,
        )
        self.journal = Journal.objects.create(
            company=self.company,
            code='OD',
            name='Opérations Diverses',
            journal_type=Journal.JournalType.OD,
        )

    def test_accounting_api_uses_real_balances_without_demo_fallback(self):
        response = self.client.get(reverse('api_accounting_data'))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['total_assets'], 1000.0)
        self.assertEqual(payload['equity'], 1000.0)
        self.assertEqual(payload['total_liabilities'], 0.0)
        self.assertEqual(payload['journal_entries'], [])
        self.assertFalse(payload['quality']['is_reliable'])

    def test_account_viewset_forces_company_scope_on_create(self):
        response = self.client.post(
            reverse('account-list'),
            data={
                'code': '401000',
                'name': 'Fournisseurs',
                'account_class': Account.AccountClass.CLASS_4,
                'account_type': Account.AccountType.LIABILITY,
            },
        )

        self.assertEqual(response.status_code, 201)
        account = Account.objects.get(code='401000')
        self.assertEqual(account.company, self.company)

    def test_create_transaction_rejects_unbalanced_lines(self):
        response = self.client.post(
            reverse('api_create_transaction'),
            data=json.dumps({
                'journal': str(self.journal.id),
                'reference': 'MAN-1',
                'date': '2026-04-02',
                'description': 'Ecriture non équilibrée',
                'lines': [
                    {'account': self.cash.code, 'debit': 100, 'credit': 0},
                    {'account': self.revenue.code, 'debit': 0, 'credit': 50},
                ],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("équilibrée", response.json()['message'])

    def test_create_transaction_requires_csrf_token(self):
        secured_client = Client(enforce_csrf_checks=True)
        secured_client.force_login(self.user)

        page_response = secured_client.get(reverse('accounting'))
        self.assertEqual(page_response.status_code, 200)

        response = secured_client.post(
            reverse('api_create_transaction'),
            data=json.dumps({
                'journal': str(self.journal.id),
                'reference': 'MAN-2',
                'date': '2026-04-02',
                'description': 'Ecriture équilibrée',
                'lines': [
                    {'account': self.cash.code, 'debit': 100, 'credit': 0},
                    {'account': self.revenue.code, 'debit': 0, 'credit': 100},
                ],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)


class ReportingDataTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Gamma')
        self.user = User.objects.create_user(
            email='reporting@gamma.test',
            password='testpass123',
            first_name='Gamma',
            last_name='Reporting',
            company=self.company,
            role=User.Role.CFO,
        )
        self.client.force_login(self.user)
        self.cash = Account.objects.create(
            company=self.company,
            code='521100',
            name='Banque',
            account_class=Account.AccountClass.CLASS_5,
            account_type=Account.AccountType.ASSET,
        )
        self.revenue = Account.objects.create(
            company=self.company,
            code='701100',
            name='Prestations',
            account_class=Account.AccountClass.CLASS_7,
            account_type=Account.AccountType.INCOME,
        )
        self.journal = Journal.objects.create(
            company=self.company,
            code='VEN',
            name='Ventes',
            journal_type=Journal.JournalType.SALES,
        )

    def test_reporting_api_stays_empty_without_posted_entries(self):
        response = self.client.get(reverse('api_reporting_data'))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['income_statement'], [])
        self.assertFalse(payload['quality']['is_reliable'])
        self.assertEqual(payload['reports'], [])

    def test_reporting_api_aggregates_posted_entries(self):
        transaction = Transaction.objects.create(
            company=self.company,
            journal=self.journal,
            reference='VEN-001',
            date='2026-04-02',
            description='Vente',
            status=Transaction.TransactionStatus.POSTED,
            total_debit=Decimal('500.00'),
            total_credit=Decimal('500.00'),
            created_by=self.user,
        )
        TransactionLine.objects.create(transaction=transaction, account=self.cash, debit=Decimal('500.00'), credit=Decimal('0.00'))
        TransactionLine.objects.create(transaction=transaction, account=self.revenue, debit=Decimal('0.00'), credit=Decimal('500.00'))

        response = self.client.get(reverse('api_reporting_data'))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['quality']['is_reliable'])
        self.assertEqual(payload['revenue_current'], 500.0)
        self.assertEqual(payload['net_income'], 500.0)
        self.assertEqual(len(payload['income_statement']), 3)
