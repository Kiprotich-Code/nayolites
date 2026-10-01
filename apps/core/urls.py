"""
Public website URL patterns.
"""

from django.urls import path
from . import views

app_name = 'public'

urlpatterns = [
    path('', views.public_home, name='home'),
    path('about/', views.public_about, name='about'),
    path('courses/', views.public_courses, name='courses'),
    path('courses/<slug:slug>/', views.public_course_detail, name='course_detail'),
    path('admissions/', views.public_admissions, name='admissions'),
    path('fees/', views.public_fees, name='fees'),
    path('contact/', views.public_contact, name='contact'),
]
