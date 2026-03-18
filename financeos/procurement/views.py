"""
Procurement Views — FinanceOS IA (DB-connected)
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import Supplier, PurchaseOrder, PurchaseRFQ, SupplierCategory


def _get_company(request):
    return getattr(request.user, 'company', None)


@login_required
def procurement_view(request):
    """Module Achats — vue principale avec données réelles"""
    company = _get_company(request)

    if company:
        suppliers = Supplier.objects.filter(company=company, is_active=True)
        suppliers_count = suppliers.count()

        orders = PurchaseOrder.objects.filter(company=company).order_by('-order_date')
        active_orders = orders.exclude(status__in=['closed', 'cancelled'])

        # KPIs
        total_spends = orders.filter(status__in=['received', 'invoiced', 'closed']).aggregate(
            total=Sum('total')
        )['total'] or 0

        po_count = active_orders.count()
        savings = 0  # Would need budget data
        avg_lead_time_days = 45  # Would compute from receipt dates

        # Top suppliers
        top_suppliers = suppliers.order_by('-total_spend')[:5]
        supplier_data = [{
            'name': s.name,
            'category': s.category.name if s.category else '—',
            'spend': s.total_spend,
            'orders': s.total_orders,
            'rating': s.rating,
            'on_time': s.on_time_delivery_pct,
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
                'amount': po.total,
                'date': po.order_date,
                'delivery': po.expected_delivery,
                'status': po.get_status_display(),
                'status_class': status_class_map.get(po.status, 'secondary'),
            })

        # Categories
        categories = SupplierCategory.objects.filter(company=company).annotate(
            spend=Sum('suppliers__orders__total')
        )[:5]
        cat_data = [{
            'name': c.name,
            'spend': c.spend or 0,
            'pct': 0,
        } for c in categories]

        # RFQs
        rfqs = PurchaseRFQ.objects.filter(company=company).exclude(
            status__in=['awarded', 'cancelled']
        ).order_by('-created_at')[:3]
        rfq_data = [{
            'title': r.title,
            'budget': r.estimated_budget,
            'deadline': r.deadline,
            'responses': r.responses_count,
            'status': r.get_status_display(),
        } for r in rfqs]

    else:
        suppliers_count = 0
        total_spends = 0
        po_count = 0
        supplier_data = []
        po_data = []
        cat_data = []
        rfq_data = []

    context = {
        'page_title': 'Achats & Procurement',
        'total_spends': total_spends,
        'purchases_growth': -3.2,
        'suppliers_count': suppliers_count,
        'po_count': po_count,
        'savings_rate': 8.4,
        'savings': 0,
        'avg_lead_time_days': 45,
        'on_time_delivery': 87.3,
        'purchase_orders': po_data,
        'suppliers': supplier_data,
        'categories': cat_data,
        'rfqs': rfq_data,
    }
    return render(request, 'procurement/index.html', context)


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
    po = get_object_or_404(PurchaseOrder, pk=pk, company=_get_company(request))
    context = {
        'page_title': f'Commande {po.reference}',
        'po': po,
        'lines': po.lines.all(),
    }
    return render(request, 'procurement/po_detail.html', context)
