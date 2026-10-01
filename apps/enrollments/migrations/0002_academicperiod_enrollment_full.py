"""
Migration 0002: Replace placeholder AcademicPeriod/Enrollment with full models.
Depends on students 0001 and courses 0002 being applied first.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0001_initial'),
        ('students', '0001_initial'),
        ('courses', '0002_course_courseunit_full'),
    ]

    operations = [
        # ----------------------------------------------------------------
        # AcademicPeriod — add all fields
        # ----------------------------------------------------------------
        migrations.AddField(
            model_name='academicperiod',
            name='name',
            field=models.CharField(default='', max_length=100, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='academicperiod',
            name='start_date',
            field=models.DateField(default='2026-01-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='academicperiod',
            name='end_date',
            field=models.DateField(default='2026-12-31'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='academicperiod',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text='Active periods appear in enrollment workflows. Inactive periods are archived.',
            ),
        ),
        migrations.AddField(
            model_name='academicperiod',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='academicperiod',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name='academicperiod',
            options={
                'ordering': ['-start_date'],
                'verbose_name': 'academic period',
                'verbose_name_plural': 'academic periods',
                'permissions': [('manage_academicperiod', 'Can create and modify academic periods')],
            },
        ),
        # ----------------------------------------------------------------
        # Enrollment — add all fields and constraints
        # ----------------------------------------------------------------
        migrations.AddField(
            model_name='enrollment',
            name='student',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='enrollments',
                to='students.studentprofile',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='enrollment',
            name='course',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='enrollments',
                to='courses.course',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='enrollment',
            name='academic_period',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='enrollments',
                to='enrollments.academicperiod',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='enrollment',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('ACTIVE', 'Active'),
                    ('COMPLETED', 'Completed'),
                    ('WITHDRAWN', 'Withdrawn'),
                    ('CANCELLED', 'Cancelled'),
                ],
                default='PENDING',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='enrolled_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='withdrawn_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name='enrollment',
            options={
                'ordering': ['-enrolled_at'],
                'verbose_name': 'enrollment',
                'verbose_name_plural': 'enrollments',
                'permissions': [('approve_enrollment', 'Can approve enrollment')],
            },
        ),
        # Partial uniqueness constraint — prevents duplicate open enrollments
        migrations.AddConstraint(
            model_name='enrollment',
            constraint=models.UniqueConstraint(
                fields=['student', 'course', 'academic_period'],
                condition=models.Q(status__in=['PENDING', 'ACTIVE']),
                name='unique_open_enrollment_per_student_course_period',
            ),
        ),
    ]
