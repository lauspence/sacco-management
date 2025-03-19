from django.db import models
from django.contrib.auth.models import User

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
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  
    duration_months = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        """ Set remaining balance when loan is approved """
        if self.status == "approved" and self.remaining_balance == 0:
            self.remaining_balance = self.amount  # Initialize remaining balance
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.user.username} - ${self.amount} - {self.status}"

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
    description = models.CharField(max_length=255, blank=True, null=True)  # ✅ Added description for transfers

    def save(self, *args, **kwargs):
        """ ✅ Update member balance when a transaction is saved """
        if self.pk is None:  # Only update balance for new transactions
            if self.transaction_type == "deposit":
                self.member.balance += self.amount
            
            elif self.transaction_type == "withdrawal":
                if self.member.balance >= self.amount:
                    self.member.balance -= self.amount
                else:
                    raise ValueError("Insufficient funds for withdrawal")
            
            elif self.transaction_type == "loan_repayment":
                if self.member.balance >= self.amount:
                    self.member.balance -= self.amount
                else:
                    raise ValueError("Insufficient funds for loan repayment")

            elif self.transaction_type == "transfer":
                # ✅ Ensure transfer logic is handled in the view (not here)
                pass

            self.member.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.user.username} - {self.transaction_type} - ${self.amount}"


# ✅ Loan Repayment Model
class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """ Deduct repayment from remaining loan balance """
        if self.loan.remaining_balance >= self.amount_paid:
            self.loan.remaining_balance -= self.amount_paid
            self.loan.save()
        else:
            raise ValueError("Payment exceeds remaining balance.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.loan.member.user.username} - Paid: ${self.amount_paid} - Remaining: ${self.loan.remaining_balance}"
