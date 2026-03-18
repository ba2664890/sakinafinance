"""
AI Engine URLs — FinanceOS IA
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_dashboard, name='ai_engine_dashboard'),
    path('api/forecast/', views.ai_forecast_api, name='ai_forecast_api'),
    path('api/chat/', views.api_ai_chat, name='api_ai_chat'),
]
