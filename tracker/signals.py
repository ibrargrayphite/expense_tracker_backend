from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Account

@receiver(post_save, sender=User)
def create_cash_wallet(sender, instance, created, **kwargs):
    if created:
        # Only create when a new user is created
        Account.objects.create(
            user=instance,
            bank_name="CASH",
            account_name="Cash Wallet",
            account_number="CASH-001",
            balance=0
        )