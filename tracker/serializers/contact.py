from rest_framework import serializers
from tracker.models import Contact, ContactAccount
from django.db.models import Sum
from decimal import Decimal

class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)
    loan_stats = serializers.SerializerMethodField(read_only=True)
    accounts = serializers.SerializerMethodField(read_only=True)
    loans = serializers.SerializerMethodField(read_only=True)
    transactions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            'id', 'first_name', 'last_name', 'full_name',
            'phone1', 'phone2', 'email', 'created_at', 'updated_at',
            'loan_stats', 'accounts', 'loans', 'transactions'
        )
        read_only_fields = ('user', 'created_at', 'updated_at')

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_accounts(self, obj):
        return ContactAccountSerializer(obj.accounts.all(), many=True).data

    def get_loans(self, obj):
        from tracker.serializers.loan import LoanSerializer
        return LoanSerializer(obj.loans.all(), many=True).data

    def get_transactions(self, obj):
        # We might need a proper transaction serializer here, but for now we can do a simple list
        # or use a simplified version to avoid circular imports
        from tracker.serializers.transaction import TransactionSerializer
        return TransactionSerializer(obj.transactions.all().order_by('-date')[:10], many=True).data

    def get_loan_stats(self, obj):
        loans = obj.loans.all()
        total_loaned = loans.filter(type='TAKEN').aggregate(Sum('remaining_amount'))['remaining_amount__sum'] or Decimal('0.00')
        total_lent = loans.filter(type='LENT').aggregate(Sum('remaining_amount'))['remaining_amount__sum'] or Decimal('0.00')
        
        return {
            'total_loaned': float(total_loaned),
            'total_lent': float(total_lent),
            'net_balance': float(total_lent - total_loaned)
        }

    def validate_first_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("First name cannot be empty.")
        return value.strip()

    def validate_last_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Last name cannot be empty.")
        return value.strip()

    def validate_phone1(self, value):
        if not value.strip():
            raise serializers.ValidationError("Primary phone number cannot be empty.")
        return value.strip()

class ContactAccountSerializer(serializers.ModelSerializer):
    contact_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ContactAccount
        fields = (
            'id', 'contact', 'contact_name', 'bank_name',
            'account_name', 'account_number', 'iban',
        )

    def get_contact_name(self, obj):
        return f"{obj.contact.first_name} {obj.contact.last_name}"

    def validate_contact(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Selected contact does not belong to your account.")
        return value

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
        
        contact = self.initial_data.get('contact')
        bank_name = self.initial_data.get('bank_name')
        if contact:
            account_id = self.instance.id if self.instance else None
            if ContactAccount.objects.filter(contact_id=contact, account_number=value.strip(), bank_name=bank_name).exclude(id=account_id).exists():
                raise serializers.ValidationError("This account number is already registered for this contact.")
                
        return value.strip()
