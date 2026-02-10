from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from .models import Account, Loan, Transaction
from .serializers import AccountSerializer, LoanSerializer, TransactionSerializer, UserSerializer
from django.contrib.auth.models import User

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        account = instance.account
        loan = instance.loan

        # Update account balance
        if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
            account.balance += instance.amount
        elif instance.type in ['EXPENSE', 'MONEY_LENT', 'REPAYMENT']:
            account.balance -= instance.amount
        account.save()

        # Update loan remaining amount
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
            
            if loan.remaining_amount <= 0:
                loan.is_closed = True
            else:
                loan.is_closed = False
            loan.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        account = instance.account
        loan = instance.loan

        # Reverse account balance update
        if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
            account.balance -= instance.amount
        elif instance.type in ['EXPENSE', 'MONEY_LENT', 'REPAYMENT']:
            account.balance += instance.amount
        account.save()

        # Reverse loan update
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
            
            if loan.remaining_amount > 0:
                loan.is_closed = False
            loan.save()
        
        instance.delete()
