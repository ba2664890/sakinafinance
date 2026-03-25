"""
Core Views - SakinaFinance
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
from sakinafinance.accounting.models import Transaction, Invoice, Account
from sakinafinance.hr.models import Employee
from sakinafinance.procurement.models import PurchaseOrder


def _get_period_range(period='year'):
    """Return (start_date, end_date) for the given period string."""
    today = timezone.now().date()
    if period == 'month':
        start = today.replace(day=1)
        end = today
    elif period == 'quarter':
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=q_start_month, day=1)
        end = today
    else:  # year
        start = today.replace(month=1, day=1)
        end = today
    return start, end


def home_view(request):
    """Landing Page View"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


@login_required
def dashboard_view(request):
    """Main Dashboard View"""
    user = request.user
    company = user.company
    
    # Initialize with 0s - API will load real data
    context = {
        'user': user,
        'company': company,
        'kpis': {
            'total_revenue': 0,
            'revenue_growth': 0,
            'net_cash': 0,
            'cash_growth': 0,
            'ebitda': 0,
            'ebitda_margin': 0,
            'pending_invoices': 0,
            'overdue_invoices': 0,
        },
        'recent_activity': [],
        'page_title': 'Tableau de Bord',
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def executive_view(request):
    """Executive Dashboard View"""
    context = {
        'page_title': 'Executive View',
        'total_revenue': '0',
        'revenue_growth': '0%',
        'group_ebitda': '0',
        'ebitda_margin': '0%',
        'net_cash': '0',
        'cash_growth': '0%',
    }
    return render(request, 'core/executive.html', context)


@login_required
def consolidation_view(request):
    """Consolidation Hub View"""
    context = {
        'page_title': 'Consolidation Hub',
        'group_net_income': '0',
        'net_income_growth': '0%',
        'entity_match_rate': '0/0',
        'interco_matching': '0%',
        'days_to_close': 'N/A',
        'status': 'READY',
    }
    return render(request, 'core/consolidation.html', context)


from sakinafinance.ai_engine.models import AIInsight, AnomalyDetection

@login_required
def ai_advisor_view(request):
    """AI Advisor View — Enhanced with Engine Data"""
    user = request.user
    company = user.company
    
    context = {
        'page_title': 'IA Advisor',
        'suggested_analyses': [
            {'icon': 'bi-graph-up', 'title': 'Prévision de trésorerie', 'prompt': 'Fais-moi une prévision de trésorerie sur 6 mois.'},
            {'icon': 'bi-pie-chart', 'title': 'Analyse de marge EBITDA', 'prompt': 'Analyse ma rentabilité et ma marge EBITDA.'},
            {'icon': 'bi-shield-exclamation', 'title': 'Détection de risques', 'prompt': 'Quels sont les risques financiers actuels ?'},
        ],
        'insights': AIInsight.objects.filter(company=company, is_dismissed=False)[:5] if company else [],
        'anomalies': AnomalyDetection.objects.filter(company=company, is_false_positive=False)[:5] if company else [],
    }
    return render(request, 'core/ai_advisor.html', context)


@login_required
def settings_view(request):
    """Settings View"""
    return render(request, 'core/settings.html', {'page_title': 'Paramètres'})


# API Views
@login_required
def api_dashboard_data(request):
    """API: Get Dashboard Data with Real Database Values + period filter + EBITDA"""
    user = request.user
    company = user.company
    period = request.GET.get('period', 'year')  # month | quarter | year

    today = timezone.now().date()
    if period == 'month':
        period_start = today.replace(day=1)
    elif period == 'quarter':
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        period_start = today.replace(month=q_start_month, day=1)
    else:
        period_start = today.replace(month=1, day=1)
    period_end = today

    data = {
        'kpis': {
            'total_revenue': 0,
            'expenses': 0,
            'net_income': 0,
            'revenue_growth': 0,
            'net_cash': 0,
            'cash_inflows': 0,
            'cash_outflows': 0,
            'cash_growth': 0,
            'ebitda': 0,
            'ebitda_margin': 0,
            'pending_invoices': 0,
            'overdue_invoices': 0,
            'employee_count': 0,
            'period': period,
        },
        'chart_data': {
            'labels': [],
            'revenue': [],
            'expenses': [],
            'ebitda': [],
        },
        'recent_transactions': [],
        'top_invoices': [],
        'alerts': [],
        'cash_flow': {'inflows': 0, 'outflows': 0, 'reserve': 0},
    }

    if not company:
        return JsonResponse(data)

    # ── Revenue & Expenses (period-scoped) ──
    revenue = Transaction.objects.filter(
        company=company,
        journal__journal_type='sales',
        status='posted',
        date__range=[period_start, period_end],
    ).aggregate(total=Sum('total_credit'))['total'] or Decimal('0')

    expenses = Transaction.objects.filter(
        company=company,
        journal__journal_type__in=['purchases', 'od'],
        status='posted',
        date__range=[period_start, period_end],
    ).aggregate(total=Sum('total_debit'))['total'] or Decimal('0')

    ebitda = revenue - expenses
    ebitda_margin = round(float(ebitda) / float(revenue) * 100, 1) if revenue else 0
    net_income = ebitda  # simplified (no D&A model yet)

    # ── Cash (all-time positions) ──
    cash_qs = Transaction.objects.filter(
        company=company,
        journal__journal_type__in=['bank', 'cash'],
        status='posted',
    ).aggregate(dr=Sum('total_debit'), cr=Sum('total_credit'))
    cash_in = float(cash_qs['dr'] or 0)
    cash_out = float(cash_qs['cr'] or 0)
    net_cash = cash_in - cash_out

    # ── Invoices ──
    inv_stats = Invoice.objects.filter(company=company).aggregate(
        pending=Count('id', filter=Q(status='sent')),
        overdue=Count('id', filter=Q(status='overdue')),
    )

    # ── Employees ──
    try:
        emp_count = Employee.objects.filter(company=company, status='active').count()
    except Exception:
        emp_count = 0

    data['kpis'].update({
        'total_revenue': float(revenue),
        'expenses': float(expenses),
        'net_income': float(net_income),
        'net_cash': net_cash,
        'cash_inflows': cash_in,
        'cash_outflows': cash_out,
        'ebitda': float(ebitda),
        'ebitda_margin': ebitda_margin,
        'pending_invoices': inv_stats['pending'],
        'overdue_invoices': inv_stats['overdue'],
        'employee_count': emp_count,
    })

    # Cash flow breakdown for donut chart
    reserve = max(net_cash, 0)
    data['cash_flow'] = {
        'inflows': cash_in,
        'outflows': cash_out,
        'reserve': reserve,
    }

    # ── 8-month chart ──
    labels, rev_data, exp_data, ebitda_data = [], [], [], []
    for i in range(7, -1, -1):
        first_day = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        m_rev = float(Transaction.objects.filter(
            company=company, journal__journal_type='sales', status='posted',
            date__range=[first_day, last_day],
        ).aggregate(t=Sum('total_credit'))['t'] or 0) / 1_000_000

        m_exp = float(Transaction.objects.filter(
            company=company, journal__journal_type__in=['purchases', 'od'], status='posted',
            date__range=[first_day, last_day],
        ).aggregate(t=Sum('total_debit'))['t'] or 0) / 1_000_000

        labels.append(first_day.strftime('%b'))
        rev_data.append(round(m_rev, 2))
        exp_data.append(round(m_exp, 2))
        ebitda_data.append(round(m_rev - m_exp, 2))

    data['chart_data'] = {
        'labels': labels,
        'revenue': rev_data,
        'expenses': exp_data,
        'ebitda': ebitda_data,
    }

    # ── Recent Transactions ──
    recent = Transaction.objects.filter(
        company=company, status='posted'
    ).order_by('-date')[:8]
    for t in recent:
        data['recent_transactions'].append({
            'id': str(t.id),
            'date': t.date.strftime('%d %b %Y'),
            'description': t.description[:60],
            'amount': float(t.total_debit - t.total_credit),
            'type': t.journal.journal_type,
            'status': t.get_status_display(),
            'currency': t.currency,
        })

    # ── Top Invoices ──
    top_inv = Invoice.objects.filter(
        company=company, status__in=['sent', 'overdue']
    ).order_by('-total')[:5]
    for inv in top_inv:
        data['top_invoices'].append({
            'number': inv.invoice_number,
            'partner': inv.partner_name,
            'total': float(inv.total),
            'due': inv.due_date.strftime('%d %b %Y'),
            'status': inv.status,
            'status_label': inv.get_status_display(),
            'currency': inv.currency,
        })

    # ── Alerts ──
    if inv_stats['overdue'] > 0:
        overdue_amount = Invoice.objects.filter(
            company=company, status='overdue'
        ).aggregate(s=Sum('amount_due'))['s'] or 0
        data['alerts'].append({
            'type': 'danger',
            'icon': 'bi-exclamation-triangle-fill',
            'title': f"{inv_stats['overdue']} facture(s) en retard",
            'message': f"Montant en souffrance : {float(overdue_amount):,.0f} {inv_stats.get('currency', 'XOF')}",
            'action_text': 'Relancer clients',
            'action_url': '/accounting/',
        })
    if inv_stats['pending'] > 0:
        data['alerts'].append({
            'type': 'warning',
            'icon': 'bi-clock-fill',
            'title': f"{inv_stats['pending']} facture(s) en attente",
            'message': "Ces factures n'ont pas encore été payées.",
            'action_text': 'Voir factures',
            'action_url': '/accounting/',
        })

    return JsonResponse(data)


@login_required
def api_kpi_data(request):
    """API: Get KPI Data (Detailed)"""
    # Reuse logical part of api_dashboard_data if needed or extend
    return api_dashboard_data(request)


@login_required
def api_notifications(request):
    """API: Get Notifications — returns real count for badge"""
    user = request.user
    company = user.company
    notifications = []
    total_count = 0

    if company:
        overdue_count = Invoice.objects.filter(company=company, status='overdue').count()
        pending_count = Invoice.objects.filter(company=company, status='sent').count()

        if overdue_count > 0:
            notifications.append({
                'id': 'notif-overdue',
                'title': f'{overdue_count} facture(s) en retard',
                'message': 'Action requise — relancer les clients.',
                'type': 'danger',
                'icon': 'bi-exclamation-triangle',
                'time': 'Aujourd\'hui',
                'url': '/accounting/',
            })
            total_count += overdue_count

        if pending_count > 0:
            notifications.append({
                'id': 'notif-pending',
                'title': f'{pending_count} facture(s) en attente',
                'message': 'Ces factures attendent un paiement.',
                'type': 'warning',
                'icon': 'bi-clock',
                'time': 'Aujourd\'hui',
                'url': '/accounting/',
            })
            total_count += pending_count

    return JsonResponse({'notifications': notifications, 'total_count': total_count})


@login_required
def api_executive_data(request):
    """API: Get Executive Dashboard Data"""
    user = request.user
    company = user.company
    
    # Base Data from Dashboard API logic (reused)
    revenue = Transaction.objects.filter(company=company, journal__journal_type='sales', status='posted').aggregate(total=Sum('total_credit'))['total'] or 0
    cash = Transaction.objects.filter(company=company, journal__journal_type__in=['bank', 'cash'], status='posted').aggregate(dr=Sum('total_debit'), cr=Sum('total_credit'))
    net_cash = (cash['dr'] or 0) - (cash['cr'] or 0)
    inv_stats = Invoice.objects.filter(company=company).aggregate(
        overdue_count=Count('id', filter=Q(status='overdue')),
        overdue_amount=Sum('total', filter=Q(status='overdue'))
    )
    
    data = {
        'kpis': {
            'revenue': float(revenue),
            'revenue_growth': 12.4, # Simulé
            'ebitda': float(revenue * Decimal('0.2')), # Simulé
            'ebitda_margin': 20.0,
            'net_cash': float(net_cash),
            'liquidity_ratio': 2.4,
        },
        'risks': [
            {
                'title': 'Factures en retard',
                'level': 'danger' if inv_stats['overdue_count'] > 5 else 'warning',
                'exposure': float(inv_stats['overdue_amount'] or 0),
                'probability': 85 if inv_stats['overdue_count'] > 0 else 10
            },
            {
                'title': 'Inflation Fournisseurs',
                'level': 'warning',
                'exposure': float(revenue * Decimal('0.05')),
                'probability': 45
            }
        ],
        'entities': [
            {
                'name': company.name if company else 'Holding Principale',
                'type': 'HQ • AFRICA',
                'revenue': float(revenue),
                'margin': 20.0,
                'cash': float(net_cash),
                'vitality': 95
            },
            {
                'name': 'Cloud Services LLC',
                'type': 'TECH • NORTH AMERICA',
                'revenue': float(revenue * Decimal('0.4')),
                'margin': 28.4,
                'cash': float(net_cash * Decimal('0.3')),
                'vitality': 98
            },
            {
                'name': 'UK Logistics Hub',
                'type': 'TRANSPORT • EMEA',
                'revenue': float(revenue * Decimal('0.15')),
                'margin': 12.1,
                'cash': float(net_cash * Decimal('0.1')),
                'vitality': 64
            }
        ],
        'geography': [
            {'region': 'North America', 'value': float(revenue * Decimal('0.5'))},
            {'region': 'EMEA Region', 'value': float(revenue * Decimal('0.3'))},
            {'region': 'Asia Pacific', 'value': float(revenue * Decimal('0.2'))}
        ],
        'chart_data': {
            'labels': ['OCT', 'NOV', 'DEC', 'JAN', 'FEB', 'MAR', 'APR', 'MAY'],
            'actual': [320, 280, 350, 380, 400, 420, 410, float(revenue) / 1000000 if revenue else 428],
            'target': [300, 300, 320, 350, 380, 400, 420, 450]
        }
    }
    
    return JsonResponse(data)

@login_required
def api_consolidation_data(request):
    """API: Get Group Consolidation Data"""
    user = request.user
    company = user.company
    
    # Base Data (Consolidated across company Group)
    # We use the main company's revenue as a proxy for the group income for now
    revenue = Transaction.objects.filter(company=company, journal__journal_type='sales', status='posted').aggregate(total=Sum('total_credit'))['total'] or 0
    expenses = Transaction.objects.filter(company=company, journal__journal_type__in=['purchase', 'expense'], status='posted').aggregate(total=Sum('total_debit'))['total'] or 0
    net_income = revenue - expenses
    
    data = {
        'kpis': {
            'group_net_income': float(net_income),
            'income_change': 12.5,
            'entity_match_rate': "12/14",
            'interco_matching': 88.4,
            'days_to_close': 4,
            'status': 'IN PROGRESS'
        },
        'entities': [
            {
                'id': 'US',
                'name': 'North America Inc.',
                'currency': 'USD (Global)',
                'income': 1240000,
                'norm': 'IFRS',
                'conversion': 'Native',
                'status': 'CLOSED'
            },
            {
                'id': 'FR',
                'name': 'TechEurope SAS',
                'currency': 'EUR (Local)',
                'income': 890200,
                'norm': 'IFRS',
                'conversion': 'Pending',
                'status': 'OPEN'
            },
            {
                'id': 'SN',
                'name': 'Dakar Ops Ltd',
                'currency': 'XOF (Local)',
                'income': 450000000,
                'norm': 'OHADA',
                'conversion': 'IFRS Mapped',
                'status': 'CLOSED'
            }
        ],
        'interco': {
            'issues': 8,
            'pairs': [
                {'names': 'USA ↔ Europe', 'status': 'Matched', 'progress': 100, 'color': 'success'},
                {'names': 'Europe ↔ Dakar', 'status': 'Unbalanced (-$12k)', 'progress': 75, 'color': 'warning'},
                {'names': 'Group ↔ Asia', 'status': 'Waiting', 'progress': 0, 'color': 'secondary'}
            ]
        }
    }
    
    return JsonResponse(data)
