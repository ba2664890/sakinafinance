"""
Procurement URLs — SakinaFinance
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.procurement_view, name='procurement'),
    path('api/data/', views.api_procurement_data, name='api_procurement_data'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('inventory/create/', views.inventory_item_create, name='inventory_item_create'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('orders/<uuid:pk>/', views.po_detail, name='po_detail'),
    
    # Inventory
    path('inventory/', views.inventory_view, name='inventory'),
    path('api/inventory/', views.api_inventory_data, name='api_inventory_data'),
]
