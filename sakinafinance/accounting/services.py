"""
Accounting services shared across dashboards and reporting endpoints.
"""

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import Account, AccountTemplate, Transaction, TransactionLine


ZERO = Decimal('0')
DEBIT_NORMAL_ACCOUNT_TYPES = {
    Account.AccountType.ASSET,
    Account.AccountType.EXPENSE,
}
EQUITY_NAME_HINTS = (
    'capital',
    'reserve',
    'reserves',
    'réserve',
    'réserves',
    'resultat',
    'résultat',
    'report a nouveau',
    'report à nouveau',
    'subvention',
    'fonds propres',
)

SYSCOHADA_CLASS_ACCOUNT_TYPES = {
    '1': {Account.AccountType.LIABILITY, Account.AccountType.EQUITY},
    '2': {Account.AccountType.ASSET},
    '3': {Account.AccountType.ASSET},
    '4': {Account.AccountType.ASSET, Account.AccountType.LIABILITY},
    '5': {Account.AccountType.ASSET, Account.AccountType.LIABILITY},
    '6': {Account.AccountType.EXPENSE},
    '7': {Account.AccountType.INCOME},
    '8': {Account.AccountType.EXPENSE, Account.AccountType.INCOME},
}


def syscohada_account_compliance(company):
    issues = []
    accounts = Account.objects.filter(company=company, is_active=True).order_by('code')
    for account in accounts:
        code = (account.code or '').strip()
        if not code:
            issues.append((account, "Code manquant."))
            continue

        class_digit = code[0]
        if class_digit not in SYSCOHADA_CLASS_ACCOUNT_TYPES:
            issues.append((account, "Le code doit commencer par une classe SYSCOHADA (1 a 8)."))
            continue

        if account.account_class != class_digit:
            issues.append((account, f"Classe '{account.account_class}' incoherente avec le code {code}."))

        expected_types = SYSCOHADA_CLASS_ACCOUNT_TYPES[class_digit]
        if account.account_type not in expected_types:
            issues.append((account, f"Type '{account.account_type}' incoherent pour la classe {class_digit}."))

    return accounts.count(), issues


def get_account_template_for_company(company, code):
    if not company or not code:
        return None

    accounting_standard = getattr(company, 'accounting_standard', AccountTemplate.AccountingStandard.SYSCOHADA)
    template = AccountTemplate.objects.filter(
        accounting_standard=accounting_standard,
        code=code,
        is_active=True,
    ).select_related('parent').first()

    if template:
        return template

    if accounting_standard != AccountTemplate.AccountingStandard.SYSCOHADA:
        return AccountTemplate.objects.filter(
            accounting_standard=AccountTemplate.AccountingStandard.SYSCOHADA,
            code=code,
            is_active=True,
        ).select_related('parent').first()

    return None


def materialize_account_from_template(company, code=None, template=None, entity=None):
    template = template or get_account_template_for_company(company, code)
    if template is None:
        return None

    parent_account = None
    if template.parent_id:
        parent_account = materialize_account_from_template(company, template=template.parent, entity=entity)

    account, created = Account.objects.get_or_create(
        company=company,
        code=template.code,
        defaults={
            'entity': entity,
            'template': template,
            'name': template.name,
            'name_en': template.name_en,
            'account_class': template.account_class,
            'account_type': template.account_type,
            'parent': parent_account,
            'level': template.level,
            'is_active': template.is_active,
            'is_system': template.is_system,
            'description': template.description,
        },
    )

    updated_fields = []
    if account.template_id != template.id:
        account.template = template
        updated_fields.append('template')
    if parent_account and account.parent_id is None:
        account.parent = parent_account
        updated_fields.append('parent')
    if entity and account.entity_id is None:
        account.entity = entity
        updated_fields.append('entity')

    if updated_fields:
        account.save(update_fields=[*updated_fields, 'updated_at'])

    return account


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


def is_probable_equity_account(account):
    if account.account_type == Account.AccountType.EQUITY:
        return True

    if account.account_class != Account.AccountClass.CLASS_1:
        return False

    code = (account.code or '').strip()
    name = (account.name or '').lower()

    if code.startswith(('10', '11', '12', '13', '14')):
        return True

    return any(keyword in name for keyword in EQUITY_NAME_HINTS)


def build_balance_sheet_snapshot(company, end_date=None):
    balances = get_company_account_balances(company, end_date=end_date)

    asset_buckets = [
        ('Immobilisations', lambda account: account.account_class == Account.AccountClass.CLASS_2),
        ('Stocks', lambda account: account.account_class == Account.AccountClass.CLASS_3),
        ('Créances et tiers débiteurs', lambda account: account.account_class == Account.AccountClass.CLASS_4 and account.account_type == Account.AccountType.ASSET),
        ('Disponibilités', lambda account: account.account_class == Account.AccountClass.CLASS_5 and account.account_type != Account.AccountType.LIABILITY),
    ]
    liability_buckets = [
        ('Capitaux propres', is_probable_equity_account),
        ('Dettes financières et ressources durables', lambda account: account.account_class == Account.AccountClass.CLASS_1 and not is_probable_equity_account(account)),
        ('Dettes fournisseurs et tiers', lambda account: account.account_class == Account.AccountClass.CLASS_4 and account.account_type == Account.AccountType.LIABILITY),
        ('Trésorerie passive et concours bancaires', lambda account: account.account_class == Account.AccountClass.CLASS_5 and account.account_type == Account.AccountType.LIABILITY),
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
        non_zero_values = [(label, amount) for label, amount in values if amount != ZERO]
        selected_values = non_zero_values or values
        denominator = total if total != ZERO else sum((abs(amount) for _, amount in selected_values), ZERO)

        return [
            {
                'label': label,
                'amount': float(amount),
                'pct': float(round((amount / denominator) * 100, 1)) if denominator else 0.0,
            }
            for label, amount in selected_values
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
    current_liabilities += next(
        (amount for label, amount in liability_values if label == 'Trésorerie passive et concours bancaires'),
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


def post_transaction(transaction, user=None):
    """
    Valide officiellement une transaction :
    - Change le statut à 'posted'
    - Enregistre qui a validé et quand
    - Déclenche la mise à jour des soldes de tous les comptes affectés
    """
    if transaction.status == Transaction.TransactionStatus.POSTED:
        return transaction

    transaction.status = Transaction.TransactionStatus.POSTED
    transaction.posted_by = user
    transaction.posted_at = timezone.now()
    transaction.save()

    # Déclencher la mise à jour des soldes pour la société
    refresh_current_balances(transaction.company)

    return transaction
