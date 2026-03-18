"""
Projets Views — FinanceOS IA
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def projects_view(request):
    """Module Projets — vue principale"""
    context = {
        'page_title': 'Gestion de Projets',

        # KPIs Projets
        'total_projects': 24,
        'active_projects_count': 14,
        'completed_ytd': 7,
        'total_budget': 485_000_000,
        'spent_budget': 298_400_000,
        'budget_pct': 62,
        'on_schedule': 10,
        'delayed': 4,
        'overdue_tasks': 4,
        'completion_rate': 68,

        # Liste des projets actifs
        'active_projects': [
            {
                'name': 'Déploiement ERP Zone UEMOA',
                'client': 'Gouvernement Sénégal',
                'manager': 'A. Diallo',
                'budget': 85_000_000,
                'spent': 52_400_000,
                'progress': 62,
                'deadline': '30/06/2025',
                'status': 'En cours',
                'status_class': 'primary',
                'health': 'Excellent',
                'priority': 'Critique',
                'priority_class': 'danger',
                'team': 8,
            },
            {
                'name': 'Refonte Système Comptable',
                'client': 'Port Autonome',
                'manager': 'M. Traoré',
                'budget': 42_000_000,
                'spent': 18_900_000,
                'progress': 45,
                'deadline': '15/05/2025',
                'status': 'En cours',
                'status_class': 'primary',
                'health': 'Stable',
                'priority': 'Haute',
                'priority_class': 'warning',
                'team': 5,
            },
            {
                'name': 'Migration Cloud Infrastructure',
                'client': 'Interne',
                'manager': 'K. Coulibaly',
                'budget': 68_000_000,
                'spent': 71_200_000,
                'progress': 105,
                'deadline': '31/03/2025',
                'status': 'En retard',
                'status_class': 'danger',
                'health': 'Critique',
                'priority': 'Critique',
                'priority_class': 'danger',
                'team': 6,
            },
            {
                'name': 'Expansion Centre Logistique Abidjan',
                'client': 'Logistics SA',
                'manager': 'F. Koné',
                'budget': 124_000_000,
                'spent': 89_200_000,
                'progress': 72,
                'deadline': '31/08/2025',
                'status': 'En cours',
                'status_class': 'primary',
                'health': 'Excellent',
                'priority': 'Haute',
                'priority_class': 'warning',
                'team': 12,
            },
            {
                'name': 'Programme Formation Leadership',
                'client': 'UEMOA Academy',
                'manager': 'I. Sawadogo',
                'budget': 15_000_000,
                'spent': 14_200_000,
                'progress': 95,
                'deadline': '30/04/2025',
                'status': 'Finalisation',
                'status_class': 'success',
                'health': 'Excellent',
                'priority': 'Normale',
                'priority_class': 'secondary',
                'team': 3,
            },
            {
                'name': 'Audit ISO 9001:2015',
                'client': 'Certification Pro',
                'manager': 'O. Bamba',
                'budget': 8_500_000,
                'spent': 3_200_000,
                'progress': 38,
                'deadline': '20/05/2025',
                'status': 'En cours',
                'status_class': 'primary',
                'health': 'Stable',
                'priority': 'Haute',
                'priority_class': 'warning',
                'team': 4,
            },
        ],

        # Jalons à venir
        'milestones': [
            {'project': 'Déploiement ERP Zone UEMOA', 'title': 'Go-Live Sénégal', 'date': '01/04/2025', 'status': 'À venir'},
            {'project': 'Migration Cloud', 'title': 'Revue post-migration', 'date': '05/04/2025', 'status': 'En retard'},
            {'project': 'Refonte Système Comptable', 'title': 'UAT Validation', 'date': '15/04/2025', 'status': 'Planifié'},
            {'project': 'Audit ISO 9001', 'title': 'Pré-audit interne', 'date': '20/04/2025', 'status': 'Planifié'},
        ],
    }
    return render(request, 'projects/index.html', context)
