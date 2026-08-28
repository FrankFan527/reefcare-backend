from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator
from app.core.enums import CaseStatus


class CaseOwnerResponse(BaseModel):
    id: int
    display_name: str


class CoordinatorQueueItem(BaseModel):
    report_id: int
    report_reference: str

    threat: str
    area: str | None = None

    # v_unclaimed_queue currently exposes
    # case_status.internal_label.
    status_label: str

    submitted_at: datetime
    hours_in_queue: int


class CoordinatorQueueResponse(BaseModel):
    items: list[CoordinatorQueueItem]

    page: int
    page_size: int
    total: int


class ClaimedCaseResponse(BaseModel):
    report_id: int
    report_reference: str

    owner: CaseOwnerResponse

    status_code: CaseStatus
    status_label: str

    claimed_at: datetime


class PreciseLocationResponse(BaseModel):
    latitude: float | None = None
    longitude: float | None = None

    uncertainty_metres: int | None = None
    confidence_label: str | None = None
    source_label: str | None = None

    relocation_notes: str | None = None


class EvidenceSummary(BaseModel):
    evidence_id: int
    media_type: str

    captured_at: datetime | None = None
    uploaded_at: datetime


class CoordinatorCaseResponse(BaseModel):
    report_id: int
    report_reference: str

    observer_id: int

    threat: str
    description: str

    estimated_depth_metres: float | None = None

    area: str | None = None

    precise_location: PreciseLocationResponse | None = None

    status_code: CaseStatus
    status_label: str

    submitted_at: datetime

    owner: CaseOwnerResponse

    evidence: list[EvidenceSummary] = []

class InformationRequestCreate(BaseModel):
    """
    The coordinator's reason for asking the observer for more information.

    API schema only. Iteration 1 has no information_request table: the reason
    is written into case_event.note by reefcare_change_status(), which records
    the status move and the note in one transaction.
    """

    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, the_value: str) -> str:
        """
        A reason made only of spaces is not a reason.

        This one is observer-visible, so an empty string would show up in
        their timeline as an unexplained request for more information.
        """

        the_trimmed_reason = the_value.strip()

        if the_trimmed_reason == "":
            raise ValueError("reason must not be empty")

        return the_trimmed_reason


class InformationRequestResponse(BaseModel):
    """Confirmation that the case moved to needs_more_info."""

    report_reference: str

    # the canonical database status code, e.g. "needs_more_info"
    status: str

    reason: str
    requested_at: datetime



class ResponseTypeDecisionCreate(BaseModel):
    """
    A coordinator's Iteration 1 response-type decision on an owned case.

    Named per the updated backend doc, which replaces the older generic
    DecisionCreate. The values below are case_decision.response_type as
    enforced by case_decision_response_type_valid, not the API-level
    CaseDecision enum in core/enums.py, whose values do not exist in the
    database.

    The three-versus-four question is still open with the team. Four are
    accepted here because the CHECK constraint accepts four; narrowing to
    three later is a one-line change.
    """

    response_type: str
    notes: str | None = Field(default=None, max_length=1000)

    # who the case was shared or referred to, required for refer_or_share
    referred_to: str | None = Field(default=None, max_length=200)

    @field_validator("response_type")
    @classmethod
    def response_type_must_be_a_database_value(cls, the_value: str) -> str:
        """Reject anything the case_decision CHECK constraint would refuse."""

        the_permitted_response_types = {
            "monitoring_only",
            "refer_or_share",
            "intervention_required",
            "no_responsible_partner",
        }

        if the_value not in the_permitted_response_types:
            raise ValueError(
                "response_type must be one of: "
                + ", ".join(sorted(the_permitted_response_types))
            )

        return the_value

    @model_validator(mode="after")
    def referral_must_name_the_recipient(self):
        """
        Mirror the trg_case_decision_validate rule.

        A referral that does not say who it went to is not actionable, and
        Postgres rejects it. Catching it here names the missing field instead
        of surfacing a raw trigger exception.
        """

        if self.response_type == "refer_or_share":
            if self.referred_to is None or self.referred_to.strip() == "":
                raise ValueError(
                    "referred_to is required when response_type is refer_or_share"
                )

        return self


class ResponseTypeDecisionResponse(BaseModel):
    """Confirmation that a decision was recorded."""

    report_reference: str
    response_type: str
    decided_at: datetime
    decided_by: int

    