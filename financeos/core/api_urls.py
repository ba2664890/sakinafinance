"""
API URLs for FinanceOS IA
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

# Import viewsets from each app
from financeos.accounts.api import UserViewSet, CompanyViewSet
from financeos.accounting.api import (
    AccountViewSet, JournalViewSet, TransactionViewSet,
    InvoiceViewSet, FinancialStatementViewSet
)
from financeos.treasury.api import (
    BankAccountViewSet, CashFlowViewSet, ForecastViewSet
)
from financeos.hr.api import EmployeeViewSet, PayrollViewSet
from financeos.procurement.api import (
    SupplierViewSet, PurchaseOrderViewSet, ExpenseViewSet
)
from financeos.projects.api import ProjectViewSet

# Create router
router = DefaultRouter()

# Accounts
router.register(r'users', UserViewSet, basename='user')
router.register(r'companies', CompanyViewSet, basename='company')

# Accounting
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'journals', JournalViewSet, basename='journal')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'financial-statements', FinancialStatementViewSet, basename='financial-statement')

# Treasury
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-account')
router.register(r'cash-flows', CashFlowViewSet, basename='cash-flow')
router.register(r'forecasts', ForecastViewSet, basename='forecast')

# HR
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'payrolls', PayrollViewSet, basename='payroll')

# Procurement
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'expenses', ExpenseViewSet, basename='expense')

# Projects
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    path('auth/', include('rest_framework.urls')),
]
