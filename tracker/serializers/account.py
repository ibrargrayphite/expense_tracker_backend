from rest_framework import serializers
from tracker.models import Account

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            'id', 'bank_name', 'account_name', 'account_number',
            'iban', 'balance', 'created_at', 'updated_at',
        )
        read_only_fields = ('user', 'created_at', 'updated_at')
