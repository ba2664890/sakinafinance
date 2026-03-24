"""
Core Models for SakinaFinance
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DashboardWidget(models.Model):
    """Dashboard Widget Configuration"""
    
    class WidgetType(models.TextChoices):
        KPI = 'kpi', _('KPI Card')
        CHART = 'chart', _('Chart')
        TABLE = 'table', _('Table')
        LIST = 'list', _('List')
        AI_INSIGHT = 'ai_insight', _('AI Insight')
        ALERT = 'alert', _('Alert')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_widgets'
    )
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WidgetType.choices)
    
    # Configuration
    data_source = models.CharField(max_length=100)
    filters = models.JSONField(default=dict, blank=True)
    refresh_interval = models.IntegerField(default=300)  # seconds
    
    # Layout
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4)
    height = models.IntegerField(default=4)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"{self.name} - {self.user}"


class SystemSetting(models.Model):
    """Global System Settings"""
    
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['key']
    
    def __str__(self):
        return self.key


class AuditLog(models.Model):
    """System-wide Audit Log"""
    
    class ActionType(models.TextChoices):
        CREATE = 'create', _('Create')
        UPDATE = 'update', _('Update')
        DELETE = 'delete', _('Delete')
        VIEW = 'view', _('View')
        EXPORT = 'export', _('Export')
        LOGIN = 'login', _('Login')
        LOGOUT = 'logout', _('Logout')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    module = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} - {self.module} - {self.timestamp}"


class Integration(models.Model):
    """Third-party Integrations"""
    
    class IntegrationType(models.TextChoices):
        BANK = 'bank', _('Banque')
        ACCOUNTING = 'accounting', _('Comptabilité')
        CRM = 'crm', _('CRM')
        ERP = 'erp', _('ERP')
        PAYMENT = 'payment', _('Paiement')
        COMMUNICATION = 'communication', _('Communication')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    name = models.CharField(max_length=100)
    integration_type = models.CharField(max_length=20, choices=IntegrationType.choices)
    provider = models.CharField(max_length=100)
    
    # Credentials (encrypted)
    api_key = models.CharField(max_length=500, blank=True)
    api_secret = models.CharField(max_length=500, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires = models.DateTimeField(null=True, blank=True)
    
    # Configuration
    config = models.JSONField(default=dict, blank=True)
    webhooks = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)
    last_sync = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.company}"


class Currency(models.Model):
    """Currency Model"""
    
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'currencies'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ExchangeRate(models.Model):
    """Exchange Rate Model"""
    
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    date = models.DateField()
    source = models.CharField(max_length=50, default='ECB')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['from_currency', 'to_currency', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.from_currency}/{self.to_currency} - {self.rate} - {self.date}"
