"""
Admin configuration for Core Module
"""

from django.contrib import admin
from .models import DashboardWidget, SystemSetting, AuditLog, Integration, Currency, ExchangeRate

@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'widget_type', 'is_active']
    list_filter = ['widget_type', 'is_active']
    search_fields = ['name', 'user__email']

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'is_public', 'updated_at']
    search_fields = ['key', 'description']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'module', 'model_name', 'user', 'timestamp']
    list_filter = ['action', 'module', 'timestamp']
    search_fields = ['model_name', 'object_id', 'user__email']
    readonly_fields = ['id', 'timestamp']

@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'integration_type', 'provider', 'is_active', 'is_connected']
    list_filter = ['integration_type', 'is_active', 'is_connected']
    search_fields = ['name', 'provider']

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['from_currency', 'to_currency', 'rate', 'date', 'source']
    list_filter = ['from_currency', 'to_currency', 'date', 'source']
    date_hierarchy = 'date'
