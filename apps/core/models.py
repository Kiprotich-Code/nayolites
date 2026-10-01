from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    # ---- Authentication ----
    LOGIN_SUCCESS = 'login_success', 'Successful Login'
    LOGIN_FAILED = 'login_failed', 'Failed Login Attempt'
    LOGOUT = 'logout', 'Logout'
    PASSWORD_CHANGED = 'password_changed', 'Password Changed'
    PASSWORD_RESET_ADMIN = 'password_reset_admin', 'Password Reset by Admin'
    # ---- User / staff management ----
    STAFF_ACCOUNT_CREATED = 'staff_account_created', 'Staff Account Created'
    ACCOUNT_STATUS_CHANGED = 'account_status_changed', 'Account Status Changed'
    GROUP_ASSIGNMENT_CHANGED = 'group_assignment_changed', 'Group Assignment Changed'
    # ---- Student domain ----
    STUDENT_CREATED = 'student_created', 'Student Record Created'
    STUDENT_UPDATED = 'student_updated', 'Student Record Updated'
    STUDENT_STATUS_CHANGED = 'student_status_changed', 'Student Status Changed'
    # ---- Course domain ----
    COURSE_CREATED = 'course_created', 'Course Created'
    COURSE_UPDATED = 'course_updated', 'Course Updated'
    COURSE_STATUS_CHANGED = 'course_status_changed', 'Course Activated/Deactivated'
    COURSE_UNIT_CREATED = 'course_unit_created', 'Course Unit Created'
    COURSE_UNIT_UPDATED = 'course_unit_updated', 'Course Unit Updated'
    # ---- Academic period ----
    ACADEMIC_PERIOD_CREATED = 'academic_period_created', 'Academic Period Created'
    ACADEMIC_PERIOD_UPDATED = 'academic_period_updated', 'Academic Period Updated'
    ACADEMIC_PERIOD_STATUS_CHANGED = 'academic_period_status_changed', 'Academic Period Status Changed'
    # ---- Enrollment ----
    ENROLLMENT_CREATED = 'enrollment_created', 'Enrollment Created'
    ENROLLMENT_STATUS_CHANGED = 'enrollment_status_changed', 'Enrollment Status Changed'
    ENROLLMENT_APPROVED = 'enrollment_approved', 'Enrollment Approved'
    # ---- Public application ----
    APPLICATION_SUBMITTED = 'application_submitted', 'Course Application Submitted'
    APPLICATION_STATUS_CHANGED = 'application_status_changed', 'Application Status Changed'
    # ---- Results ----
    RESULT_ENTERED = 'result_entered', 'Result Entered / Updated'
    RESULT_SUBMITTED = 'result_submitted', 'Result Submitted for Review'
    RESULT_APPROVED = 'result_approved', 'Result Approved'
    RESULT_PUBLISHED = 'result_published', 'Result Published'
    # ---- Content ----
    CONTENT_UPLOADED = 'content_uploaded', 'Content Uploaded'
    CONTENT_UPDATED = 'content_updated', 'Content Updated'
    CONTENT_DELETED = 'content_deleted', 'Content Deleted'
    # ---- Finance / Payments ----
    FEE_STRUCTURE_CREATED = 'fee_structure_created', 'Fee Structure Created'
    FEE_STRUCTURE_UPDATED = 'fee_structure_updated', 'Fee Structure Updated'
    FEE_STRUCTURE_ACTIVATED = 'fee_structure_activated', 'Fee Structure Activated/Deactivated'
    INVOICE_CREATED = 'invoice_created', 'Invoice Created'
    INVOICE_ISSUED = 'invoice_issued', 'Invoice Issued'
    INVOICE_VOIDED = 'invoice_voided', 'Invoice Voided'
    PAYMENT_CREATED = 'payment_created', 'Payment Created'
    PAYMENT_STATUS_CHANGED = 'payment_status_changed', 'Payment Status Changed'
    PAYMENT_ALLOCATED = 'payment_allocated', 'Payment Allocated'
    PAYMENT_REVERSED = 'payment_reversed', 'Payment Reversed'
    RECEIPT_ISSUED = 'receipt_issued', 'Receipt Issued'
    MANUAL_PAYMENT_RECORDED = 'manual_payment_recorded', 'Manual Payment Recorded'


class AuditLog(models.Model):
    """
    Immutable record of security-sensitive events.

    Application-layer code MUST only ever call AuditLog.objects.create().
    No view, form, or management command should call .save(), .update(), or .delete()
    on existing AuditLog instances.
    """
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_actions',
    )
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'audit log entry'
        verbose_name_plural = 'audit log entries'

    def __str__(self):
        actor_str = str(self.actor) if self.actor else 'anonymous'
        return f'[{self.created_at}] {actor_str} \u2014 {self.get_action_display()}'
