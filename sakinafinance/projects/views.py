"""
Projects Views — SakinaFinance (DB-connected)
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from .forms import ProjectForm, TaskForm, MilestoneForm

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
@login_required
def project_create(request):
    """Créer un nouveau projet"""
    company = _get_company(request)
    if request.method == 'POST':
        form = ProjectForm(request.POST, company=company)
        if form.is_valid():
            project = form.save(commit=False)
            project.company = company
            project.created_by = request.user
            project.save()
            return redirect('projects')
    else:
        form = ProjectForm(company=company)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'page_title': 'Nouveau Projet',
        'action': 'Créer'
    })


@login_required
def task_create(request, project_pk=None):
    """Créer une tâche"""
    company = _get_company(request)
    project = None
    if project_pk:
        project = get_object_or_404(Project, pk=project_pk, company=company)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, project=project, company=company)
        if form.is_valid():
            task = form.save()
            return redirect('project_detail', pk=task.project.pk)
    else:
        form = TaskForm(project=project, company=company)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'page_title': 'Nouvelle Tâche',
        'action': 'Ajouter'
    })


@login_required
def milestone_create(request, project_pk):
    """Créer un jalon"""
    company = _get_company(request)
    project = get_object_or_404(Project, pk=project_pk, company=company)
    
    if request.method == 'POST':
        form = MilestoneForm(request.POST, project=project)
        if form.is_valid():
            form.save()
            return redirect('project_detail', pk=project.pk)
    else:
        form = MilestoneForm(project=project)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'page_title': 'Nouveau Jalon',
        'action': 'Ajouter'
    })
