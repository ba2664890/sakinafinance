from .models import Account, Journal, Transaction, Invoice, FinancialStatement
from .serializers import (
    AccountSerializer, JournalSerializer, TransactionSerializer,
    InvoiceSerializer, FinancialStatementSerializer
)
from sakinafinance.core.api_mixins import CompanyScopedModelViewSet

class AccountViewSet(CompanyScopedModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

class JournalViewSet(CompanyScopedModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer

class TransactionViewSet(CompanyScopedModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class InvoiceViewSet(CompanyScopedModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

class FinancialStatementViewSet(CompanyScopedModelViewSet):
    queryset = FinancialStatement.objects.all()
    serializer_class = FinancialStatementSerializer
