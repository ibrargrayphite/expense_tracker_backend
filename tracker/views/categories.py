from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from tracker.models import IncomeSource, ExpenseCategory
from tracker.serializers.categories import IncomeSourceSerializer, ExpenseCategorySerializer
from tracker.pagination import StandardResultsSetPagination
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiExample, OpenApiResponse
)


@extend_schema_view(
    list=extend_schema(
        tags=["Income Sources"],
        summary="List income sources",
        description="Returns a paginated, alphabetically sorted list of all income sources for the authenticated user.",
        responses={200: IncomeSourceSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Income Sources"],
        summary="Create an income source",
        description=(
            "Creates a new income source for the authenticated user.\n\n"
            "**Required fields:** `name`\n\n"
            "**Optional fields:** `description`\n\n"
            "Income source names must be **unique** (case-insensitive) per user."
        ),
        request=IncomeSourceSerializer,
        responses={
            201: IncomeSourceSerializer,
            400: OpenApiResponse(description="Validation error (e.g. duplicate name)."),
        },
        examples=[
            OpenApiExample(
                "Create income source",
                request_only=True,
                value={"name": "Freelance", "description": "Earnings from freelance projects"},
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Income Sources"],
        summary="Retrieve an income source",
        responses={200: IncomeSourceSerializer},
    ),
    update=extend_schema(
        tags=["Income Sources"],
        summary="Update an income source (full)",
        request=IncomeSourceSerializer,
        responses={200: IncomeSourceSerializer},
    ),
    partial_update=extend_schema(
        tags=["Income Sources"],
        summary="Update an income source (partial)",
        request=IncomeSourceSerializer,
        responses={200: IncomeSourceSerializer},
    ),
    destroy=extend_schema(
        tags=["Income Sources"],
        summary="Delete an income source",
        responses={204: None},
    ),
)
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

    @extend_schema(
        tags=["Income Sources"],
        summary="List income sources for dropdown",
        description="Returns all income sources as a flat list (no pagination) for select/dropdown elements.",
        responses={200: IncomeSourceSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        tags=["Expense Categories"],
        summary="List expense categories",
        description="Returns a paginated, alphabetically sorted list of all expense categories for the authenticated user.",
        responses={200: ExpenseCategorySerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Expense Categories"],
        summary="Create an expense category",
        description=(
            "Creates a new expense category for the authenticated user.\n\n"
            "**Required fields:** `name`\n\n"
            "**Optional fields:** `description`\n\n"
            "Category names must be **unique** (case-insensitive) per user."
        ),
        request=ExpenseCategorySerializer,
        responses={
            201: ExpenseCategorySerializer,
            400: OpenApiResponse(description="Validation error (e.g. duplicate name)."),
        },
        examples=[
            OpenApiExample(
                "Create expense category",
                request_only=True,
                value={"name": "Groceries", "description": "Food and household supplies"},
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Expense Categories"],
        summary="Retrieve an expense category",
        responses={200: ExpenseCategorySerializer},
    ),
    update=extend_schema(
        tags=["Expense Categories"],
        summary="Update an expense category (full)",
        request=ExpenseCategorySerializer,
        responses={200: ExpenseCategorySerializer},
    ),
    partial_update=extend_schema(
        tags=["Expense Categories"],
        summary="Update an expense category (partial)",
        request=ExpenseCategorySerializer,
        responses={200: ExpenseCategorySerializer},
    ),
    destroy=extend_schema(
        tags=["Expense Categories"],
        summary="Delete an expense category",
        responses={204: None},
    ),
)
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

    @extend_schema(
        tags=["Expense Categories"],
        summary="List expense categories for dropdown",
        description="Returns all expense categories as a flat list (no pagination) for select/dropdown elements.",
        responses={200: ExpenseCategorySerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)