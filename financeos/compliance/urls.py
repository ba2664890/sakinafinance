from django.urls import path
from . import views

urlpatterns = [
    path('', views.compliance_view, name='taxation'),
    path('regulatory/', views.compliance_view, name='regulatory'),
]
