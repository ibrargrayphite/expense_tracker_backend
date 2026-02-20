from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, LoanViewSet, TransactionViewSet, UserViewSet, ContactViewSet, ContactAccountViewSet

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'users', UserViewSet, basename='user')
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'contact-accounts', ContactAccountViewSet, basename='contact-account')

urlpatterns = [
    path('', include(router.urls)),
]
