from rest_framework import viewsets, permissions

class StubViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    def list(self, request):
        from rest_framework.response import Response
        return Response({'status': 'stub', 'app': 'hr'})

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

