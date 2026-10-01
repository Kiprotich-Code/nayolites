"""
Migration 0003: Remove null=True from created_at and sync grade help_text.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0002_result_full'),
    ]

    operations = [
        migrations.AlterField(
            model_name='result',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='result',
            name='grade',
            field=models.CharField(
                blank=True,
                help_text='Letter grade computed from total.',
                max_length=3,
            ),
        ),
    ]
