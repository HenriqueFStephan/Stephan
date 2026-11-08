"""Parse one invitation list. One column, and each cell chooses its channel.

The header `email` or `contato` is optional. When the first cell is one of
those words, that row is the header. Otherwise every row is an address. A
value with @ that is a valid email is
sent by email. A Brazilian phone number is sent on WhatsApp. JSON uses the
same two keys, one per row. Unknown columns reject the whole file so a name
is never stored by accident.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from io import BytesIO

from email_validator import EmailNotValidError, validate_email
from openpyxl import load_workbook

MAX_BYTES = 1_000_000
MAX_ROWS = 5_000
CONTACT_HEADERS = {"email", "contato"}
_PHONE_CHARS = set("0123456789+ -().")


class InvitationFileError(Exception):
    def __init__(self, code: str, columns: list[str] | None = None) -> None:
        self.code = code
        self.columns = columns or []
        super().__init__(code)


@dataclass
class ParsedInvitations:
    format: str
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    ignored_empty: int = 0
    duplicates_in_file: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)


def parse_invitation_file(filename: str, data: bytes) -> ParsedInvitations:
    if len(data) > MAX_BYTES:
        raise InvitationFileError("bad_file")
    kind = _kind(filename, data)
    if kind == "xlsx":
        rows = _xlsx_rows(data)
        parsed = _from_rows(rows)
        parsed.format = "xlsx"
        return parsed
    if kind == "json":
        parsed = _from_json(data)
        parsed.format = "json"
        return parsed
    parsed = _from_csv(data)
    parsed.format = "csv"
    return parsed


def present_address(address: str) -> str:
    """Show a stored phone as +55 19 99877-2525. An email is returned as stored."""
    if address.isdigit() and address.startswith("55") and len(address) in (12, 13):
        national = address[2:]
        ddd = national[:2]
        rest = national[2:]
        if len(rest) == 9:
            pretty = f"{rest[:5]}-{rest[5:]}"
        else:
            pretty = f"{rest[:4]}-{rest[4:]}"
        return f"+55 {ddd} {pretty}"
    return address


def _kind(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if data[:2] == b"PK" or name.endswith(".xlsx"):
        return "xlsx"
    stripped = data.lstrip(b"\xef\xbb\xbf \t\r\n")
    if stripped.startswith(b"{") or name.endswith(".json"):
        return "json"
    return "csv"


def _from_json(data: bytes) -> ParsedInvitations:
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvitationFileError("bad_file") from exc
    if not isinstance(payload, dict):
        raise InvitationFileError("bad_file")
    extra_root = sorted(set(payload) - {"invitations"})
    if extra_root:
        raise InvitationFileError("unknown_columns", extra_root)
    if set(payload) != {"invitations"} or not isinstance(payload["invitations"], list):
        raise InvitationFileError("bad_file")
    rows: list[list[str]] = [["email"]]
    for item in payload["invitations"]:
        if not isinstance(item, dict):
            raise InvitationFileError("bad_file")
        extra = sorted(str(key) for key in item if key not in CONTACT_HEADERS)
        if extra:
            raise InvitationFileError("unknown_columns", extra)
        present = [key for key in ("email", "contato") if key in item]
        if len(present) != 1:
            raise InvitationFileError("bad_file")
        value = item[present[0]]
        if value is None:
            rows.append([""])
        elif isinstance(value, str):
            rows.append([value])
        else:
            rows.append([str(value)])
    return _from_rows(rows)


def _from_csv(data: bytes) -> ParsedInvitations:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvitationFileError("bad_file") from exc
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise InvitationFileError("bad_file")
    delimiter = _delimiter(lines[0])
    rows: list[list[str]] = []
    for line in lines:
        if not line.strip():
            rows.append([""])
            continue
        try:
            cells = next(csv.reader([line], delimiter=delimiter))
        except csv.Error as exc:
            raise InvitationFileError("bad_file") from exc
        rows.append(cells)
    return _from_rows(rows)


def _delimiter(first_line: str) -> str:
    if ";" in first_line:
        return ";"
    return ","


def _xlsx_rows(data: bytes) -> list[list[str]]:
    if data[:2] != b"PK":
        raise InvitationFileError("bad_file")
    try:
        workbook = load_workbook(BytesIO(data), read_only=False, data_only=True)
    except Exception as exc:
        raise InvitationFileError("bad_file") from exc
    try:
        if not workbook.worksheets:
            raise InvitationFileError("bad_file")
        sheet = workbook.worksheets[0]
        rows: list[list[str]] = []
        for row in sheet.iter_rows(values_only=True):
            rows.append([_cell_text(value) for value in row])
        return rows
    finally:
        workbook.close()


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _from_rows(rows: list[list[str]]) -> ParsedInvitations:
    if not rows:
        raise InvitationFileError("bad_file")
    data_rows = _without_optional_header(rows)
    if len(data_rows) > MAX_ROWS:
        raise InvitationFileError("bad_file")

    parsed = ParsedInvitations(format="csv")
    seen: set[str] = set()
    for raw in data_rows:
        _reject_side_values(raw)
        kind, channel, value = _classify_contact(raw[0] if raw else "")
        if kind == "empty":
            parsed.ignored_empty += 1
        elif kind == "invalid":
            parsed.invalid.append(value)
        elif value in seen:
            parsed.duplicates_in_file.append(value)
        elif channel == "whatsapp":
            seen.add(value)
            parsed.phones.append(value)
        else:
            seen.add(value)
            parsed.emails.append(value)
    return parsed


def _without_optional_header(rows: list[list[str]]) -> list[list[str]]:
    """Skip a first row of `email` or `contato`. Any other first row is an address."""
    header = _trim_row(rows[0])
    folded = [cell.casefold() for cell in header]
    if folded in (["email"], ["contato"]):
        return rows[1:]
    if any(cell in CONTACT_HEADERS for cell in folded):
        unknown = [cell for cell in header if cell and cell.casefold() not in CONTACT_HEADERS]
        raise InvitationFileError("unknown_columns", unknown or ["column_2"])
    return rows


def _trim_row(row: list[str]) -> list[str]:
    cells = list(row)
    while cells and cells[-1].strip() == "":
        cells.pop()
    return [cell.strip() for cell in cells]


def _reject_side_values(row: list[str]) -> None:
    extras = [cell.strip() for cell in row[1:] if cell.strip()]
    if extras:
        raise InvitationFileError("unknown_columns", ["column_2"])


def _classify_contact(value: str) -> tuple[str, str, str]:
    text = value.strip()
    if not text:
        return "empty", "", ""
    if any(ch in text for ch in "\r\n\t"):
        return "invalid", "", text[:200]
    if "@" in text:
        try:
            checked = validate_email(text, check_deliverability=False)
        except EmailNotValidError:
            return "invalid", "", text[:200]
        return "ok", "email", checked.normalized.casefold()
    phone = _normalize_phone(text)
    if phone:
        return "ok", "whatsapp", phone
    return "invalid", "", text[:200]


def _normalize_phone(text: str) -> str | None:
    if any(ch not in _PHONE_CHARS for ch in text):
        return None
    digits = re.sub(r"\D", "", text)
    if digits.startswith("0") and len(digits) - 1 in (10, 11, 12, 13):
        digits = digits[1:]
    if digits.startswith("55") and len(digits) in (12, 13):
        national = digits[2:]
    elif len(digits) in (10, 11):
        national = digits
        digits = "55" + digits
    else:
        return None
    if national[:1] == "0":
        return None
    if len(national) not in (10, 11):
        return None
    return digits
