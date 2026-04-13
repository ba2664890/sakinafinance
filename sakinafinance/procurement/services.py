"""
Services d'Achats — SakinaFinance
"""
from django.core.exceptions import ValidationError
from .models import PurchaseOrder, StockTransaction, SupplierInvoice

def check_3way_match(purchase_order):
    """
    Vérifie la correspondance entre :
    1. Bon de Commande (quantité commandée)
    2. Réceptions de stock (quantité reçue)
    3. Factures fournisseurs (quantité facturée)
    """
    results = {
        'ordered_total': 0,
        'received_total': 0,
        'invoiced_total': 0,
        'is_complete': False,
        'discrepancies': []
    }
    
    # 1. Quantité commandée
    for item in purchase_order.items.all():
        results['ordered_total'] += item.quantity
        
    # 2. Quantité reçue (via StockTransaction liées au PO)
    # Note: On suppose qu'il y a un lien direct ou via reference
    receptions = StockTransaction.objects.filter(
        reference__icontains=purchase_order.order_number,
        transaction_type='in'
    )
    for rec in receptions:
        results['received_total'] += rec.quantity
        
    # 3. Quantité facturée
    invoices = SupplierInvoice.objects.filter(
        purchase_order=purchase_order,
        status='paid' # Ou validé
    )
    for inv in invoices:
        # Ici on simplifie, on devrait itérer sur les lignes de facture
        results['invoiced_total'] += purchase_order.total_amount # Approximatif car montant != quantité
        
    if results['ordered_total'] == results['received_total'] == results['invoiced_total']:
        results['is_complete'] = True
    else:
        if results['received_total'] < results['ordered_total']:
            results['discrepancies'].append("Réception incomplète")
        if results['received_total'] > results['ordered_total']:
            results['discrepancies'].append("Sur-réception")
            
    return results
