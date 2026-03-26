"""
Procurement Forms — SakinaFinance
"""
from django import forms
from .models import Supplier, PurchaseOrder, InventoryItem, SupplierCategory

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'name', 'category', 'supplier_code', 'tax_id', 'email', 
            'phone', 'address', 'city', 'country', 'payment_terms_days',
            'currency', 'bank_name', 'account_number'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['category'].queryset = SupplierCategory.objects.filter(company=company)

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'reference', 'order_date', 'expected_delivery', 
            'currency', 'payment_terms', 'delivery_address', 'notes', 'priority'
        ]
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery': forms.DateInput(attrs={'type': 'date'}),
            'delivery_address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['supplier'].queryset = Supplier.objects.filter(company=company, status='active')

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            'name', 'sku', 'description', 'item_type', 'unit_measure',
            'unit_cost', 'unit_price', 'min_stock_level', 'reorder_level'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }
