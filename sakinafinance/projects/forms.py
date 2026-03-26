"""
Projects Forms — SakinaFinance
"""
from django import forms
from .models import Project, Task, Milestone, ProjectCategory

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'code', 'category', 'description', 'client_name', 
            'manager', 'start_date', 'end_date', 'budget_total', 
            'currency', 'priority', 'health'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['category'].queryset = ProjectCategory.objects.filter(company=company)
            # You might want to filter managers (Users) by company too if that's a requirement
            # self.fields['manager'].queryset = User.objects.filter(company=company)

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'project', 'milestone', 'title', 'description', 
            'assigned_to', 'due_date', 'estimated_hours', 'priority', 'status'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if project:
            self.fields['project'].initial = project
            self.fields['project'].widget = forms.HiddenInput()
            self.fields['milestone'].queryset = Milestone.objects.filter(project=project)
        elif company:
            self.fields['project'].queryset = Project.objects.filter(company=company)

class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['project', 'name', 'description', 'due_date', 'status']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        if project:
            self.fields['project'].initial = project
            self.fields['project'].widget = forms.HiddenInput()
