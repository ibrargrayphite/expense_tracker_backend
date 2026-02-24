from rest_framework import serializers
from tracker.models import Contact, ContactAccount

class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            'id', 'first_name', 'last_name', 'full_name',
            'phone1', 'phone2', 'email', 'created_at', 'updated_at',
        )
        read_only_fields = ('user', 'created_at', 'updated_at')

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

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
