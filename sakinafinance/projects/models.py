"""
Gestion de Projets Models — SakinaFinance
Suivi des projets, tâches, budgets et temps
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ProjectCategory(models.Model):
    """Catégorie de projet"""

    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='project_categories'
    )
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default='primary')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Project(models.Model):
    """Projet"""

    class Status(models.TextChoices):
        PLANNING = 'planning', _('Planification')
        IN_PROGRESS = 'in_progress', _('En cours')
        ON_HOLD = 'on_hold', _('En pause')
        FINALIZING = 'finalizing', _('Finalisation')
        COMPLETED = 'completed', _('Terminé')
        CANCELLED = 'cancelled', _('Annulé')

    class Priority(models.TextChoices):
        LOW = 'low', _('Faible')
        NORMAL = 'normal', _('Normale')
        HIGH = 'high', _('Haute')
        CRITICAL = 'critical', _('Critique')

    class Health(models.TextChoices):
        EXCELLENT = 'excellent', _('Excellent')
        STABLE = 'stable', _('Stable')
        AT_RISK = 'at_risk', _('À risque')
        CRITICAL = 'critical', _('Critique')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='projects'
    )
    entity = models.ForeignKey(
        'accounts.Entity', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='projects'
    )
    category = models.ForeignKey(
        ProjectCategory, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Basics
    code = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    client_name = models.CharField(max_length=255, blank=True)

    # Manager
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_projects'
    )

    # Dates
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)

    # Budget
    budget_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    budget_spent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')

    # Progress
    progress_pct = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNING
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NORMAL
    )
    health = models.CharField(
        max_length=20, choices=Health.choices, default=Health.STABLE
    )

    # Accounting
    revenue_account = models.ForeignKey(
        'accounting.Account', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='project_revenue'
    )
    cost_account = models.ForeignKey(
        'accounting.Account', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='project_cost'
    )

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_projects'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name}"

    @property
    def budget_remaining(self):
        return self.budget_total - self.budget_spent

    @property
    def budget_usage_pct(self):
        if self.budget_total > 0:
            return round((self.budget_spent / self.budget_total) * 100, 1)
        return 0

    @property
    def is_over_budget(self):
        return self.budget_spent > self.budget_total

    @property
    def is_overdue(self):
        if self.end_date and self.status not in ['completed', 'cancelled']:
            return timezone.now().date() > self.end_date
        return False


class ProjectMember(models.Model):
    """Membre de l'équipe projet"""

    class Role(models.TextChoices):
        MANAGER = 'manager', _('Chef de Projet')
        LEAD = 'lead', _('Lead Technique')
        MEMBER = 'member', _('Membre')
        STAKEHOLDER = 'stakeholder', _('Partie Prenante')
        OBSERVER = 'observer', _('Observateur')

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_memberships'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateField(default=timezone.now)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['project', 'user']

    def __str__(self):
        return f"{self.user} — {self.project} ({self.role})"


class Milestone(models.Model):
    """Jalon de projet"""

    class Status(models.TextChoices):
        PLANNED = 'planned', _('Planifié')
        IN_PROGRESS = 'in_progress', _('En cours')
        COMPLETED = 'completed', _('Atteint')
        DELAYED = 'delayed', _('En retard')
        CANCELLED = 'cancelled', _('Annulé')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED
    )
    completion_pct = models.IntegerField(default=0)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f"{self.project.name} — {self.name}"


class Task(models.Model):
    """Tâche projet"""

    class Status(models.TextChoices):
        TODO = 'todo', _('À faire')
        IN_PROGRESS = 'in_progress', _('En cours')
        REVIEW = 'review', _('En révision')
        DONE = 'done', _('Terminé')
        CANCELLED = 'cancelled', _('Annulé')

    class Priority(models.TextChoices):
        LOW = 'low', _('Faible')
        NORMAL = 'normal', _('Normale')
        HIGH = 'high', _('Haute')
        URGENT = 'urgent', _('Urgent')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    milestone = models.ForeignKey(
        Milestone, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks'
    )
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subtasks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tasks'
    )
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    actual_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NORMAL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-priority']

    def __str__(self):
        return f"{self.project.name} — {self.title}"

    @property
    def is_overdue(self):
        if self.due_date and self.status not in ['done', 'cancelled']:
            return timezone.now().date() > self.due_date
        return False


class TimeEntry(models.Model):
    """Saisie de temps"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='time_entries')
    task = models.ForeignKey(
        Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='time_entries'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_entries'
    )
    date = models.DateField(default=timezone.now)
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.cost = round(float(self.hours) * float(self.hourly_rate), 2)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user} — {self.project} — {self.date} ({self.hours}h)"


class ProjectBudgetLine(models.Model):
    """Ligne budgétaire de projet"""

    class Category(models.TextChoices):
        LABOR = 'labor', _('Main d\'œuvre')
        MATERIALS = 'materials', _('Matériaux')
        EQUIPMENT = 'equipment', _('Équipements')
        SUBCONTRACT = 'subcontract', _('Sous-traitance')
        TRAVEL = 'travel', _('Déplacements')
        OVERHEAD = 'overhead', _('Frais généraux')
        OTHER = 'other', _('Autres')

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='budget_lines'
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.CharField(max_length=255)
    planned_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ['category']

    def __str__(self):
        return f"{self.project} — {self.get_category_display()} — {self.planned_amount}"

    @property
    def variance(self):
        return self.planned_amount - self.actual_amount
