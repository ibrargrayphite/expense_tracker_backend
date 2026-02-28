from rest_framework import serializers
from tracker.models import Account, ContactAccount
from rest_framework.validators import UniqueTogetherValidator

class AccountSerializer(serializers.ModelSerializer):
    recent_transactions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Account
        fields = (
            'id', 'bank_name', 'account_name', 'account_number',
            'iban', 'balance', 'created_at', 'updated_at',
            'recent_transactions'
        )
        read_only_fields = ('user', 'balance', 'created_at', 'updated_at')

    def get_recent_transactions(self, obj):
        from tracker.models import Transaction
        from tracker.serializers.transaction import TransactionSerializer
        from django.db.models import Q
        
        transactions = Transaction.objects.filter(
            Q(accounts__account=obj) |
            Q(internal_transaction__from_account=obj) |
            Q(internal_transaction__to_account=obj)
        ).distinct().order_by('-date', '-created_at')[:5]
        
        return TransactionSerializer(transactions, many=True, context=self.context).data

    def validate_bank_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Bank name cannot be empty.")
        if value.strip().upper() == 'CASH':
            raise serializers.ValidationError("The 'CASH' bank name is reserved for the system Cash Wallet.")
        return value.strip()

    def validate_account_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Account name cannot be empty.")
        return value.strip()

    def validate_account_number(self, value):
        if not value.strip():
            raise serializers.ValidationError("Account number cannot be empty.")
        
        user = self.context['request'].user
        account_id = self.instance.id if self.instance else None
        bank_name = self.initial_data.get('bank_name')
        
        if Account.objects.filter(user=user, account_number=value.strip(), bank_name=bank_name).exclude(id=account_id).exists():
            raise serializers.ValidationError("An account with this number already exists for your profile.")
        
        if ContactAccount.objects.filter(account_number=value.strip(), bank_name=bank_name).exists():
            raise serializers.ValidationError("An account with this number already exists for a contact.")
            
        return value.strip()
