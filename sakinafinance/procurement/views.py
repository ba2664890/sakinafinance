"""
Procurement Views — SakinaFinance (DB-connected)
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum, Avg, Count, Q
from django.core.exceptions import ValidationError
from .forms import SupplierForm, PurchaseOrderForm, InventoryItemForm
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation

from .models import Supplier, PurchaseOrder, PurchaseRFQ, SupplierCategory, InventoryItem, StockTransaction

def _get_company(request):
    company = getattr(request.user, 'company', None)
    if company:
        return company
    profile = getattr(request.user, 'profile', None)
    return getattr(profile, 'company', None)


@login_required
def procurement_view(request):
    """Module Achats — vue principale (Squelette)"""
    return render(request, 'procurement/index.html', {'page_title': 'Achats & Approvisionnement'})


@login_required
def api_procurement_data(request):
    """API: Get Procurement Stats and Lists"""
    company = _get_company(request)
    
    if company:
        suppliers = Supplier.objects.filter(company=company, is_active=True)
        orders = PurchaseOrder.objects.filter(company=company).order_by('-order_date')
        active_orders = orders.exclude(status__in=['closed', 'cancelled'])

        # KPIs
        total_spends = orders.filter(status__in=['received', 'invoiced', 'closed']).aggregate(
            total=Sum('total')
        )['total'] or 0

        # Top suppliers
        top_suppliers = suppliers.order_by('-total_spend')[:5]
        supplier_data = [{
            'name': s.name,
            'category': s.category.name if s.category else '—',
            'spend': float(s.total_spend),
            'orders': s.total_orders,
            'rating': float(s.rating),
            'on_time': float(s.on_time_delivery_pct),
        } for s in top_suppliers]

        # Purchase orders
        po_data = []
        status_class_map = {
            'draft': 'secondary', 'pending': 'secondary', 'approved': 'primary',
            'sent': 'info', 'confirmed': 'primary', 'in_transit': 'warning',
            'received': 'success', 'invoiced': 'success', 'closed': 'dark', 'cancelled': 'danger'
        }
        for po in active_orders[:5]:
            po_data.append({
                'id': po.reference,
                'supplier': po.supplier.name,
                'amount': float(po.total),
                'date': po.order_date.strftime('%d/%m/%Y'),
                'delivery': po.expected_delivery.strftime('%d/%m/%Y') if po.expected_delivery else '—',
                'status': po.get_status_display(),
                'status_class': status_class_map.get(po.status, 'secondary'),
            })

        # Categories
        categories = SupplierCategory.objects.filter(company=company).annotate(
            spend=Sum('suppliers__orders__total')
        )[:5]
        cat_data = [{
            'name': c.name,
            'spend': float(c.spend or 0),
        } for c in categories]

        # RFQs
        rfqs = PurchaseRFQ.objects.filter(company=company).exclude(
            status__in=['awarded', 'cancelled']
        ).order_by('-created_at')[:3]
        rfq_data = [{
            'title': r.title,
            'budget': float(r.estimated_budget),
            'deadline': r.deadline.strftime('%d/%m/%Y') if r.deadline else '—',
            'responses': r.responses_count,
            'status': r.get_status_display(),
        } for r in rfqs]
        
        suppliers_count = suppliers.count()
        po_count = active_orders.count()
    else:
        # Fallback to demo data if no company
        total_spends = 0
        suppliers_count = 0
        po_count = 0
        supplier_data = []
        po_data = []
        cat_data = []
        rfq_data = []

    data = {
        'total_spends': float(total_spends),
        'purchases_growth': 0.0,
        'suppliers_count': suppliers_count,
        'po_count': po_count,
        'savings_rate': 0.0,
        'savings': 0.0,
        'avg_lead_time_days': 0,
        'on_time_delivery': 0.0,
        'purchase_orders': po_data,
        'suppliers': supplier_data,
        'categories': cat_data,
        'rfqs': rfq_data,
        'suppliers_list': list(Supplier.objects.filter(company=company, is_active=True).values('id', 'name')),
    }
    return JsonResponse(data)


@login_required
def supplier_list(request):
    """Liste fournisseurs"""
    company = _get_company(request)
    suppliers = Supplier.objects.filter(company=company, is_active=True) if company else Supplier.objects.none()

    q = request.GET.get('q', '')
    if q:
        suppliers = suppliers.filter(Q(name__icontains=q) | Q(email__icontains=q))

    context = {
        'page_title': 'Fournisseurs',
        'suppliers': suppliers,
        'q': q,
    }
    return render(request, 'procurement/supplier_list.html', context)


@login_required
def po_detail(request, pk):
    """Détail bon de commande"""
    company = _get_company(request)
    po = get_object_or_404(PurchaseOrder, pk=pk, company=company)
    context = {
        'page_title': f'Commande {po.reference}',
        'po': po,
        'lines': po.lines.all(),
    }
    return render(request, 'procurement/po_detail.html', context)


@login_required
def inventory_view(request):
    """Vue principale de l'inventaire"""
    return render(request, 'procurement/inventory.html', {'page_title': 'Inventaire & Stock'})


@login_required
def api_inventory_data(request):
    """API: Get Inventory Stats and Items"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)

    items = InventoryItem.objects.filter(company=company)
    
    # Stats
    total_items = items.count()
    low_stock_items = items.filter(current_stock__lte=models.F('min_stock_level')).count()
    out_of_stock = items.filter(current_stock=0).count()
    
    # Calculate value
    total_value = sum(item.current_stock * item.unit_cost for item in items)

    # Item list
    item_list = []
    for item in items[:20]: # Limit for demo
        item_list.append({
            'sku': item.sku,
            'name': item.name,
            'type': item.get_item_type_display(),
            'stock': float(item.current_stock),
            'min': float(item.min_stock_level),
            'unit': item.unit_measure,
            'value': float(item.current_stock * item.unit_cost),
            'status': 'critical' if item.current_stock <= item.min_stock_level else 'good'
        })

    # Recent transactions
    transactions = StockTransaction.objects.filter(item__company=company).order_by('-timestamp')[:10]
    transaction_data = []
    for t in transactions:
        transaction_data.append({
            'item': t.item.name,
            'type': t.get_transaction_type_display(),
            'qty': float(t.quantity),
            'date': t.timestamp.strftime('%d/%m/%Y %H:%M'),
            'ref': t.reference or '—'
        })

    data = {
        'total_items': total_items,
        'low_stock_count': low_stock_items,
        'out_of_stock_count': out_of_stock,
        'inventory_value': float(total_value),
        'items': item_list,
        'items_list': list(items.values('id', 'name', 'sku')),
        'transactions': transaction_data,
    }
    return JsonResponse(data)


@login_required
def supplier_create(request):
    """Créer un nouveau fournisseur"""
    company = _get_company(request)
    if request.method == 'POST':
        form = SupplierForm(request.POST, company=company)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.company = company
            supplier.save()
            return redirect('procurement')
    else:
        form = SupplierForm(company=company)
    
    return render(request, 'procurement/form.html', {
        'form': form,
        'page_title': 'Nouveau Fournisseur',
        'action': 'Créer'
    })


@login_required
def purchase_order_create(request):
    """Créer un bon de commande"""
    company = _get_company(request)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, company=company)
        if form.is_valid():
            po = form.save(commit=False)
            po.company = company
            po.created_by = request.user
            po.save()
            return redirect('procurement')
    else:
        form = PurchaseOrderForm(company=company)
    
    return render(request, 'procurement/form.html', {
        'form': form,
        'page_title': 'Nouveau Bon de Commande',
        'action': 'Créer'
    })


@login_required
def inventory_item_create(request):
    """Créer un article d'inventaire"""
    company = _get_company(request)
    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.company = company
            item.save()
            return redirect('procurement')
    else:
        form = InventoryItemForm()
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'page_title': 'Nouvel Article',
        'action': 'Ajouter'
    })


@require_POST
@login_required
def api_po_create(request):
    """API: Créer un bon de commande"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': "Aucune entreprise n'est associée à cet utilisateur."}, status=400)
    supplier_id = request.POST.get('supplier')
    expected_delivery = request.POST.get('expected_delivery')
    items_json = request.POST.get('items') # JSON string of items
    
    supplier = get_object_or_404(Supplier, id=supplier_id, company=company)
    
    # Création simplifiée pour l'exemple
    # Générer une référence automatique SYSCOHADA-friendly
    base_ref = f"PO-{timezone.now().strftime('%Y%m%d')}"
    ref = base_ref
    suffix = 1
    while PurchaseOrder.objects.filter(company=company, reference=ref).exists():
        suffix += 1
        ref = f"{base_ref}-{suffix:02d}"

    po = PurchaseOrder.objects.create(
        company=company,
        supplier=supplier,
        expected_delivery=expected_delivery or None,
        reference=ref,
        status='draft',
        created_by=request.user,
        total=Decimal('0')
    )
    
    # Logique pour parser les items et créer les lignes de commande si nécessaire
    
    return JsonResponse({
        'status': 'success',
        'message': 'Bon de commande créé',
        'po': {'reference': po.reference}
    })


@require_POST
@login_required
def api_inventory_item_create(request):
    """API: Créer un article"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': "Aucune entreprise n'est associée à cet utilisateur."}, status=400)
    name = request.POST.get('name')
    sku = request.POST.get('sku')
    unit = request.POST.get('unit', 'unit')
    min_stock = Decimal(request.POST.get('min_stock_level', '10'))

    if not sku:
        base_sku = f"SKU-{timezone.now().strftime('%Y%m%d')}"
        sku = base_sku
        suffix = 1
        while InventoryItem.objects.filter(company=company, sku=sku).exists():
            sku = f"{base_sku}-{suffix:03d}"
            suffix += 1

    item = InventoryItem.objects.create(
        company=company,
        name=name,
        sku=sku,
        unit_measure=unit,
        min_stock_level=min_stock
    )
    
    return JsonResponse({
        'status': 'success',
        'message': 'Article créé',
        'item': {'id': str(item.id), 'name': item.name}
    })


@require_POST
@login_required
def api_stock_transaction_create(request):
    """API: Créer un mouvement de stock"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': "Aucune entreprise n'est associée à cet utilisateur."}, status=400)
    item_id = request.POST.get('inventory_item')
    trans_type = (request.POST.get('transaction_type') or '').lower()
    if trans_type in {'in', 'out', 'adj', 'return'}:
        normalized_type = trans_type
    elif trans_type == 'in':
        normalized_type = 'in'
    elif trans_type == 'out':
        normalized_type = 'out'
    elif trans_type == 'IN'.lower():
        normalized_type = 'in'
    elif trans_type == 'OUT'.lower():
        normalized_type = 'out'
    else:
        normalized_type = 'in'
    quantity = Decimal(request.POST.get('quantity', '0'))
    unit_price = Decimal(request.POST.get('unit_price', '0'))
    reference = request.POST.get('reference')
    
    item = get_object_or_404(InventoryItem, id=item_id, company=company)
    
    try:
        if not reference:
            base_ref = f"STK-{timezone.now().strftime('%Y%m%d')}"
            reference = base_ref
            suffix = 1
            while StockTransaction.objects.filter(item__company=company, reference=reference).exists():
                reference = f"{base_ref}-{suffix:03d}"
                suffix += 1

        trans = StockTransaction.objects.create(
            item=item,
            transaction_type=normalized_type,
            quantity=quantity,
            unit_cost=unit_price,
            reference=reference
        )
        return JsonResponse({
            'status': 'success',
            'message': 'Mouvement de stock enregistré',
            'new_stock': float(item.current_stock)
        })
    except (ValueError, InvalidOperation, ValidationError) as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Erreur lors de l’enregistrement'}, status=500)
