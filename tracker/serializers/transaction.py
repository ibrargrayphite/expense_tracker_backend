from rest_framework import serializers
from tracker.models import (
    InternalTransaction, Transaction, TransactionAccount, 
    TransactionSplit, Loan, Account, Contact, ContactAccount,
    ExpenseCategory, IncomeSource
)
from django.db import transaction
from django.db.models import Sum

class InternalTransactionSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source='from_account.account_name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.account_name', read_only=True)

    class Meta:
        model = InternalTransaction
        fields = (
            'id', 'from_account', 'from_account_name', 'to_account', 
            'to_account_name', 'amount', 'note', 'date', 'created_at'
        )
        read_only_fields = ('user', 'created_at')

class TransactionSplitSerializer(serializers.ModelSerializer):
    loan_details = serializers.SerializerMethodField(read_only=True)
    expense_category_name = serializers.CharField(source='expense_category.name', read_only=True)
    income_source_name = serializers.CharField(source='income_source.name', read_only=True)

    class Meta:
        model = TransactionSplit
        fields = (
            'id', 'type', 'amount', 'loan', 'loan_details', 
            'expense_category', 'expense_category_name', 
            'income_source', 'income_source_name', 'note'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user:
            self.fields['loan'].queryset = Loan.objects.filter(user=request.user)
            self.fields['expense_category'].queryset = ExpenseCategory.objects.filter(user=request.user)
            self.fields['income_source'].queryset = IncomeSource.objects.filter(user=request.user)

    def get_loan_details(self, obj):
        if obj.loan:
            return {
                "id": obj.loan.id,
                "type": obj.loan.type,
                "contact": f"{obj.loan.contact.first_name} {obj.loan.contact.last_name}"
            }
        return None

class TransactionAccountSerializer(serializers.ModelSerializer):
    splits = TransactionSplitSerializer(many=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    bank_name = serializers.CharField(source='account.bank_name', read_only=True)

    class Meta:
        model = TransactionAccount
        fields = ('id', 'account', 'account_name', 'bank_name', 'splits')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user:
            self.fields['account'].queryset = Account.objects.filter(user=request.user)

class TransactionSerializer(serializers.ModelSerializer):
    accounts = TransactionAccountSerializer(many=True)
    contact_name = serializers.SerializerMethodField(read_only=True)
    total_amount = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Transaction
        fields = (
            'id', 'contact', 'contact_name', 'contact_account', 
            'date', 'image', 'accounts', 
            'total_amount', 'created_at'
        )
        read_only_fields = ('user', 'created_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user:
            self.fields['contact'].queryset = Contact.objects.filter(user=request.user)
            self.fields['contact_account'].queryset = ContactAccount.objects.filter(contact__user=request.user)

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}"
        return None

    def get_total_amount(self, obj):
        total = TransactionSplit.objects.filter(
            transaction_account__transaction=obj
        ).aggregate(Sum('amount'))['amount__sum']
        return total or 0

    def validate(self, attrs):
        """
        Validate transaction data based on type-specific requirements.
        """
        accounts_data = attrs.get('accounts', [])
        contact = attrs.get('contact')
        contact_account = attrs.get('contact_account')

        if not accounts_data:
            raise serializers.ValidationError({"accounts": "This field is required and cannot be empty."})

        for acc_idx, acc_data in enumerate(accounts_data):
            account = acc_data.get('account')
            splits_data = acc_data.get('splits', [])

            if not splits_data:
                raise serializers.ValidationError({f"accounts[{acc_idx}].splits": "At least one split is required."})

            for split_idx, split in enumerate(splits_data):
                stype = split.get('type')
                amount = split.get('amount')
                loan = split.get('loan')
                expense_category = split.get('expense_category')
                income_source = split.get('income_source')

                # Rule enforcement based on transaction type
                if stype == 'INCOME':
                    if not income_source:
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].income_source": "Income source is required for income transactions."})
                
                elif stype == 'EXPENSE':
                    if not expense_category:
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].expense_category": "Expense category is required for expense transactions."})
                
                elif stype == 'LOAN_TAKEN' or stype == 'MONEY_LENT':
                    if not contact:
                        raise serializers.ValidationError({"contact": f"Contact is required for {stype.replace('_', ' ').title()}."})
                    if not contact_account:
                        raise serializers.ValidationError({"contact_account": f"Contact account is required for {stype.replace('_', ' ').title()}."})
                
                elif stype == 'LOAN_REPAYMENT' or stype == 'REIMBURSEMENT':
                    if not contact:
                        raise serializers.ValidationError({"contact": f"Contact is required for {stype.replace('_', ' ').title()}."})
                    if not contact_account:
                        raise serializers.ValidationError({"contact_account": f"Contact account is required for {stype.replace('_', ' ').title()}."})
                    if not loan:
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].loan": f"Loan is required for {stype.replace('_', ' ').title()}."})
                    
                    if loan and loan.contact != contact:
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].loan": "Selected loan must belong to the selected contact."})

                # Balance Check (for outgoing money)
                if stype in ['EXPENSE', 'MONEY_LENT', 'LOAN_REPAYMENT']:
                    if amount > account.balance:
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].amount": f"Insufficient balance in account '{account.account_name}'. Current balance: {account.balance}"})

                # Loan-specific validations
                if stype == 'LOAN_REPAYMENT':
                    if loan and loan.type != 'TAKEN':
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].loan": "Loan repayment can only be applied to 'Loan Taken' type loans."})
                    if loan and amount > loan.remaining_amount:
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].amount": f"Repayment amount ({amount}) exceeds remaining loan amount ({loan.remaining_amount})."})
                
                if stype == 'REIMBURSEMENT':
                    if loan and loan.type != 'LENT':
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].loan": "Reimbursement can only be applied to 'Money Lent' type loans."})
                    if loan and amount > loan.remaining_amount:
                        raise serializers.ValidationError({f"accounts[{acc_idx}].splits[{split_idx}].amount": f"Reimbursement amount ({amount}) exceeds remaining amount owed ({loan.remaining_amount})."})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        Handle nested creation of accounts and splits, and update associated records.
        """
        accounts_data = validated_data.pop('accounts')
        user = self.context['request'].user
        
        # 1. Create the main transaction
        transaction_instance = Transaction.objects.create(user=user, **validated_data)
        
        for acc_data in accounts_data:
            splits_data = acc_data.pop('splits')
            account = acc_data['account']
            
            # 2. Create TransactionAccount
            ta = TransactionAccount.objects.create(transaction=transaction_instance, account=account)
            
            for split_data in splits_data:
                stype = split_data.get('type')
                amount = split_data.get('amount')
                loan = split_data.get('loan')
                snote = split_data.get('note')
                expense_category = split_data.get('expense_category')
                income_source = split_data.get('income_source')
                
                # 3. Create/Manage Loan for TAKEN/LENT if not provided
                if not loan and stype in ['LOAN_TAKEN', 'MONEY_LENT'] and transaction_instance.contact:
                    loan_type = 'TAKEN' if stype == 'LOAN_TAKEN' else 'LENT'
                    loan = Loan.objects.create(
                        user=user,
                        contact=transaction_instance.contact,
                        type=loan_type,
                        total_amount=0,
                        remaining_amount=0,
                        description=snote
                    )

                # 4. Create TransactionSplit
                TransactionSplit.objects.create(transaction_account=ta, **split_data, loan=loan)
                
                # 5. Update Loan Balances
                if loan:
                    if stype in ['LOAN_TAKEN', 'MONEY_LENT']:
                        loan.total_amount += amount
                        loan.remaining_amount += amount
                    elif stype in ['LOAN_REPAYMENT', 'REIMBURSEMENT']:
                        loan.remaining_amount -= amount
                    
                    loan.is_closed = (loan.remaining_amount <= 0)
                    loan.save()
                
                # 6. Update Account Balance
                if stype in ['INCOME', 'LOAN_TAKEN', 'REIMBURSEMENT']:
                    account.balance += amount
                else:
                    account.balance -= amount
                account.save()
                
        return transaction_instance
