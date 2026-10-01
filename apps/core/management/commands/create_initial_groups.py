"""
Management command to seed the six initial staff groups with their permissions.

This command is idempotent — safe to run multiple times.
Run after migrations: python manage.py create_initial_groups
"""

import logging

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def _get_perm(app_label, model_name, codename):
    """
    Retrieve a Permission by app_label + model_name + codename.
    Returns None and logs a warning if not found (e.g., model not yet migrated).
    """
    try:
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        return Permission.objects.get(content_type=ct, codename=codename)
    except (ContentType.DoesNotExist, Permission.DoesNotExist):
        logger.warning('Permission not found: %s.%s.%s', app_label, model_name, codename)
        return None


def _collect_perms(spec_list):
    """
    spec_list: list of (app_label, model_name, codename) tuples.
    Returns list of Permission objects, skipping any that don't exist.
    """
    perms = []
    for app_label, model_name, codename in spec_list:
        perm = _get_perm(app_label, model_name, codename)
        if perm:
            perms.append(perm)
    return perms


class Command(BaseCommand):
    help = 'Seed the six initial staff groups with their documented permissions.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding initial staff groups...')

        # Each entry: (app_label, model_name, codename)
        GROUP_PERMISSIONS = {
            'Administrator': '__all__',  # handled specially below

            'Registrar': [
                # Students
                ('students', 'studentprofile', 'view_studentprofile'),
                ('students', 'studentprofile', 'add_studentprofile'),
                ('students', 'studentprofile', 'change_studentprofile'),
                ('students', 'studentprofile', 'deactivate_student'),
                # Courses (view only — Registrar needs to select courses for enrollment)
                ('courses', 'course', 'view_course'),
                ('courses', 'courseunit', 'view_courseunit'),
                # Academic periods
                ('enrollments', 'academicperiod', 'view_academicperiod'),
                # Enrollments
                ('enrollments', 'enrollment', 'view_enrollment'),
                ('enrollments', 'enrollment', 'add_enrollment'),
                ('enrollments', 'enrollment', 'change_enrollment'),
                ('enrollments', 'enrollment', 'approve_enrollment'),
                # Applications
                ('enrollments', 'courseapplication', 'view_courseapplication'),
                ('enrollments', 'courseapplication', 'change_courseapplication'),
                ('enrollments', 'courseapplication', 'review_courseapplication'),
            ],

            'Finance Officer': [
                ('finance', 'invoice', 'view_invoice'),
                ('finance', 'invoice', 'add_invoice'),
                ('finance', 'invoice', 'change_invoice'),
                ('finance', 'payment', 'view_payment'),
                ('finance', 'payment', 'add_payment'),
                ('finance', 'payment', 'change_payment'),
                ('finance', 'feestructure', 'view_feestructure'),
                ('finance', 'feestructure', 'add_feestructure'),
                ('finance', 'feestructure', 'change_feestructure'),
                # View-only access to academic records for finance context
                ('students', 'studentprofile', 'view_studentprofile'),
                ('enrollments', 'enrollment', 'view_enrollment'),
                ('courses', 'course', 'view_course'),
            ],

            'Academic Officer': [
                # Students (view)
                ('students', 'studentprofile', 'view_studentprofile'),
                # Courses (full management)
                ('courses', 'course', 'view_course'),
                ('courses', 'course', 'add_course'),
                ('courses', 'course', 'change_course'),
                ('courses', 'course', 'activate_course'),
                ('courses', 'courseunit', 'view_courseunit'),
                ('courses', 'courseunit', 'add_courseunit'),
                ('courses', 'courseunit', 'change_courseunit'),
                # Academic periods (full management)
                ('enrollments', 'academicperiod', 'view_academicperiod'),
                ('enrollments', 'academicperiod', 'add_academicperiod'),
                ('enrollments', 'academicperiod', 'change_academicperiod'),
                ('enrollments', 'academicperiod', 'manage_academicperiod'),
                # Enrollments (view + approve)
                ('enrollments', 'enrollment', 'view_enrollment'),
                ('enrollments', 'enrollment', 'approve_enrollment'),
                # Results
                ('results', 'result', 'view_result'),
                ('results', 'result', 'add_result'),
                ('results', 'result', 'change_result'),
                ('results', 'result', 'publish_result'),
                ('results', 'result', 'approve_result'),
                # Content management
                ('content', 'coursecontent', 'view_coursecontent'),
                ('content', 'coursecontent', 'add_coursecontent'),
                ('content', 'coursecontent', 'change_coursecontent'),
                ('content', 'coursecontent', 'delete_coursecontent'),
            ],

            'Lecturer': [
                # View academic context
                ('students', 'studentprofile', 'view_studentprofile'),
                ('courses', 'course', 'view_course'),
                ('courses', 'courseunit', 'view_courseunit'),
                ('enrollments', 'enrollment', 'view_enrollment'),
                # Results entry
                ('results', 'result', 'add_result'),
                ('results', 'result', 'change_result'),
                ('results', 'result', 'view_result'),
                # Content upload
                ('content', 'coursecontent', 'add_coursecontent'),
                ('content', 'coursecontent', 'change_coursecontent'),
                ('content', 'coursecontent', 'view_coursecontent'),
                ('content', 'coursecontent', 'delete_coursecontent'),
            ],

            'Receptionist': [
                ('students', 'studentprofile', 'view_studentprofile'),
                ('courses', 'course', 'view_course'),
                ('enrollments', 'enrollment', 'view_enrollment'),
                ('enrollments', 'academicperiod', 'view_academicperiod'),
                ('finance', 'invoice', 'view_invoice'),
                # View applications (for answering enquiries)
                ('enrollments', 'courseapplication', 'view_courseapplication'),
            ],
        }

        for group_name, perms_spec in GROUP_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f'  {action} group: {group_name}')

            if perms_spec == '__all__':
                all_perms = list(Permission.objects.all())
                group.permissions.set(all_perms)
                self.stdout.write(
                    f'    Assigned all {len(all_perms)} permissions to Administrator'
                )
            else:
                perms = _collect_perms(perms_spec)
                group.permissions.set(perms)
                self.stdout.write(
                    f'    Assigned {len(perms)}/{len(perms_spec)} permissions'
                )

        self.stdout.write(self.style.SUCCESS('Initial groups seeded successfully.'))
