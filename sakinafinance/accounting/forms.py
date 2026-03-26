from django import forms
from .models import Transaction, TransactionLine, Account, Journal
from django.forms import inlineformset_factory

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['journal', 'reference', 'date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'journal': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['journal'].queryset = Journal.objects.filter(company=company, is_active=True)

class TransactionLineForm(forms.ModelForm):
    class Meta:
        model = TransactionLine
        fields = ['account', 'debit', 'credit', 'description']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'debit': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01'}),
            'credit': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['account'].queryset = Account.objects.filter(company=company, is_active=True)

TransactionLineFormSet = inlineformset_factory(
    Transaction, TransactionLine,
    form=TransactionLineForm,
    extra=2,
    can_delete=True
)
