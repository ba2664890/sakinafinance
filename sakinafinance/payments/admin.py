"""
Admin configuration for Payments Module
"""

from django.contrib import admin
from sakinafinance.core.admin_mixins import CompanyScopedAdminMixin
from .models import Subscription, PaymentMethod, Invoice, PaymentHistory, Plan

@admin.register(Subscription)
class SubscriptionAdmin(CompanyScopedAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'company', 'plan', 'billing_cycle', 'status', 'current_period_end']
    list_filter = ['plan', 'billing_cycle', 'status', 'company']
    search_fields = ['user__email', 'company__name', 'stripe_subscription_id']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(PaymentMethod)
class PaymentMethodAdmin(CompanyScopedAdminMixin, admin.ModelAdmin):
    company_lookup = 'user__company'
    list_display = ['user', 'card_brand', 'card_last4', 'is_default', 'is_active']
    list_filter = ['card_brand', 'is_default', 'is_active']
    search_fields = ['user__email', 'card_last4']

@admin.register(Invoice)
class PaymentInvoiceAdmin(CompanyScopedAdminMixin, admin.ModelAdmin):
    company_lookup = 'subscription__company'
    list_display = ['invoice_number', 'subscription', 'total', 'currency', 'status', 'invoice_date']
    list_filter = ['status', 'currency', 'invoice_date']
    search_fields = ['invoice_number', 'subscription__user__email']
    readonly_fields = ['id', 'created_at']

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(CompanyScopedAdminMixin, admin.ModelAdmin):
    company_lookup = 'user__company'
    list_display = ['user', 'amount', 'currency', 'status', 'processed_at']
    list_filter = ['status', 'currency', 'processed_at']
    search_fields = ['user__email', 'stripe_payment_intent_id']
    readonly_fields = ['id', 'created_at']

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_monthly', 'price_yearly', 'max_users', 'max_entities', 'is_active']
    list_filter = ['is_active', 'is_popular']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
