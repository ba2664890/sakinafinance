"""
Fiscalité & Conformité (Compliance) Views — FinanceOS IA
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def compliance_view(request):
    """Module Fiscalité & Réglementaire — vue principale"""
    context = {
        'page_title': 'Fiscalité & Réglementaire',

        # KPIs Conformité
        'compliance_score': 88.4,
        'open_risks': 7,
        'declarations_pending': 3,
        'overdue_filings': 1,
        'tax_provision': 47_500_000,
        'next_deadline_days': 5,

        # Calendrier fiscal
        'tax_calendar': [
            {'deadline': '20/03/2025', 'tax': 'TVA Mars 2025', 'entity': 'OS Sénégal SARL', 'amount': 4_200_000, 'status': 'À soumettre', 'status_class': 'warning', 'days_left': 3, 'urgent': True},
            {'deadline': '31/03/2025', 'tax': 'IS Acompte Q1 2025', 'entity': 'OS Africa Ltd', 'amount': 11_875_000, 'status': 'À préparer', 'status_class': 'secondary', 'days_left': 14, 'urgent': False},
            {'deadline': '15/04/2025', 'tax': 'CNSS & IPRES Mars', 'entity': 'Toutes entités', 'amount': 8_920_000, 'status': 'À préparer', 'status_class': 'secondary', 'days_left': 29, 'urgent': False},
            {'deadline': '30/04/2025', 'tax': 'TVA Avril 2025', 'entity': 'OS Côte d\'Ivoire', 'amount': 5_840_000, 'status': 'Planifié', 'status_class': 'info', 'days_left': 44, 'urgent': False},
            {'deadline': '30/06/2025', 'tax': 'Déclaration IS 2024', 'entity': 'Groupe OS', 'amount': 47_500_000, 'status': 'En préparation', 'status_class': 'primary', 'days_left': 105, 'urgent': False},
        ],

        # Déclarations récentes
        'filed_declarations': [
            {'period': 'Fév 2025', 'tax': 'TVA', 'entity': 'OS Sénégal SARL', 'amount': 3_980_000, 'filed': '19/02/2025', 'receipt': 'DGI-25-02-48521'},
            {'period': 'Fév 2025', 'tax': 'CNSS', 'entity': 'Toutes entités', 'amount': 8_650_000, 'filed': '14/02/2025', 'receipt': 'CNSS-25-02-12847'},
            {'period': 'Jan 2025', 'tax': 'TVA', 'entity': 'OS Africa Ltd', 'amount': 4_100_000, 'filed': '20/01/2025', 'receipt': 'DGI-25-01-38241'},
        ],

        # Risques réglementaires identifiés
        'risks': [
            {'description': 'Délai TVA Sénégal dépassé de 2 jours', 'impact': 'Pénalité ~420,000 XOF', 'probability': 'Élevée', 'status': 'En traitement', 'level': 'danger'},
            {'description': 'Prix de transfert intercos non documentés', 'impact': 'Redressement potentiel', 'probability': 'Moyenne', 'status': 'Analyse en cours', 'level': 'warning'},
            {'description': 'Taux CNSS Côte d\'Ivoire incorrectement appliqué', 'impact': 'Régularisation ~1.2M XOF', 'probability': 'Élevée', 'status': 'En correction', 'level': 'warning'},
            {'description': 'Documentation IS 2023 incomplète', 'impact': 'Risque de rejet', 'probability': 'Faible', 'status': 'Validé', 'level': 'success'},
        ],

        # Entités & TIN
        'entities': [
            {'name': 'OS Sénégal SARL', 'country': 'Sénégal', 'tin': 'SN-8821-04521', 'vat_reg': 'SN/TVA/2019/0284', 'status': 'Active'},
            {'name': 'OS Côte d\'Ivoire SA', 'country': 'Côte d\'Ivoire', 'tin': 'CI-4421-08214', 'vat_reg': 'CI/TVA/2020/0147', 'status': 'Active'},
            {'name': 'OS Africa Ltd', 'country': 'Ghana', 'tin': 'GH-C0174-21', 'vat_reg': 'GH/VAT/2021/0089', 'status': 'En révision'},
        ],
    }
    return render(request, 'compliance/index.html', context)
