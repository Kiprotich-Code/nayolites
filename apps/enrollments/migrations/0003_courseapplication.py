"""
Migration 0003: Add CourseApplication model for the public application workflow.
"""

import apps.enrollments.applications
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0002_academicperiod_enrollment_full'),
        ('courses', '0002_course_courseunit_full'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=150)),
                ('last_name', models.CharField(max_length=150)),
                ('email', models.EmailField()),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('message', models.TextField(blank=True, help_text='Optional note from the applicant.')),
                ('reference_number', models.CharField(
                    default=apps.enrollments.applications._generate_reference,
                    editable=False,
                    max_length=20,
                    unique=True,
                    help_text='Auto-generated reference given to the applicant for tracking.',
                )),
                ('status', models.CharField(
                    choices=[
                        ('SUBMITTED', 'Submitted'),
                        ('UNDER_REVIEW', 'Under Review'),
                        ('ACCEPTED', 'Accepted'),
                        ('REJECTED', 'Rejected'),
                        ('WITHDRAWN', 'Withdrawn'),
                    ],
                    default='SUBMITTED',
                    max_length=12,
                    help_text='Only staff may change this field.',
                )),
                ('staff_notes', models.TextField(blank=True, help_text='Internal staff notes — not visible to applicant.')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='applications',
                    to='courses.course',
                    help_text='The course the applicant wishes to enrol in.',
                )),
                ('preferred_period', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='applications',
                    to='enrollments.academicperiod',
                    help_text='Optional preferred intake period.',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_applications',
                    to=settings.AUTH_USER_MODEL,
                    help_text='Staff member who last changed status.',
                )),
                ('linked_enrollment', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='source_application',
                    to='enrollments.enrollment',
                    help_text='Set when staff converts this application to an enrollment.',
                )),
            ],
            options={
                'verbose_name': 'course application',
                'verbose_name_plural': 'course applications',
                'ordering': ['-created_at'],
                'permissions': [('review_courseapplication', 'Can review and process course applications')],
            },
        ),
    ]
