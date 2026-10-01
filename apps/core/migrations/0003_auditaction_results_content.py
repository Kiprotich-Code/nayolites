"""
Migration 0003: Add Results and Content audit action choices.
All values fit within the existing VARCHAR(50) column.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auditaction_academic_events'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('login_success', 'Successful Login'),
                    ('login_failed', 'Failed Login Attempt'),
                    ('logout', 'Logout'),
                    ('password_changed', 'Password Changed'),
                    ('password_reset_admin', 'Password Reset by Admin'),
                    ('staff_account_created', 'Staff Account Created'),
                    ('account_status_changed', 'Account Status Changed'),
                    ('group_assignment_changed', 'Group Assignment Changed'),
                    ('student_created', 'Student Record Created'),
                    ('student_updated', 'Student Record Updated'),
                    ('student_status_changed', 'Student Status Changed'),
                    ('course_created', 'Course Created'),
                    ('course_updated', 'Course Updated'),
                    ('course_status_changed', 'Course Activated/Deactivated'),
                    ('course_unit_created', 'Course Unit Created'),
                    ('course_unit_updated', 'Course Unit Updated'),
                    ('academic_period_created', 'Academic Period Created'),
                    ('academic_period_updated', 'Academic Period Updated'),
                    ('academic_period_status_changed', 'Academic Period Status Changed'),
                    ('enrollment_created', 'Enrollment Created'),
                    ('enrollment_status_changed', 'Enrollment Status Changed'),
                    ('enrollment_approved', 'Enrollment Approved'),
                    ('application_submitted', 'Course Application Submitted'),
                    ('application_status_changed', 'Application Status Changed'),
                    ('result_entered', 'Result Entered / Updated'),
                    ('result_submitted', 'Result Submitted for Review'),
                    ('result_approved', 'Result Approved'),
                    ('result_published', 'Result Published'),
                    ('content_uploaded', 'Content Uploaded'),
                    ('content_updated', 'Content Updated'),
                    ('content_deleted', 'Content Deleted'),
                ],
            ),
        ),
    ]
