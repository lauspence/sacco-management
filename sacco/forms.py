from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Member, Loan, Transaction, LoanRepayment

# User Registration Form
class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Encrypt password
        if commit:
            user.save()
        return user


# Member Registration Form (Links to User)
class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['phone']


# Loan Application Form (Automatically assigns logged-in user)
class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['amount', 'interest_rate', 'duration_months']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)  # Pass request to auto-assign member
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        loan = super().save(commit=False)
        if self.request:
            loan.member = self.request.user.member  # Auto-assign logged-in member
        if commit:
            loan.save()
        return loan


# Transaction Form (Automatically assigns logged-in user)
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'transaction_type']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        transaction = super().save(commit=False)
        if self.request:
            transaction.member = self.request.user.member  # Auto-assign logged-in member
        if commit:
            transaction.save()
        return transaction


class LoanRepaymentForm(forms.ModelForm):
    ACCOUNT_CHOICES = [
        ("wallet", "Wallet"),
        ("savings", "Savings Account"),
    ]
    
    account = forms.ChoiceField(choices=ACCOUNT_CHOICES, widget=forms.Select(attrs={"class": "form-control"}))

    class Meta:
        model = LoanRepayment
        fields = ["loan", "amount_paid", "account"]


class FundTransferForm(forms.Form):
    ACCOUNT_CHOICES = [
        ("wallet", "Wallet"),
        ("savings", "Savings"),
    ]

    from_account = forms.ChoiceField(choices=ACCOUNT_CHOICES, widget=forms.Select(attrs={"class": "form-control"}))
    to_account = forms.ChoiceField(choices=ACCOUNT_CHOICES, widget=forms.Select(attrs={"class": "form-control"}))
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=1, 
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get("from_account")
        to_account = cleaned_data.get("to_account")

        if from_account == to_account:
            raise ValidationError("You cannot transfer funds to the same account.")

        return cleaned_data