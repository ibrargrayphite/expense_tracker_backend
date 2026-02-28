from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from tracker.models import IncomeSource, ExpenseCategory
from tracker.serializers.categories import IncomeSourceSerializer, ExpenseCategorySerializer
from tracker.pagination import StandardResultsSetPagination

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
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return IncomeSource.objects.filter(user=self.request.user).order_by('name')

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user).order_by('name')

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)