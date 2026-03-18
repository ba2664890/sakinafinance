"""
Payments Models - Stripe Integration
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Subscription(models.Model):
    """User Subscription Model"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Actif')
        TRIAL = 'trial', _('Essai')
        PAST_DUE = 'past_due', _('En retard')
        CANCELED = 'canceled', _('Annulé')
        UNPAID = 'unpaid', _('Non payé')
        INCOMPLETE = 'incomplete', _('Incomplet')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    
    # Plan
    plan = models.CharField(
        max_length=20,
        choices=[
            ('startup', 'Startup'),
            ('pme', 'PME'),
            ('enterprise', 'Enterprise'),
            ('groupe', 'Groupe'),
        ]
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=[('monthly', 'Mensuel'), ('yearly', 'Annuel')],
        default='monthly'
    )
    
    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    stripe_price_id = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INCOMPLETE
    )
    
    # Dates
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.plan} - {self.status}"
    
    def is_active(self):
        return self.status in [self.Status.ACTIVE, self.Status.TRIAL]
    
    def is_trial(self):
        return self.status == self.Status.TRIAL
    
    def days_until_renewal(self):
        if self.current_period_end:
            return (self.current_period_end - timezone.now()).days
        return 0


class PaymentMethod(models.Model):
    """Stored Payment Methods"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    # Stripe
    stripe_payment_method_id = models.CharField(max_length=100)
    stripe_customer_id = models.CharField(max_length=100)
    
    # Card Info (last 4 only for security)
    card_brand = models.CharField(max_length=20, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_exp_month = models.IntegerField(null=True, blank=True)
    card_exp_year = models.IntegerField(null=True, blank=True)
    
    # Status
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.card_brand} ****{self.card_last4}"


class Invoice(models.Model):
    """Payment Invoice"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        OPEN = 'open', _('Ouverte')
        PAID = 'paid', _('Payée')
        UNCOLLECTIBLE = 'uncollectible', _('Impayée')
        VOID = 'void', _('Annulée')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    
    # Invoice Details
    invoice_number = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='XOF')
    
    # Stripe
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Dates
    invoice_date = models.DateField()
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'payment invoice'
        verbose_name_plural = 'payment invoices'
    
    def __str__(self):
        return self.invoice_number


class PaymentHistory(models.Model):
    """Payment Transaction History"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        SUCCEEDED = 'succeeded', _('Réussi')
        FAILED = 'failed', _('Échoué')
        REFUNDED = 'refunded', _('Remboursé')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_history'
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    # Payment Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='XOF')
    description = models.TextField(blank=True)
    
    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_charge_id = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Error Info
    error_message = models.TextField(blank=True)
    
    # Dates
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'payment history'
        verbose_name_plural = 'payment histories'
    
    def __str__(self):
        return f"{self.amount} {self.currency} - {self.status}"


class Plan(models.Model):
    """Subscription Plans"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Stripe
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
    
    # Features
    features = models.JSONField(default=list)
    max_users = models.IntegerField(default=1)
    max_entities = models.IntegerField(default=1)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['display_order']
    
    def __str__(self):
        return self.name
