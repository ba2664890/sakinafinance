from django.urls import path
from . import views

urlpatterns = [
    path('', views.accounting_view, name='accounting'),
]
