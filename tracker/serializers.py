from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Account, Loan, Transaction, Contact, ContactAccount, 
    TransactionAccount, TransactionSplit, ExpenseCategory, IncomeSource,
    InternalTransaction
)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = '__all__'
        read_only_fields = ('user',)

class IncomeSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeSource
        fields = '__all__'
        read_only_fields = ('user',)

class TransactionSplitSerializer(serializers.ModelSerializer):
    loan_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TransactionSplit
        fields = ('id', 'type', 'amount', 'loan', 'loan_details')

    def get_loan_details(self, obj):
        if obj.loan:
            return {
                "id": obj.loan.id,
                "type": obj.loan.type,
                "contact": f"{obj.loan.contact.first_name} {obj.loan.contact.last_name}"
            }
        return None

class TransactionAccountSerializer(serializers.ModelSerializer):
    splits = TransactionSplitSerializer(many=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    bank_name = serializers.CharField(source='account.bank_name', read_only=True)

    class Meta:
        model = TransactionAccount
        fields = ('id', 'account', 'account_name', 'bank_name', 'splits')

class TransactionSerializer(serializers.ModelSerializer):
    accounts = TransactionAccountSerializer(many=True, read_only=True)
    contact_name = serializers.SerializerMethodField()
    expense_category_name = serializers.CharField(source='expense_category.name', read_only=True)
    income_source_name = serializers.CharField(source='income_source.name', read_only=True)
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = (
            'id', 'user', 'contact', 'contact_name', 'contact_account', 
            'note', 'date', 'expense_category', 'expense_category_name',
            'income_source', 'income_source_name', 'image', 'accounts', 
            'total_amount', 'created_at'
        )
        read_only_fields = ('user', 'created_at')

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}"
        return None

    def get_total_amount(self, obj):
        from django.db.models import Sum
        # Sum all splits across all accounts for this transaction
        total = TransactionSplit.objects.filter(transaction_account__transaction=obj).aggregate(Sum('amount'))['amount__sum']
        return total or 0

class InternalTransactionSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source='from_account.account_name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.account_name', read_only=True)

    class Meta:
        model = InternalTransaction
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

class LoanSerializer(serializers.ModelSerializer):
    contact_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ('user',)

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}"
        return None

class AccountSerializer(serializers.ModelSerializer):
    transactions = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = '__all__'
        read_only_fields = ('user',)

    def get_transactions(self, obj):
        # Get splits for this account
        splits = TransactionSplit.objects.filter(
            transaction_account__account=obj
        ).select_related('transaction_account__transaction').order_by('-transaction_account__transaction__date')[:10]
        
        return [{
            'id': s.transaction_account.transaction.id,
            'amount': str(s.amount),
            'type': s.type,
            'note': s.transaction_account.transaction.note,
            'date': s.transaction_account.transaction.date,
        } for s in splits]

    def validate(self, data):
        bank_name = data.get('bank_name')
        account_number = data.get('account_number')
        
        if bank_name != 'CASH' and not account_number:
            raise serializers.ValidationError({"account_number": "Account number is required for bank accounts."})
        
        return data

class ContactAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactAccount
        fields = '__all__'

class ContactSerializer(serializers.ModelSerializer):
    accounts = ContactAccountSerializer(many=True, read_only=True)
    loans = LoanSerializer(many=True, read_only=True)
    transactions = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    loan_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ('user',)

    def get_transactions(self, obj):
        txs = Transaction.objects.filter(contact=obj).order_by('-date')[:10]
        return TransactionSerializer(txs, many=True).data

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_loan_stats(self, obj):
        loans = obj.loans.all()
        total_loaned = sum(loan.remaining_amount for loan in loans if loan.type == 'TAKEN')
        total_lent = sum(loan.remaining_amount for loan in loans if loan.type == 'LENT')
        return {
            'total_loaned': float(total_loaned),
            'total_lent': float(total_lent),
            'net_balance': float(total_lent - total_loaned)
        }
