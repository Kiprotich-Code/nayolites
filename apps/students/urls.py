"""
Student portal URL patterns.
"""

from django.urls import path
from . import views

from apps.finance.student_views import (
    StudentFinanceSummaryView, StudentInvoiceListView, StudentInvoiceDetailView,
    StudentPaymentListView, StudentReceiptListView, StudentReceiptDetailView,
    StudentStatementView, StudentPaymentInitiateView,
)

app_name = 'student'

urlpatterns = [
    path('', views.student_dashboard, name='dashboard'),
    path('profile/', views.student_profile, name='profile'),
    path('course/', views.student_course, name='course'),
    path('enrollments/', views.student_enrollments, name='enrollments'),
    path('results/', views.student_results, name='results'),
    path('documents/', views.student_documents, name='documents'),
    path('content/', views.student_content, name='content'),

    # Finance routes
    path('finance/', StudentFinanceSummaryView.as_view(), name='finance'),
    path('finance/invoices/', StudentInvoiceListView.as_view(), name='my_invoices'),
    path('finance/invoices/<int:pk>/', StudentInvoiceDetailView.as_view(), name='my_invoice_detail'),
    path('finance/payments/', StudentPaymentListView.as_view(), name='my_payments'),
    path('finance/receipts/', StudentReceiptListView.as_view(), name='my_receipts'),
    path('finance/receipts/<int:pk>/', StudentReceiptDetailView.as_view(), name='my_receipt_detail'),
    path('finance/statement/', StudentStatementView.as_view(), name='my_statement'),
    path('finance/pay/<int:enrollment_pk>/', StudentPaymentInitiateView.as_view(), name='pay'),
]
