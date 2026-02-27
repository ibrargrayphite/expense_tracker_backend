from rest_framework import viewsets, permissions, mixins
from tracker.models import Loan
from tracker.serializers.loan import LoanSerializer
from tracker.pagination import StandardResultsSetPagination

class LoanViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    """
    Restricted read-only access for loans. Users can only view loans.

    list     GET    /api/loans/
    retrieve GET    /api/loans/{id}/
    """
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).order_by('-created_at')