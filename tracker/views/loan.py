from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from tracker.models import Loan
from tracker.serializers.loan import LoanSerializer
from tracker.pagination import TransactionResultsSetPagination
from tracker.filters import LoanFilter

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
    pagination_class = TransactionResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LoanFilter
    search_fields = ['contact__first_name', 'contact__last_name', 'description']
    ordering_fields = ['remaining_amount', 'created_at', 'contact__first_name']

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)