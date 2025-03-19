# Generated by Django 5.1.7 on 2025-03-13 16:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sacco', '0002_remove_member_email_remove_member_name_member_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='loan',
            name='interest_rate',
            field=models.DecimalField(decimal_places=2, max_digits=5),
        ),
    ]
