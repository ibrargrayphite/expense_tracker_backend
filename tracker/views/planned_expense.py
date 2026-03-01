from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from tracker.models import PlannedExpense
from tracker.serializers.planned_expense import PlannedExpenseSerializer
from tracker.pagination import StandardResultsSetPagination
from django.utils import timezone


class PlannedExpenseViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for planned expenses.

    list     GET    /api/planned-expenses/?status=pending|completed|overdue&category=<id>
    create   POST   /api/planned-expenses/
    retrieve GET    /api/planned-expenses/{id}/
    update   PUT    /api/planned-expenses/{id}/
    partial  PATCH  /api/planned-expenses/{id}/
    destroy  DELETE /api/planned-expenses/{id}/
    """
    serializer_class = PlannedExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = PlannedExpense.objects.filter(user=self.request.user)
        today = timezone.localdate()

        status = self.request.query_params.get('status')
        if status == 'completed':
            qs = qs.filter(is_completed=True)
        elif status == 'overdue':
            qs = qs.filter(is_completed=False, end_date__lt=today)
        elif status == 'pending':
            qs = qs.filter(is_completed=False, end_date__gte=today)

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)

        ordering = self.request.query_params.get('ordering', 'end_date')
        allowed_orderings = {'end_date', '-end_date', 'amount', '-amount'}
        if ordering not in allowed_orderings:
            ordering = 'end_date'

        return qs.order_by(ordering)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        is_completed = serializer.validated_data.get('is_completed')
        if is_completed:
            serializer.validated_data['completed_at'] = timezone.now()
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        """Return all non-completed planned expenses as flat list for dropdown."""
        today = timezone.localdate()
        queryset = PlannedExpense.objects.filter(
            user=request.user,
            is_completed=False
        ).order_by('end_date')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
