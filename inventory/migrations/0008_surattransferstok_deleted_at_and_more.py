# Generated by Django 5.1.7 on 2025-07-05 19:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0007_spg_deleted_at_spg_is_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='surattransferstok',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='surattransferstok',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='surattransferstokitems',
            name='surat_transfer_stok',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='items', to='inventory.surattransferstok'),
        ),
    ]
