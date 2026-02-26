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

    def validate_contact(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Selected contact does not belong to your account.")
        return value

    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total amount must be greater than zero.")
        return value

    def validate(self, data):
        total_amount = data.get('total_amount')
        remaining_amount = data.get('remaining_amount')

        if total_amount is not None and remaining_amount is not None:
            if remaining_amount > total_amount:
                raise serializers.ValidationError({
                    "remaining_amount": "Remaining amount cannot be greater than the total loan amount."
                })
            
        if remaining_amount is not None and remaining_amount < 0:
            raise serializers.ValidationError({
                "remaining_amount": "Remaining amount cannot be negative."
            })

        return data
