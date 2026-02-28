from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from tracker.models import Loan
from tracker.serializers.loan import LoanSerializer
from tracker.pagination import TransactionResultsSetPagination
from tracker.filters import LoanFilter
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse
)
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        tags=["Loans"],
        summary="List loans",
        description=(
            "Returns a paginated list of all loans associated with the authenticated user's contacts.\n\n"
            "Loans are created automatically when a `LOAN_TAKEN` or `MONEY_LENT` transaction is recorded. "
            "They cannot be created manually through this endpoint.\n\n"
            "**Filterable by:** `type`, `contact`, `status`, `min_amount`, `max_amount`\n\n"
            "**Searchable by:** contact's `first_name`, `last_name`, and loan `description`\n\n"
            "**Sortable by:** `remaining_amount`, `created_at`, `contact__first_name`"
        ),
        parameters=[
            OpenApiParameter(
                "type", OpenApiTypes.STR,
                description="Filter by loan type. Choices: `TAKEN` (loan taken from contact), `LENT` (money lent to contact)."
            ),
            OpenApiParameter("contact", OpenApiTypes.INT, description="Filter by contact ID."),
            OpenApiParameter(
                "status", OpenApiTypes.STR,
                description="Filter by loan status. Choices: `ACTIVE` (remaining_amount > 0), `CLOSED` (fully repaid)."
            ),
            OpenApiParameter("min_amount", OpenApiTypes.NUMBER, description="Filter loans with remaining_amount ≥ this value."),
            OpenApiParameter("max_amount", OpenApiTypes.NUMBER, description="Filter loans with remaining_amount ≤ this value."),
            OpenApiParameter("search", OpenApiTypes.STR, description="Search by contact name or loan description."),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="Sort field. Prefix with `-` for descending. Options: `remaining_amount`, `created_at`, `contact__first_name`."),
        ],
        responses={200: LoanSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Loans"],
        summary="Retrieve a loan",
        description="Returns the full details of a specific loan including contact name and status.",
        responses={200: LoanSerializer},
    ),
)
class LoanViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    """
    Restricted read-only access for loans. Users can only view loans.
    Loans are auto-created when LOAN_TAKEN/MONEY_LENT transactions are recorded.

    list     GET    /api/loans/
    retrieve GET    /api/loans/{id}/
    """
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TransactionResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LoanFilter
    search_fields = ['contact__first_name', 'contact__last_name', 'description']
    ordering_fields = ['remaining_amount', 'created_at', 'contact__first_name']

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).order_by('-created_at')

    @extend_schema(
        tags=["Loans"],
        summary="List loans for dropdown",
        description=(
            "Returns all loans as a flat list (no pagination) for use in select/dropdown UI elements "
            "(e.g. when recording a loan repayment or reimbursement transaction)."
        ),
        responses={200: LoanSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)