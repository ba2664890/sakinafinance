"""
Projects URLs — FinanceOS IA
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.projects_view, name='projects'),
    path('<uuid:pk>/', views.project_detail, name='project_detail'),
]
