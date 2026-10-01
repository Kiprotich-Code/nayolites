"""
Migration 0002: Replace placeholder CourseContent with full model.
"""

import apps.content.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0001_initial'),
        ('courses', '0002_course_courseunit_full'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='coursecontent',
            name='course',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='content_items',
                to='courses.course',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='course_unit',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='content_items',
                to='courses.courseunit',
                help_text='Optional — attach to a specific unit within the course.',
            ),
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='title',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='content_type',
            field=models.CharField(
                choices=[
                    ('PDF', 'PDF Document'),
                    ('VIDEO_URL', 'Video URL'),
                    ('LINK', 'External Link'),
                    ('FILE', 'Other File'),
                ],
                default='PDF',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='file',
            field=models.FileField(
                blank=True, null=True,
                upload_to=apps.content.models.content_upload_path,
                help_text='Upload a file. Use this or a URL, not both.',
            ),
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='url',
            field=models.URLField(
                blank=True,
                help_text='External link. Use this or a file, not both.',
            ),
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='visibility',
            field=models.CharField(
                choices=[
                    ('ENROLLED', 'Enrolled Students'),
                    ('ALL', 'All Students'),
                    ('STAFF', 'Staff Only'),
                ],
                default='ENROLLED',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='uploaded_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='uploaded_content',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='coursecontent',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name='coursecontent',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'course content',
                'verbose_name_plural': 'course content',
            },
        ),
    ]
