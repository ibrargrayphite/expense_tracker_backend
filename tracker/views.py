from rest_framework import viewsets, status, permissions, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import (
    Account, Loan, Transaction, Contact, ContactAccount, 
    TransactionAccount, TransactionSplit, ExpenseCategory, IncomeSource,
    InternalTransaction
)
from .serializers import (
    AccountSerializer, LoanSerializer, TransactionSerializer, UserSerializer, 
    ContactSerializer, ContactAccountSerializer, InternalTransactionSerializer,
    ExpenseCategorySerializer, IncomeSourceSerializer
)
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except ImportError:
    SendGridAPIClient = None

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.action in ['create', 'forgot_password', 'reset_password']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        if User.objects.filter(username=username).exists():
            first_name = request.data.get('first_name', '').lower()
            last_name = request.data.get('last_name', '').lower()
            
            import random
            import string
            
            base = f"{first_name}{last_name}"
            if not base:
                base = "user"
            
            suggestion = ""
            while True:
                suffix = ''.join(random.choices(string.digits, k=3))
                suggestion = f"{base}{suffix}"
                if not User.objects.filter(username=suggestion).exists():
                    break
            
            return Response({
                'username': ['A user with that username already exists.'],
                'suggestion': suggestion
            }, status=status.HTTP_400_BAD_REQUEST)
            
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def forgot_password(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
                
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"

            subject = "Reset Your XPENSE Password"
            html_content = f"""
                                <p>Hello,</p>
                                <p>Click the button below to reset your password:</p>
                                <p>
                                    <a href="{reset_url}" style="padding:10px 15px;background:#4f46e5;color:white;text-decoration:none;border-radius:5px;">
                                        Reset Password
                                    </a>
                                </p>
                                <p>If you didn’t request this, you can ignore this email.</p>
                            """
            
            if SendGridAPIClient and getattr(settings, 'SENDGRID_API_KEY', None):
                email_message = Mail(
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to_emails=email,
                    subject=subject,
                    html_content=html_content
                )
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                sg.client.mail.send.post(request_body=email_message.get())
            else:
                send_mail(
                    subject,
                    "Reset your password here: " + reset_url,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_content
                )

            return Response({"detail": "Password reset link sent to your email."})
        except Exception as e:
            print(e)
            return Response({'detail': 'An error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def reset_password(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not all([uidb64, token, new_password]):
            return Response({"detail": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password has been reset successfully."})

class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class IncomeSourceViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeSourceSerializer
    def get_queryset(self):
        return IncomeSource.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ContactAccountViewSet(viewsets.ModelViewSet):
    serializer_class = ContactAccountSerializer
    def get_queryset(self):
        return ContactAccount.objects.filter(contact__user=self.request.user)

class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer
    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TransactionViewSet(mixins.CreateModelMixin, 
                         mixins.ListModelMixin, 
                         mixins.RetrieveModelMixin, 
                         mixins.DestroyModelMixin, 
                         viewsets.GenericViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user).order_by('-date', '-created_at')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=f"{end_date} 23:59:59")
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        from decimal import Decimal
        from django.db.models import F
        
        instance = serializer.save(user=self.request.user)
        accounts_data = self.request.data.get('accounts', [])
        
        for acc_data in accounts_data:
            account_id = acc_data.get('account')
            splits_data = acc_data.get('splits', [])
            
            ta = TransactionAccount.objects.create(
                transaction=instance,
                account_id=account_id
            )
            
            for split_data in splits_data:
                stype = split_data.get('type')
                amount = Decimal(str(split_data.get('amount')))
                loan_id = split_data.get('loan')
                
                loan = None
                if loan_id:
                    loan = Loan.objects.get(id=loan_id, user=self.request.user)
                elif stype in ['LOAN_TAKEN', 'MONEY_LENT'] and instance.contact:
                    loan_type = 'TAKEN' if stype == 'LOAN_TAKEN' else 'LENT'
                    loan = Loan.objects.filter(
                        user=self.request.user, contact=instance.contact, 
                        type=loan_type, is_closed=False
                    ).first()
                    
                    if not loan:
                        loan = Loan.objects.create(
                            user=self.request.user,
                            contact=instance.contact,
                            type=loan_type,
                            total_amount=0,
                            remaining_amount=0,
                            description=f"Auto-generated from transaction on {instance.date}"
                        )

                TransactionSplit.objects.create(
                    transaction_account=ta,
                    type=stype,
                    amount=amount,
                    loan=loan
                )
                
                if loan:
                    if stype in ['LOAN_TAKEN', 'MONEY_LENT']:
                        loan.total_amount += amount
                        loan.remaining_amount += amount
                    elif stype in ['LOAN_REPAYMENT', 'REIMBURSEMENT']:
                        loan.remaining_amount -= amount
                    
                    loan.is_closed = loan.remaining_amount <= 0
                    loan.save()
                
                acc = Account.objects.filter(id=account_id, user=self.request.user)
                if stype in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                    acc.update(balance=F('balance') + amount)
                else:
                    acc.update(balance=F('balance') - amount)

    @transaction.atomic
    def perform_destroy(self, instance):
        for ta in instance.accounts.all():
            account = ta.account
            for split in ta.splits.all():
                if split.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                    account.balance -= split.amount
                else:
                    account.balance += split.amount
                account.save()
                
                if split.loan:
                    loan = split.loan
                    if split.type in ['LOAN_TAKEN', 'MONEY_LENT']:
                        loan.total_amount -= split.amount
                        loan.remaining_amount -= split.amount
                    elif split.type in ['LOAN_REPAYMENT', 'REIMBURSEMENT']:
                        loan.remaining_amount += split.amount
                    
                    loan.is_closed = loan.remaining_amount <= 0
                    loan.save()
        instance.delete()

class InternalTransactionViewSet(mixins.CreateModelMixin, 
                                 mixins.ListModelMixin, 
                                 mixins.RetrieveModelMixin, 
                                 mixins.DestroyModelMixin, 
                                 viewsets.GenericViewSet):
    serializer_class = InternalTransactionSerializer

    def get_queryset(self):
        return InternalTransaction.objects.filter(user=self.request.user).order_by('-date', '-created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        from django.db.models import F
        instance = serializer.save(user=self.request.user)
        Account.objects.filter(id=instance.from_account.id).update(balance=F('balance') - instance.amount)
        Account.objects.filter(id=instance.to_account.id).update(balance=F('balance') + instance.amount)

    @transaction.atomic
    def perform_destroy(self, instance):
        from django.db.models import F
        Account.objects.filter(id=instance.from_account.id).update(balance=F('balance') + instance.amount)
        Account.objects.filter(id=instance.to_account.id).update(balance=F('balance') - instance.amount)
        instance.delete()
