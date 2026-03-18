from django.urls import path
from . import views

urlpatterns = [
    path('', views.procurement_view, name='purchases'),
]
