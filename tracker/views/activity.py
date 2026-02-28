from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from tracker.models import Transaction, InternalTransaction
from tracker.serializers.transaction import TransactionSerializer, InternalTransactionSerializer
from tracker.filters import TransactionFilter, InternalTransactionFilter
from tracker.pagination import TransactionResultsSetPagination
from django.db.models import Sum

class ActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        tx_type = request.query_params.get('type')
        fetch_transactions = not tx_type or tx_type != 'TRANSFER'
        fetch_internal = not tx_type or tx_type == 'TRANSFER'

        tx_qs = Transaction.objects.none()
        if fetch_transactions:
            tx_qs = Transaction.objects.filter(user=user).annotate(
                amount=Sum('accounts__splits__amount')
            ).order_by('-date', '-created_at')
            tx_qs = TransactionFilter(request.query_params, queryset=tx_qs).qs

        it_qs = InternalTransaction.objects.none()
        if fetch_internal:
            it_qs = InternalTransaction.objects.filter(user=user).order_by('-date', '-created_at')
            it_qs = InternalTransactionFilter(request.query_params, queryset=it_qs).qs

        tx_data = []
        if fetch_transactions:
            tx_data = TransactionSerializer(tx_qs, many=True, context={'request': request}).data
            
        it_data = []
        if fetch_internal:
            it_data = InternalTransactionSerializer(it_qs, many=True, context={'request': request}).data
            for item in it_data:
                item['is_internal'] = True
                item['type'] = 'TRANSFER'
                
        combined = tx_data + it_data
        
        ordering = request.query_params.get('ordering', '-date')
        sort_field = ordering.lstrip('-')
        reverse = ordering.startswith('-')
        
        if sort_field not in ['date', 'amount']:
            sort_field = 'date'
            
        def get_sort_key(item, field):
            val = item.get(field)
            if field == 'amount':
                return float(val or 0)
            return val or ''
            
        combined.sort(key=lambda x: (get_sort_key(x, sort_field), x.get('created_at', '')), reverse=reverse)
        
        paginator = TransactionResultsSetPagination()
        paginated_data = paginator.paginate_queryset(combined, request, view=self)
        if paginated_data is not None:
            return paginator.get_paginated_response(paginated_data)
            
        return Response(combined)
