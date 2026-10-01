"""
Authentication URL patterns.
"""

from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path

from . import views

app_name = 'auth'

urlpatterns = [
    # Login / logout
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Password change (self-service, force-change enforcement)
    path('password-change/', views.PasswordChangeView.as_view(), name='password_change'),

    # Password reset flow (Django built-ins with custom templates)
    path(
        'forgot-password/',
        PasswordResetView.as_view(
            template_name='auth/forgot_password.html',
            email_template_name='registration/password_reset_email.txt',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='/auth/forgot-password/done/',
        ),
        name='forgot_password',
    ),
    path(
        'forgot-password/done/',
        PasswordResetDoneView.as_view(template_name='auth/forgot_password_done.html'),
        name='password_reset_done',
    ),
    path(
        'reset-password/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(
            template_name='auth/reset_password.html',
            success_url='/auth/reset-password/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset-password/complete/',
        PasswordResetCompleteView.as_view(template_name='auth/reset_password_complete.html'),
        name='password_reset_complete',
    ),

    # Post-login portal routing
    path('redirect/', views.PostLoginRedirectView.as_view(), name='post_login_redirect'),

    # Student self-registration
    path('signup/', views.SignupView.as_view(), name='signup'),
]
