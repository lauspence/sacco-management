import json
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils.timezone import now, timedelta
from django.http import HttpResponse
from decimal import Decimal
from django.db.models import Count, Sum,F
from .forms import *
from .models import * 
from django.http import JsonResponse


# ✅ Function to check if the user is an admin
def is_admin(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()



# ✅ Admin Loan Approval Page
@login_required(login_url='/login/')
@user_passes_test(is_admin, login_url='/login/')
def loan_approval(request):
    # Summary Data
    total_members = Member.objects.count()
    total_savings = Member.objects.aggregate(total_savings=models.Sum('savings_balance'))['total_savings'] or Decimal(0)
    active_loans = Loan.objects.filter(status="approved").count()
    
    # Pending loans
    pending_loans = Loan.objects.filter(status="pending")
    pending_loans_count = pending_loans.count()  # Ensure query evaluation in the view

    # Recent Transactions (Latest 10)
    transactions = Transaction.objects.order_by('-created_at')[:10] or None

    context = {
        "total_members": total_members,
        "total_savings": total_savings,
        "active_loans": active_loans,
        "pending_loans": pending_loans,
        "pending_loans_count": pending_loans_count,  # Now available in the template
        "transactions": transactions,
    }
    
    return render(request, "sacco/admin_loan_approval.html", context)


# ✅ Admin Processing Loan Requests
@login_required(login_url='/login/')
@user_passes_test(is_admin, login_url='/login/')
def process_loan(request, loan_id, action):
    loan = get_object_or_404(Loan, id=loan_id)

    if action == "approve" and request.method == "POST":
        amount = Decimal(request.POST.get("amount", 0))  # Fetch amount from form

        if amount <= 0:
            messages.error(request, "Loan amount must be greater than zero.")
        else:
            loan.amount = amount
            loan.remaining_balance = amount  # Set remaining balance
            loan.status = "approved"
            loan.reviewed_by = request.user
            loan.save()

            messages.success(request, f"Loan of {amount} approved for {loan.member.user.username}.")

    elif action == "reject":
        loan.status = "rejected"
        loan.reviewed_by = request.user
        loan.save()
        messages.error(request, f"Loan for {loan.member.user.username} has been rejected.")

    return redirect("loan_approval")


# ✅ Home Page
def home(request):
    is_admin = request.user.is_authenticated and request.user.is_staff  # Check if user is admin
    return render(request, "sacco/home.html", {"is_admin": is_admin})


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

@login_required
def make_transaction(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        
        try:
            amount = Decimal(amount)  # Convert directly to Decimal
        except:
            messages.error(request, "Invalid amount entered.")
            return redirect("transaction_page")  # Adjust to your transaction page

        member = request.user.member  # Ensure correct member retrieval

        if amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
        else:
            # Ensure balance and loan amounts are properly handled as Decimal
            member.balance += amount  # Ensure `balance` is Decimal in your model
            member.save()

            Transaction.objects.create(
                member=member,
                amount=amount,
                transaction_type="deposit",  # Or "withdrawal" based on logic
                description="User deposit",
            )

            messages.success(request, "Transaction successful.")
            return redirect("dashboard")  # Adjust based on your routing

    return render(request, "sacco/transaction.html")




@login_required(login_url='/login/')
def dashboard(request):
    user = request.user
    
    # Ensure member exists
    member, created = Member.objects.get_or_create(user=user, defaults={'phone': 'Not Provided'})

    # Fetch all relevant data
    loans = Loan.objects.filter(member=member, status="approved")
    transactions = Transaction.objects.filter(member=member)
    loan_repayment_history = LoanRepayment.objects.filter(loan__member=member).order_by("-date_paid")
    transfers = transactions.filter(transaction_type="transfer")

    # Wallet & Savings Balances
    wallet_balance = float(member.balance or 0)  # Convert Decimal to float
    savings_balance = float(member.savings_balance or 0)  # Convert Decimal to float
    total_account_balance = wallet_balance + savings_balance  # Wallet + Savings (No Loans Included)

    # Get first approved loan and refresh it
    loan = loans.filter(remaining_balance__gt=0).first()
    if loan:
        loan.refresh_from_db()  # Ensure latest data

    loan_remaining_balance = float(loan.remaining_balance) if loan else 0.0
    # print(f"Debug Loan Remaining Balance: {loan_remaining_balance}")

    # Calculate Total Remaining Loan Balance
    total_loan_balance = loans.filter(remaining_balance__gt=0).aggregate(
        total=Sum(F("remaining_balance"))
    )["total"] or Decimal(0)
    total_loan_balance = float(total_loan_balance)  # Convert Decimal to float

    # print(f"Total Loan Balance Debug: {total_loan_balance}")

    # Loan Status Breakdown
    loan_status = loans.values("status").annotate(count=Count("status"))
    loan_counts = {"pending": 0, "approved": 0, "rejected": 0}
    for loan_status_item in loan_status:
        loan_counts[loan_status_item["status"]] = loan_status_item["count"]

    # Transaction Data for Chart.js (Last 7 Days)
    last_week = now() - timedelta(days=7)
    daily_totals = {}

    for i in range(7):
        day = (last_week + timedelta(days=i)).strftime("%b %d")
        daily_totals[day] = {"deposit": 0.0, "withdrawal": 0.0}

    last_week_transactions = transactions.filter(created_at__gte=last_week).values("created_at", "transaction_type", "amount")

    for txn in last_week_transactions:
        date_key = txn["created_at"].strftime("%b %d")
        if date_key in daily_totals:
            amount = float(txn["amount"])  # Convert Decimal to float
            if txn["transaction_type"] == "deposit":
                daily_totals[date_key]["deposit"] += amount
            elif txn["transaction_type"] == "withdrawal":
                daily_totals[date_key]["withdrawal"] += amount

    transaction_dates = list(daily_totals.keys())
    deposit_amounts = [daily_totals[day]["deposit"] for day in transaction_dates]
    withdrawal_amounts = [daily_totals[day]["withdrawal"] for day in transaction_dates]
    
    # Convert lists to JSON for frontend use
    context = {
        'user': user,
        'member': member,
        'loans': loans,
        'loan': loan,
        'loan_remaining_balance': loan_remaining_balance,
        'transactions': transactions,
        'loan_repayment_history': loan_repayment_history,
        'transfers': transfers,
        'wallet_balance': wallet_balance,
        'savings_balance': savings_balance,
        'total_account_balance': total_account_balance,
        'total_loan_balance': total_loan_balance,
        'approved_loans': loan_counts.get("approved", 0),
        'pending_loans': loan_counts.get("pending", 0),
        'rejected_loans': loan_counts.get("rejected", 0),
        'transaction_dates': json.dumps(transaction_dates),
        'deposit_amounts': json.dumps(deposit_amounts),
        'withdrawal_amounts': json.dumps(withdrawal_amounts),
    }
    print(f"Final Context Loan Balance Debug: {context['total_loan_balance']}")

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

@login_required
def withdraw_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id, member__user=request.user, status="approved")

    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get("amount", 0))  # Convert to Decimal

            if amount < 1 or amount > loan.remaining_balance:
                messages.error(request, "Invalid withdrawal amount.")
            else:
                # Deduct from loan
                loan.remaining_balance -= amount
                loan.total_withdrawn += amount
                loan.save()

                # Update wallet balance
                # print(f"Wallet Balance Before Withdrawal: {member.balance}")
                member = loan.member
                member.balance += amount
                member.save()

                # Log transaction
                Transaction.objects.create(
                    member=member,
                    amount=amount,
                    transaction_type="withdrawal",
                    description=f"Loan withdrawal from Loan ID {loan.id}",
                )

                messages.success(request, "Loan withdrawal successful.")
                return redirect("dashboard")

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")

    return render(request, "sacco/withdraw_loan.html", {"loan": loan})


def loan_interest_news(request):
    return render(request, 'sacco/loan_interest_news.html')

# View for AGM News
def agm_news(request):
    return render(request, 'sacco/agm_news.html')


@login_required
def buy_shares(request):
    member = request.user.member
    share, created = Share.objects.get_or_create(member=member)
    
    if request.method == "POST":
        amount = Decimal(request.POST.get("amount", 0))
        price_per_share = Decimal(100)  # Set your share price here

        if member.balance >= amount and amount > 0:
            member.balance -= amount
            member.save()
            share.buy_shares(amount, price_per_share)

            Transaction.objects.create(
                member=member,
                amount=amount,
                transaction_type="share_purchase",
                description=f"Purchased {amount / price_per_share} shares"
            )

            messages.success(request, "Shares purchased successfully.")
        else:
            messages.error(request, "Insufficient balance or invalid amount.")
    
    return render(request, "sacco/buy_shares.html", {"member": member, "share": share})


@login_required
def transfer_shares(request):
    sender = request.user.member
    receiver = None
    share, created = Share.objects.get_or_create(member=sender)

    if request.method == "POST":
        recipient_username = request.POST.get("recipient")
        num_shares = Decimal(request.POST.get("num_shares", 0))
        
        try:
            recipient = Member.objects.get(user__username=recipient_username)
            recipient_share, _ = Share.objects.get_or_create(member=recipient)
            
            if share.transfer_shares(recipient_share, num_shares):
                messages.success(request, f"Transferred {num_shares} shares to {recipient.user.username}.")
            else:
                messages.error(request, "Not enough shares to transfer.")
        except Member.DoesNotExist:
            messages.error(request, "Recipient not found.")

    return render(request, "sacco/transfer_shares.html", {"share": share})


def distribute_dividends():
    total_shares = Share.objects.aggregate(total=models.Sum("shares_owned"))["total"] or 0
    total_dividends = Decimal(50000)  # Example: Total dividends for distribution

    if total_shares > 0:
        dividend_per_share = total_dividends / Decimal(total_shares)
        for share in Share.objects.all():
            payout = share.shares_owned * dividend_per_share
            share.member.balance += payout
            share.member.save()

            Transaction.objects.create(
                member=share.member,
                amount=payout,
                transaction_type="dividend",
                description="Dividend payout"
            )


def transaction_history(request):
    transactions = Transaction.objects.all().order_by('-created_at')  # Get latest first
    
    # Filtering logic (if user applies filters)
    transaction_type = request.GET.get('transaction_type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    search_query = request.GET.get('search')
    if search_query:
        transactions = transactions.filter(description__icontains=search_query)

    # Pagination (10 transactions per page)
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'sacco/transaction_history.html', {'transactions': page_obj})

def about_us(request):
    return render(request, 'sacco/about_us.html')

def services(request):
    return render(request, 'sacco/services_page.html') 

def generate_report(request):
    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sacco_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Member', 'Amount', 'Type', 'Date'])

    transactions = Transaction.objects.all()
    for transaction in transactions:
        writer.writerow([transaction.member.user.username, transaction.amount, transaction.transaction_type, transaction.created_at])

    return response