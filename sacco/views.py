import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils.timezone import now, timedelta
from django.db.models import Count, Sum
from .forms import *
from .models import Member, Loan, Transaction, LoanRepayment 
from django.http import JsonResponse


# ✅ Function to check if the user is an admin
def is_admin(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()


# ✅ Admin Loan Approval Page
@login_required(login_url='/login/')
@user_passes_test(is_admin, login_url='/login/')
def loan_approval(request):
    pending_loans = Loan.objects.filter(status="pending")
    return render(request, "sacco/admin_loan_approval.html", {"pending_loans": pending_loans})


# ✅ Admin Processing Loan Requests
@login_required(login_url='/login/')
@user_passes_test(is_admin, login_url='/login/')
def process_loan(request, loan_id, action):
    loan = get_object_or_404(Loan, id=loan_id)

    if action == "approve":
        loan.status = "approved"
        messages.success(request, f"Loan for {loan.member.user.username} has been approved.")
    elif action == "reject":
        loan.status = "rejected"
        messages.error(request, f"Loan for {loan.member.user.username} has been rejected.")

    loan.reviewed_by = request.user
    loan.save()
    return redirect("loan_approval")


# ✅ Home Page
def home(request):
    return render(request, 'sacco/home.html')


# ✅ User Registration
def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        member_form = MemberForm(request.POST)
        if user_form.is_valid() and member_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            member = member_form.save(commit=False)
            member.user = user
            member.save()
            login(request, user)
            return redirect('dashboard')
    else:
        user_form = UserRegistrationForm()
        member_form = MemberForm()

    return render(request, 'sacco/register.html', {'user_form': user_form, 'member_form': member_form})


# ✅ User Login
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'sacco/login.html', {'form': form})


# ✅ User Logout
def user_logout(request):
    logout(request)
    return redirect('home')


# ✅ Loan Application
@login_required(login_url='/login/')
def apply_loan(request):
    if request.method == "POST":
        form = LoanForm(request.POST, request=request)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = LoanForm(request=request)
    return render(request, 'sacco/apply_loan.html', {'form': form})


# ✅ Make Transaction
@login_required(login_url='/login/')
def make_transaction(request):
    if request.method == "POST":
        form = TransactionForm(request.POST, request=request)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = TransactionForm(request=request)
    return render(request, 'sacco/make_transaction.html', {'form': form})

@login_required(login_url='/login/')
def dashboard(request):
    user = request.user
    member, created = Member.objects.get_or_create(user=user, defaults={'phone': 'Not Provided'})

    # ✅ Fetch Loans, Transactions & Transfers
    loans = Loan.objects.filter(member=member)
    transactions = Transaction.objects.filter(member=member)
    loan_repayment_history = LoanRepayment.objects.filter(loan__member=member)
    transfers = transactions.filter(transaction_type="transfer")

    # ✅ Wallet & Savings Balances
    wallet_balance = float(getattr(member, "balance", 0))
    savings_balance = float(getattr(member, "savings_balance", 0))

    # ✅ Calculate Remaining Loan Balance (Loans with balances still to pay)
    total_loan_balance = loans.filter(status="approved").aggregate(Sum("remaining_balance"))["remaining_balance__sum"] or 0
    total_loan_balance = float(total_loan_balance)

    # ✅ Total Account Balance (Wallet + Savings) WITHOUT including loans
    total_account_balance = wallet_balance + savings_balance  

    # ✅ Loan Status Breakdown
    loan_status = loans.values("status").annotate(count=Count("status"))
    loan_counts = {"pending": 0, "approved": 0, "rejected": 0}

    for loan in loan_status:
        loan_counts[loan["status"]] = loan["count"]

    pending_loans = loan_counts["pending"]
    approved_loans_count = loan_counts["approved"]
    rejected_loans = loan_counts["rejected"]

    # ✅ Transaction Data for Chart.js (Last 7 Days)
    last_week = now() - timedelta(days=7)
    transaction_dates, deposit_amounts, withdrawal_amounts = [], [], []

    for i in range(7):
        day = last_week + timedelta(days=i)
        transaction_dates.append(day.strftime("%b %d"))

        deposit_total = transactions.filter(created_at__date=day, transaction_type="deposit").aggregate(Sum("amount"))["amount__sum"] or 0
        withdrawal_total = transactions.filter(created_at__date=day, transaction_type="withdrawal").aggregate(Sum("amount"))["amount__sum"] or 0

        deposit_amounts.append(float(deposit_total))
        withdrawal_amounts.append(float(withdrawal_total))

    # ✅ Convert Python lists to JSON format for frontend charts
    context = {
        'user': user,
        'member': member,
        'loans': loans,
        'transactions': transactions,
        'loan_repayment_history': loan_repayment_history,
        'transfers': transfers,
        'wallet_balance': wallet_balance,  # ✅ Wallet Funds
        'savings_balance': savings_balance,  # ✅ Savings Funds
        'total_account_balance': total_account_balance,  # ✅ Wallet + Savings (No Loans Included)
        'total_loan_balance': total_loan_balance,  # ✅ Show Remaining Loan Balance Separately
        'approved_loans': approved_loans_count,
        'pending_loans': pending_loans,
        'rejected_loans': rejected_loans,
        'transaction_dates': json.dumps(transaction_dates),
        'deposit_amounts': json.dumps(deposit_amounts),
        'withdrawal_amounts': json.dumps(withdrawal_amounts),
    }

    return render(request, 'sacco/dashboard.html', context)




@login_required(login_url='/login/')
def repay_loan(request):
    member = request.user.member  # Get logged-in user's member profile
    loans = Loan.objects.filter(member=member, status="approved", amount__gt=0)  # Show only active loans

    if request.method == "POST":
        form = LoanRepaymentForm(request.POST)
        if form.is_valid():
            repayment = form.save(commit=False)
            loan = repayment.loan
            selected_account = form.cleaned_data['account']  # Get selected account
            amount_to_pay = repayment.amount_paid

            # ✅ Ensure the loan belongs to the logged-in user
            if loan.member != member:
                messages.error(request, "You can only repay your own loan!")
                return redirect("dashboard")

            # ✅ Prevent negative payment amounts
            if amount_to_pay <= 0:
                messages.error(request, "Repayment amount must be positive!")
                return redirect("dashboard")

            # ✅ Check available balance in the selected account
            if selected_account == "wallet":
                if member.balance < amount_to_pay:
                    messages.error(request, "Insufficient funds in your Wallet!")
                    return redirect("dashboard")
                member.balance -= amount_to_pay  # Deduct from wallet

            elif selected_account == "savings":
                if member.savings_balance < amount_to_pay:
                    messages.error(request, "Insufficient funds in your Savings Account!")
                    return redirect("dashboard")
                member.savings_balance -= amount_to_pay  # Deduct from savings

            # ✅ Prevent overpayment
            if loan.amount >= amount_to_pay:
                loan.amount -= amount_to_pay
                loan.save()
                member.save()  # Save updated balances
                repayment.save()

                # ✅ Record the transaction
                Transaction.objects.create(
                    member=member,
                    amount=amount_to_pay,
                    transaction_type="withdrawal"
                )

                messages.success(request, "Loan repayment successful.")
            else:
                messages.error(request, "Repayment amount exceeds loan balance!")

            return redirect("dashboard")
    else:
        form = LoanRepaymentForm()

    return render(request, "sacco/repay_loan.html", {"form": form, "loans": loans})

@login_required(login_url='/login/')
def transfer_funds(request):
    member = request.user.member  
    transfers = Transaction.objects.filter(member=member, transaction_type="transfer")

    # ✅ Ensure Wallet & Savings Balances Exist
    wallet_balance = float(getattr(member, "balance", 0))
    savings_balance = float(getattr(member, "savings_balance", 0))

    # ✅ Ensure Total Account Balance includes Wallet & Savings
    total_account_balance = wallet_balance + savings_balance

    if request.method == "POST":
        form = FundTransferForm(request.POST)
        if form.is_valid():
            from_account = request.POST.get("from_account")
            to_account = request.POST.get("to_account")
            amount = form.cleaned_data["amount"]

            if from_account == to_account:
                return JsonResponse({"success": False, "message": "Cannot transfer between the same account."})

            if from_account == "wallet" and to_account == "savings":
                if wallet_balance < amount:
                    return JsonResponse({"success": False, "message": "Insufficient funds in Wallet!"})
                member.balance -= amount
                member.savings_balance += amount
                description = "Transferred from Wallet to Savings"

            elif from_account == "savings" and to_account == "wallet":
                if savings_balance < amount:
                    return JsonResponse({"success": False, "message": "Insufficient funds in Savings!"})
                member.savings_balance -= amount
                member.balance += amount
                description = "Transferred from Savings to Wallet"

            # ✅ Save updated balances
            member.save()

            # ✅ Log the transaction
            transaction = Transaction.objects.create(
                member=member,
                amount=amount,
                transaction_type="transfer",
                description=description,
            )

            # ✅ Ensure balances are updated correctly
            wallet_balance = float(member.balance)
            savings_balance = float(member.savings_balance)
            total_account_balance = wallet_balance + savings_balance

            return JsonResponse({
                "success": True,
                "message": "Funds transferred successfully.",
                "wallet_balance": wallet_balance,
                "savings_balance": savings_balance,  # ✅ Ensure savings balance is passed
                "total_account_balance": total_account_balance,  
                "amount": float(amount),
                "description": description,
                "date": transaction.created_at.strftime("%b %d, %Y"),
            })

    return render(request, "sacco/transfer_funds.html", {
        "form": FundTransferForm(),
        "transfers": transfers,
        "wallet_balance": wallet_balance,
        "savings_balance": savings_balance,  # ✅ Ensure savings balance is passed
        "total_account_balance": total_account_balance
    })
