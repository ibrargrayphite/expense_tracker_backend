from rest_framework import serializers
from tracker.models import IncomeSource, ExpenseCategory

class IncomeSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeSource
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')
