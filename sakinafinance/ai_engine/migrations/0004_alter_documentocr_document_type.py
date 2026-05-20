from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0003_chatsession_chatmessage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentocr',
            name='document_type',
            field=models.CharField(
                choices=[
                    ('invoice', 'Facture'),
                    ('supplier_invoice', 'Facture fournisseur'),
                    ('receipt', 'Reçu'),
                    ('bank_statement', 'Relevé bancaire'),
                    ('purchase_order', 'Bon de commande'),
                    ('delivery_note', 'Bon de livraison'),
                    ('receipt_note', 'Bon de réception'),
                    ('stock_count', 'Fiche d’inventaire'),
                    ('contract', 'Contrat'),
                    ('payslip', 'Bulletin de paie'),
                    ('other', 'Autre'),
                ],
                default='invoice',
                max_length=20,
            ),
        ),
    ]
