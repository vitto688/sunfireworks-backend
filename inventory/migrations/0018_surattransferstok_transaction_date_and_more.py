# Generated by Django 5.1.7 on 2025-07-26 17:42

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0017_alter_spg_transaction_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='surattransferstok',
            name='transaction_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='sj',
            name='transaction_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='spk',
            name='transaction_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
