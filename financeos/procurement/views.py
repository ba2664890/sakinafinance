"""
Achats & Procurement Views — FinanceOS IA
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def procurement_view(request):
    """Module Achats & Procurement — vue principale"""
    context = {
        'page_title': 'Achats & Procurement',

        # KPIs Achats
        'total_spends': 142_500_000,
        'purchases_growth': -3.2,
        'suppliers_count': 148,
        'po_count': 34,
        'savings_rate': 8.4,
        'savings': 13_100_000,
        'avg_lead_time_days': 45,
        'on_time_delivery': 87.3,

        # Commandes en cours
        'purchase_orders': [
            {'id': 'PO-2025-0892', 'supplier': 'SABC Fournisseur SA', 'amount': 4_200_000, 'date': '15/03/2025', 'delivery': '25/03/2025', 'status': 'En transit', 'status_class': 'warning'},
            {'id': 'PO-2025-0891', 'supplier': 'Tech Solutions SARL', 'amount': 8_750_000, 'date': '14/03/2025', 'delivery': '28/03/2025', 'status': 'Confirmée', 'status_class': 'primary'},
            {'id': 'PO-2025-0890', 'supplier': 'Matériaux Ouest Afrique', 'amount': 12_400_000, 'date': '13/03/2025', 'delivery': '01/04/2025', 'status': 'En attente', 'status_class': 'secondary'},
            {'id': 'PO-2025-0889', 'supplier': 'Logistique Express CI', 'amount': 2_850_000, 'date': '12/03/2025', 'delivery': '18/03/2025', 'status': 'Livrée', 'status_class': 'success'},
            {'id': 'PO-2025-0888', 'supplier': 'Bureau Fournitures Pro', 'amount': 650_000, 'date': '11/03/2025', 'delivery': '17/03/2025', 'status': 'Livrée', 'status_class': 'success'},
        ],

        # Top fournisseurs
        'suppliers': [
            {'name': 'SABC Fournisseur SA', 'category': 'Matières premières', 'spend': 28_400_000, 'orders': 24, 'rating': 4.8, 'on_time': 96},
            {'name': 'Tech Solutions SARL', 'category': 'IT & Logiciels', 'spend': 18_750_000, 'orders': 12, 'rating': 4.5, 'on_time': 92},
            {'name': 'Matériaux Ouest Afrique', 'category': 'Équipements', 'spend': 15_200_000, 'orders': 8, 'rating': 4.2, 'on_time': 85},
            {'name': 'Logistique Express CI', 'category': 'Transport', 'spend': 12_900_000, 'orders': 48, 'rating': 4.6, 'on_time': 94},
            {'name': 'Agence Publicité Dakar', 'category': 'Marketing', 'spend': 8_400_000, 'orders': 15, 'rating': 3.9, 'on_time': 78},
        ],

        # Répartition achats par catégorie
        'categories': [
            {'name': 'Matières & Consommables', 'spend': 58_200_000, 'pct': 41},
            {'name': 'Équipements & Immobilisations', 'spend': 28_400_000, 'pct': 20},
            {'name': 'Services & Prestations', 'spend': 24_800_000, 'pct': 17},
            {'name': 'IT & Télécoms', 'spend': 18_750_000, 'pct': 13},
            {'name': 'Frais généraux', 'spend': 12_350_000, 'pct': 9},
        ],

        # Appels d'offres en cours
        'rfqs': [
            {'title': 'Fourniture de serveurs & stockage', 'budget': 45_000_000, 'deadline': '25/03/2025', 'responses': 6, 'status': 'En cours'},
            {'title': 'Prestation sécurité informatique', 'budget': 12_000_000, 'deadline': '30/03/2025', 'responses': 3, 'status': 'En cours'},
            {'title': 'Véhicules utilitaires zone UEMOA', 'budget': 85_000_000, 'deadline': '10/04/2025', 'responses': 8, 'status': 'Ouvert'},
        ],
    }
    return render(request, 'procurement/index.html', context)
