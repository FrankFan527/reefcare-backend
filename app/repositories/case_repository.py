# ---------------------------------------------------------------------------
# Case queries and sanctioned status changes.
#
# Repositories own SQL; services own workflow. Nothing here decides whether an
# action is allowed, it only reads and writes.
#
# Every status move goes through reefcare_change_status(). Direct UPDATEs on
# report.current_status_id are rejected by trg_report_status_guard with
# insufficient_privilege, even when the transition itself would be valid.
# ---------------------------------------------------------------------------
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_case_ownership_and_status(
    db: AsyncSession,
    report_reference: str,
) -> dict | None:
    """
    Return who owns a case and what state it is in, or None if it does not exist.

    This is the lookup the ownership check depends on. reefcare_change_status()
    does not verify that the actor owns the case, so without this any
    coordinator could move any case.

    deleted_at IS NULL matches the function's own filter, so a withdrawn
    report is treated as missing here rather than failing later inside
    Postgres with a less helpful message.
    """

    the_case_result = await db.execute(
        text(
            """
            SELECT
                r.report_reference,
                r.claimed_by_user_id,
                cs.code  AS current_status_code,
                cs.internal_label AS current_status_label
            FROM report AS r
            JOIN case_status AS cs
                ON cs.case_status_id = r.current_status_id
            WHERE r.report_reference = :report_reference
              AND r.deleted_at IS NULL
            """
        ),
        {"report_reference": report_reference},
    )

    the_case_row = the_case_result.mappings().first()

    if the_case_row is None:
        return None

    return dict(the_case_row)


async def transition_is_permitted(
    db: AsyncSession,
    from_status_code: str,
    to_status_code: str,
) -> bool:
    """
    Whether case_status_transition allows this move.

    An application pre-check only. The database rejects an unlisted transition
    regardless, but asking first lets the route return a 409 naming both
    states instead of surfacing a raw Postgres exception.

    Reading the table rather than hardcoding a list means this stays correct
    if the permitted transitions change.
    """

    the_transition_result = await db.execute(
        text(
            """
            SELECT 1
            FROM case_status_transition AS t
            JOIN case_status AS f ON f.case_status_id = t.from_status_id
            JOIN case_status AS s ON s.case_status_id = t.to_status_id
            WHERE f.code = :from_status_code
              AND s.code = :to_status_code
            """
        ),
        {
            "from_status_code": from_status_code,
            "to_status_code": to_status_code,
        },
    )

    return the_transition_result.first() is not None


async def change_status(
    db: AsyncSession,
    report_reference: str,
    to_status_code: str,
    actor_user_id: int,
    note: str | None = None,
    event_type: str = "status_change",
) -> str:
    """
    Move a case through the only sanctioned path.

    reefcare_change_status() writes report.current_status_id and the matching
    case_event row in one transaction, so the two can never drift apart. It
    returns the new status code.

    The caller commits.
    """

    the_status_result = await db.execute(
        text(
            """
            SELECT reefcare_change_status(
                :report_reference,
                :to_status_code,
                :actor_user_id,
                :note,
                :event_type
            ) AS new_status_code
            """
        ),
        {
            "report_reference": report_reference,
            "to_status_code": to_status_code,
            "actor_user_id": actor_user_id,
            "note": note,
            "event_type": event_type,
        },
    )

    return the_status_result.scalar_one()

async def get_closure_reason(
    db: AsyncSession,
    closure_reason_code: str,
) -> dict | None:
    """
    Return a closure reason's rules, or None if the code is unknown.

    requires_note and iteration_added are read rather than hardcoded, so the
    reference data stays the single source of truth. Adding a reason later
    means seeding a row, not editing Python.
    """

    the_reason_result = await db.execute(
        text(
            """
            SELECT
                code,
                internal_label,
                observer_label,
                requires_note,
                iteration_added
            FROM closure_reason
            WHERE code = :closure_reason_code
            """
        ),
        {"closure_reason_code": closure_reason_code},
    )

    the_reason_row = the_reason_result.mappings().first()

    if the_reason_row is None:
        return None

    return dict(the_reason_row)


async def close_report(
    db: AsyncSession,
    report_reference: str,
    coordinator_id: int,
    closure_reason_code: str,
    terminal_status_code: str,
    note: str | None = None,
    referred_to: str | None = None,
) -> str:
    """
    Close a case through the only sanctioned path.

    reefcare_close_report() writes the case_decision row and the terminal
    status together, and routes the status move through
    reefcare_change_status() so the case_event is written in the same
    transaction. It checks ownership itself, unlike reefcare_change_status().

    It returns the terminal status code.

    IMPORTANT FOR CALLERS: trg_report_closure_reason is DEFERRABLE INITIALLY
    DEFERRED, so a closure that violates it raises at COMMIT rather than here.
    The caller must commit inside its own error handling, or a failed close
    will look like a success.
    """

    the_closure_result = await db.execute(
        text(
            """
            SELECT reefcare_close_report(
                :report_reference,
                :coordinator_id,
                :closure_reason_code,
                :terminal_status_code,
                :note,
                :referred_to
            ) AS terminal_status_code
            """
        ),
        {
            "report_reference": report_reference,
            "coordinator_id": coordinator_id,
            "closure_reason_code": closure_reason_code,
            "terminal_status_code": terminal_status_code,
            "note": note,
            "referred_to": referred_to,
        },
    )

    return the_closure_result.scalar_one()