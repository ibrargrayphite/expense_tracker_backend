from rest_framework import viewsets, permissions
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from tracker.models import Account
from tracker.serializers.account import AccountSerializer, AccountDropdownSerializer
from tracker.pagination import StandardResultsSetPagination
from tracker.filters import AccountFilter
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse
)
from drf_spectacular.types import OpenApiTypes

logger = logging.getLogger(__name__)


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
        return Account.objects.filter(user=self.request.user).select_related('user').order_by('-created_at')

    # ------------------------------------------------------------------
    # Optimised recent-transactions: batch-load for all accounts at once
    # ------------------------------------------------------------------
    def _build_recent_transactions_map(self, account_ids):
        """
        Fetch the 5 most recent transactions for each account in *account_ids*
        using a single batched DB query, returning::

            {account_id: [Transaction, ...], ...}

        Covers both direct account transactions (via TransactionAccount) and
        internal transfer transactions (via InternalTransaction FK fields).
        All related data needed by TransactionSerializer is select/prefetched
        so the serializer runs with zero additional queries.
        """
        from tracker.models import Transaction
        from django.db.models import Q

        if not account_ids:
            return {}

        id_set = set(account_ids)

        transactions = list(
            Transaction.objects
            .filter(
                Q(accounts__account_id__in=id_set) |
                Q(internal_transaction__from_account_id__in=id_set) |
                Q(internal_transaction__to_account_id__in=id_set)
            )
            .distinct()
            .select_related(
                'internal_transaction__from_account',
                'internal_transaction__to_account',
                'contact',
                'contact_account',
            )
            .prefetch_related(
                'accounts__splits__expense_category',
                'accounts__splits__income_source',
                'accounts__splits__loan__contact',
            )
            .order_by('-date', '-created_at')
        )

        # Distribute transactions to their accounts in Python (no extra queries).
        result = {aid: [] for aid in id_set}
        for tx in transactions:
            # Direct account transactions
            for ta in tx.accounts.all():
                aid = ta.account_id
                if aid in result and len(result[aid]) < 5:
                    result[aid].append(tx)
            # Internal transfer transactions
            it = tx.internal_transaction
            if it:
                for aid in (it.from_account_id, it.to_account_id):
                    if aid in result and len(result[aid]) < 5:
                        if tx not in result[aid]:
                            result[aid].append(tx)

        return result

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        action = getattr(self, 'action', None)

        if action == 'list':
            account_ids = list(
                self.filter_queryset(self.get_queryset()).values_list('id', flat=True)
            )
            ctx['recent_transactions_map'] = self._build_recent_transactions_map(account_ids)
        elif action == 'retrieve':
            try:
                account_ids = [int(self.kwargs.get('pk'))]
            except (TypeError, ValueError):
                account_ids = []
            ctx['recent_transactions_map'] = self._build_recent_transactions_map(account_ids)

        return ctx

    def list(self, request, *args, **kwargs):
        from django.core.cache import cache
        from tracker.cache import accounts_list_key, CACHE_TTL

        _FILTER_PARAMS = {'bank_name', 'min_balance', 'max_balance', 'search', 'ordering', 'page'}
        has_filters = any(request.query_params.get(k) for k in _FILTER_PARAMS)

        if not has_filters:
            cache_key = accounts_list_key(request.user.id)
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Accounts cache HIT for user %s", request.user.id)
                return Response(cached)
            logger.debug("Accounts cache MISS for user %s", request.user.id)

        response = super().list(request, *args, **kwargs)

        if not has_filters:
            logger.debug("Accounts cache SET for user %s", request.user.id)
            cache.set(cache_key, response.data, CACHE_TTL)

        return response

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
        serializer = AccountDropdownSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        logger.info("Account created by user %s: %s (%s)",
                    self.request.user.id,
                    serializer.validated_data.get('account_name', ''),
                    serializer.validated_data.get('bank_name', ''))

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.bank_name.upper() == 'CASH':
            logger.warning("User %s attempted to modify the CASH account", self.request.user.id)
            raise ValidationError({"detail": "The system 'CASH' account cannot be modified."})
        serializer.save()
        logger.info("Account %s updated by user %s", instance.id, self.request.user.id)

    def perform_destroy(self, instance):
        if instance.bank_name.upper() == 'CASH':
            logger.warning("User %s attempted to delete the CASH account", self.request.user.id)
            raise ValidationError({"detail": "The system 'CASH' account cannot be deleted."})
        logger.info("Account %s deleted by user %s", instance.id, self.request.user.id)
        instance.delete()


