"""
Payments URLs - Stripe Integration
"""

from django.urls import path
from . import views

urlpatterns = [
    # Root redirect
    path('', views.pricing_view, name='payments_index'),
    
    # Pricing
    path('pricing/', views.pricing_view, name='pricing'),
    
    # Subscription
    path('subscribe/<str:plan_slug>/', views.subscribe_view, name='subscribe'),
    path('success/', views.subscription_success_view, name='subscription_success'),
    path('cancel/', views.subscription_cancel_view, name='subscription_cancel'),
    path('manage/', views.manage_subscription_view, name='manage_subscription'),
    path('cancel-subscription/', views.cancel_subscription_view, name='cancel_subscription'),
    
    # Payment Methods
    path('payment-methods/add/', views.add_payment_method_view, name='add_payment_method'),
    path('payment-methods/<uuid:method_id>/remove/', views.remove_payment_method_view, name='remove_payment_method'),
    
    # Invoices
    path('invoices/', views.invoices_view, name='invoices'),
    
    # Webhook
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]
