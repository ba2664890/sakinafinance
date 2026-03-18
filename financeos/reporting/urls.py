from django.urls import path
from . import views

urlpatterns = [
    path('', views.reporting_view, name='financial_statements'),
]
