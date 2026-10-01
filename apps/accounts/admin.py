from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AccountStatus, StaffProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for the custom User model.
    Uses email as the identifier instead of username.
    """
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'account_status', 'is_staff', 'is_active')
    list_filter = ('account_status', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Account status', {'fields': ('account_status', 'force_password_change')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    # Remove username field references
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_number', 'job_title', 'department', 'is_active')
    list_filter = ('is_active', 'department')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'staff_number')
    raw_id_fields = ('user',)
