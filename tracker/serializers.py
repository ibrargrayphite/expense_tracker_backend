from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Account, Loan, Transaction, Contact, ContactAccount, TransactionSplit

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'
        read_only_fields = ('user',)

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
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ('user',)

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

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
