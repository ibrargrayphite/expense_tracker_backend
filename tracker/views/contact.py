from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from tracker.models import Contact, ContactAccount
from tracker.serializers.contact import ContactSerializer, ContactAccountSerializer
from tracker.pagination import StandardResultsSetPagination
from tracker.filters import ContactFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse
)
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        tags=["Contacts"],
        summary="List contacts",
        description=(
            "Returns a paginated list of all contacts belonging to the authenticated user.\n\n"
            "Each contact includes nested `loan_stats`, `accounts`, `loans`, and up to 10 recent `transactions`.\n\n"
            "**Filterable by:** `first_name`, `last_name`, `phone1`, `net_balance`\n\n"
            "**Searchable by:** `first_name`, `last_name`, `phone1`, `phone2`, `email`\n\n"
            "**Sortable by:** `first_name`, `last_name`"
        ),
        parameters=[
            OpenApiParameter("first_name", OpenApiTypes.STR, description="Filter by first name."),
            OpenApiParameter("last_name", OpenApiTypes.STR, description="Filter by last name."),
            OpenApiParameter("phone1", OpenApiTypes.STR, description="Filter by primary phone number."),
            OpenApiParameter(
                "net_balance", OpenApiTypes.STR,
                description="Filter by loan net balance. Choices: `POSITIVE` (you are owed money), `NEGATIVE` (you owe money), `SETTLED`."
            ),
            OpenApiParameter("search", OpenApiTypes.STR, description="Search across first_name, last_name, phone1, phone2, email."),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="Sort field. Options: `first_name`, `last_name`."),
        ],
        responses={200: ContactSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Contacts"],
        summary="Create a contact",
        description=(
            "Creates a new contact for the authenticated user.\n\n"
            "**Required fields:** `first_name`, `last_name`, `phone1`\n\n"
            "**Optional fields:** `phone2`, `email`"
        ),
        request=ContactSerializer,
        responses={
            201: ContactSerializer,
            400: OpenApiResponse(description="Validation error (e.g. empty name or phone)."),
        },
        examples=[
            OpenApiExample(
                "Create contact",
                request_only=True,
                value={
                    "first_name": "Ali",
                    "last_name": "Khan",
                    "phone1": "+923001234567",
                    "phone2": "+923007654321",
                    "email": "ali@example.com",
                },
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Contacts"],
        summary="Retrieve a contact",
        description="Returns full details of a contact including loan stats, bank accounts, loans, and recent transactions.",
        responses={200: ContactSerializer},
    ),
    update=extend_schema(
        tags=["Contacts"],
        summary="Update a contact (full)",
        request=ContactSerializer,
        responses={200: ContactSerializer}
    ),
    partial_update=extend_schema(
        tags=["Contacts"],
        summary="Update a contact (partial)",
        request=ContactSerializer,
        responses={200: ContactSerializer}
    ),
    destroy=extend_schema(
        tags=["Contacts"],
        summary="Delete a contact",
        description="Permanently deletes a contact and all associated data (loans, contact accounts).",
        responses={204: None}
    ),
)
class ContactViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for the authenticated user's contacts.

    list     GET    /api/contacts/
    create   POST   /api/contacts/
    retrieve GET    /api/contacts/{id}/
    update   PUT    /api/contacts/{id}/
    partial  PATCH  /api/contacts/{id}/
    destroy  DELETE /api/contacts/{id}/
    """
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContactFilter
    search_fields = ['first_name', 'last_name', 'phone1', 'phone2', 'email']
    ordering_fields = ['first_name', 'last_name']
    ordering = ['first_name', 'last_name']

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user).order_by('first_name', 'last_name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        tags=["Contacts"],
        summary="List contacts for dropdown",
        description=(
            "Returns the user's contacts as a flat list (no pagination) for use in select/dropdown UI elements."
        ),
        responses={200: ContactSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=["Contact Accounts"],
        summary="List contact bank accounts",
        description=(
            "Returns a paginated list of all bank accounts belonging to the authenticated user's contacts.\n\n"
            "**Filter by contact:** `?contact={contact_id}`"
        ),
        parameters=[
            OpenApiParameter(
                "contact", OpenApiTypes.INT,
                description="Filter accounts by contact ID.",
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: ContactAccountSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Contact Accounts"],
        summary="Add a bank account to a contact",
        description=(
            "Adds a bank/wallet account to an existing contact.\n\n"
            "**Required fields:** `contact` (ID), `bank_name`, `account_name`, `account_number`\n\n"
            "**Optional fields:** `iban`\n\n"
            "**Notes:**\n"
            "- The contact must belong to the authenticated user.\n"
            "- `account_number` must be unique per bank per contact.\n"
            "- Only one `CASH` wallet is allowed per contact."
        ),
        request=ContactAccountSerializer,
        responses={
            201: ContactAccountSerializer,
            400: OpenApiResponse(description="Validation error (e.g. duplicate account number, multiple CASH wallets)."),
        },
        examples=[
            OpenApiExample(
                "Add bank account",
                request_only=True,
                value={
                    "contact": 1,
                    "bank_name": "MCB",
                    "account_name": "Current",
                    "account_number": "0987654321",
                    "iban": "",
                },
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Contact Accounts"],
        summary="Retrieve a contact account",
        responses={200: ContactAccountSerializer},
    ),
    update=extend_schema(
        tags=["Contact Accounts"],
        summary="Update a contact account (full)",
        request=ContactAccountSerializer,
        responses={200: ContactAccountSerializer},
    ),
    partial_update=extend_schema(
        tags=["Contact Accounts"],
        summary="Update a contact account (partial)",
        request=ContactAccountSerializer,
        responses={200: ContactAccountSerializer},
    ),
    destroy=extend_schema(
        tags=["Contact Accounts"],
        summary="Delete a contact account",
        responses={204: None},
    ),
)
class ContactAccountViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for bank accounts belonging to a contact.

    list     GET    /api/contact-accounts/
    create   POST   /api/contact-accounts/
    retrieve GET    /api/contact-accounts/{id}/
    update   PUT    /api/contact-accounts/{id}/
    partial  PATCH  /api/contact-accounts/{id}/
    destroy  DELETE /api/contact-accounts/{id}/

    Optional filter:  /api/contact-accounts/?contact={id}
    """
    serializer_class = ContactAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = ContactAccount.objects.filter(
            contact__user=self.request.user
        ).select_related('contact').order_by('contact__first_name', 'bank_name')

        contact_id = self.request.query_params.get('contact')
        if contact_id:
            qs = qs.filter(contact_id=contact_id)

        return qs

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.bank_name.upper() == 'CASH':
            raise ValidationError({"detail": "The system 'CASH' account cannot be modified."})
        if ContactAccount.objects.filter(user=self.request.user, first_name=instance.first_name, last_name=instance.last_name).exclude(id=instance.id).exists():
            raise ValidationError({"detail": "A contact with this name already exists."})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.bank_name.upper() == 'CASH':
            raise ValidationError({"detail": "The system 'CASH' account cannot be deleted."})
        instance.delete()

    @extend_schema(
        tags=["Contact Accounts"],
        summary="List contact accounts for dropdown",
        description=(
            "Returns the contact's bank accounts as a flat list (no pagination) for use in select/dropdown UI elements. "
            "Use `?contact={id}` to filter by a specific contact."
        ),
        parameters=[
            OpenApiParameter("contact", OpenApiTypes.INT, description="Filter by contact ID."),
        ],
        responses={200: ContactAccountSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
