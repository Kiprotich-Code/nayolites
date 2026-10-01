# Nayolites --- Architecture

## 1. Architectural style

Use a Django monolith initially.

The monolith is intentional.

It should have clear internal module boundaries without pretending to be
a distributed system.

Preferred stack:

-   Python
-   Django
-   Django REST Framework
-   PostgreSQL
-   Bootstrap 5
-   Django templates
-   Appropriate testing tools
-   Standard production WSGI/ASGI deployment

## 2. Architectural principles

### Principle 1 --- Boring technology wins

Prefer mature, explicit, maintainable technology over fashionable
complexity.

### Principle 2 --- Domain-first

Organize the application around business domains rather than technical
layers alone.

### Principle 3 --- One source of truth

Avoid duplicated state.

### Principle 4 --- Backend enforcement

Security and authorization must be enforced server-side.

### Principle 5 --- Historical integrity

Financial and academic records must preserve historical truth.

### Principle 6 --- Explicit business rules

Important business rules should be visible in code and tests, not hidden
in templates or JavaScript.

### Principle 7 --- Progressive complexity

Start simple. Add abstraction only when a real requirement justifies it.

## 3. Suggested Django apps

``` text
apps/
├── accounts/
├── students/
├── courses/
├── enrollments/
├── finance/
├── results/
├── content/
└── core/
```

Possible future apps:

-   admissions
-   attendance
-   notifications
-   certificates
-   reporting
-   lms

Do not create future apps just to make the directory look
enterprise-grade.

## 4. Responsibility boundaries

### accounts

Authentication, User, Staff profile, groups/permissions integration.

### students

Student profile and student-specific operations.

### courses

Course and course unit definitions.

### enrollments

Academic periods and enrollment.

### finance

Fee structures, invoices, payments, receipts.

### results

Academic results and publication.

### content

Course content and student documents where appropriate.

### core

College settings, audit infrastructure, shared utilities.

## 5. Presentation architecture

Use Django server-rendered templates for the primary web application.

Use Bootstrap 5 as the baseline UI system.

Use JavaScript selectively for progressive enhancement.

Do not turn the project into a client-side SPA without a demonstrated
requirement.

## 6. API architecture

DRF provides JSON APIs.

The API should reuse the same business/domain rules as HTML views.

Do not create a second, contradictory implementation of business logic
exclusively for the API.

## 7. Authentication versus authorization

Authentication answers:

> Who is this user?

Authorization answers:

> What is this user allowed to do?

Never combine these concepts into one role flag.

## 8. Data integrity

Use database constraints for invariants that the database can enforce.

Examples:

-   Unique email
-   Unique admission number
-   Unique staff number
-   Unique course code
-   Unique course-unit code within a course
-   Unique invoice number
-   Unique payment reference
-   Appropriate enrollment uniqueness

Use application validation for rules requiring cross-object reasoning.

## 9. Deletion policy

Use `PROTECT` for records whose deletion would destroy important
historical information.

Examples:

-   Enrollment
-   Invoice
-   Payment
-   Result

Use `CASCADE` for true dependent children where historical preservation
is not independently required.

Examples:

-   InvoiceItem under an Invoice
-   FeeItem under a FeeStructure, subject to future archival
    requirements

Deletion should not be the default administrative workflow for important
records. Status/archive/deactivation is often safer.

## 10. Finance architecture

Finance is record-driven.

The system should derive financial state from:

-   invoices
-   invoice items
-   successful payments

Do not make the student profile the accounting ledger.

Payment providers are integrations around the Payment domain.

## 11. Result architecture

Results should be independently auditable and should have a clear
publication lifecycle.

A student-facing query should only return:

-   the current authenticated student
-   their enrollments
-   their published results

## 12. Configuration

Institutional configuration belongs in the database where it is
operationally configurable.

Business-critical configuration should not require source-code edits.

## 13. What not to introduce without approval

Do not introduce:

-   Microservices
-   Event sourcing
-   CQRS
-   GraphQL
-   Kubernetes
-   Message brokers
-   Complex workflow engines
-   Generic plugin architectures
-   Multi-tenancy
-   A separate frontend framework

unless a documented requirement makes one necessary.

## 14. Deployment philosophy

Development, staging, and production configuration should be separated.

Secrets must not be committed.

Production should use:

-   PostgreSQL
-   Secure secret configuration
-   HTTPS
-   Proper static/media handling
-   Backups
-   Logging
-   Error monitoring
-   Database migrations

Deployment architecture should remain simple enough for the team to
operate confidently.
