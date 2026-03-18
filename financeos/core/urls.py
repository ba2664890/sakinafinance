"""
Core URLs - Landing & Public Pages
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
]
