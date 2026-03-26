from django.urls import path
from . import views

urlpatterns = [
    path('', views.accounting_view, name='accounting_dashboard'),
    path('api/data/', views.api_accounting_data, name='api_accounting_data'),
    path('api/transactions/create/', views.api_create_transaction, name='api_create_transaction'),
]
