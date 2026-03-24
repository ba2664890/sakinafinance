"""
Projects URLs — SakinaFinance
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.projects_view, name='projects'),
    path('api/data/', views.api_project_data, name='api_project_data'),
    path('<uuid:pk>/', views.project_detail, name='project_detail'),
]
