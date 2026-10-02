"""Store invitation lists and anonymous HSE answers for one company at a time.

The answer write does not take an email, a token, or an invitation id.
The invitation is marked submitted in the same transaction, after the lookup
by token hash, and that id is not copied onto the answer.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Json

from app.services.invitation_file import ParsedInvitations
from app.services.invitation_mail import MailDeliveryError, MailNotConfigured, deliver_invitations

# Anexo B codes stored on hse_responses. The Portuguese sentences live in the form.
# Keep this aligned with frontend/src/app/features/tool/profile.ts.
DEMOGRAPHIC_FIELDS: dict[str, tuple[str, ...]] = {
    "age_band": ("18_24", "25_34", "35_44", "45_54", "55_64", "65_plus"),
    "gender": ("female", "male", "undisclosed"),
    "education": ("fundamental", "high_school", "higher_incomplete", "higher_complete", "postgraduate"),
    "economic_sector": (
        "manufacturing",
        "retail",
        "services",
        "health",
        "education",
        "it",
        "construction",
        "transport",
        "agribusiness",
        "public_admin",
        "other",
    ),
    "org_size": ("micro", "small", "medium", "large", "unknown"),
    "employment_bond": ("clt", "public_statute", "autonomous_pj", "intern_apprentice", "other"),
    "tenure_org": ("lt_1", "y1_3", "y4_10", "gt_10"),
    "tenure_profession": ("lt_1", "y1_5", "y6_15", "gt_15"),
    "work_shift": ("day_fixed", "night_fixed", "rotating", "flexible"),
    "leadership": ("yes", "no"),
    "region": ("north", "northeast", "center_west", "southeast", "south"),
}
REQUIRED_DEMOGRAPHIC_KEYS = frozenset({"age_band", "economic_sector"})
DEMOGRAPHIC_COLUMNS = tuple(DEMOGRAPHIC_FIELDS)

# Identifiers we already refused. This is not the list of demographic fields.
BLOCKED_DEMOGRAPHIC_KEYS = frozenset(
    {
        "name",
        "nome",
        "full_name",
        "email",
        "e-mail",
        "mail",
        "job",
        "job_title",
        "jobtitle",
        "cargo",
        "funcao",
        "função",
        "token",
        "link_token",
        "ip",
        "invitation_id",
        "invitation",
    }
)

ITEM_COLUMNS = tuple(f"i{number:02d}" for number in range(1, 36))


class NoOpenRound(Exception):
    """This company has no open round to attach the list or the answer to."""


class UnknownInvitation(Exception):
    """No invitation has this token."""


class InvitationAlreadySubmitted(Exception):
    """This link was already used."""


class DemographicRejected(Exception):
    """A demographic payload tried to carry an identifier or a nested value."""


def add_invitations(conn, company_id, filename: str, parsed: ParsedInvitations) -> dict[str, Any]:
    company_id, round_id, round_label = _open_round(conn, company_id)
    existing = {
        row["email"]
        for row in conn.execute(
            "SELECT email FROM invitations WHERE round_id = %s",
            (round_id,),
        ).fetchall()
    }
    already = [email for email in parsed.emails if email in existing]
    accepted = [email for email in parsed.emails if email not in existing]
    not_sent: list[str] = []
    sent: list[tuple[str, str]] = []
    if accepted:
        pending = [(email, secrets.token_urlsafe(32)) for email in accepted]
        sent, not_sent = deliver_invitations(pending)
        if not sent:
            raise MailDeliveryError()

    upload_id = None
    if sent or not accepted:
        upload_id = conn.execute(
            """
            INSERT INTO invitation_uploads (id, company_id, round_id, source_name, format)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (uuid4(), company_id, round_id, _source_name(filename), parsed.format),
        ).fetchone()["id"]

    for email, token in sent:
        conn.execute(
            """
            INSERT INTO invitations (
                id, company_id, round_id, upload_id, email,
                link_token, link_token_hash, status, sent_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', now())
            """,
            (
                uuid4(),
                company_id,
                round_id,
                upload_id,
                email,
                token,
                hashlib.sha256(token.encode("utf-8")).hexdigest(),
            ),
        )

    return {
        "round_label": round_label,
        "accepted": len(sent),
        "ignored_empty": parsed.ignored_empty,
        "duplicates_in_file": parsed.duplicates_in_file,
        "already_invited": already,
        "invalid": parsed.invalid,
        "not_sent": not_sent,
    }


def list_invitations(conn, company_id) -> dict[str, Any]:
    """Participation for this company's open round. Counts and shares only: no addresses."""
    _company_id, round_id, round_label = _open_round(conn, company_id)
    row = conn.execute(
        """
        SELECT
          count(*) FILTER (WHERE status = 'pending') AS waiting,
          count(*) FILTER (WHERE status = 'submitted') AS responded
        FROM invitations
        WHERE round_id = %s
        """,
        (round_id,),
    ).fetchone()
    waiting = int(row["waiting"])
    responded = int(row["responded"])
    invited = waiting + responded
    responded_percent = _percent(responded, invited)
    waiting_percent = None if responded_percent is None else 100 - responded_percent
    return {
        "round_label": round_label,
        "invited": invited,
        "responded_percent": responded_percent,
        "waiting_percent": waiting_percent,
    }


def submit_invitation(
    conn,
    token: str,
    *,
    submitted_on: date,
    demographics: dict[str, Any],
    answers: list[int],
) -> UUID:
    """Save one anonymous form for the invitation's company and mark that link used.

    The token is only the lookup key. It is not written on the answer.
    """
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invitation = conn.execute(
        """
        SELECT id, company_id, round_id, status
        FROM invitations
        WHERE link_token_hash = %s
        FOR UPDATE
        """,
        (digest,),
    ).fetchone()
    if invitation is None:
        raise UnknownInvitation()
    if invitation["status"] != "pending":
        raise InvitationAlreadySubmitted()
    response_id = record_response(
        conn,
        company_id=invitation["company_id"],
        round_id=invitation["round_id"],
        submitted_on=submitted_on,
        demographics=demographics,
        answers=answers,
    )
    conn.execute("DELETE FROM hse_drafts WHERE link_token_hash = %s", (digest,))
    updated = conn.execute(
        """
        UPDATE invitations
        SET status = 'submitted', submitted_at = now()
        WHERE id = %s
          AND status = 'pending'
        """,
        (invitation["id"],),
    )
    if updated.rowcount != 1:
        raise InvitationAlreadySubmitted()
    return response_id


def record_response(
    conn,
    *,
    company_id,
    round_id,
    submitted_on: date,
    demographics: dict[str, Any],
    answers: list[int],
) -> UUID:
    """Insert one anonymous form. No email, token, invitation id, or address."""
    if len(answers) != 35 or any(type(value) is not int or not 1 <= value <= 5 for value in answers):
        raise ValueError("HSE answers must be 35 integers from 1 to 5")
    cleaned = clean_demographics(demographics)
    response_id = uuid4()
    columns = ", ".join(ITEM_COLUMNS)
    placeholders = ", ".join(["%s"] * 35)
    demo_columns = ", ".join(DEMOGRAPHIC_COLUMNS)
    demo_placeholders = ", ".join(["%s"] * len(DEMOGRAPHIC_COLUMNS))
    demo_values = [cleaned.get(column) for column in DEMOGRAPHIC_COLUMNS]
    conn.execute(
        f"""
        INSERT INTO hse_responses (
            id, company_id, round_id, submitted_on, demographics, {demo_columns}, {columns}
        )
        VALUES (%s, %s, %s, %s, %s, {demo_placeholders}, {placeholders})
        """,
        (response_id, company_id, round_id, submitted_on, Json(cleaned), *demo_values, *answers),
    )
    return response_id


def clean_demographics(raw: dict[str, Any], *, require_complete: bool = True) -> dict[str, Any]:
    """Keep Anexo B codes only. A finished form requires age band and economic sector."""
    if not isinstance(raw, dict):
        raise DemographicRejected("demographics must be an object")
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise DemographicRejected("invalid demographic key")
        norm = key.strip().casefold()
        if norm in BLOCKED_DEMOGRAPHIC_KEYS:
            raise DemographicRejected(norm)
        allowed = DEMOGRAPHIC_FIELDS.get(norm)
        if allowed is None:
            raise DemographicRejected("unknown demographic key")
        if isinstance(value, bool) or not isinstance(value, str):
            raise DemographicRejected("invalid demographic value")
        norm_value = value.strip().casefold()
        if norm_value not in allowed:
            raise DemographicRejected("invalid demographic value")
        cleaned[norm] = norm_value
    if require_complete:
        missing = REQUIRED_DEMOGRAPHIC_KEYS - cleaned.keys()
        if missing:
            raise DemographicRejected("required demographic")
    return cleaned


def clean_draft_answers(raw: list[Any]) -> list[int | None]:
    """Thirty-five marks. An unanswered item is None."""
    if not isinstance(raw, list) or len(raw) != 35:
        raise ValueError("draft answers must be 35 marks")
    cleaned: list[int | None] = []
    for value in raw:
        if value is None:
            cleaned.append(None)
            continue
        if type(value) is not int or not 1 <= value <= 5:
            raise ValueError("draft answers must be 35 marks")
        cleaned.append(value)
    return cleaned


def save_draft(
    conn,
    token: str,
    *,
    place: str,
    item_index: int,
    demographics: dict[str, Any],
    answers: list[Any],
) -> None:
    """Store an unfinished form for this link. The invitation stays pending.

    The row is keyed by the token hash, which also sits on the invitation.
    Submit deletes it. The hash is not written on the finished answer.
    """
    if place not in {"profile", "ask"}:
        raise ValueError("draft place")
    if type(item_index) is not int or isinstance(item_index, bool) or not 0 <= item_index <= 34:
        raise ValueError("draft index")
    if place == "profile":
        item_index = 0
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invitation = conn.execute(
        """
        SELECT id, status
        FROM invitations
        WHERE link_token_hash = %s
        FOR UPDATE
        """,
        (digest,),
    ).fetchone()
    if invitation is None:
        raise UnknownInvitation()
    if invitation["status"] != "pending":
        raise InvitationAlreadySubmitted()
    cleaned = clean_demographics(demographics, require_complete=False)
    marks = clean_draft_answers(answers)
    columns = ["link_token_hash", "place", "item_index", "demographics", *DEMOGRAPHIC_COLUMNS, *ITEM_COLUMNS]
    values: list[Any] = [digest, place, item_index, Json(cleaned), *[cleaned.get(column) for column in DEMOGRAPHIC_COLUMNS], *marks]
    assignments = ", ".join(f"{column} = EXCLUDED.{column}" for column in columns if column != "link_token_hash")
    placeholders = ", ".join(["%s"] * len(values))
    conn.execute(
        f"""
        INSERT INTO hse_drafts ({", ".join(columns)}, updated_at)
        VALUES ({placeholders}, now())
        ON CONFLICT (link_token_hash) DO UPDATE SET
            {assignments},
            updated_at = now()
        """,
        values,
    )


def open_pending_invitation(conn, token: str) -> dict[str, Any] | None:
    """Return the unfinished form when this link is still pending.

    None means the link is valid and nothing has been saved yet.
    Does not return the address, the token, or the invitation id.
    """
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    mark_columns = ", ".join(f"d.{column}" for column in ITEM_COLUMNS)
    row = conn.execute(
        f"""
        SELECT i.status, d.place, d.item_index, d.demographics, {mark_columns}
        FROM invitations AS i
        LEFT JOIN hse_drafts AS d ON d.link_token_hash = i.link_token_hash
        WHERE i.link_token_hash = %s
        """,
        (digest,),
    ).fetchone()
    if row is None:
        raise UnknownInvitation()
    if row["status"] != "pending":
        raise InvitationAlreadySubmitted()
    if row["place"] is None:
        return None
    return {
        "place": row["place"],
        "index": row["item_index"],
        "demographics": row["demographics"] or {},
        "answers": [row[column] for column in ITEM_COLUMNS],
    }


def _percent(part: int, whole: int) -> int | None:
    if whole <= 0:
        return None
    return round(100 * part / whole)


def _open_round(conn, company_id) -> tuple[Any, Any, str]:
    row = conn.execute(
        """
        SELECT c.id AS company_id, r.id AS round_id, r.label
        FROM companies AS c
        JOIN company_rounds AS r ON r.company_id = c.id
        WHERE c.id = %s
          AND r.closed_on IS NULL
        """,
        (company_id,),
    ).fetchone()
    if row is None:
        raise NoOpenRound()
    return row["company_id"], row["round_id"], row["label"]


def _source_name(filename: str) -> str:
    name = Path(filename or "upload").name
    cleaned = "".join(ch for ch in name if ch.isprintable()).strip()
    return (cleaned or "upload")[:180]
