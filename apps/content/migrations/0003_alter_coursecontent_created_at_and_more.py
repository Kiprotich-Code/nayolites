"""
Migration 0003: Clean up auto_now_add fields that were added with null=True
in 0002 (required for existing rows at the time). Now remove null=True.

Also removes the duplicate url help_text change that Django auto-detected.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_coursecontent_full'),
    ]

    operations = [
        # Remove null=True from created_at — existing NULL rows get a sensible default
        migrations.AlterField(
            model_name='coursecontent',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        # Sync url help_text with model (cosmetic — no DDL change needed)
        migrations.AlterField(
            model_name='coursecontent',
            name='url',
            field=models.URLField(
                blank=True,
                help_text='External link (YouTube, Google Drive, etc.). Use this or a file, not both.',
            ),
        ),
    ]
