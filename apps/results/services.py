"""
Result domain services.

All result lifecycle transitions go through these functions.
Views orchestrate; these functions own the rules.

Lifecycle:
    DRAFT → SUBMITTED (by entrant)
    SUBMITTED → APPROVED (by approver — requires approve_result permission)
    APPROVED → PUBLISHED (by publisher — requires publish_result permission)
    Any non-PUBLISHED state → DRAFT (reset — clears approval)

Transitions that are not in the above map raise ValueError.
"""

import logging
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone

from apps.core.audit import audit_log
from apps.core.models import AuditAction

logger = logging.getLogger(__name__)

# Valid forward transitions
_VALID_TRANSITIONS = {
    'DRAFT':     {'SUBMITTED'},
    'SUBMITTED': {'APPROVED', 'DRAFT'},   # DRAFT = reset/reject
    'APPROVED':  {'PUBLISHED', 'DRAFT'},  # DRAFT = reset
    'PUBLISHED': set(),                   # terminal
}


def create_result(*, enrollment, course_unit, score_cat=None, score_exam=None,
                  entered_by, request=None):
    """
    Create a new Result in DRAFT status.

    Enforces:
    - course_unit belongs to enrollment.course (validated in model.clean())
    - No duplicate result for the same enrollment + unit (DB constraint)

    Returns: Result instance
    Raises:  ValidationError on rule violation or duplicate
    """
    from .models import Result

    with transaction.atomic():
        result = Result(
            enrollment=enrollment,
            course_unit=course_unit,
            score_cat=score_cat,
            score_exam=score_exam,
            status='DRAFT',
            entered_by=entered_by,
        )
        try:
            result.full_clean()
            result.save()
        except ValidationError:
            raise
        except IntegrityError:
            raise ValidationError(
                f'A result for {course_unit.code} already exists '
                f'for this enrollment.'
            )

        audit_log(
            actor=entered_by,
            action=AuditAction.RESULT_ENTERED,
            obj=result,
            description=f'Result entered (DRAFT): {result}',
            request=request,
        )

    return result


def update_result_scores(*, result, score_cat=None, score_exam=None,
                         updated_by, request=None):
    """
    Update scores on a DRAFT result.
    Only allowed while the result is in DRAFT status.
    """
    if result.status != 'DRAFT':
        raise ValueError(
            f'Scores can only be edited on DRAFT results. '
            f'Current status: {result.status}.'
        )

    result.score_cat = score_cat
    result.score_exam = score_exam
    # save() recomputes total + grade via the model override
    result.save(update_fields=['score_cat', 'score_exam', 'total', 'grade', 'updated_at'])

    audit_log(
        actor=updated_by,
        action=AuditAction.RESULT_ENTERED,
        obj=result,
        description=f'Result scores updated: {result}',
        request=request,
    )
    return result


def transition_result(*, result, new_status, actor, request=None):
    """
    Transition a Result to a new status, enforcing valid transitions.

    Parameters:
        result     : Result instance
        new_status : Target ResultStatus string
        actor      : User performing the action
        request    : HttpRequest (optional, for IP logging)

    Raises:
        ValueError on invalid transition
    """
    from .models import ResultStatus

    old_status = result.status
    if old_status == new_status:
        return result

    allowed = _VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise ValueError(
            f'Cannot transition result from {old_status} to {new_status}. '
            f'Allowed: {allowed or "none (terminal)"}.'
        )

    update_fields = ['status', 'updated_at']

    if new_status == 'APPROVED':
        result.approved_by = actor
        update_fields.append('approved_by')
    elif new_status == 'PUBLISHED':
        result.published_at = timezone.now()
        update_fields += ['published_at']
    elif new_status == 'DRAFT':
        # Reset — clear approval
        result.approved_by = None
        result.published_at = None
        update_fields += ['approved_by', 'published_at']

    # Map status → audit action
    action_map = {
        'SUBMITTED': AuditAction.RESULT_SUBMITTED,
        'APPROVED':  AuditAction.RESULT_APPROVED,
        'PUBLISHED': AuditAction.RESULT_PUBLISHED,
        'DRAFT':     AuditAction.RESULT_ENTERED,
    }
    audit_action = action_map.get(new_status, AuditAction.RESULT_ENTERED)

    with transaction.atomic():
        result.status = new_status
        result.save(update_fields=update_fields)

        audit_log(
            actor=actor,
            action=audit_action,
            obj=result,
            description=(
                f'Result status changed: {result.enrollment.student.admission_number} '
                f'[{result.course_unit.code}] {old_status} → {new_status}'
            ),
            request=request,
        )

    return result


def bulk_enter_results(*, enrollment_ids, course_unit, scores_map,
                       entered_by, request=None):
    """
    Enter or update results for multiple enrollments in one unit.

    scores_map: {enrollment_id: {'score_cat': X, 'score_exam': Y}}

    Creates DRAFT results where none exist; updates scores where they do.
    Returns list of (enrollment_id, result, created) tuples.
    """
    from .models import Result

    results = []
    for enrollment_id in enrollment_ids:
        scores = scores_map.get(enrollment_id, {})
        cat = scores.get('score_cat')
        exam = scores.get('score_exam')

        try:
            existing = Result.objects.get(
                enrollment_id=enrollment_id,
                course_unit=course_unit,
            )
            if existing.status == 'DRAFT':
                existing = update_result_scores(
                    result=existing,
                    score_cat=cat,
                    score_exam=exam,
                    updated_by=entered_by,
                    request=request,
                )
            results.append((enrollment_id, existing, False))
        except Result.DoesNotExist:
            from apps.enrollments.models import Enrollment
            try:
                enrollment = Enrollment.objects.get(pk=enrollment_id)
                result = create_result(
                    enrollment=enrollment,
                    course_unit=course_unit,
                    score_cat=cat,
                    score_exam=exam,
                    entered_by=entered_by,
                    request=request,
                )
                results.append((enrollment_id, result, True))
            except (Enrollment.DoesNotExist, ValidationError) as exc:
                logger.warning('bulk_enter_results: skipping %s — %s', enrollment_id, exc)

    return results
