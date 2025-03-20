from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('apply-loan/', views.apply_loan, name='apply_loan'),
    path('transaction/', views.make_transaction, name='make_transaction'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('repay-loan/', views.repay_loan, name='repay_loan'),
    path('loan-approval/', views.loan_approval, name='loan_approval'),
    path('process-loan/<int:loan_id>/<str:action>/', views.process_loan, name='process_loan'),
    path('repay-loan/', views.repay_loan, name='repay_loan'),
    path("transfer-funds/", views.transfer_funds, name="transfer_funds"),
    path("withdraw-loan/<int:loan_id>/", views.withdraw_loan, name="withdraw_loan"),
    path('loan-interest-news/', views.loan_interest_news, name='loan_interest_news'),
    path('agm-news/', views.agm_news, name='agm_news'),
    path("buy-shares/", views.buy_shares, name="buy_shares"),
    path("transfer-shares/", views.transfer_shares, name="transfer_shares"),
    path('transactions/', views.transaction_history, name="transaction_history"),
    path('about/', views.about_us, name='about_us'),
    path('services/', views.services, name='services'),
    path('generate-report/', views.generate_report, name='generate_report'),

]
