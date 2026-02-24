from rest_framework import viewsets, permissions, mixins
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
        from decimal import Decimal
        from django.db.models import F
        
        # Save the main transaction
        instance = serializer.save(user=self.request.user)
        
        # We handle accounts and splits manually from request.data
        accounts_data = self.request.data.get('accounts', [])
        
        for acc_data in accounts_data:
            account_id = acc_data.get('account')
            splits_data = acc_data.get('splits', [])
            
            # Create TransactionAccount
            ta = TransactionAccount.objects.create(
                transaction=instance,
                account_id=account_id
            )
            
            for split_data in splits_data:
                stype = split_data.get('type')
                amount = Decimal(str(split_data.get('amount')))
                loan_id = split_data.get('loan', None)
                
                loan = None
                if loan_id:
                    loan = Loan.objects.get(id=loan_id, user=self.request.user)
                elif stype in ['LOAN_TAKEN', 'MONEY_LENT'] and instance.contact:
                    loan_type = 'TAKEN' if stype == 'LOAN_TAKEN' else 'LENT'
                    loan = Loan.objects.create(
                        user=self.request.user,
                        contact=instance.contact,
                        type=loan_type,
                        total_amount=0,
                        remaining_amount=0,
                        description=instance.note
                    )

                # Create Split
                TransactionSplit.objects.create(
                    transaction_account=ta,
                    type=stype,
                    amount=amount,
                    loan=loan
                )
                
                # Update Loan if applicable
                if loan:
                    if stype in ['LOAN_TAKEN', 'REIMBURSEMENT']:
                        loan.total_amount += amount
                        loan.remaining_amount += amount
                    elif stype in ['LOAN_REPAYMENT', 'MONEY_LENT']:
                        loan.remaining_amount -= amount
                    
                    loan.is_closed = loan.remaining_amount == 0
                    loan.save()
                
                # Update Account Balance
                # INCOME, LOAN_TAKEN, REIMBURSEMENT increase balance
                # EXPENSE, MONEY_LENT, LOAN_REPAYMENT decrease balance
                acc = Account.objects.filter(id=account_id, user=self.request.user)
                if stype in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                    acc.update(balance=F('balance') + amount)
                else:
                    acc.update(balance=F('balance') - amount)


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
