from django.urls import path
from . import views

urlpatterns = [
    path('', views.reporting_view, name='financial_statements'),
    path('api/data/', views.api_reporting_data, name='api_reporting_data'),
]
