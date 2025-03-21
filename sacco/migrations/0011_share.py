# Generated by Django 5.1.7 on 2025-03-19 16:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sacco', '0010_loan_repayment_status_loan_total_withdrawn'),
    ]

    operations = [
        migrations.CreateModel(
            name='Share',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shares_owned', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_investment', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('member', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='sacco.member')),
            ],
        ),
    ]
