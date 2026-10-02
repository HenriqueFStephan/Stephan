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
    conn.execute(
        f"""
        INSERT INTO hse_responses (
            id, company_id, round_id, submitted_on, demographics, {columns}
        )
        VALUES (%s, %s, %s, %s, %s, {placeholders})
        """,
        (response_id, company_id, round_id, submitted_on, Json(cleaned), *answers),
    )
    return response_id


def clean_demographics(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DemographicRejected("demographics must be an object")
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip() or len(key.strip()) > 40:
            raise DemographicRejected("invalid demographic key")
        norm = key.strip().casefold()
        if norm in BLOCKED_DEMOGRAPHIC_KEYS:
            raise DemographicRejected(norm)
        if isinstance(value, bool) or value is None or isinstance(value, (int, float, str)):
            if isinstance(value, str) and len(value) > 80:
                raise DemographicRejected("demographic value is too long")
            if isinstance(value, bool):
                cleaned[norm] = value
            elif isinstance(value, float) and value != value:
                raise DemographicRejected("invalid demographic value")
            else:
                cleaned[norm] = value
            continue
        raise DemographicRejected("demographic values must be scalars")
    return cleaned


def _percent(part: int, whole: int) -> int | None:
    if whole <= 0:
        return None
    return round(100 * part / whole)


def invitation_is_pending(conn, token: str) -> bool:
    """True when this token can still open the form. Does not return the address."""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = conn.execute(
        "SELECT status FROM invitations WHERE link_token_hash = %s",
        (digest,),
    ).fetchone()
    if row is None:
        raise UnknownInvitation()
    if row["status"] != "pending":
        raise InvitationAlreadySubmitted()
    return True


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
