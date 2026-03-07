from rest_framework import viewsets, permissions
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from tracker.models import PlannedExpense
from tracker.serializers.planned_expense import PlannedExpenseSerializer
from tracker.pagination import StandardResultsSetPagination
from django.utils import timezone

logger = logging.getLogger(__name__)

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
        qs = PlannedExpense.objects.filter(user=self.request.user).select_related('category')
        now = timezone.now()

        status = self.request.query_params.get('status')
        if status == 'completed':
            qs = qs.filter(is_completed=True)
        elif status == 'overdue':
            qs = qs.filter(is_completed=False, end_date__lt=now)
        elif status == 'pending':
            qs = qs.filter(is_completed=False, end_date__gte=now)

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

    def list(self, request, *args, **kwargs):
        from django.core.cache import cache
        from tracker.cache import planned_expenses_list_key, CACHE_TTL

        _FILTER_PARAMS = {'status', 'category', 'ordering', 'page'}
        has_filters = any(request.query_params.get(k) for k in _FILTER_PARAMS)

        if not has_filters:
            cache_key = planned_expenses_list_key(request.user.id)
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Planned expenses cache HIT for user %s", request.user.id)
                return Response(cached)
            logger.debug("Planned expenses cache MISS for user %s", request.user.id)

        response = super().list(request, *args, **kwargs)

        if not has_filters:
            logger.debug("Planned expenses cache SET for user %s", request.user.id)
            cache.set(cache_key, response.data, CACHE_TTL)

        return response


    def perform_update(self, serializer):
        is_completed = serializer.validated_data.get('is_completed')
        if is_completed:
            serializer.validated_data['completed_at'] = timezone.now()
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        """Return all non-completed planned expenses as flat list for dropdown."""
        queryset = PlannedExpense.objects.filter(
            user=request.user,
            is_completed=False
        ).order_by('end_date')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
