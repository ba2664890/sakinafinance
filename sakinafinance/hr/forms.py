"""
HR Forms — SakinaFinance
"""
from django import forms
from .models import Employee, LeaveRequest, Department, JobPosition, LeaveType

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'employee_number', 'first_name', 'last_name', 'gender', 
            'date_of_birth', 'email', 'phone', 'address', 
            'department', 'position', 'contract_type', 'hire_date', 
            'base_salary', 'currency'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['department'].queryset = Department.objects.filter(company=company)
            self.fields['position'].queryset = JobPosition.objects.filter(company=company)

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'days', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['employee'].queryset = Employee.objects.filter(company=company, is_active=True)
            self.fields['leave_type'].queryset = LeaveType.objects.filter(company=company)
