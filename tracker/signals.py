from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import (
    Account, ExpenseCategory, TransactionAccount, 
    Transaction, TransactionSplit, Loan, InternalTransaction
)

@receiver(post_save, sender=User)
def create_initial_user_data(sender, instance, created, **kwargs):
    if created:
        # Create default cash wallet
        Account.objects.get_or_create(
            user=instance,
            bank_name="CASH",
            account_name="Cash Wallet",
            defaults={"account_number": "CASH-001", "balance": 0}
        )
    
        DEFAULT_EXPENSE_CATEGORIES = [
            "Food",
            "Transportation",
            "Utilities",
            "Health",
            "Entertainment",
            "Education",
            "Rent / Mortgage",
            "Shopping",
            "Travel",
            "Gifts / Donations",
            "Subscriptions",
            "Pet Care",
            "Personal Care",
            "Taxes / Fees",
            "Miscellaneous"
        ]

        for name in DEFAULT_EXPENSE_CATEGORIES:
            ExpenseCategory.objects.get_or_create(user=instance, name=name)

@receiver(post_delete, sender=TransactionAccount)
def delete_orphaned_transaction(sender, instance, **kwargs):
    """
    When a TransactionAccount is deleted (e.g. because its Account was deleted),
    we want to delete the parent Transaction as well.
    """
    try:
        if instance.transaction:
            instance.transaction.delete()
    except (Transaction.DoesNotExist, Exception):
        pass
