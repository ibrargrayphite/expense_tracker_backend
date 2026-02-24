from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models import Q, F
from django.core.exceptions import ValidationError

class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    bank_name = models.CharField(max_length=5)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    iban = models.CharField(max_length=50, blank=True, null=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, validators=[MinValueValidator(Decimal('0.00'))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["bank_name"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "account_number"],
                name="unique_account_per_user"
            )
        ]

    def __str__(self):
        return f"{self.bank_name} - {self.account_name} - {self.account_number}"

class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone1 = models.CharField(max_length=20)
    phone2 = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["first_name"]),
            models.Index(fields=["last_name"]),
            models.Index(fields=["phone1"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class ContactAccount(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='accounts')
    bank_name = models.CharField(max_length=5)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    iban = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_name} - {self.account_number}"

class InternalTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='internal_transactions')
    from_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='outgoing_internal_transactions')
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='incoming_internal_transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    note = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["from_account"]),
            models.Index(fields=["to_account"]),
        ]

        constraints = [
            models.CheckConstraint(
                check=~Q(from_account=F("to_account")),
                name="prevent_self_transfer"
            )
        ]

    def __str__(self):
        return f"Internal Transaction: {self.from_account.bank_name} - {self.to_account.bank_name} - {self.amount}"

    def clean(self):
        if self.from_account.user != self.user:
            raise ValidationError("From account invalid.")

        if self.to_account.user != self.user:
            raise ValidationError("To account invalid.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class LoanType(models.TextChoices):
    TAKEN = "TAKEN", "Loan Taken"
    LENT = "LENT", "Money Lent"

class Loan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='loans')
    type = models.CharField(max_length=10, choices=LoanType.choices)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    description = models.TextField(blank=True, null=True)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_closed"]),
            models.Index(fields=["contact"]),
            models.Index(fields=["type"]),
        ]

        constraints = [
            models.CheckConstraint(
                check=Q(remaining_amount__lte=F("total_amount")),
                name="remaining_not_more_than_total"
            ),
            models.CheckConstraint(
                check=Q(remaining_amount__gte=0),
                name="remaining_amount_positive"
            )
        ]

    def __str__(self):
        return f"{self.type}: {self.contact.first_name} {self.contact.last_name} - {self.total_amount}"

class TransactionType(models.TextChoices):
    INCOME = "INCOME", "Income"
    EXPENSE = "EXPENSE", "Expense"
    LOAN_TAKEN = "LOAN_TAKEN", "Loan Taken"
    MONEY_LENT = "MONEY_LENT", "Money Lent"
    LOAN_REPAYMENT = "LOAN_REPAYMENT", "Loan Repayment"
    REIMBURSEMENT = "REIMBURSEMENT", "Reimbursement"

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True, related_name='transactions')
    contact_account = models.ForeignKey(ContactAccount, on_delete=models.CASCADE, null=True, blank=True, related_name='received_transactions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, null=True, blank=True, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    note = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='transactions/', blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["account", "date"]),
            models.Index(fields=["user", "type", "date"]),
            models.Index(fields=["contact"]),
            models.Index(fields=["loan"]),
            models.Index(fields=["type"]),
        ]



    def __str__(self):
        return f"{self.type} - {self.amount}"

    def clean(self):
        if self.account.user != self.user:
            raise ValidationError("Account does not belong to user.")

        if self.contact and self.contact.user != self.user:
            raise ValidationError("Contact does not belong to user.")

        if self.loan and self.loan.user != self.user:
            raise ValidationError("Loan does not belong to user.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
