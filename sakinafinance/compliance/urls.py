from django.urls import path
from . import views

urlpatterns = [
    path('', views.compliance_view, name='taxation'),
    path('regulatory/', views.compliance_view, name='regulatory'),
    path('api/data/', views.api_compliance_data, name='api_compliance_data'),
]
