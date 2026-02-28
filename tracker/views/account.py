from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from tracker.models import Account
from tracker.serializers.account import AccountSerializer
from tracker.pagination import StandardResultsSetPagination
from tracker.filters import AccountFilter

class AccountViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for the authenticated user's accounts.

    list     GET    /api/accounts/
    create   POST   /api/accounts/
    retrieve GET    /api/accounts/{id}/
    update   PUT    /api/accounts/{id}/
    partial  PATCH  /api/accounts/{id}/
    destroy  DELETE /api/accounts/{id}/
    """
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AccountFilter
    search_fields = ['account_name', 'bank_name', 'account_number', 'iban']
    ordering_fields = ['balance', 'account_name', 'created_at', 'bank_name']

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.bank_name.upper() == 'CASH':
            raise ValidationError({"detail": "The system 'CASH' account cannot be modified."})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.bank_name.upper() == 'CASH':
            raise ValidationError({"detail": "The system 'CASH' account cannot be deleted."})
        instance.delete()
