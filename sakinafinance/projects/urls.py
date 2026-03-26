"""
Projects URLs — SakinaFinance
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.projects_view, name='projects'),
    path('api/data/', views.api_project_data, name='api_project_data'),
    path('create/', views.project_create, name='project_create'),
    path('<uuid:pk>/', views.project_detail, name='project_detail'),
    path('<uuid:project_pk>/tasks/add/', views.task_create, name='task_add'),
    path('<uuid:project_pk>/milestones/add/', views.milestone_create, name='milestone_add'),
]
