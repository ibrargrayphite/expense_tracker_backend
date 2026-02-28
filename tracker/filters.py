import django_filters
from tracker.models import Transaction, Loan, Account, Contact, InternalTransaction
from django.db.models import Sum, Count

class ContactFilter(django_filters.FilterSet):
    net_balance = django_filters.CharFilter(method='filter_net_balance')

    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'phone1']
        
    def filter_net_balance(self, queryset, name, value):
        from django.db.models import Sum, Q, F, DecimalField
        from django.db.models.functions import Coalesce
        from decimal import Decimal

        queryset = queryset.annotate(
            total_lent=Coalesce(
                Sum('loans__remaining_amount', filter=Q(loans__type='LENT')),
                Decimal('0.0'),
                output_field=DecimalField()
            ),
            total_loaned=Coalesce(
                Sum('loans__remaining_amount', filter=Q(loans__type='TAKEN')),
                Decimal('0.0'),
                output_field=DecimalField()
            )
        ).annotate(
            annotated_net_balance=F('total_lent') - F('total_loaned')
        )

        if value == 'POSITIVE':
            return queryset.filter(annotated_net_balance__gt=0)
        if value == 'NEGATIVE':
            return queryset.filter(annotated_net_balance__lt=0)
        if value == 'SETTLED':
            return queryset.filter(annotated_net_balance=0)
            
        return queryset

class TransactionFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name="date", lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name="date", lookup_expr='lte')
    type = django_filters.CharFilter(method='filter_type')
    account = django_filters.NumberFilter(method='filter_account')
    search = django_filters.CharFilter(method='filter_search')
    min_amount = django_filters.NumberFilter(method='filter_min_amount')
    max_amount = django_filters.NumberFilter(method='filter_max_amount')
    expense_category = django_filters.NumberFilter(field_name='accounts__splits__expense_category_id')
    income_source = django_filters.NumberFilter(field_name='accounts__splits__income_source_id')

    class Meta:
        model = Transaction
        fields = ['start_date', 'end_date', 'type', 'account', 'contact']
        
    def filter_type(self, queryset, name, value):
        from django.db.models import Q
        if value == 'TRANSFER':
            return queryset.filter(internal_transaction__isnull=False)
        return queryset.filter(accounts__splits__type=value)
        
    def filter_account(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(accounts__account_id=value) |
            Q(internal_transaction__from_account_id=value) |
            Q(internal_transaction__to_account_id=value)
        ).distinct()
        
    def filter_min_amount(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(amount__gte=value)
        )

    def filter_max_amount(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(amount__lte=value)
        )
        
    def filter_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(accounts__splits__note__icontains=value) |
            Q(contact__first_name__icontains=value) |
            Q(contact__last_name__icontains=value) |
            Q(internal_transaction__note__icontains=value)
        ).distinct()

class InternalTransactionFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name="date", lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name="date", lookup_expr='lte')
    account = django_filters.NumberFilter(method='filter_account')
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = InternalTransaction
        fields = ['start_date', 'end_date', 'account']

    def filter_account(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(Q(from_account_id=value) | Q(to_account_id=value))

    def filter_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(note__icontains=value)
        ).distinct()

class LoanFilter(django_filters.FilterSet):
    min_amount = django_filters.NumberFilter(field_name="remaining_amount", lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name="remaining_amount", lookup_expr='lte')
    status = django_filters.CharFilter(method='filter_status')
    
    class Meta:
        model = Loan
        fields = ['type', 'min_amount', 'max_amount', 'contact', 'remaining_amount']
        
    def filter_status(self, queryset, name, value):
        if value == 'ACTIVE':
            return queryset.filter(is_closed=False)
        if value == 'CLOSED':
            return queryset.filter(is_closed=True)
        return queryset

class AccountFilter(django_filters.FilterSet):
    bank_name = django_filters.CharFilter(lookup_expr='iexact')
    min_balance = django_filters.NumberFilter(field_name="balance", lookup_expr='gte')
    max_balance = django_filters.NumberFilter(field_name="balance", lookup_expr='lte')
    
    class Meta:
        model = Account
        fields = ['bank_name', 'min_balance', 'max_balance']
