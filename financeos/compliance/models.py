"""
Compliance Models — FinanceOS IA
Gestion de la fiscalité, du réglementaire et des risques
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class TaxType(models.Model):
    """Type d'impôt ou taxe (Ex: TVA, IS, BRS, VRS, etc.)"""
    
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='tax_types'
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('monthly', _('Mensuel')),
            ('quarterly', _('Trimestriel')),
            ('annually', _('Annuel')),
            ('ocassional', _('Occasionnel')),
        ],
        default='monthly'
    )

    class Meta:
        unique_together = ['company', 'code']
        verbose_name = _('type de taxe')
        verbose_name_plural = _('types de taxes')

    def __str__(self):
        return f"{self.name} ({self.code})"


class TaxFiling(models.Model):
    """Déclaration fiscale spécifique"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        PENDING = 'pending', _('À soumettre')
        FILED = 'filed', _('Déposée')
        PAID = 'paid', _('Payée')
        CANCELLED = 'cancelled', _('Annulée')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='tax_filings'
    )
    entity = models.ForeignKey(
        'accounts.Entity', on_delete=models.CASCADE, related_name='tax_filings'
    )
    tax_type = models.ForeignKey(TaxType, on_delete=models.PROTECT, related_name='filings')
    
    period_start = models.DateField()
    period_end = models.DateField()
    deadline = models.DateField()
    
    base_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    filed_at = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    document = models.FileField(upload_to='compliance/declarations/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-deadline']
        verbose_name = _('déclaration fiscale')
        verbose_name_plural = _('déclarations fiscales')

    def __str__(self):
        return f"{self.tax_type.code} - {self.period_start.strftime('%m/%Y')} - {self.entity.name}"


class RegulatoryRequirement(models.Model):
    """Obligation réglementaire (Ex: CNSS, IPRES, DPAE, etc.)"""

    class Frequency(models.TextChoices):
        MONTHLY = 'monthly', _('Mensuel')
        QUARTERLY = 'quarterly', _('Trimestriel')
        ANNUAL = 'annual', _('Annuel')
        EVENT = 'event', _('Sur événement')

    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='regulatory_requirements'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    authority = models.CharField(max_length=255, blank=True) # Ex: DGI, CNSS
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.MONTHLY)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ComplianceRisk(models.Model):
    """Risque de conformité identifié"""

    class Level(models.TextChoices):
        LOW = 'low', _('Faible')
        MEDIUM = 'medium', _('Moyen')
        HIGH = 'high', _('Élevé')
        CRITICAL = 'critical', _('Critique')
    
    @property
    def level_class(self):
        mapping = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'danger',
        }
        return mapping.get(self.severity, 'secondary')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='compliance_risks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    impact_description = models.TextField(blank=True)
    probability = models.CharField(max_length=20, choices=[('low', 'Faible'), ('medium', 'Moyenne'), ('high', 'Élevée')])
    severity = models.CharField(max_length=20, choices=Level.choices, default=Level.MEDIUM)
    
    status = models.CharField(max_length=50, default='En analyse')
    mitigation_plan = models.TextField(blank=True)
    
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-severity', '-created_at']

    def __str__(self):
        return self.title
