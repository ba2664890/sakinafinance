"""
AI Engine Models — FinanceOS IA
Intelligence Artificielle : Forecasting, Anomalies, OCR, Insights
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AIAnalysis(models.Model):
    """Analyse produite par le moteur IA"""

    class AnalysisType(models.TextChoices):
        CASH_FORECAST = 'cash_forecast', _('Prévision de trésorerie')
        REVENUE_FORECAST = 'revenue_forecast', _('Prévision de revenus')
        EXPENSE_ANOMALY = 'expense_anomaly', _('Anomalie de dépenses')
        FRAUD_DETECTION = 'fraud_detection', _('Détection de fraude')
        CREDIT_RISK = 'credit_risk', _('Risque de crédit')
        PROFITABILITY = 'profitability', _('Analyse de rentabilité')
        BUDGET_VARIANCE = 'budget_variance', _('Écart budgétaire')
        GENERAL = 'general', _('Analyse générale')

    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        PROCESSING = 'processing', _('En traitement')
        COMPLETED = 'completed', _('Terminé')
        FAILED = 'failed', _('Échec')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='ai_analyses'
    )
    analysis_type = models.CharField(max_length=30, choices=AnalysisType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Parameters
    parameters = models.JSONField(default=dict, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # Results
    result_data = models.JSONField(default=dict, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    insights = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='ai_analyses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_analysis_type_display()} — {self.company} ({self.status})"


class CashFlowForecast(models.Model):
    """Prévision de trésorerie par Prophet/ML"""

    class ForecastHorizon(models.TextChoices):
        THREE_MONTHS = '3m', _('3 mois')
        SIX_MONTHS = '6m', _('6 mois')
        TWELVE_MONTHS = '12m', _('12 mois')
        EIGHTEEN_MONTHS = '18m', _('18 mois')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='cash_forecasts'
    )
    entity = models.ForeignKey(
        'accounts.Entity', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cash_forecasts'
    )
    analysis = models.ForeignKey(
        AIAnalysis, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='forecasts'
    )

    forecast_date = models.DateField()
    horizon = models.CharField(
        max_length=5, choices=ForecastHorizon.choices, default=ForecastHorizon.TWELVE_MONTHS
    )

    # Prophet output
    forecast_data = models.JSONField(default=list)
    # [{"ds": "2025-04-01", "yhat": 1200000, "yhat_lower": 900000, "yhat_upper": 1500000}]

    # Summary metrics
    min_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_monthly_inflow = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_monthly_outflow = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Risk flags
    has_liquidity_risk = models.BooleanField(default=False)
    risk_period = models.CharField(max_length=50, blank=True)
    risk_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    model_version = models.CharField(max_length=20, default='prophet-1.0')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-forecast_date']

    def __str__(self):
        return f"Forecast {self.company} — {self.forecast_date} ({self.horizon})"


class AIInsight(models.Model):
    """Recommandation / Insight produit par l'IA"""

    class InsightType(models.TextChoices):
        WARNING = 'warning', _('Avertissement')
        OPPORTUNITY = 'opportunity', _('Opportunité')
        RISK = 'risk', _('Risque')
        INFO = 'info', _('Information')
        RECOMMENDATION = 'recommendation', _('Recommandation')

    class Priority(models.TextChoices):
        LOW = 'low', _('Faible')
        MEDIUM = 'medium', _('Moyen')
        HIGH = 'high', _('Élevé')
        CRITICAL = 'critical', _('Critique')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='ai_insights'
    )
    analysis = models.ForeignKey(
        AIAnalysis, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ai_insights'
    )
    insight_type = models.CharField(max_length=20, choices=InsightType.choices)
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_required = models.TextField(blank=True)
    module = models.CharField(max_length=50, blank=True)
    impact_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.priority.upper()}] {self.title}"


class DocumentOCR(models.Model):
    """Traitement OCR des documents comptables"""

    class DocumentType(models.TextChoices):
        INVOICE = 'invoice', _('Facture')
        RECEIPT = 'receipt', _('Reçu')
        BANK_STATEMENT = 'bank_statement', _('Relevé bancaire')
        CONTRACT = 'contract', _('Contrat')
        PAYSLIP = 'payslip', _('Bulletin de paie')
        OTHER = 'other', _('Autre')

    class Status(models.TextChoices):
        UPLOADED = 'uploaded', _('Téléchargé')
        PROCESSING = 'processing', _('Traitement en cours')
        EXTRACTED = 'extracted', _('Données extraites')
        VALIDATED = 'validated', _('Validé')
        FAILED = 'failed', _('Échec')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='ocr_documents'
    )
    document_type = models.CharField(
        max_length=20, choices=DocumentType.choices, default=DocumentType.INVOICE
    )
    file = models.FileField(upload_to='ocr/documents/')
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField(default=0)

    # Extraction Results
    raw_text = models.TextField(blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    # {vendor, amount, date, tax_amount, invoice_number, ...}

    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADED
    )
    error_message = models.TextField(blank=True)

    # Linked entity
    linked_invoice = models.ForeignKey(
        'accounting.Invoice', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ocr_documents'
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.get_status_display()})"


class AnomalyDetection(models.Model):
    """Anomalie détectée dans les données financières"""

    class AnomalyType(models.TextChoices):
        UNUSUAL_AMOUNT = 'unusual_amount', _('Montant inhabituel')
        DUPLICATE = 'duplicate', _('Doublon potentiel')
        UNAUTHORIZED = 'unauthorized', _('Transaction non autorisée')
        TIMING = 'timing', _('Anomalie temporelle')
        PATTERN = 'pattern', _('Motif inhabituel')

    class Severity(models.TextChoices):
        LOW = 'low', _('Faible')
        MEDIUM = 'medium', _('Moyen')
        HIGH = 'high', _('Élevé')
        CRITICAL = 'critical', _('Critique')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='anomalies'
    )
    anomaly_type = models.CharField(max_length=20, choices=AnomalyType.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    title = models.CharField(max_length=255)
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    anomaly_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)

    # Linked entity
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)

    is_confirmed = models.BooleanField(default=False)
    is_false_positive = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_anomalies'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"
