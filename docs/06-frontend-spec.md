# Nayolites --- Frontend Specification

## 1. Frontend architecture

Use Django templates and Bootstrap 5.

The UI should be componentized through reusable template
partials/components.

Suggested template structure:

``` text
templates/
├── base.html
├── components/
├── public/
├── student/
└── staff/
```

JavaScript should progressively enhance the interface rather than become
the application's entire architecture.

## 2. Public website

Primary pages:

-   Home
-   About
-   Courses
-   Course detail
-   Admissions
-   Fees
-   Contact
-   Login

### Homepage objectives

A visitor should quickly understand:

1.  What Nayolites is.
2.  What it teaches.
3.  Who it serves.
4.  How to explore courses.
5.  How to contact or begin the relevant process.

Do not fill the homepage with invented statistics or marketing claims.

### Courses

The course listing should make it easy to:

-   Browse courses
-   Search/filter if the catalogue warrants it
-   Open course details
-   Understand duration and relevant information

## 3. Authentication screens

Include:

-   Login
-   Password reset request
-   Password reset
-   Appropriate session/error feedback

The interface should be simple and focused.

## 4. Student portal

### Student dashboard

The dashboard should prioritize actionable information.

Suggested sections:

-   Current enrollment
-   Academic period
-   Financial summary
-   Recent payments
-   Recent/published results
-   Available course content
-   Important notices when such a feature exists

Avoid filling the dashboard with meaningless metric cards.

### Student navigation

Suggested:

-   Dashboard
-   My Profile
-   My Course
-   Enrollments
-   Fees & Payments
-   Results
-   Documents
-   Course Content

Only show sections the student can actually use.

### Student profile

Allow the student to view their own information.

Editable fields should be explicitly defined; sensitive institutional
fields may be read-only.

### Fees & payments

Should clearly show:

-   Invoices
-   Invoice details
-   Amount due
-   Successful payments
-   Payment status
-   Receipt access

Do not present financial information as decorative dashboard cards
alone.

### Results

Results should provide:

-   Academic period
-   Course
-   Course unit
-   Score
-   Grade
-   Publication status where relevant

Students must only see published results.

## 5. Staff portal

### Staff dashboard

The dashboard should adapt to permissions.

Possible sections:

-   Student operations
-   Enrollment operations
-   Finance
-   Academic results
-   Course/content management
-   Reports
-   Administration

The dashboard should prioritize the staff member's actual work.

### Staff navigation

Navigation must be permission-aware.

However, backend authorization remains mandatory.

### Students

Staff screens should support:

-   Search
-   Filtering
-   Student list
-   Student detail
-   Relevant actions based on permission
-   Enrollment history
-   Financial summary where authorized
-   Academic information where authorized

### Courses

Staff with permissions can:

-   Create course
-   Edit course
-   Activate/deactivate course
-   Manage course units
-   Manage course content where authorized

### Enrollment

Staff should be able to:

-   View enrollments
-   Create enrollments where authorized
-   Change enrollment status where authorized
-   View academic history

### Finance

Finance screens should support:

-   Fee structures
-   Fee items
-   Invoices
-   Invoice details
-   Payments
-   Receipts
-   Search/filter
-   Reconciliation-related information as the integration matures

### Results

Academic staff should be able to:

-   Enter results
-   Review results
-   Submit/approve as authorized
-   Publish results if authorized

Students should never see drafts.

## 6. Administrative screens

Administration should include:

-   Users
-   Staff
-   Groups/roles
-   Permissions
-   Institutional settings
-   Audit log

The interface should be designed for operations rather than looking like
Django Admin.

Django Admin may remain available as a trusted back-office/developer
tool.

## 7. Navigation behavior

The interface should provide:

-   clear current-section indication
-   predictable breadcrumbs where useful
-   consistent page titles
-   obvious primary actions
-   appropriate secondary actions

## 8. Destructive actions

Destructive or irreversible actions should require explicit
confirmation.

Where historical data must be preserved, prefer:

-   deactivate
-   archive
-   reverse
-   cancel
-   void

rather than hard deletion.

## 9. Error handling

Errors should explain:

-   what went wrong
-   what the user can do
-   whether data was saved
-   whether they should retry

Never expose stack traces to normal users.

## 10. Print/document UX

Financial receipts and important academic documents should have clean
print/PDF representations.

These should be designed documents, not browser screenshots.

## 11. Frontend implementation sequence

Build the visual foundation first:

1.  Global layout
2.  Typography
3.  Colors/design tokens
4.  Navigation
5.  Buttons/forms
6.  Tables
7.  Alerts/statuses
8.  Empty/error states

Then build representative screens:

1.  Public home
2.  Course catalogue
3.  Login
4.  Student dashboard
5.  Staff dashboard
6.  Student list
7.  Student detail
8.  Finance table/detail
9.  Results table/detail

Only after the visual language is coherent should the rest of the
screens be expanded.
