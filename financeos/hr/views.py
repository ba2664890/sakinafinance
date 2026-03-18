"""
RH & Paie Views — FinanceOS IA
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def hr_view(request):
    """Module RH & Paie — vue principale"""
    context = {
        'page_title': 'RH & Paie',

        # KPIs RH
        'total_employees': 284,
        'new_hires': 12,
        'turnover_rate': 6.2,
        'payroll_total': 89_200_000,
        'payroll_growth': 4.8,
        'avg_salary': 314_084,
        'satisfaction_score': 78,

        # Répartition effectifs par département
        'departments': [
            {'name': 'Finance & Comptabilité', 'count': 42, 'pct': 15, 'color': 'primary'},
            {'name': 'Commercial & Ventes', 'count': 68, 'pct': 24, 'color': 'success'},
            {'name': 'Opérations & Supply', 'count': 74, 'pct': 26, 'color': 'warning'},
            {'name': 'IT & Systèmes', 'count': 38, 'pct': 13, 'color': 'info'},
            {'name': 'RH & Administration', 'count': 28, 'pct': 10, 'color': 'secondary'},
            {'name': 'Audit & Conformité', 'count': 34, 'pct': 12, 'color': 'danger'},
        ],

        # Bulletins de paie récents (synthèse)
        'payroll_runs': [
            {'period': 'Mars 2025', 'employees': 284, 'gross': 89_200_000, 'deductions': 22_800_000, 'net': 66_400_000, 'status': 'En cours', 'date': '25/03/2025'},
            {'period': 'Fév 2025', 'employees': 282, 'gross': 88_450_000, 'deductions': 22_600_000, 'net': 65_850_000, 'status': 'Payé', 'date': '25/02/2025'},
            {'period': 'Jan 2025', 'employees': 281, 'gross': 87_900_000, 'deductions': 22_450_000, 'net': 65_450_000, 'status': 'Payé', 'date': '25/01/2025'},
            {'period': 'Déc 2024', 'employees': 278, 'gross': 92_400_000, 'deductions': 23_600_000, 'net': 68_800_000, 'status': 'Payé', 'date': '23/12/2024'},
        ],

        # Congés & absences (en cours)
        'leave_summary': [
            {'type': 'Congé annuel', 'pending': 8, 'approved': 24, 'ongoing': 3},
            {'type': 'Maladie', 'pending': 2, 'approved': 5, 'ongoing': 2},
            {'type': 'Formation', 'pending': 5, 'approved': 12, 'ongoing': 8},
            {'type': 'Congé maternité/paternité', 'pending': 0, 'approved': 3, 'ongoing': 2},
        ],

        # Recrutements en cours
        'recruitments': [
            {'title': 'Contrôleur de Gestion Senior', 'dept': 'Finance', 'posted': '01/03/2025', 'candidates': 24, 'stage': 'Entretiens'},
            {'title': 'Développeur Python/Django', 'dept': 'IT', 'posted': '10/03/2025', 'candidates': 41, 'stage': 'Test technique'},
            {'title': 'Responsable Commercial Zone UEMOA', 'dept': 'Ventes', 'posted': '15/03/2025', 'candidates': 18, 'stage': 'CV screening'},
            {'title': 'Auditeur Interne', 'dept': 'Audit', 'posted': '05/03/2025', 'candidates': 12, 'stage': 'Offre envoyée'},
        ],
    }
    return render(request, 'hr/index.html', context)
