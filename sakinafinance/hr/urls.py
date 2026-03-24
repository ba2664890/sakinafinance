"""
HR URLs — SakinaFinance
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.hr_view, name='hr_payroll'),
    path('api/data/', views.api_hr_data, name='api_hr_data'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/<uuid:pk>/', views.employee_detail, name='employee_detail'),
    path('payslips/<uuid:pk>/', views.payslip_detail, name='payslip_detail'),
]
