"""
Student portal URL patterns.
"""

from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    path('', views.student_dashboard, name='dashboard'),
    path('profile/', views.student_profile, name='profile'),
    path('course/', views.student_course, name='course'),
    path('enrollments/', views.student_enrollments, name='enrollments'),
    path('fees/', views.student_fees, name='fees'),
    path('fees/invoice/<str:invoice_number>/', views.student_invoice_detail, name='invoice_detail'),
    path('fees/receipt/<str:receipt_number>/', views.student_receipt, name='receipt'),
    path('results/', views.student_results, name='results'),
    path('documents/', views.student_documents, name='documents'),
    path('content/', views.student_content, name='content'),
]
