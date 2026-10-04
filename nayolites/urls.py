"""
Root URL configuration for the Nayolites platform.
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

# Custom error handlers (Req 20.1, 20.2, 20.3)
handler403 = 'apps.core.error_views.permission_denied'
handler404 = 'apps.core.error_views.page_not_found'
handler500 = 'apps.core.error_views.server_error'

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # Authentication
    path('auth/', include('apps.accounts.urls', namespace='auth')),

    # Student portal
    path('student/', include('apps.students.urls', namespace='student')),

    # Staff portal
    path('staff/', include('apps.core.staff_urls', namespace='staff')),

    # Courses (public-facing course URLs)
    path('courses/', include('apps.courses.urls', namespace='courses')),

    # REST API v1
    path('api/v1/', include('apps.core.api_urls', namespace='api')),

    # Finance (webhook endpoint — must be outside staff auth middleware)
    path('finance/', include('apps.finance.urls')),

    # Public website (must be last — catches remaining paths)
    path('', include('apps.core.urls', namespace='public')),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
