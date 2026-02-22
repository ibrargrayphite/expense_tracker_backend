from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Account, Loan, Transaction, Contact, ContactAccount, TransactionSplit
from .serializers import AccountSerializer, LoanSerializer, TransactionSerializer, UserSerializer, ContactSerializer, ContactAccountSerializer
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


@extend_schema_view(
    list=extend_schema(description='List all users', tags=['Users']),
    create=extend_schema(description='Register a new user', tags=['Users']),
    retrieve=extend_schema(description='Get user details', tags=['Users']),
    update=extend_schema(description='Update user', tags=['Users']),
    partial_update=extend_schema(description='Partially update user', tags=['Users']),
    destroy=extend_schema(description='Delete user', tags=['Users']),
)
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
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            # Handle multiple users with same email by taking the first one
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
                
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"

            subject = "Reset Your XPENSE Password"
            text_content = f"Click the link below to reset your password:\n\n{reset_url}"
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
            
            email_message = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send(fail_silently=False)
            print("EMAIL SENT")

            return Response({"detail": "Password reset link sent to your email."})
            
            # send_mail(
            #     subject,
            #     text_content,
            #     html_content,
            #     getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@xpense.com'),
            #     [email],
            #     fail_silently=False,
            # )
            # return Response({'detail': 'Password reset link sent to your email.'})
        except Exception as e:
            # Log the error in production
            print(e)
            return Response({'detail': 'An error occurred. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def reset_password(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not all([uidb64, token, new_password]):
            return Response(
                {"detail": "Invalid request."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password strength
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password has been reset successfully."})

@extend_schema_view(
    list=extend_schema(description='List all accounts for the authenticated user', tags=['Accounts']),
    create=extend_schema(description='Create a new account', tags=['Accounts']),
    retrieve=extend_schema(description='Get account details', tags=['Accounts']),
    update=extend_schema(description='Update account', tags=['Accounts']),
    partial_update=extend_schema(description='Partially update account', tags=['Accounts']),
    destroy=extend_schema(description='Delete account', tags=['Accounts']),
)
class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@extend_schema_view(
    list=extend_schema(description='List all loans for the authenticated user', tags=['Loans']),
    create=extend_schema(description='Create a new loan record', tags=['Loans']),
    retrieve=extend_schema(description='Get loan details', tags=['Loans']),
    update=extend_schema(description='Update loan', tags=['Loans']),
    partial_update=extend_schema(description='Partially update loan', tags=['Loans']),
    destroy=extend_schema(description='Delete loan', tags=['Loans']),
)
class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@extend_schema_view(
    list=extend_schema(description='List all contacts for the authenticated user', tags=['Contacts']),
    create=extend_schema(description='Create a new contact', tags=['Contacts']),
    retrieve=extend_schema(description='Get contact details', tags=['Contacts']),
    update=extend_schema(description='Update contact', tags=['Contacts']),
    partial_update=extend_schema(description='Partially update contact', tags=['Contacts']),
    destroy=extend_schema(description='Delete contact', tags=['Contacts']),
)
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

@extend_schema_view(
    list=extend_schema(description='List all transactions for the authenticated user', tags=['Transactions']),
    create=extend_schema(description='Create a new transaction (automatically updates account balance and loan amounts)', tags=['Transactions']),
    retrieve=extend_schema(description='Get transaction details', tags=['Transactions']),
    update=extend_schema(description='Update transaction', tags=['Transactions']),
    partial_update=extend_schema(description='Partially update transaction', tags=['Transactions']),
    destroy=extend_schema(description='Delete transaction (reverses account and loan updates)', tags=['Transactions']),
)
class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        import json
        instance = serializer.save(user=self.request.user)
        
        # 1. Handle Automatic Loan Creation (if applicable)
        if instance.type in ['LOAN_TAKEN', 'MONEY_LENT'] and instance.contact and not instance.loan:
            loan_type = 'TAKEN' if instance.type == 'LOAN_TAKEN' else 'LENT'
            new_loan = Loan.objects.create(
                user=instance.user,
                contact=instance.contact,
                type=loan_type,
                total_amount=0, 
                remaining_amount=0,
                description=instance.note
            )
            instance.loan = new_loan
            instance.save()

        # 2. Handle Account Splits & Balance Updates
        splits_data = self.request.data.get('splits')
        if isinstance(splits_data, str):
            try:
                splits_data = json.loads(splits_data)
            except:
                splits_data = []

        if splits_data and len(splits_data) > 0:
            for split in splits_data:
                acc_id = split.get('account')
                amt = int(split.get('amount'))
                acc = Account.objects.get(id=acc_id, user=instance.user)
                TransactionSplit.objects.create(transaction=instance, account=acc, amount=amt)
                
                # Update balance for each split account
                if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                    acc.balance += amt
                else:
                    acc.balance -= amt
                acc.save()
        elif instance.account:
            # Simple transaction (one account)
            account = instance.account
            if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                account.balance += instance.amount
            else:
                account.balance -= instance.amount
            account.save()

        # 3. Update Loan Totals
        loan = instance.loan
        if loan:
            if instance.type == 'REPAYMENT':
                loan.remaining_amount -= instance.amount
            elif instance.type == 'REIMBURSEMENT':
                loan.remaining_amount -= instance.amount
            elif instance.type == 'LOAN_TAKEN':
                loan.remaining_amount += instance.amount
                loan.total_amount += instance.amount
            elif instance.type == 'MONEY_LENT':
                loan.remaining_amount += instance.amount
                loan.total_amount += instance.amount
            
            loan.is_closed = loan.remaining_amount <= 0
            loan.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        # Reverse balance updates for all accounts involved
        splits = instance.splits.all()
        if splits.exists():
            for split in splits:
                acc = split.account
                if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                    acc.balance -= split.amount
                else:
                    acc.balance += split.amount
                acc.save()
        elif instance.account:
            account = instance.account
            if instance.type in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                account.balance -= instance.amount
            else:
                account.balance += instance.amount
            account.save()

        # Reverse loan update
        loan = instance.loan
        if loan:
            if instance.type == 'REPAYMENT':
                loan.remaining_amount += instance.amount
            elif instance.type == 'REIMBURSEMENT':
                loan.remaining_amount += instance.amount
            elif instance.type == 'LOAN_TAKEN':
                loan.remaining_amount -= instance.amount
                loan.total_amount -= instance.amount
            elif instance.type == 'MONEY_LENT':
                loan.remaining_amount -= instance.amount
                loan.total_amount -= instance.amount
            
            loan.is_closed = loan.remaining_amount <= 0
            loan.save()
        
        instance.delete()
