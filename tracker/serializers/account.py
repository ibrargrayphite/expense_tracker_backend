from rest_framework import serializers
from tracker.models import Account
from rest_framework.validators import UniqueTogetherValidator

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            'id', 'bank_name', 'account_name', 'account_number',
            'iban', 'balance', 'created_at', 'updated_at',
        )
        read_only_fields = ('user', 'created_at', 'updated_at')

    def validate_bank_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Bank name cannot be empty.")
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
        
        if Account.objects.filter(user=user, account_number=value.strip()).exclude(id=account_id).exists():
            raise serializers.ValidationError("An account with this number already exists for your profile.")
            
        return value.strip()
