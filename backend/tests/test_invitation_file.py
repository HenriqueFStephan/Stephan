"""Invitation files: one shape each, and no extra columns."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.invitation_file import InvitationFileError, parse_invitation_file, present_address

EXAMPLES = Path(__file__).resolve().parents[2] / "docs" / "tool"


def test_json_example_keeps_only_emails():
    parsed = parse_invitation_file("invitations.json", (EXAMPLES / "invitations.json").read_bytes())
    assert parsed.format == "json"
    assert parsed.emails == ["pessoa.um@example.com", "pessoa.dois@example.com"]


def test_json_rejects_a_bare_array_and_any_other_shape():
    with pytest.raises(InvitationFileError) as bare:
        parse_invitation_file("list.json", b'[{"email":"a@example.com"}]')
    assert bare.value.code == "bad_file"

    with pytest.raises(InvitationFileError) as extra:
        parse_invitation_file(
            "list.json",
            b'{"invitations":[{"email":"a@example.com"}],"company":"x"}',
        )
    assert extra.value.code == "unknown_columns"
    assert extra.value.columns == ["company"]


def test_json_rejects_a_name_and_stores_nothing_from_that_file():
    with pytest.raises(InvitationFileError) as error:
        parse_invitation_file(
            "list.json",
            b'{"invitations":[{"email":"a@example.com","name":"Ada"}]}',
        )
    assert error.value.code == "unknown_columns"
    assert error.value.columns == ["name"]


def test_csv_example_and_semicolon_header():
    comma = parse_invitation_file("invitations.csv", (EXAMPLES / "invitations.csv").read_bytes())
    assert comma.format == "csv"
    assert comma.emails == ["pessoa.um@example.com", "pessoa.dois@example.com"]

    semi = parse_invitation_file(
        "invitations.semicolon.csv",
        (EXAMPLES / "invitations.semicolon.csv").read_bytes(),
    )
    assert semi.emails == ["pessoa.tres@example.com"]


def test_csv_rejects_unknown_columns_and_ignores_empty_rows():
    with pytest.raises(InvitationFileError) as named:
        parse_invitation_file("people.csv", b"email,name\nada@example.com,Ada\n")
    assert named.value.code == "unknown_columns"
    assert named.value.columns == ["name"]

    named_only = parse_invitation_file("people.csv", "nome\nada@example.com\n".encode())
    assert named_only.emails == ["ada@example.com"]
    assert named_only.invalid == ["nome"]

    parsed = parse_invitation_file(
        "people.csv",
        "email\n\npessoa.um@example.com\n,\nPESSOA.UM@example.com\nnot-an-email\n".encode(),
    )
    assert parsed.emails == ["pessoa.um@example.com"]
    assert parsed.duplicates_in_file == ["pessoa.um@example.com"]
    assert parsed.invalid == ["not-an-email"]
    assert parsed.ignored_empty == 2


def test_csv_and_xlsx_without_a_header_keep_the_first_address():
    parsed = parse_invitation_file(
        "people.csv",
        b"pessoa.um@example.com\npessoa.dois@example.com\n",
    )
    assert parsed.emails == ["pessoa.um@example.com", "pessoa.dois@example.com"]
    assert parsed.invalid == []

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["pessoa.um@example.com"])
    sheet.append(["pessoa.dois@example.com"])
    opened = parse_invitation_file("lista.xlsx", _workbook_bytes(workbook))
    assert opened.emails == ["pessoa.um@example.com", "pessoa.dois@example.com"]


def test_csv_rejects_bytes_that_are_not_utf8():
    with pytest.raises(InvitationFileError) as error:
        parse_invitation_file("people.csv", b"email\n\xff\n")
    assert error.value.code == "bad_file"


def test_xlsx_example_matches_the_csv_example():
    parsed = parse_invitation_file("invitations.xlsx", (EXAMPLES / "invitations.xlsx").read_bytes())
    assert parsed.format == "xlsx"
    assert parsed.emails == ["pessoa.um@example.com", "pessoa.dois@example.com"]


def test_xlsx_reads_the_first_sheet_only_and_rejects_a_second_column():
    workbook = Workbook()
    first = workbook.active
    first.title = "convites"
    first.append(["email"])
    first.append(["pessoa.um@example.com"])
    first.append([""])
    second = workbook.create_sheet("nomes")
    second.append(["nome"])
    second.append(["Ada"])
    data = _workbook_bytes(workbook)

    parsed = parse_invitation_file("lista.xlsx", data)
    assert parsed.format == "xlsx"
    assert parsed.emails == ["pessoa.um@example.com"]
    assert parsed.ignored_empty == 1

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["email", "cargo"])
    sheet.append(["pessoa.um@example.com", "analista"])
    with pytest.raises(InvitationFileError) as error:
        parse_invitation_file("lista.xlsx", _workbook_bytes(workbook))
    assert error.value.code == "unknown_columns"
    assert "cargo" in error.value.columns


def test_one_column_keeps_an_email_and_a_phone_together():
    parsed = parse_invitation_file(
        "people.csv",
        (
            "email\n"
            "pessoa.um@example.com\n"
            "+55 19 99877-2525\n"
            "(19) 99877-2525\n"
            "019998772525\n"
            "998772525\n"
            "not-an-email\n"
        ).encode(),
    )
    assert parsed.emails == ["pessoa.um@example.com"]
    assert parsed.phones == ["5519998772525"]
    assert parsed.duplicates_in_file == ["5519998772525", "5519998772525"]
    assert parsed.invalid == ["998772525", "not-an-email"]
    assert present_address("5519998772525") == "+55 19 99877-2525"
    assert present_address("551133334444") == "+55 11 3333-4444"


def test_contato_header_and_json_accept_either_key():
    parsed = parse_invitation_file(
        "people.csv",
        "contato\npessoa.um@example.com\n".encode(),
    )
    assert parsed.emails == ["pessoa.um@example.com"]
    assert parsed.phones == []

    mixed = parse_invitation_file(
        "list.json",
        b'{"invitations":[{"email":"pessoa.um@example.com"},{"contato":"(19) 99877-2525"}]}',
    )
    assert mixed.emails == ["pessoa.um@example.com"]
    assert mixed.phones == ["5519998772525"]

    with pytest.raises(InvitationFileError) as both:
        parse_invitation_file(
            "list.json",
            b'{"invitations":[{"email":"pessoa.um@example.com","contato":"19998772525"}]}',
        )
    assert both.value.code == "bad_file"


def test_xlsx_reads_a_phone_stored_as_a_number():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["contato"])
    sheet.append([11998772525])
    sheet.append([11988887777.0])
    parsed = parse_invitation_file("lista.xlsx", _workbook_bytes(workbook))
    assert parsed.phones == ["5511998772525", "5511988887777"]
    assert parsed.emails == []


def _workbook_bytes(workbook: Workbook) -> bytes:
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
