"""
Comptabilité Views — FinanceOS IA
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


@login_required
def accounting_view(request):
    """Module Comptabilité — vue principale"""
    context = {
        'page_title': 'Comptabilité Générale',

        # KPIs Comptables
        'total_assets': 845_200_000,
        'total_assets_growth': 8.3,
        'total_liabilities': 423_100_000,
        'equity': 422_100_000,
        'equity_ratio': 49.9,
        'net_income': 84_200_000,
        'net_income_margin': 19.6,
        'pending_entries': 47,

        # Bilan simplifié (en milliers XOF)
        'balance_sheet': {
            'actif': [
                {'label': 'Immobilisations nettes', 'amount': 312_000_000, 'pct': 37},
                {'label': 'Stocks', 'amount': 156_000_000, 'pct': 18},
                {'label': 'Créances clients', 'amount': 245_000_000, 'pct': 29},
                {'label': 'Trésorerie & équivalents', 'amount': 132_200_000, 'pct': 16},
            ],
            'passif': [
                {'label': 'Capitaux propres', 'amount': 422_100_000, 'pct': 50},
                {'label': 'Dettes financières', 'amount': 198_500_000, 'pct': 24},
                {'label': 'Dettes fournisseurs', 'amount': 145_400_000, 'pct': 17},
                {'label': 'Autres dettes', 'amount': 79_200_000, 'pct': 9},
            ],
        },

        # Dernières écritures comptables
        'journal_entries': [
            {'date': '17/03/2025', 'ref': 'JV-2025-1847', 'libelle': 'Vente marchandises Dakar', 'debit': 4_500_000, 'credit': 0, 'compte': '411100'},
            {'date': '17/03/2025', 'ref': 'JV-2025-1846', 'libelle': 'TVA collectée T1', 'debit': 0, 'credit': 752_000, 'compte': '445710'},
            {'date': '16/03/2025', 'ref': 'JV-2025-1845', 'libelle': 'Achat matières premières', 'debit': 2_180_000, 'credit': 0, 'compte': '601100'},
            {'date': '16/03/2025', 'ref': 'JV-2025-1844', 'libelle': 'Règlement fournisseur SABC', 'debit': 0, 'credit': 1_200_000, 'compte': '401200'},
            {'date': '15/03/2025', 'ref': 'JV-2025-1843', 'libelle': 'Dotation amortissement Q1', 'debit': 3_850_000, 'credit': 0, 'compte': '681100'},
            {'date': '15/03/2025', 'ref': 'JV-2025-1842', 'libelle': 'Salaires Mars 2025', 'debit': 18_400_000, 'credit': 0, 'compte': '641100'},
        ],

        # Comptes de charges par catégorie
        'expense_breakdown': [
            {'category': 'Achats & Consommations', 'amount': 142_500_000, 'pct': 41, 'color': 'primary'},
            {'category': 'Charges de personnel', 'amount': 89_200_000, 'pct': 26, 'color': 'success'},
            {'category': 'Dotations amortissements', 'amount': 45_800_000, 'pct': 13, 'color': 'warning'},
            {'category': 'Charges financières', 'amount': 32_100_000, 'pct': 9, 'color': 'danger'},
            {'category': 'Autres charges', 'amount': 34_680_000, 'pct': 11, 'color': 'secondary'},
        ],

        # Alertes comptables
        'alerts': [
            {'type': 'warning', 'icon': 'bi-exclamation-triangle', 'msg': 'TVA T1 2025 : déclaration due dans 5 jours'},
            {'type': 'info', 'icon': 'bi-info-circle', 'msg': '47 écritures en attente de validation'},
            {'type': 'success', 'icon': 'bi-check-circle', 'msg': 'Clôture Février 2025 validée'},
        ],
    }
    return render(request, 'accounting/index.html', context)
