from django import forms
from .models import TaxFiling, ComplianceRisk, TaxType
from sakinafinance.accounts.models import Entity

class TaxFilingForm(forms.ModelForm):
    class Meta:
        model = TaxFiling
        fields = ['entity', 'tax_type', 'period_start', 'period_end', 'deadline', 'base_amount', 'tax_amount', 'notes']
        widgets = {
            'period_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'period_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'entity': forms.Select(attrs={'class': 'form-select'}),
            'tax_type': forms.Select(attrs={'class': 'form-select'}),
            'base_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['entity'].queryset = Entity.objects.filter(company=company)
            self.fields['tax_type'].queryset = TaxType.objects.filter(company=company)

class ComplianceRiskForm(forms.ModelForm):
    class Meta:
        model = ComplianceRisk
        fields = ['title', 'description', 'impact_description', 'probability', 'severity', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'impact_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'probability': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.TextInput(attrs={'class': 'form-control'}),
        }
