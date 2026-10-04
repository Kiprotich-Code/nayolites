"""Finance app URLs — webhook endpoint only (staff/student routes are in core/students URLs)."""
from django.urls import path

from apps.finance.webhook_views import PayHeroCallbackView

app_name = 'finance_callbacks'

urlpatterns = [
    path('callbacks/payhero/', PayHeroCallbackView.as_view(), name='payhero_callback'),
]
