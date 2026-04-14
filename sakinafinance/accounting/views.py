"""
Comptabilité Views — SakinaFinance
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
import json
from datetime import datetime
from decimal import Decimal
from json import JSONDecodeError

from django.db.models import Sum
from django.utils import timezone
from .models import Account, Transaction, TransactionLine, Journal
from .services import (
    ZERO,
    SYSCOHADA_CLASS_ACCOUNT_TYPES,
    aggregate_posted_movements,
    build_accounting_insight,
    build_balance_sheet_snapshot,
    post_transaction,
    syscohada_account_compliance,
)


def _validate_syscohada_journal_rules(journal, normalized_lines):
    """
    Enforce core SYSCOHADA-oriented journal patterns on manual entry forms.
    Returns an error string when a rule is violated, else None.
    """
    for line in normalized_lines:
        account = line['account']
        expected_types = SYSCOHADA_CLASS_ACCOUNT_TYPES.get((account.account_class or '').strip(), set())
        if expected_types and account.account_type not in expected_types:
            return (
                f"Le compte {account.code} ({account.name}) est incoherent pour la classe "
                f"{account.account_class}. Corrigez le type de compte selon SYSCOHADA."
            )

    journal_type = journal.journal_type

    def has_line(predicate):
        return any(predicate(line) for line in normalized_lines)

    has_class_5 = has_line(lambda line: line['account'].account_class == Account.AccountClass.CLASS_5)
    if journal_type in {Journal.JournalType.BANK, Journal.JournalType.CASH} and not has_class_5:
        return "Un journal de tresorerie (Banque/Caisse) doit contenir au moins un compte de classe 5."

    if journal_type == Journal.JournalType.SALES:
        has_revenue_credit = has_line(
            lambda line: line['account'].account_class == Account.AccountClass.CLASS_7 and line['credit'] > ZERO
        )
        has_counterpart_debit = has_line(
            lambda line: line['account'].account_class in {Account.AccountClass.CLASS_4, Account.AccountClass.CLASS_5}
            and line['debit'] > ZERO
        )
        if not (has_revenue_credit and has_counterpart_debit):
            return (
                "Journal Ventes: il faut au moins une ligne de produit (classe 7 au credit) "
                "et une contrepartie client/tresorerie (classe 4/5 au debit)."
            )

    if journal_type == Journal.JournalType.PURCHASES:
        has_expense_debit = has_line(
            lambda line: line['account'].account_class in {
                Account.AccountClass.CLASS_2,
                Account.AccountClass.CLASS_3,
                Account.AccountClass.CLASS_6,
            } and line['debit'] > ZERO
        )
        has_counterpart_credit = has_line(
            lambda line: line['account'].account_class in {Account.AccountClass.CLASS_4, Account.AccountClass.CLASS_5}
            and line['credit'] > ZERO
        )
        if not (has_expense_debit and has_counterpart_credit):
            return (
                "Journal Achats: il faut une charge/stock/immobilisation (classe 6/3/2 au debit) "
                "et une contrepartie fournisseur/tresorerie (classe 4/5 au credit)."
            )

    if journal_type == Journal.JournalType.PAYROLL:
        has_payroll_debit = has_line(
            lambda line: line['account'].account_class == Account.AccountClass.CLASS_6 and line['debit'] > ZERO
        )
        has_payroll_counterpart = has_line(
            lambda line: line['account'].account_class in {Account.AccountClass.CLASS_4, Account.AccountClass.CLASS_5}
            and line['credit'] > ZERO
        )
        if not (has_payroll_debit and has_payroll_counterpart):
            return (
                "Journal Paie: il faut une charge de personnel (classe 6 au debit) "
                "et une contrepartie tiers/tresorerie (classe 4/5 au credit)."
            )

    if journal_type == Journal.JournalType.INVENTORY:
        has_inventory_class = has_line(lambda line: line['account'].account_class == Account.AccountClass.CLASS_3)
        if not has_inventory_class:
            return "Journal Stocks: au moins une ligne de classe 3 est requise."

    return None

@login_required
def accounting_view(request):
    """Module Comptabilité — vue principale (Squelette)"""
    return render(request, 'accounting/index.html', {'page_title': 'Comptabilité Générale'})


@login_required
def api_accounting_data(request):
    """API: Get accounting metrics based on posted entries and opening balances."""
    company = _get_company(request)

    data = {
        'total_assets': 0.0,
        'total_assets_growth': None,
        'total_liabilities': 0.0,
        'equity': 0.0,
        'equity_ratio': None,
        'net_income': 0.0,
        'net_income_margin': None,
        'pending_entries': 0,
        'ai_insight': build_accounting_insight(False, ZERO, ZERO, ZERO, None, None),
        'journal_entries': [],
        'balance_sheet': {
            'actif': [],
            'passif': [],
        },
        'ratios': {
            'liquidity_ratio': None,
            'solvability_ratio': None,
        },
        'quality': {
            'level': 'warning',
            'title': 'Données comptables partielles',
            'message': "Aucune entreprise n'est associée à cet utilisateur.",
            'is_reliable': False,
        },
        'journals': [],
        'compliance': {
            'total_accounts': 0,
            'issues_count': 0,
            'issues': [],
        },
    }

    if not company:
        return JsonResponse(data)

    today = timezone.now().date()
    year_start = today.replace(month=1, day=1)
    try:
        last_year_end = today.replace(year=today.year - 1)
    except ValueError:
        last_year_end = today.replace(year=today.year - 1, day=28)
    period_movements = aggregate_posted_movements(company, start_date=year_start, end_date=today)
    period_accounts = Account.objects.in_bulk(period_movements.keys())
    balance_sheet = build_balance_sheet_snapshot(company, end_date=today)
    previous_balance_sheet = build_balance_sheet_snapshot(company, end_date=last_year_end)
    posted_transactions = Transaction.objects.filter(company=company, status=Transaction.TransactionStatus.POSTED)
    pending_transactions = Transaction.objects.filter(company=company, status=Transaction.TransactionStatus.PENDING)

    revenue = ZERO
    ebitda = ZERO
    ebit = ZERO
    financial_result = ZERO
    tax = ZERO
    
    for account_id, movement in period_movements.items():
        account = period_accounts.get(account_id)
        if not account:
            continue
            
        # Classe 7: Produits
        if account.account_class == Account.AccountClass.CLASS_7:
            revenue += movement['credit'] - movement['debit']
            
        # Classe 6: Charges
        elif account.account_class == Account.AccountClass.CLASS_6:
            # Séparation simplifiée pour EBITDA/EBIT
            # 60-65: Exploitation (Approximatif)
            # 67: Financement
            # 68: Dotations
            # 69: Impôts
            if account.code.startswith('67'):
                financial_result -= (movement['debit'] - movement['credit'])
            elif account.code.startswith('68'):
                ebit -= (movement['debit'] - movement['credit'])
            elif account.code.startswith('69'):
                tax += (movement['debit'] - movement['credit'])
            else:
                ebitda -= (movement['debit'] - movement['credit'])

    ebitda += revenue
    ebit += ebitda
    net_income = ebit + financial_result - tax
    total_assets = balance_sheet['total_assets']
    total_liabilities = balance_sheet['total_liabilities']
    equity = balance_sheet['total_equity']
    current_assets = balance_sheet['current_assets']
    current_liabilities = balance_sheet['current_liabilities']
    prev_total_assets = previous_balance_sheet['total_assets']

    liquidity_ratio = float(current_assets / current_liabilities) if current_liabilities > ZERO else None
    solvability_ratio = float(equity / total_assets) if total_assets > ZERO else None
    net_income_margin = float((net_income / revenue) * 100) if revenue > ZERO else None
    total_assets_growth = None
    if prev_total_assets and prev_total_assets > ZERO:
        total_assets_growth = float(((total_assets - prev_total_assets) / prev_total_assets) * 100)

    last_entries = []
    for tx in posted_transactions.select_related('journal').prefetch_related('lines__account').order_by('-date', '-created_at')[:6]:
        first_line = tx.lines.first()
        last_entries.append({
            'date': tx.date.strftime('%d/%m/%Y'),
            'ref': tx.reference,
            'libelle': tx.description,
            'debit': float(tx.total_debit),
            'credit': float(tx.total_credit),
            'compte': 'MULT' if tx.lines.count() > 2 else first_line.account.code if first_line else 'N/A',
        })

    posted_lines_totals = TransactionLine.objects.filter(
        transaction__company=company,
        transaction__status=Transaction.TransactionStatus.POSTED,
    ).aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))
    total_posted_debit = posted_lines_totals['total_debit'] or ZERO
    total_posted_credit = posted_lines_totals['total_credit'] or ZERO
    trial_balance_gap = total_posted_debit - total_posted_credit
    balance_sheet_gap = total_assets - (total_liabilities + equity)

    is_reliable = posted_transactions.exists()
    checks_ok = abs(trial_balance_gap) < Decimal('0.01') and abs(balance_sheet_gap) < Decimal('0.01')
    quality_message = (
        "Vue calculée à partir des écritures validées et des soldes d'ouverture. Le mapping détaillé des états OHADA reste encore simplifié."
        if is_reliable
        else "Aucune écriture validée n'alimente encore cette vue. Les rubriques restent limitées aux soldes d'ouverture éventuels."
    )
    if is_reliable and not checks_ok:
        quality_message += " Un ecart de controle est detecte sur la balance ou le bilan."

    compliance_total = 0
    compliance_issues = []
    if company.accounting_standard == 'syscohada':
        compliance_total, compliance_issues = syscohada_account_compliance(company)

    data.update({
        'total_assets': float(total_assets),
        'total_assets_growth': round(total_assets_growth, 1) if total_assets_growth is not None else None,
        'total_liabilities': float(total_liabilities),
        'equity': float(equity),
        'equity_ratio': round(solvability_ratio * 100, 1) if solvability_ratio is not None else None,
        'net_income': float(net_income),
        'net_income_margin': round(net_income_margin, 1) if net_income_margin is not None else None,
        'pending_entries': pending_transactions.count(),
        'ai_insight': build_accounting_insight(
            is_reliable,
            total_assets,
            total_liabilities,
            equity,
            liquidity_ratio,
            solvability_ratio,
        ),
        'journal_entries': last_entries,
        'balance_sheet': {
            'actif': balance_sheet['actif'],
            'passif': balance_sheet['passif'],
        },
        'balance_sheet_meta': {
            'current_assets': float(balance_sheet['current_assets']),
            'current_liabilities': float(balance_sheet['current_liabilities']),
            'cash': float(balance_sheet['cash']),
            'stocks': float(balance_sheet['stocks']),
        },
        'ratios': {
            'liquidity_ratio': round(liquidity_ratio, 2) if liquidity_ratio is not None else None,
            'solvability_ratio': round(solvability_ratio, 2) if solvability_ratio is not None else None,
        },
        'quality': {
            'level': 'info' if (is_reliable and checks_ok) else ('danger' if is_reliable else 'warning'),
            'title': 'Base comptable contrôlée' if (is_reliable and checks_ok) else ('Contrôles à vérifier' if is_reliable else 'Données comptables partielles'),
            'message': quality_message,
            'is_reliable': is_reliable,
        },
        'journals': list(Journal.objects.filter(company=company, is_active=True).values('id', 'name', 'code')),
        'accounts': list(Account.objects.filter(company=company, is_active=True).order_by('code').values('id', 'code', 'name')[:200]),
        'checks': {
            'trial_balance_gap': float(trial_balance_gap),
            'balance_sheet_gap': float(balance_sheet_gap),
            'total_posted_debit': float(total_posted_debit),
            'total_posted_credit': float(total_posted_credit),
            'is_trial_balanced': abs(trial_balance_gap) < Decimal('0.01'),
            'is_balance_sheet_balanced': abs(balance_sheet_gap) < Decimal('0.01'),
        },
        'compliance': {
            'total_accounts': compliance_total,
            'issues_count': len(compliance_issues),
            'issues': [
                {
                    'code': issue[0].code,
                    'name': issue[0].name,
                    'message': issue[1],
                }
                for issue in compliance_issues[:8]
            ],
        },
    })

    return JsonResponse(data)

def _get_company(request):
    """Helper to get the user's company"""
    if hasattr(request.user, 'company') and request.user.company:
        return request.user.company
    if hasattr(request.user, 'profile') and request.user.profile.company:
        return request.user.profile.company
    return None

@login_required
@require_POST
def api_create_transaction(request):
    """Create a manual journal entry."""
    try:
        payload = json.loads(request.body)
    except JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Payload JSON invalide.'}, status=400)

    try:
        company = _get_company(request)
        if not company:
            return JsonResponse({'status': 'error', 'message': 'Company non spécifiée'}, status=400)
        
        journal_id = payload.get('journal')
        if not journal_id:
            journal = Journal.objects.filter(company=company, journal_type='od').first()
            if not journal:
                return JsonResponse({'status': 'error', 'message': 'Journal non trouvé'}, status=400)
        else:
            try:
                journal = Journal.objects.get(id=journal_id, company=company)
            except (Journal.DoesNotExist, ValueError, DjangoValidationError):
                journal = Journal.objects.get(code=journal_id, company=company)
            
        lines_payload = payload.get('lines', [])
        if len(lines_payload) < 2:
            return JsonResponse({'status': 'error', 'message': 'Au moins deux lignes sont requises.'}, status=400)

        total_debit = Decimal('0')
        total_credit = Decimal('0')
        normalized_lines = []
        
        for line in lines_payload:
            acc_id = line.get('account')
            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))
            
            if not acc_id:
                continue
            if debit < 0 or credit < 0:
                return JsonResponse({'status': 'error', 'message': 'Les montants négatifs ne sont pas autorisés.'}, status=400)
            if debit > 0 and credit > 0:
                return JsonResponse({'status': 'error', 'message': 'Une ligne ne peut pas porter un débit et un crédit simultanément.'}, status=400)
            if debit == 0 and credit == 0:
                return JsonResponse({'status': 'error', 'message': 'Chaque ligne doit porter un montant.'}, status=400)

            try:
                account = Account.objects.get(id=acc_id, company=company)
            except (Account.DoesNotExist, ValueError, DjangoValidationError):
                account = Account.objects.get(code=acc_id, company=company)

            normalized_lines.append({
                'account': account,
                'debit': debit,
                'credit': credit,
                'description': line.get('description', payload.get('description', 'Saisie manuelle')),
            })
            total_debit += debit
            total_credit += credit

        if len(normalized_lines) < 2:
            return JsonResponse({'status': 'error', 'message': 'Au moins deux lignes valides sont requises.'}, status=400)
        if total_debit <= ZERO or total_credit <= ZERO:
            return JsonResponse({'status': 'error', 'message': 'Les totaux débit et crédit doivent être strictement positifs.'}, status=400)
        if total_debit != total_credit:
            return JsonResponse({'status': 'error', 'message': "L'écriture doit être équilibrée."}, status=400)

        tx = Transaction.objects.create(
            company=company,
            journal=journal,
            reference=payload.get('reference', f"MAN-{datetime.now().strftime('%Y%m%d%H%M')}"),
            date=payload.get('date', datetime.now().date()),
            description=payload.get('description', 'Saisie manuelle'),
            status=Transaction.TransactionStatus.PENDING,
            created_by=request.user
        )

        for line in normalized_lines:
            TransactionLine.objects.create(
                transaction=tx,
                account=line['account'],
                debit=line['debit'],
                credit=line['credit'],
                description=line['description']
            )
        
        tx.total_debit = total_debit
        tx.total_credit = total_credit
        tx.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Écriture créée en attente de validation',
            'transaction_id': str(tx.id)
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def api_post_transaction(request, transaction_id):
    """
    Valide une transaction en attente.
    """
    try:
        company = _get_company(request)
        tx = Transaction.objects.get(id=transaction_id, company=company)
        
        if tx.status != Transaction.TransactionStatus.PENDING:
            return JsonResponse({'status': 'error', 'message': 'Seules les transactions en attente peuvent être validées.'}, status=400)
            
        post_transaction(tx, user=request.user)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Transaction validée avec succès et soldes mis à jour.'
        })
    except Transaction.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Transaction non trouvée.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
@login_required
def api_trial_balance(request):
    """API: Get Full Trial Balance (Essai Complet)"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': 'Company non spécifiée'}, status=400)
    
    # 1. Fetch all accounts
    accounts = Account.objects.filter(company=company).order_by('code')
    
    # 2. Prepare aggregated movements
    # We aggregate debits and credits from TransactionLine for validated transactions
    movements = TransactionLine.objects.filter(
        transaction__company=company,
        transaction__status=Transaction.TransactionStatus.POSTED
    ).values('account_id').annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )
    
    # Map movements for quick access
    movements_dict = {m['account_id']: (m['total_debit'] or ZERO, m['total_credit'] or ZERO) for m in movements}
    
    trial_balance = []
    total_initial_debit = Decimal('0')
    total_initial_credit = Decimal('0')
    total_mov_debit = Decimal('0')
    total_mov_credit = Decimal('0')
    total_final_debit = Decimal('0')
    total_final_credit = Decimal('0')
    
    for acc in accounts:
        # Initial balance (OHADA/IFRS logic)
        # For Assets (2,3,5) and Expenses (6): Opening is usually debit
        # For Liabilities (1,4L), Equity (1) and Income (7): Opening is usually credit
        # Here we use the stored opening_balance and assume it follows the account type
        
        initial_debit = Decimal('0')
        initial_credit = Decimal('0')
        
        # Simple heuristic for trial balance display:
        if acc.account_type in [Account.AccountType.ASSET, Account.AccountType.EXPENSE]:
            if acc.opening_balance >= 0:
                initial_debit = acc.opening_balance
            else:
                initial_credit = abs(acc.opening_balance)
        else:
            if acc.opening_balance >= 0:
                initial_credit = acc.opening_balance
            else:
                initial_debit = abs(acc.opening_balance)
        
        # Movements
        mov_debit, mov_credit = movements_dict.get(acc.id, (Decimal('0'), Decimal('0')))
        
        # Final Balance
        # Calculation: Opening + Movements
        # Current balance in model might be net, but we want debit/credit columns
        
        # Net sum of all
        net_total = (initial_debit - initial_credit) + (mov_debit - mov_credit)
        
        final_debit = Decimal('0')
        final_credit = Decimal('0')
        
        if net_total >= 0:
            final_debit = net_total
        else:
            final_credit = abs(net_total)
            
        trial_balance.append({
            'id': str(acc.id),
            'code': acc.code,
            'name': acc.name,
            'initial_debit': float(initial_debit),
            'initial_credit': float(initial_credit),
            'mov_debit': float(mov_debit),
            'mov_credit': float(mov_credit),
            'final_debit': float(final_debit),
            'final_credit': float(final_credit),
        })
        
        # Totals for row confirmation
        total_initial_debit += initial_debit
        total_initial_credit += initial_credit
        total_mov_debit += mov_debit
        total_mov_credit += mov_credit
        total_final_debit += final_debit
        total_final_credit += final_credit
        
    return JsonResponse({
        'status': 'success',
        'data': trial_balance,
        'totals': {
            'initial_debit': float(total_initial_debit),
            'initial_credit': float(total_initial_credit),
            'mov_debit': float(total_mov_debit),
            'mov_credit': float(total_mov_credit),
            'final_debit': float(total_final_debit),
            'final_credit': float(total_final_credit),
        }
    })
