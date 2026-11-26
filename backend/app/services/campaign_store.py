"""Store invitation lists and anonymous HSE answers for one company at a time.

The answer write does not take an email, a token, or an invitation id.
The invitation is marked submitted in the same transaction, after the lookup
by token hash, and that id is not copied onto the answer.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
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
from app.services.invitation_video import video_ready
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
    "education": (
        "fundamental_incomplete",
        "fundamental_complete",
        "high_school_incomplete",
        "high_school",
        "higher_incomplete",
        "higher_complete",
        "postgraduate",
        "fundamental",
    ),
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
# Questions still on the form. Older columns stay in DEMOGRAPHIC_FIELDS so a
# stored row can keep them, and a new form may omit them.
REQUIRED_DEMOGRAPHIC_KEYS = frozenset()
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

# The form goes at least this long after its video, so the person gets them in order.
VIDEO_LEAD = timedelta(seconds=60)
# How far ahead the company may schedule a send.
MAX_SCHEDULE_AHEAD = timedelta(days=365)
# A message that came due this recently is still on its way. Older ones are failures.
_FAILURE_GRACE = timedelta(minutes=5)
# The automatic pass stops retrying a failure after this long. The retry button has no limit.
AUTO_RETRY_WINDOW = timedelta(hours=24)
# Postgres advisory lock key so only one send pass runs at a time.
_DUE_LOCK = 7_203_041


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
    """Store new addresses whose channel is ready. Nothing is sent here.

    The list is held until the company chooses when the video and the form go
    out (see release_invitations). An address already in this round, whether
    held, scheduled or sent, is not added again. A channel that is not
    configured does not get a new row.
    """
    company_id, round_id, round_label = _open_round(conn, company_id)
    existing: set[str] = set()
    for row in conn.execute(
        "SELECT channel, email, phone FROM invitations WHERE round_id = %s",
        (round_id,),
    ).fetchall():
        address = _row_address(row)
        if address:
            existing.add(address)
    contacts = [("email", address) for address in parsed.emails] + [
        ("whatsapp", address) for address in parsed.phones
    ]
    already: list[str] = []
    fresh: list[tuple[str, str]] = []
    for channel, address in contacts:
        if address in existing:
            already.append(address)
        else:
            fresh.append((channel, address))
    send_fresh = [(channel, address) for channel, address in fresh if _channel_ready(channel)]
    blocked_fresh = [(channel, address) for channel, address in fresh if not _channel_ready(channel)]
    if fresh and not send_fresh:
        _raise_unconfigured({channel for channel, _address in fresh})

    upload_id = conn.execute(
        """
        INSERT INTO invitation_uploads (id, company_id, round_id, source_name, format)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (uuid4(), company_id, round_id, _source_name(filename), parsed.format),
    ).fetchone()["id"]
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

    return {
        "round_label": round_label,
        "accepted": len(send_fresh),
        "ignored_empty": parsed.ignored_empty,
        "duplicates_in_file": _show(parsed.duplicates_in_file),
        "already_invited": _show(already),
        "invalid": parsed.invalid,
        "not_sent": [],
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


class VideoNotConfigured(Exception):
    """The tutorial video file is not on the server."""


class NothingToSend(Exception):
    """This round has no saved addresses waiting to be sent."""


class BadSchedule(Exception):
    """The times are not allowed. code is form_before_video or too_far."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def release_invitations(
    conn,
    company_id,
    video_at: datetime | None = None,
    form_at: datetime | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Choose when the held addresses get the video and the form.

    Nothing leaves here. The send step (process_due) picks each message up when
    its time comes. None means now. The video may be days ahead. The form is
    never earlier than the video, and it only goes after the video has gone.
    """
    moment = now or datetime.now(timezone.utc)
    video_when = _aware(video_at) if video_at is not None else moment
    form_when = _aware(form_at) if form_at is not None else video_when
    if video_when < moment:
        video_when = moment
    if form_when < video_when:
        raise BadSchedule("form_before_video")
    if form_when > moment + MAX_SCHEDULE_AHEAD or video_when > moment + MAX_SCHEDULE_AHEAD:
        raise BadSchedule("too_far")
    if not video_ready():
        raise VideoNotConfigured()
    _company_id, round_id, _label = _open_round(conn, company_id)
    channels = {
        row.get("channel") or "email"
        for row in conn.execute(
            "SELECT channel FROM invitations WHERE round_id = %s AND form_due_at IS NULL",
            (round_id,),
        ).fetchall()
    }
    if not channels:
        raise NothingToSend()
    missing = {channel for channel in channels if not _channel_ready(channel)}
    if missing:
        _raise_unconfigured(missing)
    people = conn.execute(
        """
        UPDATE invitations
        SET video_due_at = %s, form_due_at = %s
        WHERE round_id = %s
          AND form_due_at IS NULL
        """,
        (video_when, form_when, round_id),
    ).rowcount
    conn.commit()
    return {
        "people": people,
        "video_at": video_when.isoformat(),
        "form_at": form_when.isoformat(),
        "immediate": video_when <= moment + timedelta(seconds=1),
    }


def process_due(
    conn,
    company_id=None,
    now: datetime | None = None,
    max_age: timedelta | None = None,
) -> dict[str, int]:
    """Send every video and every form whose time has come.

    A video goes first. A form goes only after its video was sent and the
    VIDEO_LEAD gap has passed, so the person gets them in that order. A channel
    that is not configured is skipped and tried again on the next pass. Only one
    pass runs at a time, so a second worker cannot send the same message twice.
    max_age keeps the automatic pass from retrying an old failure forever: a
    message that came due longer ago than that waits for the company's retry.
    """
    moment = now or datetime.now(timezone.utc)
    locked = conn.execute("SELECT pg_try_advisory_lock(%s) AS ok", (_DUE_LOCK,)).fetchone()["ok"]
    if not locked:
        conn.rollback()
        return {"videos": 0, "forms": 0}
    try:
        videos = _send_due(conn, "video", company_id, moment, max_age)
        forms = _send_due(conn, "form", company_id, moment, max_age)
    finally:
        conn.rollback()
        conn.execute("SELECT pg_advisory_unlock(%s)", (_DUE_LOCK,))
        conn.commit()
    return {"videos": videos, "forms": forms}


def _send_due(conn, kind: str, company_id, moment: datetime, max_age: timedelta | None = None) -> int:
    scope = "" if company_id is None else "AND company_id = %s"
    oldest = moment - (timedelta(days=36500) if max_age is None else max_age)
    if kind == "video":
        condition = """
            video_due_at IS NOT NULL
            AND video_due_at <= %s
            AND video_due_at > %s
            AND video_sent_at IS NULL
            AND sent_at IS NULL
        """
        params: list[Any] = [moment, oldest]
        order = "video_due_at, created_at"
    else:
        condition = """
            form_due_at <= %s
            AND form_due_at > %s
            AND sent_at IS NULL
            AND (video_due_at IS NULL OR (video_sent_at IS NOT NULL AND video_sent_at <= %s))
        """
        params = [moment, oldest, moment - VIDEO_LEAD]
        order = "form_due_at, created_at"
    if company_id is not None:
        params.append(company_id)
    rows = conn.execute(
        f"""
        SELECT channel, email, phone, link_token
        FROM invitations
        WHERE form_due_at IS NOT NULL
          AND {condition}
          {scope}
        ORDER BY {order}
        """,
        params,
    ).fetchall()
    pending: list[tuple[str, str, str]] = []
    for row in rows:
        channel = row.get("channel") or "email"
        address = _row_address(row)
        if address and _channel_ready(channel):
            pending.append((address, row["link_token"], channel))
    if not pending:
        return 0
    sent, _failed = _deliver_pending(conn, pending, kind, moment)
    return len(sent)


def retry_unsent(conn, company_id) -> dict[str, Any]:
    """Try again for the addresses in the open round whose message is due and never left."""
    _company_id, round_id, _label = _open_round(conn, company_id)
    rows = _due_unsent(conn, round_id, datetime.now(timezone.utc), grace=timedelta(0))
    ready = [row for row in rows if _channel_ready(row.get("channel") or "email")]
    stuck = {row.get("channel") or "email" for row in rows if not _channel_ready(row.get("channel") or "email")}
    if rows and not ready and stuck:
        _raise_unconfigured(stuck)
    moment = datetime.now(timezone.utc)
    done = process_due(conn, company_id=company_id, now=moment)
    remaining = _due_unsent(conn, round_id, moment, grace=timedelta(0))
    return {
        "sent": done["forms"],
        "not_sent": _show([_row_address(row) for row in remaining if _row_address(row)]),
    }


def dispatch_unsent(conn) -> int:
    """One pass over every company. The API runs it at start and then every minute."""
    done = process_due(conn, max_age=AUTO_RETRY_WINDOW)
    return done["videos"] + done["forms"]


def _due_unsent(conn, round_id, moment: datetime, grace: timedelta | None = None) -> list[dict]:
    """Rows whose form time came, at least `grace` ago, and whose form has not left."""
    wait = _FAILURE_GRACE if grace is None else grace
    return conn.execute(
        """
        SELECT channel, email, phone, link_token
        FROM invitations
        WHERE round_id = %s
          AND form_due_at IS NOT NULL
          AND form_due_at <= %s
          AND sent_at IS NULL
        ORDER BY created_at
        """,
        (round_id, moment - wait),
    ).fetchall()


def _deliver_pending(
    conn,
    pairs: list[tuple[str, str, str]],
    kind: str = "form",
    moment: datetime | None = None,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Send pairs that are already stored. Mark the ones that left, then commit that mark.

    kind is "form" or "video". A video is marked in video_sent_at, a form in sent_at.
    """
    if not pairs:
        return [], []
    email_pairs = [(address, token) for address, token, channel in pairs if channel == "email"]
    phone_pairs = [(address, token) for address, token, channel in pairs if channel == "whatsapp"]
    sent: list[tuple[str, str]] = []
    failed: list[str] = []
    if email_pairs:
        try:
            email_sent, email_failed = deliver_invitations(email_pairs, kind)
        except (MailDeliveryError, MailNotConfigured):
            email_sent, email_failed = [], [address for address, _token in email_pairs]
        sent.extend(email_sent)
        failed.extend(email_failed)
    if phone_pairs:
        try:
            phone_sent, phone_failed = deliver_whatsapp(phone_pairs, kind)
        except (WhatsAppDeliveryError, WhatsAppNotConfigured):
            phone_sent, phone_failed = [], [address for address, _token in phone_pairs]
        sent.extend(phone_sent)
        failed.extend(phone_failed)
    mark_sent(conn, sent, kind, moment)
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


def mark_sent(
    conn,
    sent: list[tuple[str, str]],
    kind: str = "form",
    moment: datetime | None = None,
) -> None:
    """Record that a message left. A form sets sent_at and a video sets video_sent_at."""
    column = "video_sent_at" if kind == "video" else "sent_at"
    when = moment or datetime.now(timezone.utc)
    for _address, token in sent:
        conn.execute(
            f"""
            UPDATE invitations
            SET {column} = %s
            WHERE link_token = %s
              AND {column} IS NULL
            """,
            (when, token),
        )
    if sent:
        conn.commit()


def _aware(value: datetime) -> datetime:
    """A time with no zone is read as UTC. The browser sends one with its offset."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def list_invitations(conn, company_id) -> dict[str, Any]:
    """Participation for this company's open round.

    Counts stay aggregate. The only addresses returned are the ones whose
    message was due and has not left, so the company can retry that same link.
    held counts the saved addresses that have no send time yet. scheduled
    groups the others by the time their video and their form go out.
    """
    _company_id, round_id, round_label = _open_round(conn, company_id)
    moment = datetime.now(timezone.utc)
    row = conn.execute(
        """
        SELECT
          count(*) FILTER (WHERE status = 'pending') AS waiting,
          count(*) FILTER (WHERE status = 'submitted') AS responded,
          count(*) FILTER (WHERE form_due_at IS NULL) AS held
        FROM invitations
        WHERE round_id = %s
        """,
        (round_id,),
    ).fetchone()
    unsent = _show(
        sorted(
            address
            for address in (_row_address(item) for item in _due_unsent(conn, round_id, moment))
            if address
        )
    )
    scheduled = [
        {
            "video_at": item["video_due_at"].isoformat() if item["video_due_at"] else None,
            "form_at": item["form_due_at"].isoformat(),
            "people": int(item["people"]),
        }
        for item in conn.execute(
            """
            SELECT video_due_at, form_due_at, count(*) AS people
            FROM invitations
            WHERE round_id = %s
              AND sent_at IS NULL
              AND form_due_at IS NOT NULL
              AND form_due_at > %s
            GROUP BY video_due_at, form_due_at
            ORDER BY form_due_at, video_due_at
            """,
            (round_id, moment - _FAILURE_GRACE),
        ).fetchall()
    ]
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
        "held": int(row["held"]),
        "scheduled": scheduled,
        "video_ready": video_ready(),
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
    """Keep Anexo B codes only. The form no longer asks them, so a new answer may omit every one."""
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


def open_pending_invitation(conn, token: str) -> dict[str, Any]:
    """Return the company name and any unfinished form for a pending link.

    draft is None when the link is valid and nothing has been saved yet.
    The company name is the same for every person in that wave.
    Does not return the address, the token, or the invitation id.
    """
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    mark_columns = ", ".join(f"d.{column}" for column in ITEM_COLUMNS)
    row = conn.execute(
        f"""
        SELECT c.name AS company_name, i.status, d.place, d.item_index, d.demographics, {mark_columns}
        FROM invitations AS i
        JOIN companies AS c ON c.id = i.company_id
        LEFT JOIN hse_drafts AS d ON d.link_token_hash = i.link_token_hash
        WHERE i.link_token_hash = %s
        """,
        (digest,),
    ).fetchone()
    if row is None:
        raise UnknownInvitation()
    if row["status"] != "pending":
        raise InvitationAlreadySubmitted()
    draft = None
    if row["place"] is not None:
        draft = {
            "place": row["place"],
            "index": row["item_index"],
            "demographics": row["demographics"] or {},
            "answers": [row[column] for column in ITEM_COLUMNS],
        }
    return {"company_name": row["company_name"], "draft": draft}


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
