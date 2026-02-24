from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Account, Loan, Transaction

# @admin.register(Account)
# class AccountAdmin(ModelAdmin):
#     list_display = ("bank_name", "account_name", "user", "balance", "created_at")
#     list_filter = ("bank_name", "user")
#     search_fields = ("account_name", "user__username")

# @admin.register(Loan)
# class LoanAdmin(ModelAdmin):
#     list_display = ("person_name", "type", "user", "total_amount", "remaining_amount", "is_closed")
#     list_filter = ("type", "is_closed", "user")
#     search_fields = ("person_name", "user__username")

# @admin.register(Transaction)
# class TransactionAdmin(ModelAdmin):
#     list_display = ("type", "amount", "account", "user", "date", "created_at")
#     list_filter = ("type", "account", "user", "date")
#     search_fields = ("note", "user__username", "account__account_name")
#     readonly_fields = ("created_at",)
