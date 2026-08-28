from datetime import datetime

from pydantic import BaseModel, Field, field_validator

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


    