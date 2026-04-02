from rest_framework import viewsets, permissions
from rest_framework.response import Response

class StubViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    app_name = 'procurement'

    def list(self, request):
        return Response({
            'status': 'stub',
            'implemented': False,
            'app': self.app_name,
            'message': 'Cette API est encore en mode squelette et n\'expose pas de données métier fiables pour le moment.'
        })

# Specific stubs for api_urls.py requirements
class BankAccountViewSet(StubViewSet): pass
class CashFlowViewSet(StubViewSet): pass
class ForecastViewSet(StubViewSet): pass
class EmployeeViewSet(StubViewSet): pass
class PayrollViewSet(StubViewSet): pass
class SupplierViewSet(StubViewSet): pass
class PurchaseOrderViewSet(StubViewSet): pass
class ExpenseViewSet(StubViewSet): pass
class ProjectViewSet(StubViewSet): pass
