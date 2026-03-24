"""
Achats & Procurement Models — SakinaFinance
Gestion des fournisseurs, bons de commande et stocks
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SupplierCategory(models.Model):
    """Catégorie de fournisseur"""

    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='supplier_categories'
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Fournisseur"""

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Actif')
        INACTIVE = 'inactive', _('Inactif')
        BLACKLISTED = 'blacklisted', _('Liste noire')
        PENDING = 'pending', _('En cours de validation')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='suppliers'
    )
    category = models.ForeignKey(
        SupplierCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='suppliers'
    )

    # Identity
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    supplier_code = models.CharField(max_length=20, blank=True)

    # Registration
    tax_id = models.CharField(max_length=50, blank=True)
    trade_register = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=50, blank=True)

    # Contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Sénégal')

    # Commercial terms
    payment_terms_days = models.IntegerField(default=30)
    currency = models.CharField(max_length=3, default='XOF')
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Bank
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    iban = models.CharField(max_length=50, blank=True)

    # Contact person
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    # Performance
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    on_time_delivery_pct = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    total_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)

    # Accounting
    payable_account = models.ForeignKey(
        'accounting.Account', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supplier_payable'
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PurchaseRFQ(models.Model):
    """Appel d'Offres / Request for Quotation"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        SENT = 'sent', _('Envoyé')
        RECEIVED = 'received', _('Réponses reçues')
        EVALUATED = 'evaluated', _('Évalué')
        AWARDED = 'awarded', _('Attribué')
        CANCELLED = 'cancelled', _('Annulé')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='rfqs'
    )
    reference = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    estimated_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    invited_suppliers = models.ManyToManyField(Supplier, blank=True, related_name='rfqs')
    responses_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.title}"


class PurchaseOrder(models.Model):
    """Bon de Commande"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        PENDING = 'pending', _('En attente d\'approbation')
        APPROVED = 'approved', _('Approuvé')
        SENT = 'sent', _('Envoyé au fournisseur')
        CONFIRMED = 'confirmed', _('Confirmé')
        IN_TRANSIT = 'in_transit', _('En transit')
        RECEIVED = 'received', _('Reçu')
        INVOICED = 'invoiced', _('Facturé')
        CLOSED = 'closed', _('Clôturé')
        CANCELLED = 'cancelled', _('Annulé')

    class Priority(models.TextChoices):
        LOW = 'low', _('Faible')
        NORMAL = 'normal', _('Normale')
        HIGH = 'high', _('Haute')
        URGENT = 'urgent', _('Urgent')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='purchase_orders'
    )
    entity = models.ForeignKey(
        'accounts.Entity', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_orders'
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name='orders'
    )
    rfq = models.ForeignKey(
        PurchaseRFQ, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders'
    )

    reference = models.CharField(max_length=50, unique=True)
    order_date = models.DateField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)

    # Amounts
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')

    # Terms
    payment_terms = models.CharField(max_length=100, blank=True)
    delivery_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NORMAL
    )

    # Approvals
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_pos'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_pos'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f"{self.reference} — {self.supplier.name}"

    def compute_totals(self):
        lines = self.lines.all()
        self.subtotal = sum(line.line_total for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)
        self.total = self.subtotal + self.tax_amount
        self.save(update_fields=['subtotal', 'tax_amount', 'total'])


class PurchaseOrderLine(models.Model):
    """Ligne de bon de commande"""

    order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name='lines'
    )
    product_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    unit = models.CharField(max_length=20, default='unité')
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Receiving
    quantity_received = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    quantity_invoiced = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    # Accounting
    expense_account = models.ForeignKey(
        'accounting.Account', on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        subtotal = self.quantity * self.unit_price * (1 - self.discount_pct / 100)
        self.tax_amount = round(subtotal * self.tax_rate / 100, 2)
        self.line_total = round(subtotal, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


class GoodsReceipt(models.Model):
    """Réception de marchandises / Bon de Livraison"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        CONFIRMED = 'confirmed', _('Confirmé')
        PARTIAL = 'partial', _('Partiel')
        COMPLETE = 'complete', _('Complet')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name='receipts'
    )
    reference = models.CharField(max_length=50, unique=True)
    receipt_date = models.DateField(default=timezone.now)
    supplier_delivery_ref = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-receipt_date']

    def __str__(self):
        return f"{self.reference} — {self.purchase_order.supplier.name}"


class InventoryItem(models.Model):
    """Article en stock / Produit"""

    class ItemType(models.TextChoices):
        RAW_MATERIAL = 'raw', _('Matière première')
        FINISHED_GOOD = 'finished', _('Produit fini')
        SERVICE = 'service', _('Service')
        CONSUMABLE = 'consumable', _('Consommable')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='inventory_items'
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.FINISHED_GOOD)
    
    # Stock levels
    current_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    min_stock_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    
    # Pricing
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unit_measure = models.CharField(max_length=20, default='unit')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.sku} — {self.name}"


class StockTransaction(models.Model):
    """Mouvement de stock (Entrée/Sortie)"""

    class TransactionType(models.TextChoices):
        IN = 'in', _('Entrée (Achat)')
        OUT = 'out', _('Sortie (Vente)')
        ADJUSTMENT = 'adj', _('Ajustement Inventaire')
        RETURN = 'return', _('Retour')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2)
    
    reference = models.CharField(max_length=100, blank=True) # Ex: PO-123, BL-456
    notes = models.TextField(blank=True)
    
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        # Update current stock level in InventoryItem
        is_new = self._state.adding
        if is_new:
            item = self.item
            if self.transaction_type in ['in', 'return']:
                item.current_stock += self.quantity
            else:
                item.current_stock -= self.quantity
            item.save(update_fields=['current_stock'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.item.name} ({self.quantity})"
