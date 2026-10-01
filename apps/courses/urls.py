"""
Public-facing course URL patterns.
"""

from django.urls import path

from . import views, application_views

app_name = "courses"

urlpatterns = [
    path("", views.public_courses, name="list"),
    path("<slug:slug>/apply/", application_views.public_apply, name="apply"),
    path("<slug:slug>/apply/confirmation/<str:reference>/", application_views.public_apply_confirmation, name="apply_confirmation"),
    path("<slug:slug>/", views.public_course_detail, name="detail"),
]
