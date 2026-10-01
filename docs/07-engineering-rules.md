# Nayolites --- Engineering Rules for AI Coding Agents

## 1. Read before coding

Before making changes:

1.  Read the relevant documents in `/docs`.
2.  Inspect the existing repository.
3.  Understand existing models, views, URLs, templates, tests, and
    migrations.
4.  Identify the relevant domain boundary.
5.  Check whether the feature already exists partially.

Do not assume the repository is empty.

## 2. Do not silently redesign the product

If an implementation decision conflicts with the documented product or
architecture:

-   identify the conflict
-   explain the impact
-   propose the alternative
-   wait for approval when the change is material

Do not silently replace the architecture.

## 3. Product requirements outrank convenience

Do not change a business rule merely because another implementation is
easier.

## 4. Architecture should remain simple

Do not introduce:

-   React
-   Vue
-   microservices
-   GraphQL
-   CQRS
-   event sourcing
-   Kubernetes
-   message queues
-   workflow engines
-   multi-tenancy

unless a documented requirement justifies the addition.

## 5. Never rely on frontend authorization

The backend must enforce every permission.

Hiding a navigation item, button, or URL is not security.

Test unauthorized access directly.

## 6. Avoid duplicated source-of-truth state

Do not add fields such as:

-   student.balance
-   student.amount_paid
-   current_invoice_total

when those values can be derived reliably from existing records.

If denormalized/cached state becomes necessary for performance, document
why and how it is synchronized.

## 7. Protect historical records

Do not casually delete:

-   payments
-   invoices
-   results
-   enrollments
-   audit records

Use appropriate constraints and lifecycle statuses.

## 8. Database constraints matter

Use database-level constraints for rules that can be enforced there.

Do not rely entirely on Python validation for uniqueness/integrity.

## 9. Validate cross-object relationships

Examples:

-   Result course unit must belong to enrollment course.
-   Student must be valid for the enrollment.
-   Payment must reference a valid invoice.
-   Invoice must belong to the relevant enrollment.

## 10. Business logic must not live primarily in templates

Templates present information.

They should not contain critical financial, authorization, enrollment,
or academic business rules.

## 11. Keep API and HTML behavior consistent

The API and HTML application should use the same underlying business
rules.

Do not implement finance calculations separately in API serializers and
templates.

## 12. Permissions should be granular

Prefer Django permissions/groups.

Avoid code like:

``` python
if user.role == "admin":
```

throughout the codebase.

Use permission checks and domain capabilities instead.

## 13. Code organization

Keep responsibilities clear.

Do not put every model, view, serializer, helper, and business rule into
one giant file.

Do not split tiny concepts into dozens of meaningless files either.

## 14. Forms and validation

Validation must exist server-side.

Frontend validation is an enhancement, not the source of truth.

Validation errors should be actionable and understandable.

## 15. Testing

Every significant feature should include tests for:

-   happy path
-   validation
-   permissions
-   unauthorized access
-   important domain invariants
-   edge cases

Financial calculations require especially strong tests.

## 16. Security

Follow Django security best practices.

Protect:

-   authentication
-   authorization
-   CSRF
-   file uploads
-   secrets
-   sensitive documents
-   payment callbacks
-   administrative actions

Do not expose sensitive records through predictable URLs without
authorization.

## 17. File uploads

Validate:

-   file type
-   size
-   storage path
-   access permissions

Do not assume uploaded files are safe merely because the filename has an
expected extension.

## 18. Auditability

Important administrative changes should be traceable.

Do not create audit logs for every trivial read unless there is a clear
reason.

## 19. UI quality

Do not accept a screen merely because it technically renders.

Check:

-   spacing
-   typography
-   alignment
-   responsiveness
-   empty state
-   error state
-   accessibility
-   action clarity
-   consistency with the design system

## 20. No AI visual clichés

Do not introduce:

-   random gradients
-   emoji icons
-   excessive rounded cards
-   glassmorphism
-   decorative blobs
-   fake metrics
-   excessive animations

unless explicitly required by the design specification.

## 21. No invented institutional content

Never invent:

-   accreditations
-   statistics
-   testimonials
-   student counts
-   rankings
-   partnerships
-   achievements
-   course claims

Use verified content or placeholders clearly marked for replacement.

## 22. Minimal unrelated changes

When implementing a feature:

-   modify the smallest reasonable set of files
-   do not refactor unrelated code
-   do not rename unrelated models
-   do not reformat the whole repository
-   do not replace working architecture for stylistic preference

## 23. Definition of done

A feature is not complete merely because the happy path works.

Before declaring completion, verify:

-   [ ] Domain model is correct
-   [ ] Database migration exists
-   [ ] Constraints are appropriate
-   [ ] Business rules are enforced
-   [ ] Authorization is enforced
-   [ ] Server-side validation exists
-   [ ] UI is implemented
-   [ ] Empty states exist
-   [ ] Error states exist
-   [ ] Responsive behavior works
-   [ ] Tests exist
-   [ ] Existing tests still pass
-   [ ] Audit requirements are handled
-   [ ] Documentation/status is updated

## 24. AI coding workflow

For every substantial feature:

``` text
READ
→ UNDERSTAND
→ PLAN
→ IMPLEMENT
→ TEST
→ REVIEW
→ DOCUMENT
```

Before implementation, produce a concise implementation plan.

After implementation, report:

-   files changed
-   behavior added
-   tests added/run
-   known limitations
-   documentation updated
