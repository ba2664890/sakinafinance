from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from sakinafinance.accounting.models import Account, Transaction, TransactionLine
from sakinafinance.accounts.models import Company, Entity, User
from sakinafinance.treasury.models import BankAccount, BankStatementLine


class TreasuryMovementConsistencyTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Treasure Corp')
        self.entity = Entity.objects.create(
            company=self.company,
            name='Siege',
            code='HQTRS0001',
            entity_type=Entity.EntityType.HEADQUARTERS,
        )
        self.user = User.objects.create_user(
            email='tresorier@treasure.test',
            password='testpass123',
            first_name='Tresorier',
            last_name='Principal',
            company=self.company,
            entity=self.entity,
            role=User.Role.TREASURER,
        )
        self.client.force_login(self.user)

        self.bank_accounting_account = Account.objects.create(
            company=self.company,
            entity=self.entity,
            code='521000',
            name='Banque principale',
            account_class=Account.AccountClass.CLASS_5,
            account_type=Account.AccountType.ASSET,
            opening_balance=Decimal('0'),
        )
        self.bank_account = BankAccount.objects.create(
            company=self.company,
            entity=self.entity,
            bank_name='Wave',
            account_name='Compte Wave',
            iban='SN123',
            currency='XOF',
            accounting_account=self.bank_accounting_account,
        )

    def _post_movement(self, mv_type, amount, date='2026-04-14'):
        return self.client.post(
            reverse('api_bank_movement_create'),
            data={
                'bank_account': str(self.bank_account.id),
                'type': mv_type,
                'amount': str(amount),
                'description': f'Mouvement {mv_type}',
                'date': date,
            },
            secure=True,
        )

    def test_bank_movement_creates_reconciled_posted_transaction(self):
        response = self._post_movement('IN', '150000')
        self.assertEqual(response.status_code, 200, msg=f"Unexpected response: status={response.status_code} url={getattr(response, 'url', '')}")
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertAlmostEqual(payload['balance'], 150000.0)
        self.assertAlmostEqual(payload['accounting_balance'], 150000.0)
        self.assertIn('transaction_id', payload)

        movement = BankStatementLine.objects.get()
        self.assertTrue(movement.is_reconciled)
        self.assertIsNotNone(movement.reconciled_transaction)
        self.assertEqual(movement.reconciled_transaction.status, Transaction.TransactionStatus.POSTED)

        lines = list(TransactionLine.objects.filter(transaction=movement.reconciled_transaction))
        self.assertEqual(len(lines), 2)
        self.assertTrue(any(line.account_id == self.bank_accounting_account.id and line.debit == Decimal('150000') for line in lines))
        self.assertTrue(any(line.account_id != self.bank_accounting_account.id and line.credit == Decimal('150000') for line in lines))

        self.bank_accounting_account.refresh_from_db()
        self.assertEqual(self.bank_accounting_account.current_balance, Decimal('150000'))

    def test_treasury_data_uses_bank_movements_as_primary_source(self):
        self._post_movement('IN', '1000', date='2026-04-14')
        self._post_movement('OUT', '250', date='2026-04-14')

        response = self.client.get(reverse('api_treasury_data'), secure=True)
        self.assertEqual(response.status_code, 200, msg=f"Unexpected response: status={response.status_code} url={getattr(response, 'url', '')}")
        payload = response.json()
        self.assertEqual(payload['liquidity_source'], 'bank_statements')
        self.assertAlmostEqual(payload['total_liquidity'], 750.0)
        self.assertEqual(len(payload['bank_accounts']), 1)
        self.assertAlmostEqual(payload['bank_accounts'][0]['balance'], 750.0)
        self.assertAlmostEqual(payload['bank_accounts'][0]['accounting_balance'], 750.0)
