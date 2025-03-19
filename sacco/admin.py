from django.contrib import admin
from .models import Member,Loan,Transaction
# Register your models here.

admin.site.register(Member)
admin.site.register(Loan)
admin.site.register(Transaction)
