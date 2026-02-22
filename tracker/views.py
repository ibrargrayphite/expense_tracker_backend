from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Account, Loan, Transaction, Contact, ContactAccount, TransactionSplit
from .serializers import AccountSerializer, LoanSerializer, TransactionSerializer, UserSerializer, ContactSerializer, ContactAccountSerializer
from django.contrib.auth.models import User

@extend_schema_view(
    list=extend_schema(description='List all users', tags=['Users']),
    create=extend_schema(description='Register a new user', tags=['Users']),
    retrieve=extend_schema(description='Get user details', tags=['Users']),
    update=extend_schema(description='Update user', tags=['Users']),
    partial_update=extend_schema(description='Partially update user', tags=['Users']),
    destroy=extend_schema(description='Delete user', tags=['Users']),
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        if User.objects.filter(username=username).exists():
            first_name = request.data.get('first_name', '').lower()
            last_name = request.data.get('last_name', '').lower()
            
            import random
            import string
            
            base = f"{first_name}{last_name}"
            if not base:
                base = "user"
            
            suggestion = ""
            while True:
                suffix = ''.join(random.choices(string.digits, k=3))
                suggestion = f"{base}{suffix}"
                if not User.objects.filter(username=suggestion).exists():
                    break
            
            return Response({
                'username': ['A user with that username already exists.'],
                'suggestion': suggestion
            }, status=status.HTTP_400_BAD_REQUEST)
            
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(description='List all accounts for the authenticated user', tags=['Accounts']),
    create=extend_schema(description='Create a new account', tags=['Accounts']),
    retrieve=extend_schema(description='Get account details', tags=['Accounts']),
    update=extend_schema(description='Update account', tags=['Accounts']),
    partial_update=extend_schema(description='Partially update account', tags=['Accounts']),
    destroy=extend_schema(description='Delete account', tags=['Accounts']),
)
class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@extend_schema_view(
    list=extend_schema(description='List all loans for the authenticated user', tags=['Loans']),
    create=extend_schema(description='Create a new loan record', tags=['Loans']),
    retrieve=extend_schema(description='Get loan details', tags=['Loans']),
    update=extend_schema(description='Update loan', tags=['Loans']),
    partial_update=extend_schema(description='Partially update loan', tags=['Loans']),
    destroy=extend_schema(description='Delete loan', tags=['Loans']),
)
class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@extend_schema_view(
    list=extend_schema(description='List all contacts for the authenticated user', tags=['Contacts']),
    create=extend_schema(description='Create a new contact', tags=['Contacts']),
    retrieve=extend_schema(description='Get contact details', tags=['Contacts']),
    update=extend_schema(description='Update contact', tags=['Contacts']),
    partial_update=extend_schema(description='Partially update contact', tags=['Contacts']),
    destroy=extend_schema(description='Delete contact', tags=['Contacts']),
)
class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ContactAccountViewSet(viewsets.ModelViewSet):
    serializer_class = ContactAccountSerializer

    def get_queryset(self):
        return ContactAccount.objects.filter(contact__user=self.request.user)

@extend_schema_view(
    list=extend_schema(description='List all transactions for the authenticated user', tags=['Transactions']),
    create=extend_schema(description='Create a new transaction (automatically updates account balance and loan amounts)', tags=['Transactions']),
    retrieve=extend_schema(description='Get transaction details', tags=['Transactions']),
    update=extend_schema(description='Update transaction', tags=['Transactions']),
    partial_update=extend_schema(description='Partially update transaction', tags=['Transactions']),
    destroy=extend_schema(description='Delete transaction (reverses account and loan updates)', tags=['Transactions']),
)
class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        import json
        instance = serializer.save(user=self.request.user)
        
        # 1. Handle Automatic Loan Creation (if applicable)
        if instance.type in ['LOAN_TAKEN', 'MONEY_LENT'] and instance.contact and not instance.loan:
            loan_type = 'TAKEN' if instance.type == 'LOAN_TAKEN' else 'LENT'
            new_loan = Loan.objects.create(
                user=instance.user,
                contact=instance.contact,
                type=loan_type,
                total_amount=0, 
                remaining_amount=0,
                description=instance.note
            )
            instance.loan = new_loan
            instance.save()

        # 2. Handle Account Splits & Balance Updates
        splits_data = self.request.data.get('splits')
        if isinstance(splits_data, str):
            try:
                splits_data = json.loads(splits_data)
            except:
                splits_data = []

        if splits_data and len(splits_data) > 0:
            for split in splits_data:
                acc_id = split.get('account')
                amt = int(split.get('amount'))
                acc = Account.objects.get(id=acc_id, user=instance.user)
                TransactionSplit.objects.create(transaction=instance, account=acc, amount=amt)
                
                # Update balance for each split account
                if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                    acc.balance += amt
                else:
                    acc.balance -= amt
                acc.save()
        elif instance.account:
            # Simple transaction (one account)
            account = instance.account
            if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                account.balance += instance.amount
            else:
                account.balance -= instance.amount
            account.save()

        # 3. Update Loan Totals
        loan = instance.loan
        if loan:
            if instance.type == 'REPAYMENT':
                loan.remaining_amount -= instance.amount
            elif instance.type == 'REIMBURSEMENT':
                loan.remaining_amount -= instance.amount
            elif instance.type == 'LOAN_TAKEN':
                loan.remaining_amount += instance.amount
                loan.total_amount += instance.amount
            elif instance.type == 'MONEY_LENT':
                loan.remaining_amount += instance.amount
                loan.total_amount += instance.amount
            
            loan.is_closed = loan.remaining_amount <= 0
            loan.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        # Reverse balance updates for all accounts involved
        splits = instance.splits.all()
        if splits.exists():
            for split in splits:
                acc = split.account
                if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                    acc.balance -= split.amount
                else:
                    acc.balance += split.amount
                acc.save()
        elif instance.account:
            account = instance.account
            if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                account.balance -= instance.amount
            else:
                account.balance += instance.amount
            account.save()

        # Reverse loan update
        loan = instance.loan
        if loan:
            if instance.type == 'REPAYMENT':
                loan.remaining_amount += instance.amount
            elif instance.type == 'REIMBURSEMENT':
                loan.remaining_amount += instance.amount
            elif instance.type == 'LOAN_TAKEN':
                loan.remaining_amount -= instance.amount
                loan.total_amount -= instance.amount
            elif instance.type == 'MONEY_LENT':
                loan.remaining_amount -= instance.amount
                loan.total_amount -= instance.amount
            
            loan.is_closed = loan.remaining_amount <= 0
            loan.save()
        
        instance.delete()
