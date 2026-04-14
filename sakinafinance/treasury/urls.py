from django.urls import path
from . import views

urlpatterns = [
    path('', views.treasury_view, name='treasury'),
    path('api/cashflow/', views.treasury_api_cashflow, name='treasury_cashflow_api'),
    path('api/data/', views.api_treasury_data, name='api_treasury_data'),
    path('api/entities/create/', views.api_entity_create, name='api_entity_create'),
    path('api/bank-accounts/create/', views.api_bank_account_create, name='api_bank_account_create'),
    path('api/movements/create/', views.api_bank_movement_create, name='api_bank_movement_create'),
]
