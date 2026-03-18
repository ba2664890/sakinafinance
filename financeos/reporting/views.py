"""
États Financiers / Reporting Views — FinanceOS IA
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


@login_required
def reporting_view(request):
    """Module États Financiers — vue principale (Squelette)"""
    return render(request, 'reporting/index.html', {'page_title': 'États Financiers'})


@login_required
def api_reporting_data(request):
    """API: Get Financial Statements Data"""
    # Note: No models currently in reporting app, using data-driven structure for now
    data = {
        'income_statement': [
            {'label': "Chiffre d'affaires net", 'current': 428_500_000, 'previous': 381_200_000, 'is_total': False, 'positive': True, 'variation': 12.4},
            {'label': 'Autres produits d\'exploitation', 'current': 12_800_000, 'previous': 10_500_000, 'is_total': False, 'positive': True, 'variation': 21.9},
            {'label': "Achats et charges externes", 'current': -142_500_000, 'previous': -128_900_000, 'is_total': False, 'positive': False, 'variation': 10.5},
            {'label': 'Charges de personnel', 'current': -89_200_000, 'previous': -82_400_000, 'is_total': False, 'positive': False, 'variation': 8.2},
            {'label': 'Dotations amortissements', 'current': -45_800_000, 'previous': -43_200_000, 'is_total': False, 'positive': False, 'variation': 6.0},
            {'label': 'Résultat d\'exploitation (EBIT)', 'current': 163_800_000, 'previous': 137_200_000, 'is_total': True, 'positive': True, 'variation': 19.4},
            {'label': 'Charges financières nettes', 'current': -32_100_000, 'previous': -28_600_000, 'is_total': False, 'positive': False, 'variation': 12.2},
            {'label': 'Résultat avant impôt', 'current': 131_700_000, 'previous': 108_600_000, 'is_total': True, 'positive': True, 'variation': 21.3},
            {'label': 'Impôts sur les bénéfices (IS 30%)', 'current': -47_500_000, 'previous': -38_900_000, 'is_total': False, 'positive': False, 'variation': 22.1},
            {'label': 'Résultat net', 'current': 84_200_000, 'previous': 69_700_000, 'is_total': True, 'positive': True, 'variation': 20.8},
        ],
        'ratios': [
            {'label': 'Marge brute', 'value': '66.8%', 'benchmark': '62%', 'status': 'good'},
            {'label': 'Marge EBITDA', 'value': '24.3%', 'benchmark': '20%', 'status': 'good'},
            {'label': 'Marge nette', 'value': '19.6%', 'benchmark': '15%', 'status': 'good'},
            {'label': 'ROE', 'value': '19.9%', 'benchmark': '15%', 'status': 'good'},
            {'label': 'ROA', 'value': '9.9%', 'benchmark': '10%', 'status': 'warning'},
            {'label': 'Ratio d\'endettement', 'value': '47%', 'benchmark': '<60%', 'status': 'good'},
        ],
        'cash_flows': [
            {'category': "Flux d'exploitation", 'amount': 124_800_000, 'positive': True},
            {'category': "Flux d'investissement", 'amount': -48_200_000, 'positive': False},
            {'category': 'Flux de financement', 'amount': -22_400_000, 'positive': False},
            {'category': 'Variation nette de trésorerie', 'amount': 54_200_000, 'positive': True},
        ],
        'reports': [
            {'name': 'Bilan consolidé T1 2025', 'date': '31/03/2025', 'type': 'Bilan', 'status': 'Finalisé'},
            {'name': 'Compte de résultat Mars 2025', 'date': '31/03/2025', 'type': 'P&L', 'status': 'Finalisé'},
            {'name': 'Rapport IFRS Q1 2025', 'date': '05/04/2025', 'type': 'IFRS', 'status': 'En cours'},
            {'name': 'États financiers annuels 2024', 'date': '28/02/2025', 'type': 'Annuel', 'status': 'Finalisé'},
        ],
        'revenue_current': 428_500_000,
        'revenue_prev': 381_200_000,
        'revenue_growth': 12.4,
        'net_income': 84_200_000,
        'ebitda_margin': 24.3,
    }
    return JsonResponse(data)
