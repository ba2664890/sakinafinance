from django.urls import path
from . import views

urlpatterns = [
    path('', views.accounting_view, name='accounting'),
    path('api/data/', views.api_accounting_data, name='api_accounting_data'),
]
