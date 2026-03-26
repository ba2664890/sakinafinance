from django.urls import path
from . import views

urlpatterns = [
    path('', views.compliance_view, name='compliance_dashboard'),
    path('api/data/', views.api_compliance_data, name='api_compliance_data'),
    path('tax/create/', views.tax_filing_create, name='tax_filing_create'),
    path('risks/add/', views.compliance_risk_create, name='compliance_risk_create'),
]
