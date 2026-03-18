from django.urls import path
from . import views

urlpatterns = [
    path('', views.treasury_view, name='treasury'),
    path('api/cashflow/', views.treasury_api_cashflow, name='treasury_cashflow_api'),
]
