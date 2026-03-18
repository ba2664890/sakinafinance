"""
AI Engine URLs — FinanceOS IA
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_dashboard, name='ai_advisor'),
    path('api/forecast/', views.ai_forecast_api, name='ai_forecast_api'),
]
