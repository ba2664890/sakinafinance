"""
États Financiers / Reporting Views — SakinaFinance
"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from sakinafinance.accounting.models import FinancialStatement, Transaction
from sakinafinance.accounting.services import (
    ZERO,
    build_balance_sheet_snapshot,
    posted_lines_queryset,
)


@login_required
def reporting_view(request):
    """Module États Financiers — vue principale."""
    return render(request, 'reporting/index.html', {'page_title': 'États Financiers'})


def _variation(current, previous):
    if previous == ZERO:
        return None
    return round(float(((current - previous) / previous) * 100), 1)


@login_required
def api_reporting_data(request):
    """API: Get simplified reporting data based on posted accounting entries."""
    company = getattr(request.user, 'company', None)

    data = {
        'income_statement': [],
        'ratios': [],
        'cash_flows': [],
        'reports': [],
        'revenue_current': 0.0,
        'revenue_prev': 0.0,
        'revenue_growth': None,
        'net_income': 0.0,
        'ebitda_margin': None,
        'quality': {
            'level': 'warning',
            'title': 'Reporting indisponible',
            'message': "Aucune entreprise n'est associée à cet utilisateur.",
            'is_reliable': False,
        },
    }

    if not company:
        return JsonResponse(data)

    today = timezone.now().date()
    period_start = today.replace(month=1, day=1)
    period_days = max((today - period_start).days + 1, 1)
    prev_end = period_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)

    current_lines = posted_lines_queryset(company, start_date=period_start, end_date=today)
    previous_lines = posted_lines_queryset(company, start_date=prev_start, end_date=prev_end)

    def class_totals(queryset, account_class):
        debit = queryset.filter(account__account_class=account_class).aggregate(total=Sum('debit'))['total'] or ZERO
        credit = queryset.filter(account__account_class=account_class).aggregate(total=Sum('credit'))['total'] or ZERO
        return debit, credit

    current_rev_debit, current_rev_credit = class_totals(current_lines, '7')
    prev_rev_debit, prev_rev_credit = class_totals(previous_lines, '7')
    current_exp_debit, current_exp_credit = class_totals(current_lines, '6')
    prev_exp_debit, prev_exp_credit = class_totals(previous_lines, '6')

    revenue_current = current_rev_credit - current_rev_debit
    revenue_prev = prev_rev_credit - prev_rev_debit
    expenses_current = current_exp_debit - current_exp_credit
    expenses_prev = prev_exp_debit - prev_exp_credit
    operating_result_current = revenue_current - expenses_current
    operating_result_prev = revenue_prev - expenses_prev

    balance_sheet = build_balance_sheet_snapshot(company, end_date=today)
    current_assets = balance_sheet['current_assets']
    current_liabilities = balance_sheet['current_liabilities']
    total_assets = balance_sheet['total_assets']
    total_equity = balance_sheet['total_equity']
    total_liabilities = balance_sheet['total_liabilities']
    cash = balance_sheet['cash']
    stocks = balance_sheet['stocks']

    liquidity_ratio = round(float(current_assets / current_liabilities), 2) if current_liabilities > ZERO else None
    quick_ratio = round(float((current_assets - stocks) / current_liabilities), 2) if current_liabilities > ZERO else None
    immediate_liquidity = round(float(cash / current_liabilities), 2) if current_liabilities > ZERO else None
    equity_ratio = round(float(total_equity / total_assets) * 100, 1) if total_assets > ZERO else None
    debt_ratio = round(float(total_liabilities / total_assets) * 100, 1) if total_assets > ZERO else None
    operating_margin = round(float((operating_result_current / revenue_current) * 100), 1) if revenue_current > ZERO else None

    cash_inflows = current_lines.filter(account__account_class='5').aggregate(total=Sum('debit'))['total'] or ZERO
    cash_outflows = current_lines.filter(account__account_class='5').aggregate(total=Sum('credit'))['total'] or ZERO
    net_cash_variation = cash_inflows - cash_outflows

    statement_rows = [
        {
            'label': 'Produits comptabilisés (classe 7)',
            'current': float(revenue_current),
            'previous': float(revenue_prev),
            'is_total': False,
            'positive': True,
            'variation': _variation(revenue_current, revenue_prev),
        },
        {
            'label': 'Charges comptabilisées (classe 6)',
            'current': float(-expenses_current),
            'previous': float(-expenses_prev),
            'is_total': False,
            'positive': False,
            'variation': _variation(expenses_current, expenses_prev),
        },
        {
            'label': 'Résultat opérationnel simplifié',
            'current': float(operating_result_current),
            'previous': float(operating_result_prev),
            'is_total': True,
            'positive': operating_result_current >= ZERO,
            'variation': _variation(operating_result_current, operating_result_prev),
        },
    ]

    statements = FinancialStatement.objects.filter(company=company).order_by('-period_end')[:5]
    reports = [
        {
            'name': statement.get_statement_type_display(),
            'date': statement.period_end.strftime('%d/%m/%Y'),
            'type': statement.statement_type,
            'status': 'Brouillon' if statement.is_draft else 'Finalisé',
        }
        for statement in statements
    ]

    has_posted_entries = Transaction.objects.filter(company=company, status=Transaction.TransactionStatus.POSTED).exists()
    quality_message = (
        "Reporting calculé sur les écritures validées. Le mapping normatif OHADA détaillé et les états réglementaires complets restent à finaliser."
        if has_posted_entries
        else "Aucune écriture validée n'alimente encore le reporting. Les tableaux restent volontairement vides pour éviter des chiffres fictifs."
    )

    data = {
        'income_statement': statement_rows if has_posted_entries else [],
        'ratios': [
            {'label': 'Liquidité générale', 'value': f'{liquidity_ratio}' if liquidity_ratio is not None else 'N/A', 'benchmark': '> 1.0', 'status': 'good' if liquidity_ratio is not None and liquidity_ratio >= 1 else 'warning'},
            {'label': 'Liquidité réduite', 'value': f'{quick_ratio}' if quick_ratio is not None else 'N/A', 'benchmark': '> 0.8', 'status': 'good' if quick_ratio is not None and quick_ratio >= 0.8 else 'warning'},
            {'label': 'Liquidité immédiate', 'value': f'{immediate_liquidity}' if immediate_liquidity is not None else 'N/A', 'benchmark': '> 0.2', 'status': 'good' if immediate_liquidity is not None and immediate_liquidity >= 0.2 else 'warning'},
            {'label': 'Autonomie financière', 'value': f'{equity_ratio}%' if equity_ratio is not None else 'N/A', 'benchmark': '> 30%', 'status': 'good' if equity_ratio is not None and equity_ratio >= 30 else 'warning'},
            {'label': "Ratio d'endettement", 'value': f'{debt_ratio}%' if debt_ratio is not None else 'N/A', 'benchmark': '< 70%', 'status': 'good' if debt_ratio is not None and debt_ratio < 70 else 'warning'},
            {'label': 'Marge opérationnelle', 'value': f'{operating_margin}%' if operating_margin is not None else 'N/A', 'benchmark': '> 10%', 'status': 'good' if operating_margin is not None and operating_margin >= 10 else 'warning'},
        ],
        'cash_flows': [
            {'category': 'Encaissements trésorerie (classe 5)', 'amount': float(cash_inflows), 'positive': True},
            {'category': 'Décaissements trésorerie (classe 5)', 'amount': float(-cash_outflows), 'positive': False},
            {'category': 'Variation nette de trésorerie', 'amount': float(net_cash_variation), 'positive': net_cash_variation >= ZERO},
        ],
        'reports': reports,
        'revenue_current': float(revenue_current),
        'revenue_prev': float(revenue_prev),
        'revenue_growth': _variation(revenue_current, revenue_prev),
        'net_income': float(operating_result_current),
        'ebitda_margin': operating_margin,
        'quality': {
            'level': 'info' if has_posted_entries else 'warning',
            'title': 'Reporting simplifié alimenté par la comptabilité' if has_posted_entries else 'Reporting en attente de données validées',
            'message': quality_message,
            'is_reliable': has_posted_entries,
        },
    }
    return JsonResponse(data)
