from rest_framework import viewsets, permissions
from tracker.models import Contact, ContactAccount
from tracker.serializers.contact import ContactSerializer, ContactAccountSerializer

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

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user).order_by('first_name', 'last_name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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

    def get_queryset(self):
        qs = ContactAccount.objects.filter(
            contact__user=self.request.user
        ).select_related('contact').order_by('contact__first_name', 'bank_name')

        contact_id = self.request.query_params.get('contact')
        if contact_id:
            qs = qs.filter(contact_id=contact_id)

        return qs

    def perform_create(self, serializer):
        # Ensure the submitted contact belongs to the requesting user
        contact = serializer.validated_data.get('contact')
        if contact.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not own this contact.")
        serializer.save()
