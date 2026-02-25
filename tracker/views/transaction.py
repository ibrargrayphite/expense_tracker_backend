from rest_framework import viewsets, permissions, mixins
from rest_framework.validators import ValidationError
from rest_framework import status
from django.db import transaction
from tracker.models import InternalTransaction, Transaction, TransactionAccount, TransactionSplit, Loan, Account
from tracker.serializers.transaction import InternalTransactionSerializer, TransactionSerializer

class TransactionViewSet(mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    """
    Create and Read for transactions.

    list     GET    /api/transactions/
    create   POST   /api/transactions/
    retrieve GET    /api/transactions/{id}/
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).order_by('-date', '-created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        try:
            serializer.save()
        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError({'detail': str(e)})


class InternalTransactionViewSet(mixins.CreateModelMixin,
                                 mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 viewsets.GenericViewSet):
    """
    Create and Read for internal transfers.

    list     GET    /api/internal-transactions/
    create   POST   /api/internal-transactions/
    retrieve GET    /api/internal-transactions/{id}/
    """
    serializer_class = InternalTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InternalTransaction.objects.filter(
            user=self.request.user
        ).order_by('-date', '-created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        from django.db.models import F
        instance = serializer.save(user=self.request.user)
        
        # Update balances
        Account.objects.filter(id=instance.from_account.id).update(balance=F('balance') - instance.amount)
        Account.objects.filter(id=instance.to_account.id).update(balance=F('balance') + instance.amount)
