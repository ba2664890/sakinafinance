"""
Procurement URLs — SakinaFinance
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.procurement_view, name='purchases'),
    path('api/data/', views.api_procurement_data, name='api_procurement_data'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('orders/<uuid:pk>/', views.po_detail, name='po_detail'),
    
    # Inventory
    path('inventory/', views.inventory_view, name='inventory'),
    path('api/inventory/', views.api_inventory_data, name='api_inventory_data'),
]
