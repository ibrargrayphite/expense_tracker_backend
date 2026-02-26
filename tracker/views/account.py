from rest_framework import viewsets, permissions
from rest_framework.exceptions import ValidationError
from tracker.models import Account
from tracker.serializers.account import AccountSerializer

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

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('-created_at')

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
