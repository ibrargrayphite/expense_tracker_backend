from rest_framework import serializers
from tracker.models import Loan

class LoanSerializer(serializers.ModelSerializer):
    contact_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Loan
        fields = (
            'id', 'contact', 'contact_name', 'type', 'total_amount',
            'remaining_amount', 'description', 'is_closed', 'created_at', 'updated_at',
        )
        read_only_fields = ('user', 'created_at', 'updated_at')

    def get_contact_name(self, obj):
        return f"{obj.contact.first_name} {obj.contact.last_name}"
