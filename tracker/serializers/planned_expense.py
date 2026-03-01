from rest_framework import serializers
from tracker.models import PlannedExpense, ExpenseCategory


class PlannedExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = PlannedExpense
        fields = (
            'id', 'amount', 'start_date', 'end_date',
            'category', 'category_name', 'note',
            'is_completed', 'created_at', 'updated_at'
        )
        read_only_fields = ('user', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user:
            self.fields['category'].queryset = ExpenseCategory.objects.filter(user=request.user)

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        amount = attrs.get('amount')
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("End date must be on or after start date.")
        if amount is not None and amount <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return attrs
