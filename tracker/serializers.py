from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Account, Loan, Transaction, Contact, ContactAccount, TransactionSplit

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

class TransactionSplitSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.bank_name', read_only=True)
    
    class Meta:
        model = TransactionSplit
        fields = ['id', 'account', 'account_name', 'amount']

class TransactionSerializer(serializers.ModelSerializer):
    splits = TransactionSplitSerializer(many=True, read_only=True)
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('user',)

    def create(self, validated_data):
        return super().create(validated_data)

class LoanSerializer(serializers.ModelSerializer):
    contact_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ('user',)

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}"
        return obj.person_name

class AccountSerializer(serializers.ModelSerializer):
    transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = '__all__'
        read_only_fields = ('user',)

    def get_transactions(self, obj):
        from .models import Transaction, TransactionSplit
        from django.db.models import Q
        
        # Get transactions where this account is either the primary account or part of a split
        split_transactions = TransactionSplit.objects.filter(account=obj).values_list('transaction_id', flat=True)
        transactions = Transaction.objects.filter(
            Q(account=obj) | Q(id__in=split_transactions)
        ).order_by('-date')[:10] # Limit to 10 most recent
        
        return TransactionSerializer(transactions, many=True).data

    def validate(self, data):
        bank_name = data.get('bank_name')
        account_number = data.get('account_number')
        
        if bank_name != 'Cash' and not account_number:
            raise serializers.ValidationError({"account_number": "Account number is required for bank accounts."})
        
        # If it's cash, we clear fields that shouldn't be there just in case
        if bank_name == 'Cash':
            data['account_number'] = None
            data['iban'] = None
            
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
        # Limit to 10 most recent
        transactions = obj.transactions.all().order_by('-date')[:10]
        return TransactionSerializer(transactions, many=True).data

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
