"""
Trésorerie & Cash Flow Views — FinanceOS IA
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


@login_required
def treasury_view(request):
    """Module Trésorerie — vue principale"""
    # Données de démonstration réalistes pour une entreprise en Afrique de l'Ouest
    context = {
        'page_title': 'Trésorerie & Cash Flow',

        # KPIs
        'total_liquidity': 12_482_903,
        'liquidity_growth': 4.2,
        'net_cashflow_30d': 842_100,
        'cashflow_growth': -1.8,
        'dso_days': 42,
        'dso_target': 38,
        'ml_confidence': 94.2,
        'cash_cycle_days': 35,

        # Comptes bancaires
        'bank_accounts': [
            {'entity': 'FinanceOS North Am.', 'bank': 'JP Morgan', 'balance': 2_840_000, 'currency': 'USD', 'status': 'active'},
            {'entity': 'OS Europe SAS', 'bank': 'BNP Paribas', 'balance': 1_240_000, 'currency': 'EUR', 'status': 'active'},
            {'entity': 'OS Africa Ltd', 'bank': 'Ecobank', 'balance': 450_000_000, 'currency': 'XOF', 'status': 'pending'},
            {'entity': 'OS Sénégal SARL', 'bank': 'CBAO', 'balance': 285_000_000, 'currency': 'XOF', 'status': 'active'},
            {'entity': 'OS Côte d\'Ivoire', 'bank': 'Société Générale', 'balance': 312_000_000, 'currency': 'XOF', 'status': 'active'},
        ],

        # Prévisions MoM
        'forecasts': [
            {'period': 'Oct 2024', 'inflows': 2_400_000, 'outflows': 1_800_000, 'net': 600_000},
            {'period': 'Nov 2024', 'inflows': 3_100_000, 'outflows': 2_200_000, 'net': 900_000},
            {'period': 'Déc 2024', 'inflows': 4_200_000, 'outflows': 2_800_000, 'net': 1_400_000},
            {'period': 'Jan 2025', 'inflows': 1_900_000, 'outflows': 2_100_000, 'net': -200_000},
            {'period': 'Fév 2025', 'inflows': 2_600_000, 'outflows': 1_950_000, 'net': 650_000},
            {'period': 'Mar 2025', 'inflows': 3_800_000, 'outflows': 2_400_000, 'net': 1_400_000},
        ],

        # Exposition devises
        'currency_exposure': [
            {'currency': 'XOF', 'amount': '1.2B', 'risk': 'VOLATILE', 'risk_class': 'warning'},
            {'currency': 'EUR', 'amount': '3.8M', 'risk': 'STABLE', 'risk_class': 'success'},
            {'currency': 'USD', 'amount': '4.2M', 'risk': 'CRITIQUE', 'risk_class': 'danger'},
        ],

        # Working Capital (BFR)
        'dio_days': 58,
        'dpo_days': 65,
    }
    return render(request, 'treasury/index.html', context)


@login_required
def treasury_api_cashflow(request):
    """API: données cashflow pour charts"""
    data = {
        'labels': ['Oct', 'Nov', 'Déc', 'Jan', 'Fév', 'Mar'],
        'inflows': [2400, 3100, 4200, 1900, 2600, 3800],
        'outflows': [1800, 2200, 2800, 2100, 1950, 2400],
    }
    return JsonResponse(data)
