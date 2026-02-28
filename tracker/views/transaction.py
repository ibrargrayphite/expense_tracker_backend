from rest_framework import viewsets, permissions, mixins
from rest_framework.validators import ValidationError
from rest_framework import status
from django.db import transaction
from django.http import HttpResponse
from tracker.models import InternalTransaction, Transaction, TransactionAccount, TransactionSplit, Loan, Account
from tracker.serializers.transaction import InternalTransactionSerializer, TransactionSerializer
from tracker.pagination import TransactionResultsSetPagination
import openpyxl
from openpyxl.styles import Font, Alignment
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from tracker.filters import TransactionFilter, InternalTransactionFilter

class TransactionViewSet(mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    """
    Create and Read for transactions.

    list     GET    /api/transactions/
    create   POST   /api/transactions/
    retrieve GET    /api/transactions/{id}/
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TransactionResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TransactionFilter
    search_fields = ['contact__first_name', 'contact__last_name', 'accounts__splits__note', 'accounts__account__account_name', 'accounts__account__bank_name']
    ordering_fields = ['date', 'created_at', 'amount']
    # Default ordering is handled directly in get_queryset()

    from rest_framework.decorators import action

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        user = request.user
        
        # Get date filter params if any
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Fetch Transactions
        tx_qs = Transaction.objects.filter(user=user).prefetch_related(
            'accounts__account', 
            'accounts__splits',
            'contact',
            'contact_account'
        )
        if start_date: tx_qs = tx_qs.filter(date__gte=start_date)
        if end_date: tx_qs = tx_qs.filter(date__lte=end_date)
        tx_qs = tx_qs.order_by('-date', '-created_at')

        # Fetch Internal Transactions
        it_qs = InternalTransaction.objects.filter(user=user).select_related('from_account', 'to_account')
        if start_date: it_qs = it_qs.filter(date__gte=start_date)
        if end_date: it_qs = it_qs.filter(date__lte=end_date)
        it_qs = it_qs.order_by('-date', '-created_at')

        # Create Workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"

        # Define Headers
        headers = ["Date", "From", "To", "Type", "Amount", "Category", "Note"]
        ws.append(headers)

        # Style Headers
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

        # Combine and Sort
        all_data = []
        
        # Format Internal Transactions
        for it in it_qs:
            all_data.append({
                'date': it.date,
                'created_at': it.created_at,
                'from': f"{it.from_account.account_name} - {it.from_account.bank_name} - {it.from_account.account_number}",
                'to': f"{it.to_account.account_name} - {it.to_account.bank_name} - {it.to_account.account_number}",
                'type': "Transfer",
                'amount': float(it.amount),
                'category': "-",
                'note': it.note or "-"
            })

        # Format Regular Transactions
        for tx in tx_qs:
            total_amt = tx.accounts.aggregate(total=Sum('splits__amount'))['total'] or 0
            
            # Logic for From/To
            from_display = "-"
            to_display = "-"
            
            # Get details from first split for type/category
            first_split = None
            for acc in tx.accounts.all():
                if acc.splits.exists():
                    first_split = acc.splits.first()
                    break
            
            tx_type = first_split.type if first_split else "-"
            category = "-"
            if first_split:
                if first_split.expense_category: category = first_split.expense_category.name
                elif first_split.income_source: category = first_split.income_source.name

            user_accounts = ", ".join([f"{acc.account.account_name} - {acc.account.bank_name} - {acc.account.account_number}" for acc in tx.accounts.all()])
            contact_acc = "-"
            if tx.contact_account:
                contact_acc = f"{tx.contact_account.account_name} - {tx.contact_account.bank_name} - {tx.contact_account.account_number}"
            elif tx.contact:
                contact_acc = f"{tx.contact.first_name} {tx.contact.last_name}"

            if tx_type == 'EXPENSE':
                from_display = user_accounts
                to_display = "-"
            elif tx_type == 'INCOME':
                from_display = "-"
                to_display = user_accounts
            elif tx_type in ['LOAN_TAKEN', 'REIMBURSEMENT']:
                from_display = contact_acc
                to_display = user_accounts
            elif tx_type in ['LOAN_REPAYMENT', 'MONEY_LENT']:
                from_display = user_accounts
                to_display = contact_acc

            all_data.append({
                'date': tx.date,
                'created_at': tx.created_at,
                'from': from_display,
                'to': to_display,
                'type': tx_type.replace('_', ' ').title(),
                'amount': float(total_amt),
                'category': category,
                'note': first_split.note if first_split else "-"
            })

        # Sort combined data by date (newest first)
        all_data.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)

        # Append to Sheet
        for row in all_data:
            ws.append([
                row['date'].strftime("%Y-%m-%d %H:%M"),
                row['from'],
                row['to'],
                row['type'],
                row['amount'],
                row['category'],
                row['note']
            ])

        # Auto-adjust column width
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws.column_dimensions[column_letter].width = max_length + 2

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=transactions.xlsx'
        wb.save(response)
        return response

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).annotate(
            amount=Sum('accounts__splits__amount')
        ).order_by('-date', '-created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        try:
            serializer.save()
        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError({'detail': str(e)})


class InternalTransactionViewSet(mixins.CreateModelMixin,
                                 mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 viewsets.GenericViewSet):
    """
    Create and Read for internal transfers.

    list     GET    /api/internal-transactions/
    create   POST   /api/internal-transactions/
    retrieve GET    /api/internal-transactions/{id}/
    """
    serializer_class = InternalTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TransactionResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = InternalTransactionFilter
    search_fields = ['note', 'from_account__account_name', 'to_account__account_name']
    ordering_fields = ['date', 'created_at', 'amount']

    def get_queryset(self):
        return InternalTransaction.objects.filter(
            user=self.request.user
        ).order_by('-date', '-created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        from django.db.models import F
        instance = serializer.save(user=self.request.user)
        
        # Update balances
        Account.objects.filter(id=instance.from_account.id).update(balance=F('balance') - instance.amount)
        Account.objects.filter(id=instance.to_account.id).update(balance=F('balance') + instance.amount)
