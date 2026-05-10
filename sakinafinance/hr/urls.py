"""
HR URLs — SakinaFinance
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.hr_dashboard, name='hr_payroll'),
    path('api/data/', views.api_hr_data, name='api_hr_data'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<uuid:pk>/', views.employee_detail, name='employee_detail'),
    path('leaves/add/', views.leave_request_create, name='leave_request_create'),
    path('payslips/<uuid:pk>/', views.payslip_detail, name='payslip_detail'),
    path('api/recruit/', views.api_hr_recruit, name='api_hr_recruit'),
    path('api/employees/add/', views.api_hr_employee_add, name='api_hr_employee_add'),
    path('api/payroll-config/', views.api_hr_payroll_config, name='api_hr_payroll_config'),
    path('api/departments/add/', views.api_hr_add_department, name='api_hr_add_department'),
    path('api/positions/add/', views.api_hr_add_job_position, name='api_hr_add_job_position'),
]
