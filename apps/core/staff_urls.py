from django.urls import path

from apps.core import staff_views as v
from apps.accounts import staff_views as user_views
from apps.core.staff_views import GroupListView, GroupDetailView, AuditLogListView, ajax_course_units

# Academic domain CBVs
from apps.courses.staff_views import (
    CourseListView, CourseCreateView, CourseDetailView, CourseEditView,
    CourseActivateView, CourseUnitListView, CourseUnitCreateView, CourseUnitEditView,
)
from apps.students.staff_views import (
    StudentListView, StudentCreateView, StudentDetailView,
    StudentEditView, StudentStatusChangeView,
)
from apps.enrollments.staff_views import (
    AcademicPeriodListView, AcademicPeriodCreateView,
    AcademicPeriodEditView, AcademicPeriodStatusView,
    EnrollmentListView, EnrollmentCreateView,
    EnrollmentDetailView, EnrollmentStatusChangeView,
)
# Results and Content CBVs
from apps.results.staff_views import (
    ResultListView, ResultDetailView, ResultStatusChangeView, ResultEnterView,
)
from apps.content.staff_views import (
    ContentListView, ContentCreateView, ContentDetailView,
    ContentEditView, ContentDeleteView,
)

app_name = "staff"

urlpatterns = [
    # ----------------------------------------------------------------
    # Dashboard
    # ----------------------------------------------------------------
    path("", v.staff_dashboard, name="dashboard"),

    # ----------------------------------------------------------------
    # Students
    # ----------------------------------------------------------------
    path("students/", StudentListView.as_view(), name="students"),
    path("students/create/", StudentCreateView.as_view(), name="student_create"),
    path("students/<int:pk>/", StudentDetailView.as_view(), name="student_detail"),
    path("students/<int:pk>/edit/", StudentEditView.as_view(), name="student_edit"),
    path("students/<int:pk>/status/", StudentStatusChangeView.as_view(), name="student_status"),

    # ----------------------------------------------------------------
    # Courses
    # ----------------------------------------------------------------
    path("courses/", CourseListView.as_view(), name="courses"),
    path("courses/create/", CourseCreateView.as_view(), name="course_create"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course_detail"),
    path("courses/<int:pk>/edit/", CourseEditView.as_view(), name="course_edit"),
    path("courses/<int:pk>/activate/", CourseActivateView.as_view(), name="course_activate"),
    path("courses/<int:course_pk>/units/", CourseUnitListView.as_view(), name="course_units"),
    path("courses/<int:course_pk>/units/add/", CourseUnitCreateView.as_view(), name="course_unit_create"),
    path("courses/<int:course_pk>/units/<int:pk>/edit/", CourseUnitEditView.as_view(), name="course_unit_edit"),

    # ----------------------------------------------------------------
    # Enrollments
    # ----------------------------------------------------------------
    path("enrollments/", EnrollmentListView.as_view(), name="enrollments"),
    path("enrollments/create/", EnrollmentCreateView.as_view(), name="enrollment_create"),
    path("enrollments/<int:pk>/", EnrollmentDetailView.as_view(), name="enrollment_detail"),
    path("enrollments/<int:pk>/status/", EnrollmentStatusChangeView.as_view(), name="enrollment_status"),

    # ----------------------------------------------------------------
    # Academic Periods
    # ----------------------------------------------------------------
    path("academic-periods/", AcademicPeriodListView.as_view(), name="academic_periods"),
    path("academic-periods/create/", AcademicPeriodCreateView.as_view(), name="academic_period_create"),
    path("academic-periods/<int:pk>/edit/", AcademicPeriodEditView.as_view(), name="academic_period_edit"),
    path("academic-periods/<int:pk>/status/", AcademicPeriodStatusView.as_view(), name="academic_period_status"),

    # ----------------------------------------------------------------
    # Results — real CBVs
    # ----------------------------------------------------------------
    path("results/", ResultListView.as_view(), name="results"),
    path("results/enter/", ResultEnterView.as_view(), name="results_enter"),
    path("results/<int:pk>/", ResultDetailView.as_view(), name="result_detail"),
    path("results/<int:pk>/status/", ResultStatusChangeView.as_view(), name="result_status"),

    # AJAX helper — returns course units as JSON for dynamic dropdowns (staff only)
    path("ajax/course-units/", ajax_course_units, name="ajax_course_units"),

    # ----------------------------------------------------------------
    # Content — real CBVs
    # ----------------------------------------------------------------
    path("content/", ContentListView.as_view(), name="content"),
    path("content/create/", ContentCreateView.as_view(), name="content_create"),
    path("content/<int:pk>/", ContentDetailView.as_view(), name="content_detail"),
    path("content/<int:pk>/edit/", ContentEditView.as_view(), name="content_edit"),
    path("content/<int:pk>/delete/", ContentDeleteView.as_view(), name="content_delete"),

    # ----------------------------------------------------------------
    # Finance — prototype stubs
    # ----------------------------------------------------------------
    path("finance/", v.staff_finance, name="finance"),
    path("finance/fee-structures/", v.staff_fee_structures, name="fee_structures"),
    path("finance/invoices/", v.staff_invoices, name="invoices"),
    path("finance/invoices/<str:invoice_number>/", v.staff_invoice_detail, name="invoice_detail"),
    path("finance/payments/", v.staff_payments, name="payments"),
    path("finance/payments/<int:pk>/", v.staff_payment_detail, name="payment_detail"),

    # ----------------------------------------------------------------
    # User management — real views (Phase 7)
    # ----------------------------------------------------------------
    path("users/", user_views.UserListView.as_view(), name="users"),
    path("users/create/", user_views.StaffCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", user_views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/status/", user_views.AccountStatusChangeView.as_view(), name="user_status"),
    path("users/<int:pk>/groups/", user_views.GroupAssignmentView.as_view(), name="user_groups"),
    path("users/<int:pk>/set-password/", user_views.PasswordSetView.as_view(), name="user_set_password"),

    # Staff list (legacy prototype)
    path("staff-members/", v.staff_staff_list, name="staff_list"),

    # ----------------------------------------------------------------
    # Groups & Audit log — real views (Phase 7)
    # ----------------------------------------------------------------
    path("groups/", GroupListView.as_view(), name="groups"),
    path("groups/<int:pk>/", GroupDetailView.as_view(), name="group_detail"),

    # Settings — stub
    path("settings/", v.staff_settings, name="settings"),

    # Audit log
    path("audit-log/", AuditLogListView.as_view(), name="audit_log"),
]
