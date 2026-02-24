from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Account, ExpenseCategory

@receiver(post_save, sender=User)
def create_initial_user_data(sender, instance, created, **kwargs):
    if created:
        # Create default cash wallet
        Account.objects.get_or_create(
            user=instance,
            bank_name="CASH",
            account_name="Cash Wallet",
            account_number="CASH-001",
            balance=0
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
