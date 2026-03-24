from django.contrib import admin
from .models import TaxType, TaxFiling, RegulatoryRequirement, ComplianceRisk

@admin.register(TaxType)
class TaxTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'frequency', 'company')
    list_filter = ('frequency', 'company')
    search_fields = ('name', 'code')

@admin.register(TaxFiling)
class TaxFilingAdmin(admin.ModelAdmin):
    list_display = ('tax_type', 'period_start', 'deadline', 'tax_amount', 'status', 'entity')
    list_filter = ('status', 'tax_type', 'entity')
    search_fields = ('receipt_number', 'notes')
    date_hierarchy = 'deadline'

@admin.register(RegulatoryRequirement)
class RegulatoryRequirementAdmin(admin.ModelAdmin):
    list_display = ('name', 'authority', 'frequency', 'is_active', 'company')
    list_filter = ('frequency', 'is_active', 'company')

@admin.register(ComplianceRisk)
class ComplianceRiskAdmin(admin.ModelAdmin):
    list_display = ('title', 'severity', 'probability', 'status', 'is_resolved', 'company')
    list_filter = ('severity', 'probability', 'is_resolved', 'company')
    search_fields = ('title', 'description')
