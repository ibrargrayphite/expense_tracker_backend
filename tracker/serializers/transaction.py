from rest_framework import serializers
from tracker.models import InternalTransaction, Transaction, TransactionAccount, TransactionSplit

class InternalTransactionSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source='from_account.account_name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.account_name', read_only=True)

    class Meta:
        model = InternalTransaction
        fields = (
            'id', 'from_account', 'from_account_name', 'to_account', 
            'to_account_name', 'amount', 'note', 'date', 'created_at'
        )
        read_only_fields = ('user', 'created_at')

class TransactionSplitSerializer(serializers.ModelSerializer):
    loan_details = serializers.SerializerMethodField(read_only=True)
    expense_category_name = serializers.CharField(source='expense_category.name', read_only=True)
    income_source_name = serializers.CharField(source='income_source.name', read_only=True)

    class Meta:
        model = TransactionSplit
        fields = ('id', 'type', 'amount', 'loan', 'loan_details', 'expense_category', 'expense_category_name', 'income_source', 'income_source_name', 'note')

    def get_loan_details(self, obj):
        if obj.loan:
            return {
                "id": obj.loan.id,
                "type": obj.loan.type,
                "contact": f"{obj.loan.contact.first_name} {obj.loan.contact.last_name}"
            }
        return None

class TransactionAccountSerializer(serializers.ModelSerializer):
    splits = TransactionSplitSerializer(many=True, read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    bank_name = serializers.CharField(source='account.bank_name', read_only=True)

    class Meta:
        model = TransactionAccount
        fields = ('id', 'account', 'account_name', 'bank_name', 'splits')

class TransactionSerializer(serializers.ModelSerializer):
    accounts = TransactionAccountSerializer(many=True, read_only=True)
    contact_name = serializers.SerializerMethodField(read_only=True)
    expense_category_name = serializers.CharField(source='expense_category.name', read_only=True)
    income_source_name = serializers.CharField(source='income_source.name', read_only=True)
    total_amount = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Transaction
        fields = (
            'id', 'contact', 'contact_name', 'contact_account', 
            'date', 'image', 'accounts', 
            'total_amount', 'created_at'
        )
        read_only_fields = ('user', 'created_at')

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}"
        return None

    def get_total_amount(self, obj):
        from django.db.models import Sum
        total = TransactionSplit.objects.filter(
            transaction_account__transaction=obj
        ).aggregate(Sum('amount'))['amount__sum']
        return total or 0
