"""
Dashboard URLs - Authenticated Pages
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('executive/', views.executive_view, name='executive'),
    path('consolidation/', views.consolidation_view, name='consolidation'),
    path('ai-advisor/', views.ai_advisor_view, name='ai_advisor'),
    path('settings/', views.settings_view, name='settings'),
    
    # API Endpoints
    path('api/data/', views.api_dashboard_data, name='api_dashboard_data'),
    path('api/kpi/', views.api_kpi_data, name='api_kpi_data'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
]
