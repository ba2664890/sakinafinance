"""
URL configuration for FinanceOS IA project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from two_factor.urls import urlpatterns as tf_urls

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Core & Landing
    path('', include('financeos.core.urls')),
    
    # Authentication
    path('', include(tf_urls)),
    path('accounts/', include('financeos.accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('auth/', include('social_django.urls', namespace='social')),
    
    # App Modules
    path('dashboard/', include('financeos.core.urls_dashboard')),
    path('accounting/', include('financeos.accounting.urls')),
    path('treasury/', include('financeos.treasury.urls')),
    path('reporting/', include('financeos.reporting.urls')),
    path('hr/', include('financeos.hr.urls')),
    path('procurement/', include('financeos.procurement.urls')),
    path('compliance/', include('financeos.compliance.urls')),
    path('projects/', include('financeos.projects.urls')),
    path('ai/', include('financeos.ai_engine.urls')),
    path('payments/', include('financeos.payments.urls')),
    
    # API
    path('api/v1/', include('financeos.core.api_urls')),
    
    # Legal Pages
    path('privacy/', TemplateView.as_view(template_name='legal/privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='legal/terms.html'), name='terms'),
    path('cookies/', TemplateView.as_view(template_name='legal/cookies.html'), name='cookies'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
