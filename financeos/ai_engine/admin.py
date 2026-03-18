"""
AI Engine Admin — FinanceOS IA
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AIAnalysis, CashFlowForecast, AIInsight,
    DocumentOCR, AnomalyDetection
)


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'analysis_type', 'company', 'status',
        'confidence_score', 'requested_by', 'created_at'
    ]
    list_filter = ['status', 'analysis_type', 'company']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'completed_at', 'result_data', 'insights']


@admin.register(CashFlowForecast)
class CashFlowForecastAdmin(admin.ModelAdmin):
    list_display = [
        'company', 'forecast_date', 'horizon', 'confidence_score',
        'min_balance', 'max_balance', 'has_liquidity_risk'
    ]
    list_filter = ['company', 'horizon', 'has_liquidity_risk']
    readonly_fields = ['created_at', 'forecast_data']


@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = [
        'priority_badge', 'title', 'insight_type', 'company',
        'impact_amount', 'is_read', 'is_dismissed', 'created_at'
    ]
    list_filter = ['insight_type', 'priority', 'is_read', 'is_dismissed', 'company']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at']
    actions = ['mark_as_read', 'dismiss_insights']

    def priority_badge(self, obj):
        colors = {
            'low': 'secondary', 'medium': 'info',
            'high': 'warning', 'critical': 'danger'
        }
        color = colors.get(obj.priority, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priorité'

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} insight(s) marqué(s) comme lu(s).")
    mark_as_read.short_description = "Marquer comme lu"

    def dismiss_insights(self, request, queryset):
        queryset.update(is_dismissed=True)
        self.message_user(request, f"{queryset.count()} insight(s) ignoré(s).")
    dismiss_insights.short_description = "Ignorer les insights"


@admin.register(DocumentOCR)
class DocumentOCRAdmin(admin.ModelAdmin):
    list_display = [
        'filename', 'document_type', 'company', 'status',
        'confidence_score', 'uploaded_by', 'created_at'
    ]
    list_filter = ['document_type', 'status', 'company']
    search_fields = ['filename']
    readonly_fields = ['created_at', 'processed_at', 'raw_text', 'extracted_data']


@admin.register(AnomalyDetection)
class AnomalyDetectionAdmin(admin.ModelAdmin):
    list_display = [
        'severity_badge', 'title', 'anomaly_type', 'company',
        'amount', 'is_confirmed', 'is_false_positive', 'created_at'
    ]
    list_filter = ['severity', 'anomaly_type', 'is_confirmed', 'is_false_positive', 'company']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'reviewed_at']
    actions = ['confirm_anomalies', 'mark_false_positive']

    def severity_badge(self, obj):
        colors = {
            'low': 'secondary', 'medium': 'warning',
            'high': 'danger', 'critical': 'dark'
        }
        color = colors.get(obj.severity, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_severity_display()
        )
    severity_badge.short_description = 'Sévérité'

    def confirm_anomalies(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_confirmed=True, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} anomalie(s) confirmée(s).")
    confirm_anomalies.short_description = "Confirmer comme anomalie réelle"

    def mark_false_positive(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_false_positive=True, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} faux positif(s) marqué(s).")
    mark_false_positive.short_description = "Marquer comme faux positif"
