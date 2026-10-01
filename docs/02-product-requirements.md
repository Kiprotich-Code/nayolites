# Nayolites --- Product Requirements

## 1. Authentication and identity

The system shall use a custom Django User model.

The User represents authentication and common identity.

Student-specific data belongs to Student.

Staff-specific data belongs to Staff.

A user may have a student profile, a staff profile, or neither.

Email should be unique.

The system should support secure login, logout, password reset, and
appropriate session handling.

Admission numbers and staff numbers are institutional identifiers; they
should not be treated as substitutes for the core User identity unless
explicitly designed that way.

## 2. Authorization

Authorization shall use Django Groups and Permissions.

Do not create a single hard-coded role field as the primary
authorization mechanism.

A staff member may belong to multiple groups.

Example groups:

-   Administrator
-   Registrar
-   Finance Officer
-   Academic Officer
-   Lecturer
-   Receptionist

Permissions should be granular enough to support least-privilege access.

Examples:

-   view_student
-   add_student
-   change_student
-   view_enrollment
-   add_enrollment
-   view_invoice
-   add_invoice
-   view_payment
-   add_payment
-   change_payment
-   view_result
-   add_result
-   change_result
-   publish_result

Student access must additionally be restricted by
ownership/queryset/object-level rules.

Hiding a button is never sufficient authorization.

## 3. Students

Student records shall include:

-   User relationship
-   Admission number
-   Personal information
-   Contact information
-   Emergency contact
-   Status
-   Timestamps

Student status should be modeled explicitly rather than inferred from
unrelated fields.

The system should support historical student enrollments.

## 4. Staff

Staff records shall include:

-   User relationship
-   Staff number
-   Job title
-   Department
-   Active status

Authorization comes from Django Groups and Permissions.

## 5. Courses

Administrators/authorized staff can manage:

-   Course code
-   Course name
-   Description
-   Duration
-   Active status

A course can contain multiple course units.

Course units should have:

-   Course
-   Code
-   Name
-   Description
-   Active status

Course unit codes should be unique within their course.

## 6. Academic periods

The system shall use an `AcademicPeriod` concept rather than assuming
every institution uses semesters.

Examples:

-   2026
-   2026 Term 1
-   2026 Semester 1
-   January 2026 Intake

An academic period has:

-   Name
-   Start date
-   End date
-   Active status

## 7. Enrollment

Enrollment is the central academic relationship between a Student and a
Course.

An enrollment belongs to:

-   Student
-   Course
-   Academic period

It also has:

-   Enrollment date
-   Status

The system should prevent accidental duplicate active enrollments for
the same student/course/period.

Historical enrollment records should be preserved.

## 8. Finance

Finance must be transaction/history oriented.

The conceptual chain is:

FeeStructure → FeeItem → Invoice → InvoiceItem → Payment

A fee structure can contain multiple fee items.

Example:

-   Tuition
-   Registration
-   Materials
-   Examination

When an invoice is created, invoice items should preserve the amounts
that were actually charged at that time.

Changing a future fee structure must not silently rewrite historical
invoices.

Balance should be derived from financial records:

Invoice total - successful payments

Do not maintain duplicated source-of-truth fields such as:

-   student.balance
-   student.amount_paid
-   current_fee

unless there is a documented caching requirement.

## 9. Payments

A Payment belongs to an Invoice.

A payment has:

-   Amount
-   Method
-   Reference
-   Status
-   Paid timestamp
-   Creation timestamp

Initial payment methods may include:

-   M-Pesa
-   Bank
-   Cash
-   Other

Payment integration providers are mechanisms, not the financial domain
itself.

M-Pesa integration should ultimately create/confirm Payments.

Provider-specific callback IDs, request payloads, reconciliation
information, and other integration metadata should be isolated from the
core financial model where practical.

## 10. Receipts

Receipts should be generated from confirmed/successful payments.

Receipt numbers must be unique.

A receipt should be reproducible from the underlying payment and should
preserve historical financial information.

## 11. Results

A Result belongs to:

-   Enrollment
-   Course unit

It contains:

-   Score
-   Grade
-   Status
-   Publication timestamp

Results should support a controlled lifecycle, such as:

Draft → Submitted/Reviewed → Approved → Published

Exact workflow may be refined during implementation.

Students should only see their own published results.

The system must validate that the course unit belongs to the course
associated with the enrollment.

## 12. Course content

The initial product should provide lightweight content management, not a
full LMS.

Course content may contain:

-   Title
-   Description
-   File
-   URL
-   Visibility
-   Creation timestamp

Content may eventually belong to a course and/or a specific course unit.

Do not introduce assignments, quizzes, grading workflows, discussion
forums, or other LMS features unless separately approved.

## 13. Student documents

Students may have documents such as:

-   Identification-related documents
-   Admission documents
-   Certificates
-   Other institutional documents

Documents must be access-controlled.

## 14. Institutional settings

College-level settings should be configurable through data.

Examples:

-   College name
-   Logo
-   Address
-   Phone
-   Email
-   Website
-   Currency
-   Public contact details

Do not hard-code institution identity throughout templates and business
logic.

## 15. Audit logging

Important operations should be auditable.

Especially:

-   Student record changes
-   Permission/group changes
-   Fee changes
-   Invoice changes
-   Payment changes
-   Result changes
-   Result publication
-   Important administrative actions

Audit records should answer:

-   Who acted?
-   What happened?
-   Which object was affected?
-   When did it happen?

## 16. API

Use Django REST Framework for:

-   Public course APIs
-   Authenticated student APIs
-   Staff APIs where useful
-   Payment callbacks/integrations
-   Future external/mobile clients

The primary web application may remain server-rendered Django.

Example endpoints:

GET /api/v1/public/courses/ GET /api/v1/public/courses/{id}/ GET
/api/v1/me/ GET /api/v1/me/enrollments/ GET /api/v1/me/payments/ GET
/api/v1/me/results/

Staff APIs should be permission-protected.

## 17. Non-functional requirements

The system should prioritize:

-   Security
-   Data integrity
-   Accessibility
-   Responsive design
-   Maintainability
-   Clear error handling
-   Auditability
-   Reasonable performance
-   Testability
-   Predictable deployments

No feature is considered complete merely because its happy-path code
works.
