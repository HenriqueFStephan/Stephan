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

from app.services.form_pricing import quote_forms, require_method
from app.services.invitation_file import ParsedInvitations, present_address
from app.services.invitation_mail import (
    MailDeliveryError,
    MailNotConfigured,
    deliver_invitations,
    smtp_ready,
)
from app.services.invitation_whatsapp import (
    ChannelsNotConfigured,
    WhatsAppDeliveryError,
    WhatsAppNotConfigured,
    deliver_whatsapp,
    whatsapp_ready,
)

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


def preview_invitations(conn, company_id, parsed: ParsedInvitations) -> dict[str, Any]:
    """Price the new addresses on this file. Does not store them and does not send."""
    _company_id, round_id, _round_label = _open_round(conn, company_id)
    existing: set[str] = set()
    for row in conn.execute(
        "SELECT channel, email, phone FROM invitations WHERE round_id = %s",
        (round_id,),
    ).fetchall():
        address = _row_address(row)
        if address:
            existing.add(address)
    contacts = list(parsed.emails) + list(parsed.phones)
    already = [address for address in contacts if address in existing]
    fresh = [address for address in contacts if address not in existing]
    quote = quote_forms(len(fresh))
    return {
        "forms": quote["forms"],
        "unit_cents": quote["unit_cents"],
        "total_cents": quote["total_cents"],
        "provisional": True,
        "methods": quote["methods"],
        "ignored_empty": parsed.ignored_empty,
        "duplicates_in_file": _show(parsed.duplicates_in_file),
        "already_invited": _show(already),
        "invalid": parsed.invalid,
    }


def add_invitations(
    conn,
    company_id,
    filename: str,
    parsed: ParsedInvitations,
    method: str | None = None,
    skipped: bool = False,
) -> dict[str, Any]:
    """Store new addresses whose channel is ready, commit them, and only then send.

    A phone number goes out on WhatsApp. An email goes by email. A crash after
    the commit leaves the row in place with the same token. An address whose
    message already left is not sent again. A channel that is not configured
    does not get a new row.
    """
    company_id, round_id, round_label = _open_round(conn, company_id)
    existing: dict[str, Any] = {}
    for row in conn.execute(
        "SELECT channel, email, phone, link_token, sent_at FROM invitations WHERE round_id = %s",
        (round_id,),
    ).fetchall():
        address = _row_address(row)
        if address:
            existing[address] = row
    contacts = [("email", address) for address in parsed.emails] + [
        ("whatsapp", address) for address in parsed.phones
    ]
    already: list[str] = []
    waiting: list[tuple[str, str, str]] = []
    fresh: list[tuple[str, str]] = []
    for channel, address in contacts:
        row = existing.get(address)
        if row is None:
            fresh.append((channel, address))
        elif row["sent_at"] is not None:
            already.append(address)
        else:
            waiting.append((channel, address, row["link_token"]))
    send_fresh = [(channel, address) for channel, address in fresh if _channel_ready(channel)]
    blocked_fresh = [(channel, address) for channel, address in fresh if not _channel_ready(channel)]
    send_waiting = [item for item in waiting if _channel_ready(item[0])]
    blocked_waiting = [item for item in waiting if not _channel_ready(item[0])]
    if (fresh or waiting) and not send_fresh and not send_waiting:
        _raise_unconfigured({channel for channel, _address in fresh} | {channel for channel, _address, _token in waiting})

    upload_id = conn.execute(
        """
        INSERT INTO invitation_uploads (id, company_id, round_id, source_name, format)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (uuid4(), company_id, round_id, _source_name(filename), parsed.format),
    ).fetchone()["id"]
    pending = [(address, token, channel) for channel, address, token in send_waiting]
    for channel, address in send_fresh:
        token = secrets.token_urlsafe(32)
        email = address if channel == "email" else None
        phone = address if channel == "whatsapp" else None
        conn.execute(
            """
            INSERT INTO invitations (
                id, company_id, round_id, upload_id, email, phone, channel,
                link_token, link_token_hash, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """,
            (
                uuid4(),
                company_id,
                round_id,
                upload_id,
                email,
                phone,
                channel,
                token,
                hashlib.sha256(token.encode("utf-8")).hexdigest(),
            ),
        )
        pending.append((address, token, channel))
    quote = quote_forms(len(send_fresh), method)
    charge_id = uuid4()
    status = "skipped" if skipped else ("method_chosen" if method else "quoted")
    conn.execute(
        """
        INSERT INTO form_charges (
            id, company_id, round_id, upload_id, forms, unit_cents, total_cents,
            provisional, method, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s, %s)
        """,
        (
            charge_id,
            company_id,
            round_id,
            upload_id,
            quote["forms"],
            quote["unit_cents"],
            quote["total_cents"],
            method,
            status,
        ),
    )
    quote["charge_id"] = str(charge_id)
    conn.commit()

    sent, not_sent = _deliver_pending(conn, pending)
    not_sent = not_sent + [address for _channel, address, _token in blocked_waiting]
    return {
        "round_label": round_label,
        "accepted": len(sent),
        "ignored_empty": parsed.ignored_empty,
        "duplicates_in_file": _show(parsed.duplicates_in_file),
        "already_invited": _show(already),
        "invalid": parsed.invalid,
        "not_sent": _show(not_sent),
        "not_configured": _show([address for _channel, address in blocked_fresh]),
        "quote": quote,
    }


class ChargeNotFound(Exception):
    """This company has no charge with that id."""


def choose_form_charge(conn, company_id, charge_id, method: str) -> dict:
    """Record the method. Does not debit and does not read a recipient account."""
    chosen = require_method(method)
    row = conn.execute(
        """
        UPDATE form_charges
        SET method = %s, status = 'method_chosen'
        WHERE id = %s
          AND company_id = %s
        RETURNING forms
        """,
        (chosen, charge_id, company_id),
    ).fetchone()
    if row is None:
        raise ChargeNotFound()
    conn.commit()
    quote = quote_forms(row["forms"], chosen)
    quote["charge_id"] = str(charge_id)
    return quote


def retry_unsent(conn, company_id) -> dict[str, Any]:
    """Send the stored link again for addresses in the open round that never left."""
    _company_id, round_id, _label = _open_round(conn, company_id)
    rows = conn.execute(
        """
        SELECT channel, email, phone, link_token
        FROM invitations
        WHERE round_id = %s
          AND sent_at IS NULL
        ORDER BY created_at
        """,
        (round_id,),
    ).fetchall()
    pending: list[tuple[str, str, str]] = []
    held: list[str] = []
    held_channels: set[str] = set()
    for row in rows:
        channel = row.get("channel") or "email"
        address = _row_address(row)
        if not address:
            continue
        if _channel_ready(channel):
            pending.append((address, row["link_token"], channel))
        else:
            held.append(address)
            held_channels.add(channel)
    if not pending and held_channels:
        _raise_unconfigured(held_channels)
    sent, not_sent = _deliver_pending(conn, pending)
    return {"sent": len(sent), "not_sent": _show(not_sent + held)}


def dispatch_unsent(conn) -> int:
    """Send every stored link whose channel is ready. Used when the API process starts."""
    rows = conn.execute(
        """
        SELECT channel, email, phone, link_token
        FROM invitations
        WHERE sent_at IS NULL
        ORDER BY created_at
        """
    ).fetchall()
    pending: list[tuple[str, str, str]] = []
    for row in rows:
        channel = row.get("channel") or "email"
        address = _row_address(row)
        if address and _channel_ready(channel):
            pending.append((address, row["link_token"], channel))
    if not pending:
        return 0
    sent, _failed = _deliver_pending(conn, pending)
    return len(sent)


def _deliver_pending(conn, pairs: list[tuple[str, str, str]]) -> tuple[list[tuple[str, str]], list[str]]:
    """Send pairs that are already stored. Mark the ones that left, then commit that mark."""
    if not pairs:
        return [], []
    email_pairs = [(address, token) for address, token, channel in pairs if channel == "email"]
    phone_pairs = [(address, token) for address, token, channel in pairs if channel == "whatsapp"]
    sent: list[tuple[str, str]] = []
    failed: list[str] = []
    if email_pairs:
        try:
            email_sent, email_failed = deliver_invitations(email_pairs)
        except (MailDeliveryError, MailNotConfigured):
            email_sent, email_failed = [], [address for address, _token in email_pairs]
        sent.extend(email_sent)
        failed.extend(email_failed)
    if phone_pairs:
        try:
            phone_sent, phone_failed = deliver_whatsapp(phone_pairs)
        except (WhatsAppDeliveryError, WhatsAppNotConfigured):
            phone_sent, phone_failed = [], [address for address, _token in phone_pairs]
        sent.extend(phone_sent)
        failed.extend(phone_failed)
    mark_sent(conn, sent)
    return sent, failed


def _channel_ready(channel: str) -> bool:
    if channel == "whatsapp":
        return whatsapp_ready()
    return smtp_ready()


def _row_address(row: dict) -> str | None:
    channel = row.get("channel") or "email"
    if channel == "whatsapp":
        return row.get("phone") or None
    return row.get("email") or None


def _raise_unconfigured(channels: set[str]) -> None:
    if channels == {"email"}:
        raise MailNotConfigured()
    if channels == {"whatsapp"}:
        raise WhatsAppNotConfigured()
    raise ChannelsNotConfigured()


def _show(addresses: list[str]) -> list[str]:
    return [present_address(address) for address in addresses]


def mark_sent(conn, sent: list[tuple[str, str]]) -> None:
    for _email, token in sent:
        conn.execute(
            """
            UPDATE invitations
            SET sent_at = now()
            WHERE link_token = %s
              AND sent_at IS NULL
            """,
            (token,),
        )
    if sent:
        conn.commit()


def list_invitations(conn, company_id) -> dict[str, Any]:
    """Participation for this company's open round.

    Counts stay aggregate. The only addresses returned are the ones whose
    message has not left, so the company can retry that same link.
    """
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
    unsent = _show(
        [
            item["address"]
            for item in conn.execute(
                """
                SELECT CASE
                    WHEN COALESCE(channel, 'email') = 'whatsapp' THEN phone
                    ELSE email
                END AS address
                FROM invitations
                WHERE round_id = %s
                  AND sent_at IS NULL
                ORDER BY address
                """,
                (round_id,),
            ).fetchall()
            if item["address"]
        ]
    )
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
        "unsent": unsent,
    }


def list_rounds(conn, company_id) -> list[dict[str, Any]]:
    """Every wave for this company. Counts and dates only: no addresses."""
    rows = conn.execute(
        """
        SELECT
          r.label,
          r.opened_on,
          r.closed_on,
          count(i.id) FILTER (WHERE i.status = 'pending') AS waiting,
          count(i.id) FILTER (WHERE i.status = 'submitted') AS responded,
          (
            SELECT max(h.submitted_on)
            FROM hse_responses AS h
            WHERE h.round_id = r.id
          ) AS latest_response_on
        FROM company_rounds AS r
        LEFT JOIN invitations AS i ON i.round_id = r.id
        WHERE r.company_id = %s
        GROUP BY r.id
        ORDER BY r.opened_on DESC, r.label DESC
        """,
        (company_id,),
    ).fetchall()
    listed = []
    for row in rows:
        waiting = int(row["waiting"])
        responded = int(row["responded"])
        invited = waiting + responded
        responded_percent = _percent(responded, invited)
        listed.append(
            {
                "label": row["label"],
                "opened_on": _day(row["opened_on"]),
                "closed_on": _day(row["closed_on"]),
                "invited": invited,
                "responded_percent": responded_percent,
                "waiting_percent": None if responded_percent is None else 100 - responded_percent,
                "latest_response_on": _day(row["latest_response_on"]),
            }
        )
    return listed


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


def _day(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


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
