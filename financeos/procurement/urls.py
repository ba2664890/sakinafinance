"""
Procurement URLs — FinanceOS IA
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.procurement_view, name='purchases'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('orders/<uuid:pk>/', views.po_detail, name='po_detail'),
]
