from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Account, Loan, Transaction, Contact, ContactAccount

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

class ContactAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactAccount
        fields = '__all__'

class ContactSerializer(serializers.ModelSerializer):
    accounts = ContactAccountSerializer(many=True, read_only=True)
    
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ('user',)

class LoanSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.first_name', read_only=True)
    
    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ('user',)

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('user',)

    def create(self, validated_data):
        # We'll handle account balance and loan remaining amount updates in the view or a service
        return super().create(validated_data)
