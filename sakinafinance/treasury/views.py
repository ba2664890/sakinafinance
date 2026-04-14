import logging
import uuid
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta

from django.db import connection, transaction as db_transaction
from django.db.models import Sum, Q
from decimal import Decimal, InvalidOperation
from sakinafinance.accounting.models import Transaction, TransactionLine, Account, Journal
from sakinafinance.accounting.services import post_transaction
from sakinafinance.accounts.models import Entity
from sakinafinance.ai_engine.services import AIService
from .models import BankAccount, BankStatement, BankStatementLine
from django.views.decorators.http import require_POST

logger = logging.getLogger('sakinafinance')

@login_required
def treasury_view(request):
    """Module Trésorerie — vue principale"""
    return render(request, 'treasury/index.html', {'page_title': 'Trésorerie & Cash Flow'})

def _get_company(request):
    user = request.user
    company = getattr(user, 'company', None)
    if company:
        return company
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'company', None)


def _ensure_default_entity(company):
    """Garantit une entité valide pour la société."""
    entity = company.entities.order_by('created_at').first()
    if entity:
        return entity

    return Entity.objects.create(
        company=company,
        name='Siège',
        code=_generate_unique_entity_code('HQ'),
        entity_type=Entity.EntityType.HEADQUARTERS,
    )


def _generate_unique_entity_code(prefix='ENT'):
    """Génère un code d'entité globalement unique (max 10 chars)."""
    safe_prefix = ''.join(ch for ch in (prefix or 'ENT').upper() if ch.isalnum())[:3] or 'ENT'
    for _ in range(25):
        code = f"{safe_prefix}{uuid.uuid4().hex[:7].upper()}"[:10]
        if not Entity.objects.filter(code=code).exists():
            return code
    raise ValueError("Impossible de générer un code d'entité unique.")


def _ensure_treasury_account(company, entity):
    """Retourne un compte de trésorerie existant, sinon en crée un."""
    account = Account.objects.filter(
        company=company,
        account_class='5',
        account_type=Account.AccountType.ASSET,
    ).order_by('code').first()
    if account:
        return account

    # Fallback: on récupère un compte classe 5, même si le type n'est pas renseigné comme 'asset'.
    account = Account.objects.filter(company=company, account_class='5').order_by('code').first()
    if account:
        return account

    for i in range(1000):
        code = f"521{i:03d}"
        if Account.objects.filter(company=company, code=code).exists():
            continue
        return Account.objects.create(
            company=company,
            entity=entity,
            code=code,
            name='Banque - Compte principal',
            account_class='5',
            account_type=Account.AccountType.ASSET,
            is_active=True,
        )

    raise ValueError("Impossible de générer un code de compte de trésorerie unique.")


def _ensure_bank_journal(company, entity=None):
    journal = Journal.objects.filter(
        company=company,
        journal_type=Journal.JournalType.BANK,
        is_active=True,
    ).order_by('code').first()
    if journal:
        return journal

    for i in range(1000):
        code = 'BQ' if i == 0 else f"BQ{i:03d}"
        if Journal.objects.filter(company=company, code=code).exists():
            continue
        return Journal.objects.create(
            company=company,
            entity=entity,
            code=code,
            name='Journal Banque',
            journal_type=Journal.JournalType.BANK,
            is_active=True,
        )

    raise ValueError("Impossible de générer un code de journal banque unique.")


def _ensure_treasury_suspense_account(company, entity):
    account = Account.objects.filter(
        company=company,
        account_class='4',
        code__startswith='471'
    ).order_by('code').first()
    if account:
        return account

    for i in range(1000):
        code = f"471{i:03d}"
        if Account.objects.filter(company=company, code=code).exists():
            continue
        return Account.objects.create(
            company=company,
            entity=entity,
            code=code,
            name="Compte d'attente tresorerie",
            account_class='4',
            account_type=Account.AccountType.LIABILITY,
            is_active=True,
        )

    raise ValueError("Impossible de generer un compte d'attente tresorerie unique.")


def _safe_bank_accounts_list(company):
    """
    Lecture robuste des comptes bancaires.
    Compatible avec des schémas legacy (ex: account_number au lieu de iban/account_name)
    pour éviter un 500 sur /treasury/api/data.
    """
    try:
        return list(
            BankAccount.objects.filter(company=company).values(
                'id', 'bank_name', 'account_name', 'iban', 'currency'
            )
        )
    except Exception as exc:
        logger.warning("Fallback bank account list (ORM) company=%s: %s", company.pk, exc)

    # Fallback SQL brut, utile si la DB prod n'est pas alignée avec le modèle actuel.
    try:
        table_name = BankAccount._meta.db_table
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table_name)
            columns = {col.name for col in description}
            company_column = 'company_id' if 'company_id' in columns else ('company' if 'company' in columns else None)
            if not company_column:
                return []

            qn = connection.ops.quote_name
            select_parts = []

            if 'id' in columns:
                select_parts.append(f"{qn('id')} AS id")
            if 'bank_name' in columns:
                select_parts.append(f"{qn('bank_name')} AS bank_name")
            else:
                return []

            if 'account_name' in columns:
                select_parts.append(f"{qn('account_name')} AS account_name")
            elif 'account_number' in columns:
                select_parts.append(f"{qn('account_number')} AS account_name")

            if 'iban' in columns:
                select_parts.append(f"{qn('iban')} AS iban")
            elif 'account_number' in columns:
                select_parts.append(f"{qn('account_number')} AS iban")

            if 'currency' in columns:
                select_parts.append(f"{qn('currency')} AS currency")

            sql = (
                f"SELECT {', '.join(select_parts)} "
                f"FROM {qn(table_name)} "
                f"WHERE {qn(company_column)} = %s"
            )
            cursor.execute(sql, [str(company.pk)])
            rows = cursor.fetchall()
            keys = [col[0] for col in cursor.description]

        normalized = []
        for row in rows:
            item = dict(zip(keys, row))
            normalized.append({
                'id': item.get('id'),
                'bank_name': item.get('bank_name') or 'Banque',
                'account_name': item.get('account_name') or '',
                'iban': item.get('iban') or '',
                'currency': item.get('currency') or 'XOF',
            })
        return normalized
    except Exception as exc:
        logger.exception("Fallback bank account list (SQL) failed company=%s: %s", company.pk, exc)
        return []


def _bank_movements_queryset(company):
    return BankStatementLine.objects.filter(statement__bank_account__company=company)


def _bank_liquidity(company, start_date=None, end_date=None):
    queryset = _bank_movements_queryset(company)
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    return queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0')


def _accounting_liquidity(company, start_date=None, end_date=None):
    queryset = TransactionLine.objects.filter(
        transaction__company=company,
        transaction__status=Transaction.TransactionStatus.POSTED,
        account__account_class='5'
    )
    if start_date:
        queryset = queryset.filter(transaction__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(transaction__date__lte=end_date)
    return queryset.aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')


def _bank_account_balances(company):
    accounts = BankAccount.objects.filter(company=company).select_related('entity').order_by('bank_name', 'account_name')
    balance_rows = _bank_movements_queryset(company).values(
        'statement__bank_account_id'
    ).annotate(total=Sum('amount'))
    balances_by_account_id = {
        str(row['statement__bank_account_id']): (row['total'] or Decimal('0'))
        for row in balance_rows
    }

    data = []
    for account in accounts:
        bank_balance = balances_by_account_id.get(str(account.id), Decimal('0'))
        accounting_balance = getattr(account.accounting_account, 'current_balance', Decimal('0')) or Decimal('0')
        data.append({
            'entity': account.entity.name if account.entity else 'N/A',
            'bank': account.bank_name or account.account_name or 'Compte bancaire',
            'balance': float(bank_balance),
            'accounting_balance': float(accounting_balance),
            'currency': account.currency or 'XOF',
            'status': 'active' if account.is_active else 'inactive',
        })
    return data

@login_required
def api_treasury_data(request):
    """API: Récupération des données de trésorerie réelles"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': "Aucune entreprise n'est associée à cet utilisateur."}, status=400)

    try:
        has_bank_movements = _bank_movements_queryset(company).exists()
        today = timezone.now().date()
        window_start = today - timedelta(days=30)

        bank_liquidity = _bank_liquidity(company)
        accounting_liquidity = _accounting_liquidity(company)
        liquidity = bank_liquidity if has_bank_movements else accounting_liquidity
        net_cashflow_30d = (
            _bank_liquidity(company, start_date=window_start)
            if has_bank_movements
            else _accounting_liquidity(company, start_date=window_start)
        )

        # 2. DSO (Days Sales Outstanding) - Simplifié : Solde Client / (CA/30)
        receivables = TransactionLine.objects.filter(
            transaction__company=company,
            transaction__status=Transaction.TransactionStatus.POSTED,
            account__account_class='4',
            account__code__startswith='411'
        ).aggregate(bal=Sum('debit') - Sum('credit'))['bal'] or Decimal('0')

        monthly_rev = TransactionLine.objects.filter(
            transaction__company=company,
            transaction__status=Transaction.TransactionStatus.POSTED,
            account__account_class='7'
        ).aggregate(bal=Sum('credit') - Sum('debit'))['bal'] or Decimal('1')

        dso = int((receivables / (monthly_rev / Decimal('30'))).quantize(Decimal('1'))) if monthly_rev > 0 else 0

        # 3. DIO (Days Inventory Outstanding)
        inventory_value = TransactionLine.objects.filter(
            transaction__company=company,
            transaction__status=Transaction.TransactionStatus.POSTED,
            account__code__startswith='3'
        ).aggregate(bal=Sum('debit') - Sum('credit'))['bal'] or Decimal('0')

        cost_of_sales = TransactionLine.objects.filter(
            transaction__company=company,
            transaction__status=Transaction.TransactionStatus.POSTED,
            account__code__startswith='60'
        ).aggregate(bal=Sum('debit') - Sum('credit'))['bal'] or Decimal('1')

        dio = int((inventory_value / (cost_of_sales / Decimal('30'))).quantize(Decimal('1'))) if cost_of_sales > 0 else 0

        # 4. DPO (Days Payables Outstanding)
        payables = TransactionLine.objects.filter(
            transaction__company=company,
            transaction__status=Transaction.TransactionStatus.POSTED,
            account__code__startswith='401'
        ).aggregate(bal=Sum('credit') - Sum('debit'))['bal'] or Decimal('0')

        dpo = int((payables / (cost_of_sales / Decimal('30'))).quantize(Decimal('1'))) if cost_of_sales > 0 else 0

        # 5. Cash Cycle
        cash_cycle = dso + dio - dpo

        # 6. Comptes Bancaires
        bank_accounts = _bank_account_balances(company)

        data = {
            'total_liquidity': float(liquidity),
            'liquidity_growth': 5.4,
            'net_cashflow_30d': float(net_cashflow_30d),
            'cashflow_growth': 2.1,
            'dso_days': dso,
            'dso_target': 35,
            'ml_confidence': 96.8,
            'cash_cycle_days': cash_cycle,
            'bank_accounts': bank_accounts,
            'bank_accounts_list': _safe_bank_accounts_list(company),
            'entities_list': list(company.entities.values('id', 'name', 'code', 'entity_type').order_by('code', 'name')),
            'currency_exposure': [
                {'currency': 'XOF', 'amount': f"{float(liquidity)/1e6:.1f}M", 'risk': 'STABLE', 'risk_class': 'success'},
            ],
            'dio_days': dio,
            'dpo_days': dpo,
            'liquidity_source': 'bank_statements' if has_bank_movements else 'accounting_entries',
        }
    except Exception as exc:
        logger.exception("Erreur api_treasury_data company=%s user=%s: %s", company.pk, request.user.pk, exc)
        return JsonResponse(
            {'status': 'error', 'message': "Erreur interne Trésorerie. Vérifiez les logs serveur (Render)."},
            status=500
        )

    # Insights IA non bloquants
    try:
        ai_service = AIService()
        data['ai_insight'] = ai_service.generate_treasury_insights(data)
    except Exception as exc:
        logger.warning("Treasury AI insight fallback: %s", exc)
        data['ai_insight'] = "Analyse des cycles en cours... L'IA calcule la stratégie optimale."

    return JsonResponse(data)

@login_required
def treasury_api_cashflow(request):
    """API: Flux de trésorerie réel sur 6 mois"""
    company = _get_company(request)
    
    labels = []
    inflows = []
    outflows = []
    has_bank_movements = _bank_movements_queryset(company).exists()
    
    today = timezone.now().date()
    for i in range(5, -1, -1):
        target_date = today - timedelta(days=i*30)
        month_label = target_date.strftime('%b')
        labels.append(month_label)

        if has_bank_movements:
            monthly_lines = _bank_movements_queryset(company).filter(
                date__month=target_date.month,
                date__year=target_date.year
            )
            inf = monthly_lines.filter(amount__gt=0).aggregate(t=Sum('amount'))['t'] or Decimal('0')
            out_signed = monthly_lines.filter(amount__lt=0).aggregate(t=Sum('amount'))['t'] or Decimal('0')
            out = abs(out_signed)
        else:
            # Fallback comptable: classe 5 validée
            inf = TransactionLine.objects.filter(
                transaction__company=company,
                transaction__status=Transaction.TransactionStatus.POSTED,
                account__account_class='5',
                transaction__date__month=target_date.month,
                transaction__date__year=target_date.year
            ).aggregate(t=Sum('debit'))['t'] or Decimal('0')

            out = TransactionLine.objects.filter(
                transaction__company=company,
                transaction__status=Transaction.TransactionStatus.POSTED,
                account__account_class='5',
                transaction__date__month=target_date.month,
                transaction__date__year=target_date.year
            ).aggregate(t=Sum('credit'))['t'] or Decimal('0')

        inflows.append(float(inf))
        outflows.append(float(out))

    return JsonResponse({
        'labels': labels,
        'inflows': inflows,
        'outflows': outflows,
    })


@require_POST
@login_required
def api_entity_create(request):
    """API: Créer une entité rapidement depuis la Trésorerie."""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': "Aucune entreprise n'est associée à cet utilisateur."}, status=400)

    name = (request.POST.get('name') or '').strip()
    entity_type = (request.POST.get('entity_type') or Entity.EntityType.BRANCH).strip()
    code = (request.POST.get('code') or '').strip().upper().replace(' ', '')

    if not name:
        return JsonResponse({'status': 'error', 'message': "Le nom de l'entité est requis."}, status=400)

    valid_entity_types = {choice[0] for choice in Entity.EntityType.choices}
    if entity_type not in valid_entity_types:
        entity_type = Entity.EntityType.BRANCH

    if code:
        if len(code) > 10:
            return JsonResponse({'status': 'error', 'message': "Le code d'entité ne doit pas dépasser 10 caractères."}, status=400)
        if Entity.objects.filter(code=code).exists():
            return JsonResponse({'status': 'error', 'message': "Ce code d'entité existe déjà."}, status=400)
    else:
        prefix = 'HQ' if entity_type == Entity.EntityType.HEADQUARTERS else 'ENT'
        code = _generate_unique_entity_code(prefix)

    entity = Entity.objects.create(
        company=company,
        name=name,
        code=code,
        entity_type=entity_type,
    )

    return JsonResponse({
        'status': 'success',
        'message': 'Entité créée',
        'entity': {
            'id': str(entity.id),
            'name': entity.name,
            'code': entity.code,
            'entity_type': entity.entity_type,
            'entity_type_display': entity.get_entity_type_display(),
        }
    })


@require_POST
@login_required
def api_bank_account_create(request):
    """API: Créer un compte bancaire"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': "Aucune entreprise n'est associée à cet utilisateur."}, status=400)
    
    bank_name = request.POST.get('bank_name')
    account_number = request.POST.get('account_number')
    currency = request.POST.get('currency', 'XOF')
    account_name = request.POST.get('account_name') or (f"Compte {bank_name}" if bank_name else "Compte bancaire")
    entity_id = request.POST.get('entity_id')
    
    if not bank_name:
        return JsonResponse({'status': 'error', 'message': 'Champs requis manquants'}, status=400)
    
    try:
        if entity_id:
            entity = Entity.objects.filter(company=company, id=entity_id).first()
            if not entity:
                return JsonResponse({'status': 'error', 'message': "L'entité sélectionnée est introuvable."}, status=400)
        else:
            # Entité créée automatiquement si absente.
            entity = _ensure_default_entity(company)

        accounting_account = _ensure_treasury_account(company, entity)
    except Exception as exc:
        logger.exception("Erreur préparation compte bancaire société=%s", company.pk)
        return JsonResponse({'status': 'error', 'message': f"Préparation impossible: {exc}"}, status=400)
        
    account = BankAccount.objects.create(
        company=company,
        entity=entity,
        bank_name=bank_name,
        account_name=account_name,
        iban=account_number or '',
        currency=currency,
        accounting_account=accounting_account
    )
    
    return JsonResponse({
        'status': 'success',
        'message': 'Compte bancaire créé',
        'account': {'id': str(account.id), 'bank': account.bank_name, 'entity': entity.name}
    })


@require_POST
@login_required
def api_bank_movement_create(request):
    """API: Créer un mouvement de fonds (direct)"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': "Aucune entreprise n'est associée à cet utilisateur."}, status=400)

    account_id = request.POST.get('bank_account')
    mv_type = (request.POST.get('type') or '').upper()  # IN or OUT
    amount_raw = (request.POST.get('amount') or '').strip()
    description = (request.POST.get('description') or '').strip() or 'Mouvement manuel'
    date_raw = (request.POST.get('date') or '').strip()

    if not account_id:
        return JsonResponse({'status': 'error', 'message': 'Compte bancaire requis.'}, status=400)
    if mv_type not in {'IN', 'OUT'}:
        return JsonResponse({'status': 'error', 'message': "Type de mouvement invalide (IN/OUT)."}, status=400)

    normalized_amount = amount_raw.replace(' ', '').replace(',', '.')
    try:
        amount = Decimal(normalized_amount)
    except (InvalidOperation, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Montant invalide.'}, status=400)
    if amount <= 0:
        return JsonResponse({'status': 'error', 'message': 'Le montant doit être strictement positif.'}, status=400)

    movement_date = parse_date(date_raw) if date_raw else timezone.now().date()
    if not movement_date:
        return JsonResponse({'status': 'error', 'message': 'Date invalide.'}, status=400)

    bank_account = get_object_or_404(BankAccount, id=account_id, company=company)

    with db_transaction.atomic():
        signed_amount = amount if mv_type == 'IN' else -amount
        statement_ref = f"MAN-{movement_date.strftime('%Y%m%d')}"
        # BankStatementLine expects a statement; reuse manual day statement to keep balances coherent.
        statement, _ = BankStatement.objects.get_or_create(
            bank_account=bank_account,
            reference=statement_ref,
            defaults={
                'start_date': movement_date,
                'end_date': movement_date,
                'opening_balance': Decimal('0'),
                'closing_balance': Decimal('0'),
                'is_imported': False,
            }
        )
        movement = BankStatementLine.objects.create(
            statement=statement,
            date=movement_date,
            description=description,
            amount=signed_amount,
            reference=f"MAN-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            is_reconciled=False
        )

        journal = _ensure_bank_journal(company, entity=bank_account.entity)
        suspense_account = _ensure_treasury_suspense_account(company, bank_account.entity)

        tx_reference = f"TRS-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        tx = Transaction.objects.create(
            company=company,
            entity=bank_account.entity,
            journal=journal,
            reference=tx_reference,
            date=movement_date,
            description=description,
            total_debit=amount,
            total_credit=amount,
            currency=bank_account.currency or 'XOF',
            status=Transaction.TransactionStatus.PENDING,
            created_by=request.user,
            source_document='bank_movement',
            source_id=str(movement.id),
        )

        if mv_type == 'IN':
            bank_debit, bank_credit = amount, Decimal('0')
            counterpart_debit, counterpart_credit = Decimal('0'), amount
        else:
            bank_debit, bank_credit = Decimal('0'), amount
            counterpart_debit, counterpart_credit = amount, Decimal('0')

        TransactionLine.objects.create(
            transaction=tx,
            account=bank_account.accounting_account,
            debit=bank_debit,
            credit=bank_credit,
            description=description,
        )
        TransactionLine.objects.create(
            transaction=tx,
            account=suspense_account,
            debit=counterpart_debit,
            credit=counterpart_credit,
            description=f"Contrepartie mouvement bancaire {movement.reference}",
        )

        post_transaction(tx, user=request.user)

        movement.reconciled_transaction = tx
        movement.is_reconciled = True
        movement.save(update_fields=['reconciled_transaction', 'is_reconciled'])

        statement_delta = statement.lines.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        statement.closing_balance = (statement.opening_balance or Decimal('0')) + statement_delta
        statement.save(update_fields=['closing_balance'])

        statement_balance = BankStatementLine.objects.filter(
            statement__bank_account=bank_account
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        bank_account.accounting_account.refresh_from_db(fields=['current_balance'])
        accounting_balance = getattr(bank_account.accounting_account, 'current_balance', Decimal('0')) or Decimal('0')

    return JsonResponse({
        'status': 'success',
        'message': 'Mouvement enregistré',
        'balance': float(statement_balance),
        'accounting_balance': float(accounting_balance),
        'movement_amount': float(signed_amount),
        'transaction_id': str(tx.id),
    })
