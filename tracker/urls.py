from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AccountViewSet, ContactViewSet, ContactAccountViewSet,
    IncomeSourceViewSet, ExpenseCategoryViewSet, LoanViewSet,
    TransactionViewSet, InternalTransactionViewSet, UserViewSet,
    ActivityView
)

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'users', UserViewSet, basename='user')
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'contact-accounts', ContactAccountViewSet, basename='contact-account')
router.register(r'income-sources', IncomeSourceViewSet, basename='income-source')
router.register(r'expense-categories', ExpenseCategoryViewSet, basename='expense-category')
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'internal-transactions', InternalTransactionViewSet, basename='internal-transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('activity/', ActivityView.as_view(), name='activity'),
]
