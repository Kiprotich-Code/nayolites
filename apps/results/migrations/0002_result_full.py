"""
Migration 0002: Replace placeholder Result with full academic model.
"""

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0001_initial'),
        ('enrollments', '0002_academicperiod_enrollment_full'),
        ('courses', '0002_course_courseunit_full'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='enrollment',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='results',
                to='enrollments.enrollment',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='result',
            name='course_unit',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='results',
                to='courses.courseunit',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='result',
            name='score_cat',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=5, null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(40),
                ],
                help_text='Continuous Assessment Test score (0–40).',
            ),
        ),
        migrations.AddField(
            model_name='result',
            name='score_exam',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=5, null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(60),
                ],
                help_text='Examination score (0–60).',
            ),
        ),
        migrations.AddField(
            model_name='result',
            name='total',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=5, null=True,
                help_text='Computed total (CAT + Exam). Stored for filtering.',
            ),
        ),
        migrations.AddField(
            model_name='result',
            name='grade',
            field=models.CharField(blank=True, max_length=3),
        ),
        migrations.AddField(
            model_name='result',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('SUBMITTED', 'Submitted for Review'),
                    ('APPROVED', 'Approved'),
                    ('PUBLISHED', 'Published'),
                ],
                default='DRAFT',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='result',
            name='entered_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='results_entered',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='result',
            name='approved_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='results_approved',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='result',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='result',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='result',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name='result',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'result',
                'verbose_name_plural': 'results',
                'permissions': [
                    ('publish_result', 'Can publish result'),
                    ('approve_result', 'Can approve result'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='result',
            constraint=models.UniqueConstraint(
                fields=['enrollment', 'course_unit'],
                name='unique_result_per_enrollment_unit',
            ),
        ),
    ]
