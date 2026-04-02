"""
Accounting services shared across dashboards and reporting endpoints.
"""

from decimal import Decimal

from django.db.models import Sum

from .models import Account, Transaction, TransactionLine


ZERO = Decimal('0')
DEBIT_NORMAL_ACCOUNT_TYPES = {
    Account.AccountType.ASSET,
    Account.AccountType.EXPENSE,
}


def posted_lines_queryset(company, start_date=None, end_date=None):
    queryset = TransactionLine.objects.filter(
        transaction__company=company,
        transaction__status=Transaction.TransactionStatus.POSTED,
    )

    if start_date:
        queryset = queryset.filter(transaction__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(transaction__date__lte=end_date)

    return queryset


def aggregate_posted_movements(company, start_date=None, end_date=None):
    rows = posted_lines_queryset(company, start_date=start_date, end_date=end_date).values('account_id').annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit'),
    )
    return {
        row['account_id']: {
            'debit': row['total_debit'] or ZERO,
            'credit': row['total_credit'] or ZERO,
        }
        for row in rows
    }


def calculate_account_balance(account, total_debit=ZERO, total_credit=ZERO):
    opening_balance = account.opening_balance or ZERO
    movement = (total_debit or ZERO) - (total_credit or ZERO)

    if account.account_type in DEBIT_NORMAL_ACCOUNT_TYPES:
        return opening_balance + movement

    return opening_balance - movement


def get_company_account_balances(company, end_date=None):
    movements = aggregate_posted_movements(company, end_date=end_date)
    balances = []

    for account in Account.objects.filter(company=company).order_by('code'):
        movement = movements.get(account.pk, {})
        balance = calculate_account_balance(
            account,
            total_debit=movement.get('debit', ZERO),
            total_credit=movement.get('credit', ZERO),
        )
        balances.append({
            'account': account,
            'debit': movement.get('debit', ZERO),
            'credit': movement.get('credit', ZERO),
            'balance': balance,
        })

    return balances


def refresh_current_balances(company, end_date=None):
    for row in get_company_account_balances(company, end_date=end_date):
        account = row['account']
        balance = row['balance']
        if account.current_balance != balance:
            account.current_balance = balance
            account.save(update_fields=['current_balance', 'updated_at'])


def build_balance_sheet_snapshot(company, end_date=None):
    balances = get_company_account_balances(company, end_date=end_date)

    asset_buckets = [
        ('Immobilisations', lambda account: account.account_class == Account.AccountClass.CLASS_2),
        ('Stocks', lambda account: account.account_class == Account.AccountClass.CLASS_3),
        ('Créances et tiers débiteurs', lambda account: account.account_class == Account.AccountClass.CLASS_4 and account.account_type == Account.AccountType.ASSET),
        ('Disponibilités', lambda account: account.account_class == Account.AccountClass.CLASS_5),
    ]
    liability_buckets = [
        ('Capitaux propres', lambda account: account.account_type == Account.AccountType.EQUITY),
        ('Dettes financières et ressources durables', lambda account: account.account_class == Account.AccountClass.CLASS_1 and account.account_type == Account.AccountType.LIABILITY),
        ('Dettes fournisseurs et tiers', lambda account: account.account_class == Account.AccountClass.CLASS_4 and account.account_type == Account.AccountType.LIABILITY),
    ]

    def bucket_total(predicate):
        return sum(
            row['balance']
            for row in balances
            if predicate(row['account'])
        )

    asset_values = [(label, bucket_total(predicate)) for label, predicate in asset_buckets]
    liability_values = [(label, bucket_total(predicate)) for label, predicate in liability_buckets]

    total_assets = sum((amount for _, amount in asset_values), ZERO)
    total_equity = next((amount for label, amount in liability_values if label == 'Capitaux propres'), ZERO)
    total_liabilities = sum(
        (amount for label, amount in liability_values if label != 'Capitaux propres'),
        ZERO,
    )

    def to_items(values, total):
        return [
            {
                'label': label,
                'amount': float(amount),
                'pct': float(round((amount / total) * 100, 1)) if total else 0.0,
            }
            for label, amount in values
            if amount != ZERO
        ]

    current_assets = sum(
        (
            amount for label, amount in asset_values
            if label in {'Stocks', 'Créances et tiers débiteurs', 'Disponibilités'}
        ),
        ZERO,
    )
    current_liabilities = next(
        (amount for label, amount in liability_values if label == 'Dettes fournisseurs et tiers'),
        ZERO,
    )
    cash = next(
        (amount for label, amount in asset_values if label == 'Disponibilités'),
        ZERO,
    )

    return {
        'actif': to_items(asset_values, total_assets),
        'passif': to_items(liability_values, total_equity + total_liabilities),
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'current_assets': current_assets,
        'current_liabilities': current_liabilities,
        'cash': cash,
        'stocks': next((amount for label, amount in asset_values if label == 'Stocks'), ZERO),
    }


def build_accounting_insight(has_posted_entries, total_assets, total_liabilities, total_equity, liquidity_ratio, solvability_ratio):
    if not has_posted_entries:
        return (
            "Aucune écriture validée n'alimente encore cette vue. "
            "Les montants visibles proviennent uniquement des soldes d'ouverture éventuels."
        )

    messages = []

    if total_assets > ZERO:
        messages.append(
            f"L'actif suivi par écritures validées s'établit à <span class=\"text-white fw-bold\">{float(total_assets):,.0f} XOF</span>."
        )

    if total_equity > ZERO and solvability_ratio is not None:
        messages.append(
            f"L'autonomie financière ressort à <span class=\"text-white fw-bold\">{solvability_ratio:.2f}</span>."
        )

    if total_liabilities > ZERO and liquidity_ratio is not None:
        messages.append(
            f"La liquidité générale simplifiée ressort à <span class=\"text-white fw-bold\">{liquidity_ratio:.2f}</span> sur la base des comptes de tiers et de trésorerie."
        )

    if not messages:
        messages.append("Les écritures validées existent, mais les indicateurs restent partiels tant que le mapping OHADA détaillé n'est pas finalisé.")

    return ' '.join(messages)
