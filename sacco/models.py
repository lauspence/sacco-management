from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

# ✅ Member Model
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Balance tracking
    savings_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Savings balance
    joined_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.user.username


# ✅ Loan Model
class Loan(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Track remaining balance
    total_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Track total withdrawn
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Interest rate
    duration_months = models.IntegerField()  # Loan duration in months
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    repayment_status = models.CharField(
        max_length=20,
        choices=[('ongoing', 'Ongoing'), ('completed', 'Completed')],
        default='ongoing'
    )  # Track the repayment status
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        """ Ensure remaining balance updates properly without overriding repayments """
        print(f"Before Save - Loan ID: {self.id}, Remaining Balance: {self.remaining_balance}")

        # Only set remaining balance when first approving a loan, not during repayments or updates
        if self.status == "approved" and self._state.adding:
            self.remaining_balance = self.amount

        super().save(*args, **kwargs)

        print(f"After Save - Loan ID: {self.id}, Remaining Balance: {self.remaining_balance}")

    def calculate_interest(self):
        """ Method to calculate loan interest """
        if self.status == "approved" and self.interest_rate:
            # Interest calculation (simple interest for example)
            interest = (self.amount * self.interest_rate / 100) * self.duration_months
            return interest
        return 0

    def update_withdrawn_balance(self, amount):
        """ Method to update total withdrawn amount """
        if amount <= self.remaining_balance:
            self.total_withdrawn += amount
            self.remaining_balance -= amount
            self.save()
        else:
            raise ValueError("Withdrawal amount exceeds remaining loan balance")

    def __str__(self):
        return f"{self.member.user.username} - Loan Amount: ${self.amount} - Remaining Balance: ${self.remaining_balance} - Status: {self.status}"


# ✅ Transaction Model
class Transaction(models.Model):
    TRANSACTION_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('loan_repayment', 'Loan Repayment'),
        ('transfer', 'Transfer'),
    ]

    member = models.ForeignKey("Member", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_CHOICES, default='deposit')
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        """ Update member balance when a transaction is saved """
        if self.pk is None:  # Only update balance for new transactions
            if self.transaction_type == "deposit":
                # Adding deposit amount to member's balance
                self.member.balance += self.amount
            
            elif self.transaction_type == "withdrawal":
                # Deducting withdrawal amount from member's balance, ensuring sufficient funds
                if self.member.balance >= self.amount:
                    self.member.balance -= self.amount
                else:
                    raise ValueError("Insufficient funds for withdrawal")
            
            elif self.transaction_type == "loan_repayment":
                # Deduct loan repayment from member's balance
                if self.member.balance >= self.amount:
                    self.member.balance -= self.amount

                    # Find an ongoing loan to apply the repayment
                    loan = Loan.objects.filter(member=self.member, repayment_status="ongoing").first()
                    if loan:
                        LoanRepayment.objects.create(loan=loan, amount_paid=self.amount)
                    else:
                        raise ValueError("No ongoing loan found for repayment.")

                else:
                    raise ValueError("Insufficient funds for loan repayment")

            elif self.transaction_type == "transfer":
                # Transfer logic handled separately, no balance change here
                pass

            # Save the member's updated balance
            self.member.save()

        # Ensure the transaction record is saved
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.user.username} - {self.transaction_type} - Ksh {self.amount}"


# ✅ Loan Repayment Model
class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """ Deduct repayment from remaining loan balance and update status """
        print(f"Before Repayment - Loan ID: {self.loan.id}, Remaining Balance: {self.loan.remaining_balance}")

        if self.loan.remaining_balance < self.amount_paid:
            raise ValueError("Payment exceeds remaining balance.")

        # Deduct the repayment
        self.loan.remaining_balance -= self.amount_paid
        print(f"After Deduction - New Remaining Balance: {self.loan.remaining_balance}")

        # Mark loan as completed if fully paid
        if self.loan.remaining_balance == 0:
            self.loan.repayment_status = "completed"
            self.loan.status = "approved"

        self.loan.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Loan ID: {self.loan.id} - Amount Paid: {self.amount_paid} - Date: {self.date_paid}"
    

class Share(models.Model):
    member = models.OneToOneField("Member", on_delete=models.CASCADE)
    shares_owned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_investment = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def buy_shares(self, amount, price_per_share):
        num_shares = Decimal(amount) / Decimal(price_per_share)
        self.shares_owned += num_shares
        self.total_investment += amount
        self.save()

    def transfer_shares(self, recipient, num_shares):
        if self.shares_owned >= num_shares:
            self.shares_owned -= num_shares
            recipient.shares_owned += num_shares
            self.save()
            recipient.save()
            return True
        return False
