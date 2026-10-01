"""
Migration 0003: Add explicit status field to StudentProfile.
Depends on both existing 0002 migrations (no merge needed; single dependency chain).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_alter_studentprofile_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='status',
            field=models.CharField(
                choices=[
                    ('ACTIVE', 'Active'),
                    ('INACTIVE', 'Inactive'),
                    ('SUSPENDED', 'Suspended'),
                    ('GRADUATED', 'Graduated'),
                ],
                default='ACTIVE',
                max_length=10,
                help_text='Explicit lifecycle status. Changing status does not delete historical records.',
            ),
        ),
    ]
