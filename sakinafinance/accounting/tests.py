import json
import subprocess
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from sakinafinance.accounting.models import Account, AccountTemplate, Journal, Transaction, TransactionLine
from sakinafinance.accounting.services import build_balance_sheet_snapshot, materialize_account_from_template
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

    def test_account_viewset_rejects_invalid_syscohada_account_type(self):
        response = self.client.post(
            reverse('account-list'),
            data={
                'name': 'Capital mal paramétré',
                'account_class': Account.AccountClass.CLASS_1,
                'account_type': Account.AccountType.ASSET,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('account_type', response.json())


class AccountingBalanceSheetDisplayTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Delta')
        self.user = User.objects.create_user(
            email='delta@finance.test',
            password='testpass123',
            first_name='Delta',
            last_name='Finance',
            company=self.company,
            role=User.Role.CFO,
        )
        self.client.force_login(self.user)

    def test_accounting_api_keeps_balance_sheet_sections_visible_without_accounts(self):
        response = self.client.get(reverse('api_accounting_data'))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['label'] for item in payload['balance_sheet']['actif']],
            ['Immobilisations', 'Stocks', 'Créances et tiers débiteurs', 'Disponibilités'],
        )
        self.assertEqual(
            [item['label'] for item in payload['balance_sheet']['passif']],
            [
                'Capitaux propres',
                'Dettes financières et ressources durables',
                'Dettes fournisseurs et tiers',
                'Trésorerie passive et concours bancaires',
            ],
        )
        self.assertTrue(all(item['amount'] == 0.0 for item in payload['balance_sheet']['actif']))
        self.assertTrue(all(item['amount'] == 0.0 for item in payload['balance_sheet']['passif']))

    def test_balance_sheet_reports_class_5_liabilities_in_passif(self):
        Account.objects.create(
            company=self.company,
            code='565000',
            name='Banques créditrices',
            account_class=Account.AccountClass.CLASS_5,
            account_type=Account.AccountType.LIABILITY,
            opening_balance=Decimal('250.00'),
        )

        snapshot = build_balance_sheet_snapshot(self.company)
        liabilities = {item['label']: item['amount'] for item in snapshot['passif']}

        self.assertEqual(liabilities['Trésorerie passive et concours bancaires'], 250.0)
        self.assertEqual(snapshot['current_liabilities'], Decimal('250.00'))

    def test_accounting_page_contains_balance_sheet_filter_controls(self):
        response = self.client.get(reverse('accounting'))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-balance-filter="all"', content)
        self.assertIn('data-balance-filter="actif"', content)
        self.assertIn('data-balance-filter="passif"', content)


class AccountingTemplateCatalogTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='TemplateCo')
        self.other_company = Company.objects.create(name='TemplateCo 2')

        self.parent_template = AccountTemplate.objects.create(
            accounting_standard=AccountTemplate.AccountingStandard.SYSCOHADA,
            code='52',
            name='Trésorerie',
            account_class=Account.AccountClass.CLASS_5,
            account_type=Account.AccountType.ASSET,
            level=1,
        )
        self.bank_template = AccountTemplate.objects.create(
            accounting_standard=AccountTemplate.AccountingStandard.SYSCOHADA,
            code='521',
            name='Banques',
            account_class=Account.AccountClass.CLASS_5,
            account_type=Account.AccountType.ASSET,
            parent=self.parent_template,
            level=2,
        )

    def test_materialize_account_from_template_creates_company_account_on_demand(self):
        account = materialize_account_from_template(self.company, code='521')

        self.assertIsNotNone(account)
        self.assertEqual(account.company, self.company)
        self.assertEqual(account.code, '521')
        self.assertEqual(account.template, self.bank_template)
        self.assertEqual(Account.objects.filter(company=self.company).count(), 2)
        self.assertEqual(Account.objects.filter(company=self.other_company).count(), 0)


class SyscohadaTemplateImportCommandTests(TestCase):
    def test_import_command_populates_global_catalog_only(self):
        Company.objects.create(name='Alpha Import')
        Company.objects.create(name='Beta Import')

        with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_pdf:
            with patch('sakinafinance.accounting.management.commands.import_syscohada_plan.subprocess.run') as mocked_run:
                mocked_run.return_value = subprocess.CompletedProcess(
                    args=['pdftotext'],
                    returncode=0,
                    stdout='10 Capital\n101 Capital social\n521 Banques\n',
                    stderr='',
                )

                call_command('import_syscohada_plan', pdf=temp_pdf.name)

        self.assertEqual(AccountTemplate.objects.count(), 3)
        self.assertEqual(Account.objects.count(), 0)
        self.assertEqual(
            list(AccountTemplate.objects.values_list('code', flat=True)),
            ['10', '101', '521'],
        )


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
