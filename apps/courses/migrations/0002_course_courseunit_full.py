"""
Migration 0002: Replace placeholder Course/CourseUnit with full academic models.

The 0001_initial migration created empty tables. This migration adds all
fields, constraints, and custom permissions.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Course — add all fields
        # ----------------------------------------------------------------
        migrations.AddField(
            model_name='course',
            name='code',
            field=models.CharField(
                default='',
                max_length=20,
                unique=True,
                help_text='Short programme code, e.g. DCS, DBM. Must be unique.',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='name',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='slug',
            field=models.SlugField(
                blank=True,
                max_length=220,
                unique=True,
                default='',
                help_text='Auto-generated from name for public URLs.',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='course',
            name='duration',
            field=models.CharField(
                default='',
                max_length=50,
                help_text='Human-readable duration, e.g. "2 Years" or "1 Year".',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text='Inactive courses are hidden from public catalogue and cannot accept new enrollments.',
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name='course',
            options={
                'ordering': ['name'],
                'verbose_name': 'course',
                'verbose_name_plural': 'courses',
                'permissions': [('activate_course', 'Can activate/deactivate course')],
            },
        ),
        # ----------------------------------------------------------------
        # CourseUnit — add all fields
        # ----------------------------------------------------------------
        migrations.AddField(
            model_name='courseunit',
            name='course',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='units',
                to='courses.course',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='courseunit',
            name='code',
            field=models.CharField(
                default='',
                max_length=30,
                help_text='Unit code, e.g. DCS 101. Must be unique within the course.',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='courseunit',
            name='name',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='courseunit',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='courseunit',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='courseunit',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='courseunit',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name='courseunit',
            options={
                'ordering': ['code'],
                'verbose_name': 'course unit',
                'verbose_name_plural': 'course units',
            },
        ),
        migrations.AddConstraint(
            model_name='courseunit',
            constraint=models.UniqueConstraint(
                fields=['course', 'code'],
                name='unique_unit_code_within_course',
            ),
        ),
    ]
