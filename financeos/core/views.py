"""
Core Views for FinanceOS IA
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta


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
    
    # Get KPIs based on user's company and permissions
    kpis = {
        'total_revenue': 0,
        'total_expenses': 0,
        'net_cash': 0,
        'pending_invoices': 0,
    }
    
    if company:
        # These would be calculated from actual data
        kpis = {
            'total_revenue': 428500000,  # Example: 428.5M XOF
            'revenue_growth': 12.4,
            'total_expenses': 344280000,
            'expense_growth': -2.1,
            'net_cash': 112900000,
            'cash_growth': 5.7,
            'ebitda': 84200000,
            'ebitda_margin': 19.6,
            'pending_invoices': 23,
            'overdue_invoices': 5,
        }
    
    context = {
        'user': user,
        'company': company,
        'kpis': kpis,
        'page_title': 'Tableau de Bord',
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def executive_view(request):
    """Executive Dashboard View"""
    context = {
        'page_title': 'Executive View',
        'total_revenue': '$428.5M',
        'revenue_growth': '+12.4%',
        'group_ebitda': '$84.2M',
        'ebitda_margin': '19.6%',
        'net_cash': '$112.9M',
        'cash_growth': '+5.7%',
    }
    return render(request, 'core/executive.html', context)


@login_required
def consolidation_view(request):
    """Consolidation Hub View"""
    context = {
        'page_title': 'Consolidation Hub',
        'group_net_income': '$4.2M',
        'net_income_growth': '+12.5%',
        'entity_match_rate': '12/14',
        'interco_matching': '88.4%',
        'days_to_close': '4 Days',
        'status': 'IN PROGRESS',
    }
    return render(request, 'core/consolidation.html', context)


@login_required
def ai_advisor_view(request):
    """AI Advisor View"""
    context = {
        'page_title': 'IA Advisor',
        'suggested_analyses': [
            {'icon': 'trending_down', 'title': 'Analyze EBITDA drop'},
            {'icon': 'monitoring', 'title': 'Predict Q4 Cash'},
        ],
    }
    return render(request, 'core/ai_advisor.html', context)


@login_required
def settings_view(request):
    """Settings View"""
    return render(request, 'core/settings.html', {'page_title': 'Paramètres'})


# API Views
@login_required
def api_dashboard_data(request):
    """API: Get Dashboard Data"""
    data = {
        'kpis': {
            'total_revenue': 428500000,
            'revenue_growth': 12.4,
            'net_cash': 112900000,
            'cash_growth': 5.7,
            'ebitda': 84200000,
            'ebitda_margin': 19.6,
        },
        'chart_data': {
            'labels': ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May'],
            'revenue': [320, 280, 350, 380, 400, 420, 410, 428],
            'target': [300, 300, 320, 350, 380, 400, 420, 450],
        },
        'recent_transactions': [
            {'date': '2024-05-15', 'description': 'Vente Client A', 'amount': 1250000, 'type': 'income'},
            {'date': '2024-05-14', 'description': 'Fournisseur B', 'amount': -450000, 'type': 'expense'},
            {'date': '2024-05-13', 'description': 'Salaires', 'amount': -2800000, 'type': 'expense'},
        ],
        'alerts': [
            {'type': 'warning', 'message': 'TVA à déclarer dans 3 jours'},
            {'type': 'info', 'message': 'Nouveau rapport mensuel disponible'},
        ]
    }
    return JsonResponse(data)


@login_required
def api_kpi_data(request):
    """API: Get KPI Data"""
    period = request.GET.get('period', 'month')
    
    # This would query actual database
    data = {
        'revenue': {
            'value': 428500000,
            'growth': 12.4,
            'trend': 'up',
        },
        'expenses': {
            'value': 344280000,
            'growth': -2.1,
            'trend': 'down',
        },
        'cash': {
            'value': 112900000,
            'growth': 5.7,
            'trend': 'up',
        },
        'ebitda': {
            'value': 84200000,
            'margin': 19.6,
            'trend': 'up',
        },
    }
    return JsonResponse(data)


@login_required
def api_notifications(request):
    """API: Get Notifications"""
    notifications = [
        {
            'id': 1,
            'title': 'Alerte Trésorerie',
            'message': 'Le solde passe sous le seuil défini',
            'type': 'warning',
            'time': '5 min ago',
        },
        {
            'id': 2,
            'title': 'Nouvelle Facture',
            'message': 'Facture #F-2024-0123 reçue',
            'type': 'info',
            'time': '1 hour ago',
        },
    ]
    return JsonResponse({'notifications': notifications})
