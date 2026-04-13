"""
HR URLs — SakinaFinance
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.hr_dashboard, name='hr_payroll'),
    path('api/data/', views.api_hr_data, name='api_hr_data'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<uuid:pk>/', views.employee_detail, name='employee_detail'),
    path('leaves/add/', views.leave_request_create, name='leave_request_create'),
    path('payslips/<uuid:pk>/', views.payslip_detail, name='payslip_detail'),
    path('api/recruit/', views.api_hr_recruit, name='api_hr_recruit'),
    path('api/payroll-config/', views.api_hr_payroll_config, name='api_hr_payroll_config'),
]
