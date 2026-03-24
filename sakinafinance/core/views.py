"""
Core Views - SakinaFinance
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from sakinafinance.accounting.models import Transaction, Invoice, Account
from sakinafinance.hr.models import Employee
from sakinafinance.procurement.models import PurchaseOrder


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
    """API: Get Dashboard Data with Real Database Values"""
    user = request.user
    company = user.company
    
    # Defaults
    data = {
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
        'chart_data': {
            'labels': [],
            'revenue': [],
            'target': [300, 310, 320, 330, 340, 350, 360, 370],
        },
        'recent_transactions': [],
        'alerts': []
    }
    
    if company:
        # 1. Total Revenue
        revenue = Transaction.objects.filter(
            company=company, 
            journal__journal_type='sales',
            status='posted'
        ).aggregate(total=Sum('total_credit'))['total'] or 0
        
        # 1.1 Chart Data (Last 8 months)
        today = timezone.now().date()
        labels = []
        revenue_data = []
        for i in range(7, -1, -1):
            first_day = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_rev = Transaction.objects.filter(
                company=company,
                journal__journal_type='sales',
                status='posted',
                date__range=[first_day, last_day]
            ).aggregate(total=Sum('total_credit'))['total'] or 0
            
            labels.append(first_day.strftime('%b'))
            revenue_data.append(float(month_rev) / 1000000)
            
        data['chart_data']['labels'] = labels
        data['chart_data']['revenue'] = revenue_data
        
        # 2. Net Cash
        cash = Transaction.objects.filter(
            company=company,
            journal__journal_type__in=['bank', 'cash'],
            status='posted'
        ).aggregate(dr=Sum('total_debit'), cr=Sum('total_credit'))
        net_cash = (cash['dr'] or 0) - (cash['cr'] or 0)
        
        # 3. Invoices
        inv_stats = Invoice.objects.filter(company=company).aggregate(
            pending=Count('id', filter=Q(status='sent')),
            overdue=Count('id', filter=Q(status='overdue'))
        )
        
        data['kpis'].update({
            'total_revenue': float(revenue),
            'net_cash': float(net_cash),
            'pending_invoices': inv_stats['pending'],
            'overdue_invoices': inv_stats['overdue'],
        })
        
        # 4. Recent Transactions
        recent = Transaction.objects.filter(company=company, status='posted').order_by('-date')[:5]
        for t in recent:
            data['recent_transactions'].append({
                'id': str(t.id),
                'date': t.date.strftime('%d %b %Y'),
                'description': t.description,
                'amount': float(t.total_debit - t.total_credit),
                'status': t.get_status_display()
            })
            
        # 5. Alerts
        if inv_stats['overdue'] > 0:
            data['alerts'].append({
                'type': 'danger',
                'title': f"{inv_stats['overdue']} factures en retard",
                'message': "Action requise pour la relance client.",
                'action_text': 'Voir les factures',
                'action_url': '/accounting/'
            })
            
    return JsonResponse(data)


@login_required
def api_kpi_data(request):
    """API: Get KPI Data (Detailed)"""
    # Reuse logical part of api_dashboard_data if needed or extend
    return api_dashboard_data(request)


@login_required
def api_notifications(request):
    """API: Get Notifications"""
    user = request.user
    company = user.company
    notifications = []
    
    if company:
        overdue_count = Invoice.objects.filter(company=company, status='overdue').count()
        if overdue_count > 0:
            notifications.append({
                'id': 'notif-1',
                'title': 'Factures en retard',
                'message': f'Vous avez {overdue_count} factures impayées.',
                'type': 'warning',
                'time': 'À l\'instant',
            })
            
    return JsonResponse({'notifications': notifications})


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
