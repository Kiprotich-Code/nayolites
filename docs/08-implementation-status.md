# Nayolites --- Implementation Status

This document is maintained by the engineering agent.

Status values:

-   `[ ]` Not started
-   `[-]` In progress
-   `[x]` Complete
-   `[!]` Blocked / requires decision

## Product foundation

-   [ ] Product context finalized
-   [ ] Product requirements finalized
-   [ ] Architecture finalized
-   [ ] Domain model finalized
-   [ ] Design system finalized
-   [ ] Frontend specification finalized
-   [ ] Engineering rules finalized

## Repository foundation

-   [ ] Django project created
-   [ ] Environment configuration
-   [ ] PostgreSQL configured
-   [x] Custom User model
-   [ ] Static files
-   [x] Media files (MEDIA_ROOT configured; file upload path implemented in CourseContent)
-   [x] Base template
-   [x] Shared components
-   [x] Error handling
-   [ ] Logging
-   [-] Test infrastructure (standard TestCase tests written; Hypothesis property tests deferred)

## Authentication

-   [x] Login
-   [x] Logout
-   [x] Password reset
-   [x] Session/security configuration

## RBAC

-   [x] Django groups
-   [x] Django permissions
-   [x] Staff authorization
-   [x] Student ownership restrictions
-   [x] Permission-aware navigation
-   [-] Unauthorized-access tests (standard Django tests written; Hypothesis property tests deferred)

## Students

-   [x] Student model (`StudentProfile` with `StudentStatus` enum)
-   [x] Student creation (staff `StudentCreateView` + `create_student` service)
-   [x] Student list (search by name/admission/email; filter by status/course/period; paginated)
-   [x] Student search/filter
-   [x] Student detail (identity, emergency contact, enrollment history, future-module placeholders)
-   [x] Student profile (student portal `student_profile` view)
-   [x] Student status management (`StudentStatusChangeView` + `change_student_status` service; audit logged)
-   [ ] Student document handling

## Courses

-   [x] Course model (code unique, slug auto, duration, is_active, timestamps)
-   [x] Course CRUD (list, create, detail, edit, activate/deactivate; all permission-gated)
-   [x] Course unit model (unique within course via DB constraint)
-   [x] Course unit CRUD (list, create, edit per course)
-   [x] Course catalogue (public `/courses/` reads from DB; active only)
-   [x] Public course pages (`/courses/<slug>/` — units, description, apply CTA)

## Academic periods and enrollment

-   [x] AcademicPeriod model (name unique, date validation, no single-active constraint)
-   [x] Enrollment model (student+course+period FKs PROTECT; partial uniqueness constraint)
-   [x] Enrollment workflow (`create_enrollment` service; PENDING→ACTIVE via `approve_enrollment`)
-   [x] Duplicate-enrollment protection (DB UniqueConstraint on PENDING/ACTIVE statuses)
-   [x] Enrollment history (all enrollments preserved; student detail + student portal show history)

## Public application flow

-   [x] `CourseApplication` model (reference_number auto-generated; status server-side only)
-   [x] Public application form (`/courses/<slug>/apply/` — CSRF; no privileged fields writable)
-   [x] Confirmation page (reference number only; no internal PK exposed)
-   [x] Audit logged on submission
-   [x] Architectural decision recorded: public submission ≠ automatic enrollment

## Finance

-   [ ] FeeStructure
-   [ ] FeeItem
-   [ ] Invoice
-   [ ] InvoiceItem
-   [ ] Payment
-   [ ] Receipt
-   [ ] Financial calculations
-   [ ] Payment history
-   [ ] Finance permissions
-   [ ] Financial audit trail
-   [ ] M-Pesa integration

## Results

-   [x] Result model (enrollment+course_unit; score_cat/score_exam 0–40/0–60; grade computed; status lifecycle)
-   [x] Result entry (`ResultEnterView` — two-step: select context, then bulk score table)
-   [x] Result validation (`clean()` enforces course_unit.course == enrollment.course; DB unique constraint)
-   [x] Review/approval workflow (DRAFT→SUBMITTED→APPROVED; `approve_result` permission gate)
-   [x] Publication workflow (APPROVED→PUBLISHED; `publish_result` permission gate; `published_at` timestamp)
-   [x] Student results view (published only; own enrollments only; grouped by period)
-   [x] Result permissions (`add_result`, `change_result`, `approve_result`, `publish_result`)
-   [x] Result audit trail (RESULT_ENTERED, RESULT_SUBMITTED, RESULT_APPROVED, RESULT_PUBLISHED)

## Content

-   [x] Course content model (course + optional course_unit; content_type; file upload or URL)
-   [x] Course-unit content (optional FK to CourseUnit; validated unit belongs to course)
-   [x] File uploads (`content_upload_path`; file deleted from storage on content deletion)
-   [x] Student visibility controls (ENROLLED / ALL / STAFF; student view filters by enrollment)
-   [ ] Student documents

## Administration

-   [x] User management
-   [x] Staff management
-   [x] Group management
-   [ ] Permission management
-   [ ] College settings
-   [x] Audit log

## API

-   [ ] API foundation
-   [ ] Public courses API
-   [ ] Authenticated user API
-   [ ] Student API
-   [ ] Staff API
-   [ ] Payment callback endpoints
-   [ ] API permissions/tests

## Reporting

-   [ ] Student reports
-   [ ] Enrollment reports
-   [ ] Finance reports
-   [ ] Results reports
-   [ ] CSV/Excel export where justified
-   [ ] PDF/print documents

## Quality

-   [ ] Accessibility review
-   [ ] Responsive review
-   [ ] Security review
-   [ ] Permission audit
-   [ ] Financial integrity tests
-   [-] Academic integrity tests (Result cross-validation written; Hypothesis property tests deferred)
-   [-] File-upload security review (basic type/size validation deferred; path isolation implemented)
-   [ ] Performance review
-   [ ] Production configuration review
-   [ ] Backup/restore procedure

## Release

-   [ ] Staging environment
-   [ ] Production environment
-   [ ] HTTPS
-   [ ] Database backups
-   [ ] Monitoring/error reporting
-   [ ] Deployment procedure
-   [ ] Rollback procedure
-   [ ] Final acceptance testing

---

## Feature: Authentication, Authorization, RBAC & User Management

**Status:** Complete — Phase 1–7. Authorization boundary tests written (standard Django TestCase); Hypothesis property tests deferred.

### What was implemented

#### User model & manager (`apps/accounts`)

-   Custom `User` model extending `AbstractBaseUser`; `email` is `USERNAME_FIELD`
-   `AccountStatus` enum: `ACTIVE` / `SUSPENDED` / `INACTIVE` — enforced at the authentication layer
-   `force_password_change` flag on the user model
-   `is_active` retained alongside `account_status` for Django Admin compatibility
-   Custom `UserManager` with email-based `create_user` / `create_superuser`

#### Authentication backend & middleware

-   `AccountStatusBackend` — email-based login, timing-attack-safe `DoesNotExist` handling, blocks non-ACTIVE accounts
-   `ForcePasswordChangeMiddleware` — intercepts all portal requests when `force_password_change=True`

#### Profile models

-   `StaffProfile` (`apps/accounts`) — one-to-one with `User`; auto-sets `is_staff=True`; cascades `INACTIVE` on deactivation
-   `StudentProfile` (`apps/students`) — one-to-one with `User`; mutually exclusive with `StaffProfile`

#### Groups & permissions

Six initial staff groups seeded by `create_initial_groups`:

| Group | Key permissions |
|---|---|
| Administrator | All permissions |
| Registrar | Full student + enrollment + application management; course/period view |
| Finance Officer | Full invoice/payment/fee-structure; student/enrollment/course view |
| Academic Officer | Full course + unit + period management; result approve/publish; content management |
| Lecturer | Result entry; content upload/change/delete; academic view |
| Receptionist | View student, course, enrollment, period, invoice, application |

Custom permissions: `publish_result`, `approve_result`, `approve_enrollment`, `reverse_payment`, `deactivate_student`, `activate_course`, `manage_academicperiod`, `review_courseapplication`

---

## Feature: Academic Domain Foundation

**Status:** Complete — Students, Courses, CourseUnits, AcademicPeriods, Enrollments, Public Catalogue, Public Application, Staff Management, Student Portal Foundation.

### Models and migrations

| App | Model | Migration |
|---|---|---|
| `students` | `StudentProfile` + `StudentStatus` | 0001 + 0002 (status) + 0003 (status field) |
| `courses` | `Course`, `CourseUnit` | 0001 (empty) + 0002 (full) |
| `enrollments` | `AcademicPeriod`, `Enrollment` | 0001 (empty) + 0002 (full) |
| `enrollments` | `CourseApplication` | 0003 |

### Domain services (`apps/enrollments/services.py`)

-   `create_student()` — creates User + StudentProfile atomically; audit logged
-   `change_student_status()` — lifecycle change with audit trail
-   `create_enrollment()` — validates student/course/period status; duplicate protection
-   `change_enrollment_status()` — enforced transition map; timestamps set
-   `approve_enrollment()` — convenience wrapper for PENDING→ACTIVE

### Staff views

All use `StaffRequiredMixin` + explicit `permission_required`. No role-string comparisons.

-   Students: list, create, detail, edit, status-change
-   Courses: list, create, detail, edit, activate, unit list, unit create, unit edit
-   Enrollments: list, create, detail, status-change
-   Academic Periods: list, create, edit, status-toggle
-   Dashboard: real DB data; permission-aware quick actions

### Public

-   `/courses/` — database-driven active course catalogue
-   `/courses/<slug>/` — course detail with units
-   `/courses/<slug>/apply/` — public application form (CSRF; no privileged fields)
-   `/courses/<slug>/apply/confirmation/<reference>/` — confirmation by reference number only

### Student portal

-   Dashboard, Profile, My Course, My Enrollments — all real DB data
-   Results, Content, Fees, Documents — placeholder until respective modules implemented

### Architectural decisions made

| Decision | Outcome |
|---|---|
| Public application vs direct enrollment | `CourseApplication` model; staff convert to `StudentProfile` + `Enrollment` |
| When Student record is created | By staff after application review (or directly by staff) |
| Enrollment uniqueness rule | UniqueConstraint on student+course+period where status IN ('PENDING','ACTIVE') |
| Academic period active policy | Multiple periods may be active simultaneously; no global single-active constraint |
| Deletion policy | PROTECT on all enrollment FKs; deactivation preferred over deletion |
| Student status semantics | Explicit enum: ACTIVE/INACTIVE/SUSPENDED/GRADUATED; inactive student cannot be enrolled |
| Course deactivation | `is_active` flag; inactive courses excluded from public catalogue and new enrollments |
| Course-unit uniqueness | DB UniqueConstraint on course+code; active and inactive codes both reserved |

---

## Feature: Results and Content

**Status:** Complete — Result model/lifecycle, CourseContent model/upload, staff entry/approval/publication workflow, student-facing views.

### Models and migrations

| App | Model | Migration |
|---|---|---|
| `results` | `Result` | 0001 (empty) + 0002 (full) |
| `content` | `CourseContent` | 0001 (empty) + 0002 (full) |

### Result domain (`apps/results/`)

**Model fields:** `enrollment` (PROTECT), `course_unit` (PROTECT), `score_cat` (0–40), `score_exam` (0–60), `total` (computed), `grade` (computed A/B/C/D/E), `status` (DRAFT/SUBMITTED/APPROVED/PUBLISHED), `entered_by`, `approved_by`, `published_at`.

**Invariants:**
-   `clean()` enforces `course_unit.course == enrollment.course`
-   `save()` recomputes `total` and `grade` on every save
-   `UniqueConstraint` on `enrollment + course_unit`

**Lifecycle:** `DRAFT → SUBMITTED → APPROVED → PUBLISHED`. Any non-PUBLISHED state can reset to DRAFT. Terminal state: PUBLISHED.

**Service layer** (`apps/results/services.py`): `create_result()`, `update_result_scores()`, `transition_result()`, `bulk_enter_results()`. All audit-logged.

**Staff views:** list (filters + status counts), detail (multi-button lifecycle actions), enter (two-step bulk entry — select context then score table), status-change (permission-gated per transition).

**Student view:** Only PUBLISHED results for the authenticated student's own enrollments, grouped by academic period.

### Content domain (`apps/content/`)

**Model fields:** `course` (PROTECT), `course_unit` (optional PROTECT), `title`, `description`, `content_type` (PDF/VIDEO_URL/LINK/FILE), `file` (upload), `url`, `visibility` (ENROLLED/ALL/STAFF), `uploaded_by`.

**Invariants:**
-   `clean()` validates `course_unit.course == course`
-   `clean()` rejects simultaneous file + url
-   File deleted from storage when content item is deleted

**Staff views:** list (filter by q/course/visibility), create (file upload + enctype), detail, edit, delete (with confirmation).

**Student view:** Only ENROLLED and ALL visibility items for courses the student is actively enrolled in. STAFF-only content never returned. Grouped by course then unit.

### Audit actions added

`RESULT_ENTERED`, `RESULT_SUBMITTED`, `RESULT_APPROVED`, `RESULT_PUBLISHED`, `CONTENT_UPLOADED`, `CONTENT_UPDATED`, `CONTENT_DELETED`

### Architectural decisions made

| Decision | Outcome |
|---|---|
| Course content scope | Content attaches to Course; course_unit FK is optional (both models supported) |
| Result cross-validation | Enforced in `clean()` and `bulk_enter_results()`; not only a form validation |
| File upload security | Path isolation via `content_upload_path`; full file-type validation deferred to security review |
| Result visibility | Only PUBLISHED results visible to students; DRAFT/SUBMITTED/APPROVED are staff-only |
| Content visibility | ENROLLED = enrolled students only; ALL = any authenticated student; STAFF = never shown to students |

---

## Architectural decisions pending

### Fee structure and academic period

Decide whether a `FeeStructure` must always belong to an `AcademicPeriod`.

### Receipt model

Decide whether `Receipt` should be a dedicated model or a representation generated from a confirmed `Payment`.

### Student registration

Public `SignupView` exists and creates a `StudentProfile` with a `PENDING-<uuid>` admission number. Decide whether self-registration is supported in production or whether staff creation is the only path.

### Lecturer assignment

Introduce `CourseUnitInstructor` when lecturer-specific content/results filtering requires it.

### File upload security

Validate MIME type server-side (not just extension); enforce maximum file size; restrict upload path access via Django's `FileResponse` or storage backend ACLs before production.

---

## Agent notes

The engineering agent should update this file after meaningful implementation work.

Never mark a feature complete merely because code exists. Use the Definition of Done in `07-engineering-rules.md`.
