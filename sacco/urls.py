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
]
