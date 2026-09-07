# ---------------------------------------------------------------------------
# Response type decision workflow (US5.4).
#
# Recording a decision now also moves the case, because the observer needs to
# see what was decided. reefcare_my_reports and reefcare_report_timeline both
# read case_status.observer_label from report.current_status_id, so moving the
# status is what makes the decision visible on the observer side. Nothing in
# the observer endpoints needs to change.
#
# The destinations come from case_status_transition, which already carries them
# with the reasoning in its note column:
#
#   evidence_accepted -> monitoring   Q4: monitoring only
#   evidence_accepted -> referred     Q4: refer or share
# ---------------------------------------------------------------------------
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseOperationError, WorkflowError
from app.repositories.case_decision_repository import save_case_decision
from app.repositories.case_repository import change_status
from app.services.case_workflow_service import (
    load_owned_case,
    validate_status_transition,
)


# A response decision follows the evidence assessment. Before US5.3 existed this
# also allowed under_review, monitoring and referred; it is narrowed to the one
# state now that the assessment step is built, so the workflow reads
# Review -> Evidence Assessment -> Evidence Accepted -> Response Decision.
STATUSES_THAT_MAY_RECEIVE_A_DECISION: set[str] = {
    "evidence_accepted",
}

PERMITTED_RESPONSE_TYPES: set[str] = {
    "monitoring_only",
    "refer_or_share",
    "intervention_required",
}

# Where each response type moves the case. Both destinations are non-terminal:
# a recommendation is not a completed action, and the observer wording says so.
#
# intervention_required is deliberately absent. case_status_transition has no
# destination for it from evidence_accepted, and the status that would carry it,
# response_recommended, is seeded with iteration_added = 2 as part of the
# Iteration 2 response chain. Until the team decides, a decision of
# intervention_required is recorded but does not move the case. This is a known
# gap, raised with the team rather than resolved silently here.
STATUS_FOR_RESPONSE_TYPE: dict[str, str] = {
    "monitoring_only": "monitoring",
    "refer_or_share": "referred",
}


def validate_response_type(
    response_type: str,
    referred_to: str | None,
) -> None:
    """
    Check the response type is one this endpoint offers, and that a referral
    names its recipient.

    This duplicates the validators on ResponseTypeDecisionCreate on purpose.
    The schema protects the HTTP route; this protects the service if it is ever
    called from a test, a background task or a later endpoint. The schema can be
    bypassed by not going through HTTP; this cannot.
    """

    if response_type not in PERMITTED_RESPONSE_TYPES:
        raise WorkflowError(
            "response_type must be one of: "
            + ", ".join(sorted(PERMITTED_RESPONSE_TYPES))
        )

    if response_type == "refer_or_share":
        if referred_to is None or referred_to.strip() == "":
            raise WorkflowError(
                "referred_to is required when response_type is refer_or_share"
            )


def validate_case_is_ready_for_a_decision(current_status_code: str) -> None:
    """
    A decision may only be recorded once the evidence has been accepted.

    Deciding on a case still in under_review would skip the assessment step
    entirely, which is the workflow gap US5.3 was built to close.
    """

    if current_status_code not in STATUSES_THAT_MAY_RECEIVE_A_DECISION:
        raise WorkflowError(
            f"A decision cannot be recorded while the case is "
            f"{current_status_code}; the evidence must be accepted first"
        )


async def record_decision(
    db: AsyncSession,
    report_reference: str,
    coordinator_id: int,
    response_type: str,
    notes: str | None = None,
    referred_to: str | None = None,
) -> dict:
    """
    Record the coordinator's response type and move the case accordingly.

    Ownership is checked before the status, so a coordinator probing somebody
    else's case learns nothing about its state from the error message.

    The status move is what makes the decision visible to the observer. It is
    non-terminal: monitoring and referred both mean a recommendation has been
    made, not that the work is done or that anybody has accepted a referral.
    """

    the_case = await load_owned_case(
        db=db,
        report_reference=report_reference,
        coordinator_id=coordinator_id,
    )

    validate_case_is_ready_for_a_decision(
        current_status_code=the_case["status_code"],
    )

    validate_response_type(
        response_type=response_type,
        referred_to=referred_to,
    )

    the_saved_decision = await save_case_decision(
        db=db,
        report_reference=report_reference,
        coordinator_id=coordinator_id,
        response_type=response_type,
        decision_note=notes,
        referred_to=referred_to,
    )

    if the_saved_decision is None:
        raise DatabaseOperationError(
            "The decision could not be recorded"
        )

    # the status the case is in if nothing moves it
    the_resulting_status_code = the_case["status_code"]

    the_destination_status_code = STATUS_FOR_RESPONSE_TYPE.get(response_type)

    if the_destination_status_code is not None:
        await validate_status_transition(
            db=db,
            from_status_code=the_case["status_code"],
            to_status_code=the_destination_status_code,
        )

        the_resulting_status_code = await change_status(
            db=db,
            report_reference=report_reference,
            status_code=the_destination_status_code,
            actor_user_id=coordinator_id,
            note=notes,
            event_type="decision_recorded",
        )

    return {
        "report_reference": report_reference,
        "response_type": the_saved_decision["response_type"],
        "status": the_resulting_status_code,
        "decided_at": the_saved_decision["decided_at"],
        "decided_by": the_saved_decision["coordinator_id"],
    }