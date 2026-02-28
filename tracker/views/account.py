from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from tracker.models import Account
from tracker.serializers.account import AccountSerializer
from tracker.pagination import StandardResultsSetPagination
from tracker.filters import AccountFilter
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse
)
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        tags=["Accounts"],
        summary="List user accounts",
        description=(
            "Returns a paginated list of all bank/cash accounts belonging to the authenticated user.\n\n"
            "**Filterable by:** `bank_name`, `min_balance`, `max_balance`\n\n"
            "**Searchable by:** `account_name`, `bank_name`, `account_number`, `iban`\n\n"
            "**Sortable by:** `balance`, `account_name`, `created_at`, `bank_name`"
        ),
        parameters=[
            OpenApiParameter("bank_name", OpenApiTypes.STR, description="Filter by bank name (case-insensitive exact match)."),
            OpenApiParameter("min_balance", OpenApiTypes.NUMBER, description="Filter accounts with balance ≥ this value."),
            OpenApiParameter("max_balance", OpenApiTypes.NUMBER, description="Filter accounts with balance ≤ this value."),
            OpenApiParameter("search", OpenApiTypes.STR, description="Search across account_name, bank_name, account_number, iban."),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="Sort field. Prefix with `-` for descending. Options: `balance`, `account_name`, `created_at`, `bank_name`."),
        ],
        responses={200: AccountSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Accounts"],
        summary="Create a new account",
        description=(
            "Creates a new bank/wallet account for the authenticated user.\n\n"
            "**Required fields:** `bank_name`, `account_name`, `account_number`\n\n"
            "**Optional fields:** `iban`\n\n"
            "**Notes:**\n"
            "- `bank_name` cannot be `CASH` (reserved for the system Cash Wallet).\n"
            "- `account_number` must be unique per bank per user.\n"
            "- Initial `balance` defaults to `0.00` and is read-only (set by transactions)."
        ),
        request=AccountSerializer,
        responses={
            201: AccountSerializer,
            400: OpenApiResponse(description="Validation error (e.g. duplicate account number, reserved bank name)."),
        },
        examples=[
            OpenApiExample(
                "Create bank account",
                request_only=True,
                value={
                    "bank_name": "HBL",
                    "account_name": "Savings",
                    "account_number": "1234567890",
                    "iban": "PK36SCBL0000001123456702",
                },
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Accounts"],
        summary="Retrieve an account",
        description="Returns full details of a specific account including its 5 most recent transactions.",
        responses={200: AccountSerializer},
    ),
    update=extend_schema(
        tags=["Accounts"],
        summary="Update an account (full)",
        description="Full replacement update of an account. The system `CASH` account cannot be modified.",
        request=AccountSerializer,
        responses={200: AccountSerializer, 400: OpenApiResponse(description="Cannot modify CASH account.")},
    ),
    partial_update=extend_schema(
        tags=["Accounts"],
        summary="Update an account (partial)",
        description="Partial update of an account. The system `CASH` account cannot be modified.",
        request=AccountSerializer,
        responses={200: AccountSerializer, 400: OpenApiResponse(description="Cannot modify CASH account.")},
    ),
    destroy=extend_schema(
        tags=["Accounts"],
        summary="Delete an account",
        description="Deletes an account. The system `CASH` account cannot be deleted.",
        responses={204: None, 400: OpenApiResponse(description="Cannot delete CASH account.")},
    ),
)
class AccountViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for the authenticated user's accounts.

    list     GET    /api/accounts/
    create   POST   /api/accounts/
    retrieve GET    /api/accounts/{id}/
    update   PUT    /api/accounts/{id}/
    partial  PATCH  /api/accounts/{id}/
    destroy  DELETE /api/accounts/{id}/
    """
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AccountFilter
    search_fields = ['account_name', 'bank_name', 'account_number', 'iban']
    ordering_fields = ['balance', 'account_name', 'created_at', 'bank_name']

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('-created_at')

    @extend_schema(
        tags=["Accounts"],
        summary="List accounts for dropdown",
        description=(
            "Returns the user's accounts as a flat list (no pagination) suitable for populating "
            "select/dropdown UI elements. Supports the same filters as the main list endpoint."
        ),
        responses={200: AccountSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.bank_name.upper() == 'CASH':
            raise ValidationError({"detail": "The system 'CASH' account cannot be modified."})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.bank_name.upper() == 'CASH':
            raise ValidationError({"detail": "The system 'CASH' account cannot be deleted."})
        instance.delete()
