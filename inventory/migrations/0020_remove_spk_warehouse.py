# Generated by Django 5.1.7 on 2025-07-26 17:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0019_alter_suratlain_transaction_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='spk',
            name='warehouse',
        ),
    ]
