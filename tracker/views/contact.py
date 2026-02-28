from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from tracker.models import Contact, ContactAccount
from tracker.serializers.contact import ContactSerializer, ContactAccountSerializer
from tracker.pagination import StandardResultsSetPagination
from tracker.filters import ContactFilter
from rest_framework.decorators import action
from rest_framework.response import Response


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
    ordering_fields = ['first_name', 'last_name', 'accounts_count']
    ordering = ['first_name', 'last_name']

    def get_queryset(self):
        from django.db.models import Count
        return Contact.objects.filter(user=self.request.user).annotate(
            accounts_count=Count('accounts')
        ).order_by('first_name', 'last_name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
