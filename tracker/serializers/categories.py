from rest_framework import serializers
from tracker.models import IncomeSource, ExpenseCategory

class IncomeSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeSource
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Income source name cannot be empty.")
        
        user = self.context['request'].user
        category_id = self.instance.id if self.instance else None
        
        if IncomeSource.objects.filter(user=user, name__iexact=value.strip()).exclude(id=category_id).exists():
            raise serializers.ValidationError("An income source with this name already exists.")
            
        return value.strip()

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Category name cannot be empty.")
        
        user = self.context['request'].user
        category_id = self.instance.id if self.instance else None
        
        if ExpenseCategory.objects.filter(user=user, name__iexact=value.strip()).exclude(id=category_id).exists():
            raise serializers.ValidationError("An expense category with this name already exists.")
            
        return value.strip()
