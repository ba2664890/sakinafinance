"""
Projects Views — FinanceOS IA (DB-connected)
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q

from django.http import JsonResponse
from django.utils import timezone
from .models import Project, Task, Milestone, ProjectCategory

def _get_company(request):
    return getattr(request.user, 'company', None)


@login_required
def projects_view(request):
    """Module Projets — vue principale (Squelette)"""
    return render(request, 'projects/index.html', {'page_title': 'Gestion de Projets'})


@login_required
def api_project_data(request):
    """API: Get Project Stats and Lists"""
    company = _get_company(request)

    if company:
        all_projects = Project.objects.filter(company=company, is_active=True)
        total_projects = all_projects.count()
        active_projects_qs = all_projects.filter(status__in=['in_progress', 'planning', 'finalizing'])
        active_projects_count = active_projects_qs.count()
        completed_ytd = all_projects.filter(status='completed').count()

        total_budget = all_projects.aggregate(t=Sum('budget_total'))['t'] or 0
        spent_budget = all_projects.aggregate(s=Sum('budget_spent'))['s'] or 0
        budget_pct = round(float(spent_budget) / max(float(total_budget), 1) * 100) if total_budget else 0

        on_schedule = active_projects_qs.filter(health__in=['excellent', 'stable']).count()
        delayed = active_projects_qs.filter(health__in=['at_risk', 'critical']).count()
        
        overdue_tasks = Task.objects.filter(
            project__company=company, status__in=['todo', 'in_progress'],
            due_date__lt=timezone.now().date()
        ).count()

        active_projects = []
        status_class_map = {
            'planning': 'secondary', 'in_progress': 'primary',
            'on_hold': 'warning', 'finalizing': 'info',
            'completed': 'success', 'cancelled': 'danger'
        }
        health_class_map = {'excellent': 'success', 'stable': 'primary', 'at_risk': 'warning', 'critical': 'danger'}
        
        for p in active_projects_qs.select_related('manager')[:6]:
            active_projects.append({
                'name': p.name,
                'client': p.client_name or '—',
                'manager': p.manager.get_full_name() if p.manager else '—',
                'budget': float(p.budget_total),
                'spent': float(p.budget_spent),
                'progress': p.progress_pct,
                'deadline': p.end_date.strftime('%d/%m/%Y') if p.end_date else '—',
                'status': p.get_status_display(),
                'status_class': status_class_map.get(p.status, 'secondary'),
                'health': p.get_health_display(),
                'health_class': health_class_map.get(p.health, 'secondary'),
                'team': p.members.count(),
            })

        milestones = Milestone.objects.filter(
            project__company=company
        ).exclude(status__in=['completed', 'cancelled']).order_by('due_date')[:4]
        milestone_data = [{
            'project': m.project.name,
            'title': m.name,
            'date': m.due_date.strftime('%d/%m/%Y'),
            'day': m.due_date.strftime('%d'),
            'month': m.due_date.strftime('%b'),
            'status': m.get_status_display(),
        } for m in milestones]

    else:
        # Fallback demonstration data
        total_projects = 12
        active_projects_count = 5
        completed_ytd = 4
        total_budget = 850000
        spent_budget = 425000
        budget_pct = 50
        on_schedule = 4
        delayed = 1
        overdue_tasks = 4
        active_projects = [
            {
                'name': 'Cloud Migration', 'client': 'Internal', 'manager': 'Jean Dupont',
                'budget': 150000, 'spent': 120000, 'progress': 80, 'deadline': '15/05/2025',
                'status': 'En cours', 'status_class': 'primary', 'health': 'Stable', 'health_class': 'primary', 'team': 5
            },
            {
                'name': 'ERP Implementation', 'client': 'Sakina Corp', 'manager': 'Marie Sine',
                'budget': 500000, 'spent': 210000, 'progress': 42, 'deadline': '30/09/2025',
                'status': 'En cours', 'status_class': 'primary', 'health': 'Excellent', 'health_class': 'success', 'team': 12
            }
        ]
        milestone_data = [
            {'project': 'Cloud Migration', 'title': 'UAT Testing', 'date': '20/04/2025', 'day': '20', 'month': 'AVR', 'status': 'Planifié'},
            {'project': 'ERP Implementation', 'title': 'Data Migration', 'date': '15/05/2025', 'day': '15', 'month': 'MAI', 'status': 'En cours'},
        ]

    data = {
        'total_projects': total_projects,
        'active_projects_count': active_projects_count,
        'completed_ytd': completed_ytd,
        'total_budget': float(total_budget),
        'spent_budget': float(spent_budget),
        'budget_pct': budget_pct,
        'on_schedule': on_schedule,
        'delayed': delayed,
        'overdue_tasks': overdue_tasks,
        'completion_rate': budget_pct,
        'active_projects': active_projects,
        'milestones': milestone_data,
    }
    return JsonResponse(data)


@login_required
def project_detail(request, pk):
    """Détail d'un projet"""
    project = get_object_or_404(Project, pk=pk, company=_get_company(request))
    tasks = project.tasks.select_related('assigned_to').order_by('status', 'due_date')
    milestones = project.milestones.order_by('due_date')
    budget_lines = project.budget_lines.all()
    members = project.members.select_related('user')
    context = {
        'page_title': project.name,
        'project': project,
        'tasks': tasks,
        'milestones': milestones,
        'budget_lines': budget_lines,
        'members': members,
    }
    return render(request, 'projects/project_detail.html', context)
