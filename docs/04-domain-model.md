# Nayolites --- Domain Model

## 1. Core relationship

``` text
User
├── Student
│   └── Enrollment
│       ├── Course
│       │   ├── CourseUnit
│       │   └── CourseContent
│       ├── AcademicPeriod
│       ├── Invoice
│       │   ├── InvoiceItem
│       │   └── Payment
│       └── Result
│
└── Staff
```

Additional domain objects:

``` text
CollegeSettings
AuditLog
FeeStructure
FeeItem
StudentDocument
```

## 2. User

Authentication identity.

Suggested fields:

-   id
-   email
-   password
-   first_name
-   last_name
-   phone
-   active status
-   standard Django permission/group fields
-   timestamps where appropriate

Use Django's custom User model from the beginning.

## 3. Student

One-to-one with User.

Fields include:

-   user
-   admission_number
-   date_of_birth
-   address
-   emergency_contact_name
-   emergency_contact_phone
-   status
-   created_at
-   updated_at

Student is a domain profile, not a second authentication system.

## 4. Staff

One-to-one with User.

Fields include:

-   user
-   staff_number
-   job_title
-   department
-   active

Authorization is through Groups and Permissions.

## 5. Course

Fields:

-   code
-   name
-   description
-   duration
-   active
-   timestamps

A Course contains many CourseUnits.

## 6. CourseUnit

Fields:

-   course
-   code
-   name
-   description
-   active

Constraint:

Course + code should be unique.

## 7. AcademicPeriod

Fields:

-   name
-   start_date
-   end_date
-   active

The model intentionally avoids hard-coding semester/term semantics.

## 8. Enrollment

Fields:

-   student
-   course
-   academic_period
-   enrolled_at
-   status

Enrollment is the central relationship for the student's academic
history.

A student can have multiple enrollments across time.

A course can have many enrollments.

An academic period can have many enrollments.

## 9. FeeStructure

A reusable definition of charges.

Potential fields:

-   course
-   academic_period, if fee schedules vary by period
-   name
-   active
-   timestamps

The final decision about whether academic period is mandatory should be
made before migration.

## 10. FeeItem

Belongs to FeeStructure.

Fields:

-   fee_structure
-   name
-   amount

Example:

``` text
Tuition       35,000
Registration   2,000
Materials      3,000
Examination    5,000
```

## 11. Invoice

Belongs to Enrollment.

Fields:

-   enrollment
-   invoice_number
-   issued_at
-   due_date
-   status

An enrollment may have multiple invoices.

## 12. InvoiceItem

Belongs to Invoice.

Fields:

-   invoice
-   description
-   amount

Invoice items preserve the historical amount charged.

## 13. Payment

Belongs to Invoice.

Fields:

-   invoice
-   amount
-   method
-   reference
-   status
-   paid_at
-   created_at

Potential future fields/related model:

-   provider
-   provider_transaction_id
-   provider_payload
-   reconciliation status

Keep provider-specific concerns separate from the core Payment concept
where practical.

## 14. Receipt

A confirmed payment may produce a receipt.

The receipt should preserve:

-   receipt number
-   payment
-   issue date
-   relevant payment/invoice information

A generated PDF can be a representation of the receipt rather than the
source of truth.

## 15. Result

Belongs to Enrollment and CourseUnit.

Fields:

-   enrollment
-   course_unit
-   score
-   grade
-   status
-   published_at

Validation must ensure:

CourseUnit.course == Enrollment.course

This should be enforced through application validation and tested
thoroughly.

## 16. CourseContent

Initially:

-   course
-   optional course_unit
-   title
-   description
-   file
-   URL
-   visible_to_students
-   created_at

Content should be simple.

## 17. StudentDocument

Fields:

-   student
-   title
-   document_type
-   file
-   uploaded_at

Access must be restricted.

## 18. CollegeSettings

Institution-level configuration.

Suggested fields:

-   name
-   logo
-   address
-   phone
-   email
-   website
-   currency

The system should assume one institution for now.

Do not implement multi-tenancy unless the product direction changes.

## 19. AuditLog

Fields:

-   user
-   action
-   model_name
-   object_id
-   description
-   created_at

The audit system should be useful, not a dump of every insignificant
event.

## 20. Important invariants

The implementation must protect these invariants:

1.  Admission numbers are unique.
2.  Staff numbers are unique.
3.  Course codes are unique.
4.  Course-unit codes are unique within a course.
5.  Invoice numbers are unique.
6.  Payment references are unique where references exist.
7.  Results reference valid course units for the student's enrolled
    course.
8.  Students can only access their own protected records.
9.  Published results are controlled by authorized users.
10. Historical financial records are not silently rewritten.
11. Important financial/academic records are not casually deleted.
12. Enrollment duplication is controlled with appropriate database
    constraints.
