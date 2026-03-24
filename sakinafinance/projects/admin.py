"""
Projects Admin — SakinaFinance
"""
from django.contrib import admin
from .models import (
    ProjectCategory, Project, ProjectMember,
    Milestone, Task, TimeEntry, ProjectBudgetLine
)


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'company']
    list_filter = ['company']


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1
    fields = ['user', 'role', 'joined_at', 'hourly_rate']


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0
    fields = ['name', 'due_date', 'status', 'completion_pct']


class BudgetLineInline(admin.TabularInline):
    model = ProjectBudgetLine
    extra = 1
    fields = ['category', 'description', 'planned_amount', 'actual_amount']
    readonly_fields = []


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'client_name', 'manager', 'start_date', 'end_date',
        'budget_total', 'budget_spent', 'progress_pct', 'status', 'priority', 'health'
    ]
    list_filter = ['company', 'status', 'priority', 'health', 'category']
    search_fields = ['name', 'client_name', 'code']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProjectMemberInline, MilestoneInline, BudgetLineInline]
    fieldsets = (
        ('Informations Générales', {
            'fields': ('company', 'entity', 'category', 'code', 'name', 'description', 'client_name')
        }),
        ('Planning', {
            'fields': ('manager', 'start_date', 'end_date', 'actual_end_date')
        }),
        ('Budget', {
            'fields': ('budget_total', 'budget_spent', 'currency')
        }),
        ('Statut', {
            'fields': ('progress_pct', 'status', 'priority', 'health', 'is_active')
        }),
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'assigned_to', 'due_date', 'estimated_hours', 'actual_hours', 'status', 'priority']
    list_filter = ['status', 'priority', 'project']
    search_fields = ['title', 'project__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'due_date', 'completed_date', 'status', 'completion_pct']
    list_filter = ['status', 'project']
    search_fields = ['name', 'project__name']


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'task', 'date', 'hours', 'cost']
    list_filter = ['project', 'date']
    search_fields = ['user__first_name', 'project__name']
    readonly_fields = ['cost']
