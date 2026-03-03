from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import (
    Account, ExpenseCategory, TransactionAccount,
    Transaction, TransactionSplit, Loan, InternalTransaction, ContactAccount, Contact,
    PlannedExpense
)
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_initial_user_data(sender, instance, created, **kwargs):
    if created:
        # Create default cash wallet
        Account.objects.get_or_create(
            user=instance,
            bank_name="CASH",
            account_name="Cash Wallet",
            defaults={"account_number": "Physical Cash & Wallets", "balance": 0}
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
        logger.debug("Signal: Default data created for user %s", instance.pk)

@receiver(post_delete, sender=TransactionAccount)
def delete_orphaned_transaction(sender, instance, **kwargs):
    """
    When a TransactionAccount is deleted (e.g. because its Account was deleted),
    we want to delete the parent Transaction as well.
    """
    try:
        if instance.transaction:
            instance.transaction.delete()
            logger.debug("Signal: Transaction %s deleted for user %s", instance.pk, instance.user_id)
    except (Transaction.DoesNotExist, Exception):
        logger.error("Signal: Transaction %s not found for user %s", instance.pk, instance.user_id)
        pass

@receiver(post_save, sender=Contact)
def create_contact_account(sender, instance, created, **kwargs):
    if created:
        ContactAccount.objects.create(
            contact=instance,
            bank_name="CASH",
            account_name=f"{instance.first_name} {instance.last_name}",
            account_number="Physical Cash",
        )
        logger.debug("Signal: Physical Cash Contact account created for user %s", instance.user_id)


# ── Cache Invalidation ────────────────────────────────────────────────────────

from tracker.cache import (
    invalidate_user_transactions,
    invalidate_user_contacts,
    invalidate_user_accounts,
    invalidate_user_loans,
    invalidate_user_planned_expenses,
)

@receiver([post_save, post_delete], sender=Transaction)
def on_transaction_change(sender, instance, **kwargs):
    invalidate_user_transactions(instance.user_id)
    logger.debug("Signal: Transaction %s changed for user %s", instance.pk, instance.user_id)

@receiver([post_save, post_delete], sender=InternalTransaction)
def on_internal_transaction_change(sender, instance, **kwargs):
    invalidate_user_transactions(instance.user_id)
    logger.debug("Signal: InternalTransaction %s changed for user %s", instance.pk, instance.user_id)

@receiver([post_save, post_delete], sender=Account)
def on_account_change(sender, instance, **kwargs):
    # Accounts surface inside transaction data too — bust both
    invalidate_user_accounts(instance.user_id)
    logger.debug("Signal: Account %s changed for user %s", instance.pk, instance.user_id)

@receiver([post_save, post_delete], sender=Contact)
def on_contact_change(sender, instance, **kwargs):
    invalidate_user_contacts(instance.user_id)
    logger.debug("Signal: Contact %s changed for user %s", instance.pk, instance.user_id)

@receiver([post_save, post_delete], sender=Loan)
def on_loan_change(sender, instance, **kwargs):
    invalidate_user_loans(instance.user_id)
    logger.debug("Signal: Loan %s changed for user %s", instance.pk, instance.user_id)

@receiver([post_save, post_delete], sender=PlannedExpense)
def on_planned_expense_change(sender, instance, **kwargs):
    invalidate_user_planned_expenses(instance.user_id)
    logger.debug("Signal: PlannedExpense %s changed for user %s", instance.pk, instance.user_id)

