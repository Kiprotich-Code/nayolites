"""
Authentication views for the Nayolites platform.

Security-critical: these views handle login, logout, password reset,
and the force-password-change flow.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetConfirmView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from .models import User

from apps.core.audit import audit_log
from apps.core.models import AuditAction


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginView(View):
    """
    Email + password login with:
    - AccountStatusBackend enforcement (SUSPENDED/INACTIVE blocks)
    - Targeted error messages for each denial reason
    - AuditLog entries for success and failure
    - force_password_change redirect on first login
    - next= parameter support (validated against allowed hosts)

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 17.2, 17.3
    Security-critical.
    """

    template_name = 'auth/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(self._get_portal_url(request.user))
        return render(request, self.template_name, {'page_title': 'Sign In'})

    def post(self, request):
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not email or not password:
            messages.error(request, 'Please enter your email address and password.')
            return render(request, self.template_name, {
                'page_title': 'Sign In',
                'submitted_email': email,
            })

        user = authenticate(request, username=email, password=password)

        if user is None:
            # Check why authentication failed
            denied_status = getattr(request, '_auth_denied_status', None)
            if denied_status == 'SUSPENDED':
                msg = (
                    'Your account has been suspended. '
                    'Please contact the college administration.'
                )
            elif denied_status == 'INACTIVE':
                msg = (
                    'Your account is inactive. '
                    'Please contact the college administration.'
                )
            else:
                msg = 'The email address or password you entered is incorrect.'

            # Audit: failed login (Req 2.2, 17.2, 17.3)
            audit_log(
                actor=None,
                action=AuditAction.LOGIN_FAILED,
                description=f'Failed login attempt for: {email}',
                request=request,
            )
            return render(request, self.template_name, {
                'page_title': 'Sign In',
                'submitted_email': email,
                'error': msg,
            })

        # Successful authentication
        login(request, user)

        # Audit: successful login (Req 2.5, 17.2)
        audit_log(
            actor=user,
            action=AuditAction.LOGIN_SUCCESS,
            description=f'User logged in: {user.email}',
            request=request,
            obj=user,
        )

        # Force password change takes priority over next= routing (Req 3.2)
        if getattr(user, 'force_password_change', False):
            return redirect(reverse_lazy('auth:password_change'))

        # Honour next= parameter if safe (Req 4.3)
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
        ):
            return redirect(next_url)

        return redirect(self._get_portal_url(user))

    @staticmethod
    def _get_portal_url(user):
        if hasattr(user, 'staffprofile') and user.is_staff:
            return '/staff/'
        if hasattr(user, 'studentprofile'):
            return '/student/'
        return '/'


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutView(View):
    """
    POST-only logout view. Flushes session and records audit entry.
    GET requests redirect to login (no silent logout on link-click).

    Requirements: 2.6, 17.2
    """

    def post(self, request):
        if request.user.is_authenticated:
            audit_log(
                actor=request.user,
                action=AuditAction.LOGOUT,
                description=f'User logged out: {request.user.email}',
                request=request,
                obj=request.user,
            )
        logout(request)
        return redirect('/')

    def get(self, request):
        return redirect('auth:login')


# ---------------------------------------------------------------------------
# Password Change (self-service)
# ---------------------------------------------------------------------------

class PasswordChangeView(LoginRequiredMixin, View):
    """
    Self-service password change. On success:
    - Clears force_password_change flag
    - Keeps session alive via update_session_auth_hash
    - Records AuditLog(password_changed)
    - Redirects to appropriate portal

    Requirements: 3.3, 3.4, 17.2
    """

    login_url = '/auth/login/'
    template_name = 'auth/password_change.html'

    def get(self, request):
        form = PasswordChangeForm(user=request.user)
        return render(request, self.template_name, {
            'form': form,
            'page_title': 'Change Password',
        })

    def post(self, request):
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Clear force_password_change flag (Req 3.3)
            if getattr(user, 'force_password_change', False):
                user.force_password_change = False
                user.save(update_fields=['force_password_change'])
            # Keep session alive (Req 3.3)
            update_session_auth_hash(request, user)
            # Audit (Req 3.4, 17.2)
            audit_log(
                actor=user,
                action=AuditAction.PASSWORD_CHANGED,
                description=f'Password changed by user: {user.email}',
                request=request,
                obj=user,
            )
            messages.success(request, 'Your password has been updated.')
            return redirect(LoginView._get_portal_url(user))

        return render(request, self.template_name, {
            'form': form,
            'page_title': 'Change Password',
        })


# ---------------------------------------------------------------------------
# Post-login redirect
# ---------------------------------------------------------------------------

class PostLoginRedirectView(LoginRequiredMixin, View):
    """
    Resolves the correct portal based on user profile type.
    Respects 'next' parameter before any default routing.

    Requirements: 4.1, 4.2, 4.3, 4.4
    """

    login_url = '/auth/login/'

    def get(self, request):
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
        ):
            return redirect(next_url)

        if hasattr(request.user, 'staffprofile') and request.user.is_staff:
            return redirect('/staff/')
        if hasattr(request.user, 'studentprofile'):
            return redirect('/student/')
        return redirect('/')


# ---------------------------------------------------------------------------
# Student self-registration
# ---------------------------------------------------------------------------

class SignupView(View):
    """
    Student self-registration.
    Creates a User + minimal StudentProfile, then logs in and redirects
    to the student portal.

    The StudentProfile admission_number is auto-generated as a placeholder;
    the Registrar completes the profile with the official number later.

    Requirements: student portal access, post-login routing
    """

    template_name = 'auth/signup.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(LoginView._get_portal_url(request.user))
        from .forms import StudentSignupForm
        return render(request, self.template_name, {
            'form': StudentSignupForm(),
            'page_title': 'Create Student Account',
        })

    def post(self, request):
        from .forms import StudentSignupForm
        from django.db import transaction
        from apps.students.models import StudentProfile
        import uuid

        form = StudentSignupForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form,
                'page_title': 'Create Student Account',
            })

        cd = form.cleaned_data
        with transaction.atomic():
            user = User.objects.create_user(
                email=cd['email'],
                password=cd['password'],
                first_name=cd['first_name'],
                last_name=cd['last_name'],
                phone=cd.get('phone', ''),
            )
            # Generate a temporary admission number placeholder
            temp_admission = f'PENDING-{uuid.uuid4().hex[:8].upper()}'
            StudentProfile.objects.create(
                user=user,
                admission_number=temp_admission,
            )

        login(request, user, backend='apps.accounts.backends.AccountStatusBackend')
        audit_log(
            actor=user,
            action=AuditAction.LOGIN_SUCCESS,
            description=f'New student account created and signed in: {user.email}',
            request=request,
            obj=user,
        )
        messages.success(
            request,
            f'Welcome, {user.first_name}! Your account has been created. '
            'The registrar will complete your profile with your official admission number.'
        )
        return redirect('/student/')
