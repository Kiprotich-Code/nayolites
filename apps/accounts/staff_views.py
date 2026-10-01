"""
Staff portal user management views.

These views handle the full user management lifecycle:
  - Listing, searching, and filtering users
  - Creating staff accounts
  - Changing account status
  - Assigning/removing group memberships
  - Admin-initiated password resets
  - Viewing effective permissions

Requirements: 11.1–11.5, 12.1–12.5, 13.1–13.6, 14.1–14.5, 15.1–15.3, 16.1–16.3
"""

from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.forms import (
    AccountStatusForm,
    AdminPasswordSetForm,
    GroupAssignmentForm,
    StaffCreateForm,
)
from apps.accounts.mixins import StaffRequiredMixin
from apps.accounts.models import AccountStatus, StaffProfile, User
from apps.core.audit import audit_log
from apps.core.models import AuditAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_last_administrator(user):
    """
    Returns True if user is the sole remaining member of the Administrator group.
    Used to block deactivation/suspension/group removal that would leave the
    Administrator group empty.
    Requirements: 13.5, 14.4
    """
    try:
        admin_group = Group.objects.get(name='Administrator')
    except Group.DoesNotExist:
        return False
    return (
        admin_group.user_set.count() == 1
        and admin_group.user_set.filter(pk=user.pk).exists()
    )


# ---------------------------------------------------------------------------
# User list
# ---------------------------------------------------------------------------

class UserListView(StaffRequiredMixin, View):
    """
    GET /staff/users/
    Lists all users with search and filter controls, paginated at 25 per page.
    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
    """

    permission_required = 'accounts.view_user'

    def get(self, request):
        qs = (
            User.objects
            .select_related('staffprofile')
            .order_by('last_name', 'first_name')
        )

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )

        status_filter = request.GET.get('status', '').strip()
        if status_filter in AccountStatus.values:
            qs = qs.filter(account_status=status_filter)

        profile_filter = request.GET.get('profile_type', '').strip()
        if profile_filter == 'staff':
            qs = qs.filter(staffprofile__isnull=False)
        elif profile_filter == 'student':
            qs = qs.filter(staffprofile__isnull=True, is_staff=False)

        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'staff/users/list.html', {
            'page_title': 'Users',
            'active_section': 'users',
            'page_obj': page_obj,
            'q': q,
            # template reads 'status' and 'profile_type' to re-select dropdowns
            'status': status_filter,
            'profile_type': profile_filter,
            # template iterates 'account_statuses' for the status dropdown
            'account_statuses': AccountStatus.choices,
        })


# ---------------------------------------------------------------------------
# User detail
# ---------------------------------------------------------------------------

class UserDetailView(StaffRequiredMixin, View):
    """
    GET /staff/users/<pk>/
    Shows user detail with effective permissions inspector, group membership,
    and status/password action forms.
    Requirements: 11.2, 13.1, 14.1, 15.1, 15.2, 15.3
    """

    permission_required = 'accounts.view_user'

    def get(self, request, pk):
        user = get_object_or_404(
            User.objects.select_related('staffprofile'),
            pk=pk,
        )

        # Effective permissions: union of direct + group permissions (Req 15.2)
        direct_perms = set(user.user_permissions.all())
        group_perms = set(
            Permission.objects.filter(group__user=user).select_related('content_type')
        )

        # Build effective permission list with source labels (Req 15.3)
        perm_sources = {}
        for p in direct_perms:
            perm_sources[p.pk] = perm_sources.get(p.pk, [])
            perm_sources[p.pk].append('Direct')
        for p in group_perms:
            for grp in user.groups.filter(permissions=p):
                perm_sources[p.pk] = perm_sources.get(p.pk, [])
                perm_sources[p.pk].append(grp.name)

        all_perms = sorted(
            direct_perms | group_perms,
            key=lambda p: (p.content_type.app_label, p.codename),
        )
        effective_permissions = [
            {
                'name': p.name,
                'codename': p.codename,
                'sources': perm_sources.get(p.pk, []),
            }
            for p in all_perms
        ]

        return render(request, 'staff/users/detail.html', {
            'page_title': user.get_full_name() or user.email,
            'active_section': 'users',
            # template reads 'target_user'
            'target_user': user,
            'effective_permissions': effective_permissions,
            'all_groups': Group.objects.order_by('name'),
            # template reads 'user_group_ids' to mark already-assigned groups
            'user_group_ids': set(user.groups.values_list('id', flat=True)),
            # template reads 'is_last_admin' for safeguard warnings
            'is_last_admin': _is_last_administrator(user),
            'status_form': AccountStatusForm(
                initial={'account_status': user.account_status}
            ),
            'group_form': GroupAssignmentForm(),
            'password_form': AdminPasswordSetForm(),
        })


# ---------------------------------------------------------------------------
# Staff account creation
# ---------------------------------------------------------------------------

class StaffCreateView(StaffRequiredMixin, View):
    """
    GET  /staff/users/create/  — render creation form
    POST /staff/users/create/  — validate and create user + profile atomically
    Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
    """

    permission_required = 'accounts.add_user'

    def get(self, request):
        form = StaffCreateForm()
        return render(request, 'staff/users/create.html', {
            'page_title': 'Create Staff Account',
            'active_section': 'users',
            'form': form,
        })

    def post(self, request):
        form = StaffCreateForm(request.POST)
        if not form.is_valid():
            return render(request, 'staff/users/create.html', {
                'page_title': 'Create Staff Account',
                'active_section': 'users',
                'form': form,
            })

        with transaction.atomic():
            user = User.objects.create_user(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['initial_password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone=form.cleaned_data.get('phone', ''),
                is_staff=True,
                force_password_change=True,
            )
            StaffProfile.objects.create(
                user=user,
                staff_number=form.cleaned_data['staff_number'],
                job_title=form.cleaned_data['job_title'],
                department=form.cleaned_data['department'],
            )
            for group in form.cleaned_data.get('groups', []):
                user.groups.add(group)

        audit_log(
            actor=request.user,
            action=AuditAction.STAFF_ACCOUNT_CREATED,
            obj=user,
            description=f'Staff account created: {user.email}',
            request=request,
        )
        messages.success(request, f'Staff account for {user.get_full_name()} created successfully.')
        return redirect('staff:user_detail', pk=user.pk)


# ---------------------------------------------------------------------------
# Account status change
# ---------------------------------------------------------------------------

class AccountStatusChangeView(StaffRequiredMixin, View):
    """
    POST /staff/users/<pk>/status/
    Changes user account_status with last-admin safeguard.
    Requirements: 13.1–13.6
    """

    permission_required = 'accounts.change_user'

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        form = AccountStatusForm(request.POST)

        if not form.is_valid():
            messages.error(request, 'Invalid status change request.')
            return redirect('staff:user_detail', pk=pk)

        new_status = form.cleaned_data['account_status']

        # Last-admin safeguard (Req 13.5)
        if new_status in (AccountStatus.SUSPENDED, AccountStatus.INACTIVE):
            if _is_last_administrator(target):
                messages.error(
                    request,
                    'Cannot deactivate or suspend the last remaining Administrator account.',
                )
                return redirect('staff:user_detail', pk=pk)

        previous_status = target.account_status
        target.account_status = new_status
        if new_status == AccountStatus.INACTIVE:
            target.is_active = False
        elif new_status == AccountStatus.ACTIVE:
            target.is_active = True
        target.save(update_fields=['account_status', 'is_active'])

        audit_log(
            actor=request.user,
            action=AuditAction.ACCOUNT_STATUS_CHANGED,
            obj=target,
            description=(
                f'Account status changed for {target.email}: '
                f'{previous_status} → {new_status}'
            ),
            request=request,
        )
        messages.success(
            request,
            f'Account status for {target.get_full_name()} updated to {new_status}.',
        )
        return redirect('staff:user_detail', pk=pk)


# ---------------------------------------------------------------------------
# Group assignment
# ---------------------------------------------------------------------------

class GroupAssignmentView(StaffRequiredMixin, View):
    """
    POST /staff/users/<pk>/groups/
    Adds or removes a user from a group with last-admin safeguard.
    Requirements: 14.1–14.5
    """

    permission_required = 'accounts.change_user'

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        form = GroupAssignmentForm(request.POST)

        if not form.is_valid():
            messages.error(request, 'Invalid group assignment request.')
            return redirect('staff:user_detail', pk=pk)

        group = form.cleaned_data['group']
        action = form.cleaned_data['action']

        if action == 'remove':
            # Last-admin safeguard (Req 14.4)
            if group.name == 'Administrator' and _is_last_administrator(target):
                messages.error(
                    request,
                    'Cannot remove the last Administrator from the Administrator group.',
                )
                return redirect('staff:user_detail', pk=pk)
            target.groups.remove(group)
            direction = 'removed from'
        else:
            target.groups.add(group)
            direction = 'added to'

        audit_log(
            actor=request.user,
            action=AuditAction.GROUP_ASSIGNMENT_CHANGED,
            obj=target,
            description=(
                f'{target.email} {direction} group "{group.name}"'
            ),
            request=request,
        )
        messages.success(
            request,
            f'{target.get_full_name()} {direction} "{group.name}".',
        )
        return redirect('staff:user_detail', pk=pk)


# ---------------------------------------------------------------------------
# Admin-initiated password reset
# ---------------------------------------------------------------------------

class PasswordSetView(StaffRequiredMixin, View):
    """
    POST /staff/users/<pk>/set-password/
    Validates AdminPasswordSetForm, sets the new password, sets
    force_password_change=True, and records an audit log entry.
    The form itself is rendered inline on the user detail page.
    Requirements: 16.1, 16.2, 16.3
    """

    permission_required = 'accounts.change_user'

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        form = AdminPasswordSetForm(request.POST)

        if not form.is_valid():
            # Surface errors back via messages and return to detail page
            error_msgs = ' '.join(
                e for errors in form.errors.values() for e in errors
            )
            messages.error(request, f'Password validation failed. {error_msgs}')
            return redirect('staff:user_detail', pk=pk)

        target.set_password(form.cleaned_data['new_password'])
        target.force_password_change = True
        target.save(update_fields=['password', 'force_password_change'])

        audit_log(
            actor=request.user,
            action=AuditAction.PASSWORD_RESET_ADMIN,
            obj=target,
            description=f'Password reset by admin for: {target.email}',
            request=request,
        )
        messages.success(
            request,
            f'Password for {target.get_full_name()} has been reset. '
            'They will be required to change it on next login.',
        )
        return redirect('staff:user_detail', pk=pk)
