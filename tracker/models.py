from django.db import models
from django.contrib.auth.models import User

class Account(models.Model):
    BANK_CHOICES = [
        ('Cash', 'Cash'),
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
        ('Nayapay', 'Nayapay'),
        ('SadaPay', 'SadaPay'),
        ('Bank Alfalah', 'Bank Alfalah'),
        ('Meezan Bank', 'Meezan Bank'),
        ('HBL', 'HBL'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    bank_name = models.CharField(max_length=50, choices=BANK_CHOICES)
    account_name = models.CharField(max_length=100, help_text="To distinguish multiple accounts with same bank")
    account_number = models.CharField(max_length=50, blank=True, null=True)
    iban = models.CharField(max_length=50, blank=True, null=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_name} ({self.user.username})"

class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class ContactAccount(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='accounts')
    account_name = models.CharField(max_length=100) # e.g. "JazzCash", "Meezan"
    account_number = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"

class Loan(models.Model):
    LOAN_TYPES = [
        ('TAKEN', 'Loan Taken'),
        ('LENT', 'Money Lent'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='loans')
    person_name = models.CharField(max_length=100, blank=True, null=True) # Keep for legacy or ad-hoc
    type = models.CharField(max_length=10, choices=LOAN_TYPES)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type}: {self.person_name} - {self.total_amount}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('LOAN_TAKEN', 'Loan Taken'),
        ('MONEY_LENT', 'Money Lent'),
        ('REPAYMENT', 'Repayment (Paying back loan taken)'),
        ('REIMBURSEMENT', 'Reimbursement (Getting back money lent)'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    loan = models.ForeignKey(Loan, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    note = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='transactions/', blank=True, null=True)
    date = models.DateTimeField(default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.date:
            from django.utils import timezone
            self.date = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.type} - {self.amount}"

class TransactionSplit(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='splits')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='splits')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.transaction.type} Split: {self.account.bank_name} - {self.amount}"
