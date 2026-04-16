"""
Projects Views — SakinaFinance (DB-connected)
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg
from django.urls import reverse
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

    total_projects = 0
    active_projects_count = 0
    completed_ytd = 0
    total_budget = 0
    spent_budget = 0
    budget_pct = 0
    on_schedule = 0
    delayed = 0
    overdue_tasks = 0
    completion_rate = 0
    active_projects = []
    milestone_data = []

    if company:
        all_projects = Project.objects.filter(company=company, is_active=True)
        total_projects = all_projects.count()
        active_projects_qs = all_projects.filter(status__in=['in_progress', 'planning', 'finalizing'])
        active_projects_count = active_projects_qs.count()
        completed_ytd = all_projects.filter(status='completed').count()

        total_budget = all_projects.aggregate(t=Sum('budget_total'))['t'] or 0
        spent_budget = all_projects.aggregate(s=Sum('budget_spent'))['s'] or 0
        budget_pct = round(float(spent_budget) / max(float(total_budget), 1) * 100) if total_budget else 0
        avg_progress = all_projects.aggregate(a=Avg('progress_pct'))['a'] or 0
        completion_rate = round(float(avg_progress)) if avg_progress else 0

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
                'pk': str(p.pk),
                'detail_url': reverse('project_detail', kwargs={'pk': p.pk}),
                'name': p.name,
                'code': p.code or '—',
                'client': p.client_name or '—',
                'manager': p.manager.get_full_name() if p.manager else '—',
                'budget': float(p.budget_total),
                'spent': float(p.budget_spent),
                'progress': p.progress_pct,
                'deadline': p.end_date.strftime('%d/%m/%Y') if p.end_date else '—',
                'start_date': p.start_date.strftime('%d/%m/%Y') if p.start_date else '—',
                'status': p.get_status_display(),
                'status_class': status_class_map.get(p.status, 'secondary'),
                'health': p.get_health_display(),
                'health_class': health_class_map.get(p.health, 'secondary'),
                'team': p.members.count(),
                'currency': p.currency,
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
        'completion_rate': completion_rate,
        'active_projects': active_projects,
        'milestones': milestone_data,
    }
    return JsonResponse(data)


@login_required
def project_detail(request, pk):
    """Détail d'un projet"""
    project = get_object_or_404(Project, pk=pk, company=_get_company(request))
    tasks_qs = project.tasks.select_related('assigned_to').order_by('status', 'due_date')
    milestones = project.milestones.order_by('due_date')
    budget_lines = project.budget_lines.all()
    members = project.members.select_related('user')
    today = timezone.now().date()
    timeline_pct = None
    days_left = None
    if project.start_date and project.end_date:
        total_days = (project.end_date - project.start_date).days
        if total_days > 0:
            elapsed = (today - project.start_date).days
            timeline_pct = max(0, min(100, round((elapsed / total_days) * 100)))
        days_left = (project.end_date - today).days
    tasks_total = tasks_qs.count()
    tasks_done = tasks_qs.filter(status='done').count()
    tasks_in_progress = tasks_qs.filter(status='in_progress').count()
    tasks_overdue = tasks_qs.filter(
        status__in=['todo', 'in_progress', 'review'],
        due_date__lt=today
    ).count()
    tasks_done_pct = 0
    if tasks_total:
        tasks_done_pct = round((tasks_done / tasks_total) * 100)
    next_milestone = milestones.filter(
        status__in=['planned', 'in_progress'],
        due_date__gte=today
    ).order_by('due_date').first()
    context = {
        'page_title': project.name,
        'project': project,
        'tasks': tasks_qs,
        'milestones': milestones,
        'budget_lines': budget_lines,
        'members': members,
        'timeline_pct': timeline_pct,
        'days_left': days_left,
        'tasks_total': tasks_total,
        'tasks_done': tasks_done,
        'tasks_in_progress': tasks_in_progress,
        'tasks_overdue': tasks_overdue,
        'tasks_done_pct': tasks_done_pct,
        'next_milestone': next_milestone,
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
        'action': 'Créer',
        'form_type': 'project'
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
        'action': 'Ajouter',
        'form_type': 'task'
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
        'action': 'Ajouter',
        'form_type': 'milestone'
    })
