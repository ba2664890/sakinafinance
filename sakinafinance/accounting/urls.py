from django.urls import path
from . import views

urlpatterns = [
    path('', views.accounting_view, name='accounting'),
    path('api/data/', views.api_accounting_data, name='api_accounting_data'),
    path('api/transactions/create/', views.api_create_transaction, name='api_create_transaction'),
    path('api/trial-balance/', views.api_trial_balance, name='api_trial_balance'),
]
