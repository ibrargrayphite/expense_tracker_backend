from rest_framework import viewsets, permissions
from tracker.models import IncomeSource, ExpenseCategory
from tracker.serializers.categories import IncomeSourceSerializer, ExpenseCategorySerializer

class IncomeSourceViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for income sources.

    list     GET    /api/income-sources/
    create   POST   /api/income-sources/
    retrieve GET    /api/income-sources/{id}/
    update   PUT    /api/income-sources/{id}/
    partial  PATCH  /api/income-sources/{id}/
    destroy  DELETE /api/income-sources/{id}/
    """
    serializer_class = IncomeSourceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return IncomeSource.objects.filter(user=self.request.user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for expense categories.

    list     GET    /api/expense-categories/
    create   POST   /api/expense-categories/
    retrieve GET    /api/expense-categories/{id}/
    update   PUT    /api/expense-categories/{id}/
    partial  PATCH  /api/expense-categories/{id}/
    destroy  DELETE /api/expense-categories/{id}/
    """
    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)