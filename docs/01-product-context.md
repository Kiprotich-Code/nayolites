# Nayolites Compute and Media College --- Product Context

## 1. Purpose

Nayolites Compute and Media College is building a professional college
operations platform for its students, staff, administrators, and public
visitors.

The product should feel like software the institution owns and relies on
operationally---not a generic school template, a demo project, or an
AI-generated dashboard.

The system will combine:

-   Public institutional website
-   Student self-service portal
-   Staff operations portal
-   Student and staff identity
-   Role-based access control
-   Courses and course units
-   Student enrollment
-   Fees, invoices, payments, and receipts
-   Academic results
-   Lightweight course content/documents
-   Institutional settings
-   Audit history
-   REST APIs for integrations and future clients

## 2. Product philosophy

The product should be:

-   Professional
-   Reliable
-   Simple to operate
-   Visually restrained
-   Easy to learn
-   Secure
-   Maintainable
-   Configurable where configuration is genuinely useful
-   Specific to Nayolites without unnecessarily becoming a generic
    multi-tenant SaaS

The product should prioritize clarity over novelty.

Do not add complexity merely because a technology or pattern is
fashionable.

## 3. Primary users

### Public visitor

Can:

-   View the college
-   View courses
-   Learn about admissions
-   View contact/institutional information
-   Access public course information
-   Reach the login/application/contact entry points

### Student

Can, subject to permissions and enrollment:

-   Sign in
-   View and manage their own profile information
-   View their enrollments
-   View course information
-   View course content made available to them
-   View invoices and payment history
-   Make or initiate payments through supported mechanisms
-   View receipts
-   View published academic results
-   Access permitted documents

A student must never be able to access another student's private
records.

### Staff

Staff capabilities depend on assigned Django permissions/groups.

Examples include:

-   Administrator
-   Registrar
-   Finance Officer
-   Academic Officer
-   Lecturer
-   Receptionist

These are examples, not hard-coded system roles.

A staff member may have multiple roles/groups.

### Administrator

An authorized administrator can configure and operate the system,
including:

-   Users
-   Groups/roles
-   Permissions
-   Students
-   Staff
-   Courses
-   Course units
-   Academic periods
-   Enrollments
-   Fee structures
-   Invoices
-   Payments
-   Results
-   Content
-   Institutional settings
-   Audit information

## 4. Product boundaries

### Included in the initial product

-   Authentication
-   Role-based access control
-   Student records
-   Staff records
-   Courses
-   Course units
-   Academic periods
-   Enrollment
-   Fees
-   Invoices
-   Payments
-   Receipts
-   Results
-   Lightweight course content
-   Student documents
-   Audit logging
-   Public website
-   Student portal
-   Staff portal
-   REST API foundation

### Explicitly not part of the initial product

Do not introduce these unless separately approved:

-   Full LMS
-   Assignments
-   Quizzes
-   Discussion forums
-   Parent portal
-   Payroll
-   Full accounting/GL
-   Biometric attendance
-   Complex timetable engine
-   Mobile application
-   Multi-tenancy
-   Microservices
-   Kubernetes
-   CQRS/event sourcing
-   GraphQL
-   Complex workflow engines
-   AI features for their own sake

These may become future products/modules.

## 5. Product success criteria

The product should allow a real college to perform its core operational
workflows without developer intervention for normal configuration.

For example:

1.  Administrator creates a course.
2.  Administrator creates/registers a student.
3.  Student receives an account.
4.  Student enrolls in a course.
5.  System creates the appropriate financial obligation/invoice.
6.  Student pays.
7.  Payment is recorded and confirmed.
8.  Receipt is available.
9.  Authorized academic staff enter results.
10. Authorized staff review/approve/publish results.
11. Student sees only their own published results.

The system should make these workflows obvious, safe, auditable, and
repeatable.

## 6. Long-term direction

The architecture should leave room for later modules such as:

-   Admissions
-   Attendance
-   Timetables
-   Certificates
-   Notifications
-   Reporting
-   Full LMS
-   External integrations
-   Mobile clients

Future extensibility must not justify premature complexity in version
one.
