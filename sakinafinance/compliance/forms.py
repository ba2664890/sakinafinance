from django import forms
from .models import TaxFiling, ComplianceRisk, TaxType
from sakinafinance.accounts.models import Entity

class TaxFilingForm(forms.ModelForm):
    class Meta:
        model = TaxFiling
        fields = [
            'entity', 'tax_type', 'period_start', 'period_end', 'deadline',
            'base_amount', 'tax_amount', 'status', 'receipt_number',
            'document', 'notes'
        ]
        widgets = {
            'period_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'period_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'entity': forms.Select(attrs={'class': 'form-select'}),
            'tax_type': forms.Select(attrs={'class': 'form-select'}),
            'base_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Référence du reçu ou accusé'}),
            'document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Précisions internes, point de vigilance, commentaire de dépôt...'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        self.fields['receipt_number'].required = False
        self.fields['document'].required = False
        if company:
            self.fields['entity'].queryset = Entity.objects.filter(company=company)
            self.fields['tax_type'].queryset = TaxType.objects.filter(company=company)

class ComplianceRiskForm(forms.ModelForm):
    class Meta:
        model = ComplianceRisk
        fields = ['title', 'description', 'impact_description', 'probability', 'severity', 'status', 'mitigation_plan', 'is_resolved']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Retard de déclaration TVA'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'impact_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Montant exposé, pénalités possibles, risque réputationnel...'}),
            'probability': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.TextInput(attrs={'class': 'form-control'}),
            'mitigation_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Actions, responsable, échéance de remédiation...'}),
            'is_resolved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
