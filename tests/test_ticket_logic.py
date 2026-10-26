"""Pytest suite for src/ticket_logic.py (pure logic, no Streamlit, no network)."""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.ticket_logic import (
    CATEGORIES,
    MAX_MESSAGE_LENGTH,
    PRIORITIES,
    TicketDataError,
    analyze_tickets,
    classify_ticket,
    count_by,
    draft_response,
    normalize_tickets,
    parse_csv,
    to_safe_csv,
)

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_tickets.csv"


def _frame(rows: list[dict], columns: list[str] | None = None) -> pd.DataFrame:
    columns = columns or ["ticket_id", "customer_message", "created_at"]
    return pd.DataFrame(rows, columns=columns).astype(str)


def _valid_row(ticket_id: str = "T-1", message: str = "Where is my package?",
               created_at: str = "2026-03-14T09:30:00") -> dict:
    return {"ticket_id": ticket_id, "customer_message": message, "created_at": created_at}


# --- AT-6 deterministic classification ---------------------------------------

def test_at_6_1_charged_twice_urgent_is_billing_high_negative():
    result = classify_ticket("I was charged twice, fix this immediately")
    assert result == {"category": "Billing/Payment", "priority": "High", "sentiment": "Negative"}


def test_at_6_2_thanks_jacket_fits_is_general_low_positive():
    result = classify_ticket("Thanks, the jacket fits great")
    assert result == {"category": "General Inquiry", "priority": "Low", "sentiment": "Positive"}


def test_at_6_3_text_matching_no_rule_is_general_low_neutral():
    result = classify_ticket("The weather is nice today")
    assert result == {"category": "General Inquiry", "priority": "Low", "sentiment": "Neutral"}


def test_classification_is_case_insensitive():
    lower = classify_ticket("i was charged twice, fix this immediately")
    upper = classify_ticket("I WAS CHARGED TWICE, FIX THIS IMMEDIATELY")
    mixed = classify_ticket("I Was Charged Twice, Fix This IMMEDIATELY")
    assert lower == upper == mixed


def test_classification_is_deterministic_across_repeated_calls():
    message = "My parcel is delayed and I am worried, please help"
    results = {tuple(sorted(classify_ticket(message).items())) for _ in range(20)}
    assert len(results) == 1


def test_category_precedence_billing_wins_over_refund():
    # "charged" (Billing/Payment) and "refund" (Refund/Return) both match;
    # Billing/Payment is earlier in the fixed precedence order.
    assert CATEGORIES.index("Billing/Payment") < CATEGORIES.index("Refund/Return")
    assert classify_ticket("I was charged and want a refund")["category"] == "Billing/Payment"


# --- US-1 CSV validation -----------------------------------------------------

def test_missing_customer_message_column_error_names_the_column():
    df = _frame([_valid_row()], columns=["ticket_id", "created_at"])
    with pytest.raises(TicketDataError) as excinfo:
        normalize_tickets(df)
    assert "customer_message" in str(excinfo.value)


def test_parse_csv_rejects_empty_bytes():
    with pytest.raises(TicketDataError, match="empty"):
        parse_csv(b"")


def test_parse_csv_rejects_whitespace_only_upload():
    with pytest.raises(TicketDataError, match="empty"):
        parse_csv(b"   \n\t  \n")


def test_blank_message_row_is_skipped_with_warning_and_valid_rows_kept():
    df = _frame([
        _valid_row("T-1", "Where is my package?"),
        _valid_row("T-2", "   "),
        _valid_row("T-3", "Thanks, great service"),
    ])
    clean, warnings = normalize_tickets(df)
    assert list(clean["ticket_id"]) == ["T-1", "T-3"]
    assert len(warnings) == 1
    assert "blank customer_message" in warnings[0] and "1 row" in warnings[0]


def test_duplicate_ticket_id_keeps_first_and_warns():
    df = _frame([
        _valid_row("T-1", "first message"),
        _valid_row("T-1", "second message"),
        _valid_row("T-2", "third message"),
    ])
    clean, warnings = normalize_tickets(df)
    assert list(clean["customer_message"]) == ["first message", "third message"]
    assert any("duplicate ticket_id" in w for w in warnings)


def test_over_length_message_is_skipped_and_boundary_length_kept():
    at_limit = "a" * MAX_MESSAGE_LENGTH
    over_limit = "a" * (MAX_MESSAGE_LENGTH + 1)
    df = _frame([_valid_row("T-1", at_limit), _valid_row("T-2", over_limit)])
    clean, warnings = normalize_tickets(df)
    assert list(clean["ticket_id"]) == ["T-1"]
    assert any(f"longer than {MAX_MESSAGE_LENGTH}" in w for w in warnings)


def test_invalid_created_at_row_is_skipped_with_warning():
    df = _frame([
        _valid_row("T-1", created_at="2026-03-14T09:30:00"),
        _valid_row("T-2", created_at="not-a-date"),
        _valid_row("T-3", created_at="2026-03-14"),  # date-only is accepted
    ])
    clean, warnings = normalize_tickets(df)
    assert list(clean["ticket_id"]) == ["T-1", "T-3"]
    assert any("created_at" in w for w in warnings)


def test_all_invalid_rows_raise_ticket_data_error():
    df = _frame([
        _valid_row("T-1", message=""),
        _valid_row("T-2", created_at="garbage"),
    ])
    with pytest.raises(TicketDataError, match="No valid ticket rows"):
        normalize_tickets(df)


# --- US-1 / US-2 / US-3 / US-4 end-to-end on the sample file -----------------

def test_sample_file_analyzes_all_22_rows_with_no_warnings():
    raw = SAMPLE_PATH.read_bytes()
    analyzed, warnings = analyze_tickets(parse_csv(raw))
    assert warnings == []
    assert len(analyzed) == 22
    expected_columns = {"ticket_id", "customer_message", "created_at",
                        "category", "priority", "sentiment", "suggested_response"}
    assert expected_columns.issubset(analyzed.columns)
    assert set(analyzed["category"]) <= set(CATEGORIES)
    assert set(analyzed["priority"]) <= set(PRIORITIES)


def test_count_by_includes_zero_count_labels_and_sums_to_total():
    df = pd.DataFrame({"priority": ["High", "High"]})
    counts = count_by(df, "priority", PRIORITIES)
    assert list(counts["priority"]) == PRIORITIES
    assert dict(zip(counts["priority"], counts["count"])) == {"High": 2, "Medium": 0, "Low": 0}
    assert counts["count"].sum() == len(df)


# --- US-7 draft responses ----------------------------------------------------

def test_draft_response_does_not_echo_customer_text():
    marker = "Zebra-Quartz-7731"
    message = f"{marker} my order arrived broken and I am furious"
    reply = draft_response(message, "Product Defect", "High")
    assert marker not in reply
    assert message not in reply


def test_draft_response_uses_softer_opener_for_negative_sentiment():
    reply = draft_response("terrible, worst service ever", "Product Defect", "Medium")
    assert reply.startswith("Hello, we are very sorry")


# --- US-8 / export safety ----------------------------------------------------

def test_to_safe_csv_neutralises_spreadsheet_formula_prefixes():
    df = pd.DataFrame({
        "ticket_id": ["T-1", "T-2", "T-3", "T-4", "T-5"],
        "customer_message": ['=HYPERLINK("http://example.invalid")', "+1 555 0100",
                             "-cmd|' /C calc'!A0", "@SUM(A1:A2)", "plain text"],
    })
    rows = list(csv.reader(io.StringIO(to_safe_csv(df))))
    messages = [row[1] for row in rows[1:]]
    assert messages[0].startswith("'=")
    assert messages[1].startswith("'+")
    assert messages[2].startswith("'-")
    assert messages[3].startswith("'@")
    assert messages[4] == "plain text"


# --- Upload path: raw CSV bytes -> parse_csv -> normalize (added QA coverage) --

def test_normal_csv_upload_bytes_parse_into_clean_tickets():
    raw = (
        "ticket_id,customer_message,created_at\n"
        'T-1,"My order arrived damaged, I want a refund.",2026-03-14T09:30:00\n'
        "T-2,Where is my package?,2026-03-14T10:05:00\n"
    ).encode("utf-8")
    clean, warnings = normalize_tickets(parse_csv(raw))
    assert warnings == []
    assert list(clean["ticket_id"]) == ["T-1", "T-2"]
    assert list(clean["customer_message"]) == [
        "My order arrived damaged, I want a refund.", "Where is my package?",
    ]
    assert str(clean["created_at"].dtype).startswith("datetime64")


def test_normal_csv_upload_with_utf8_bom_and_padded_headers_is_accepted():
    raw = "﻿ ticket_id , customer_message ,created_at\nT-1,Hello there,2026-03-14T09:30:00\n".encode("utf-8")
    clean, _ = normalize_tickets(parse_csv(raw))
    assert list(clean["ticket_id"]) == ["T-1"]


def test_csv_upload_missing_ticket_id_header_names_the_column():
    raw = b"customer_message,created_at\nWhere is my package?,2026-03-14T09:30:00\n"
    with pytest.raises(TicketDataError) as excinfo:
        normalize_tickets(parse_csv(raw))
    assert "ticket_id" in str(excinfo.value)
    assert "Missing required column" in str(excinfo.value)


def test_csv_upload_missing_multiple_headers_lists_all_of_them():
    raw = b"ticket_id\nT-1\n"
    with pytest.raises(TicketDataError) as excinfo:
        normalize_tickets(parse_csv(raw))
    assert "customer_message" in str(excinfo.value)
    assert "created_at" in str(excinfo.value)


def test_csv_upload_headers_only_without_rows_is_rejected():
    raw = b"ticket_id,customer_message,created_at\n"
    with pytest.raises(TicketDataError, match="no ticket rows"):
        normalize_tickets(parse_csv(raw))


def test_csv_upload_empty_customer_message_cell_is_skipped_with_warning():
    raw = (
        b"ticket_id,customer_message,created_at\n"
        b"T-1,,2026-03-14T09:30:00\n"
        b"T-2,Real message,2026-03-14T10:00:00\n"
    )
    clean, warnings = normalize_tickets(parse_csv(raw))
    assert list(clean["ticket_id"]) == ["T-2"]
    assert any("blank customer_message" in w for w in warnings)


def test_csv_upload_empty_ticket_id_cell_is_skipped_with_warning():
    raw = (
        b"ticket_id,customer_message,created_at\n"
        b",Orphan message,2026-03-14T09:30:00\n"
        b"T-2,Real message,2026-03-14T10:00:00\n"
    )
    clean, warnings = normalize_tickets(parse_csv(raw))
    assert list(clean["ticket_id"]) == ["T-2"]
    assert any("missing ticket_id" in w for w in warnings)


def test_duplicate_ids_differing_only_by_whitespace_are_treated_as_duplicates():
    raw = (
        b"ticket_id,customer_message,created_at\n"
        b"T-1,first,2026-03-14T09:30:00\n"
        b" T-1 ,second,2026-03-14T10:00:00\n"
    )
    clean, warnings = normalize_tickets(parse_csv(raw))
    assert list(clean["customer_message"]) == ["first"]
    assert any("duplicate ticket_id" in w for w in warnings)


# --- Determinism across separate interpreter runs ----------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUN_SNIPPET = (
    "import json, sys\n"
    "from pathlib import Path\n"
    "from src.ticket_logic import analyze_tickets, parse_csv\n"
    "df, _ = analyze_tickets(parse_csv(Path(sys.argv[1]).read_bytes()))\n"
    "out = df[['ticket_id', 'category', 'priority', 'sentiment', 'suggested_response']]\n"
    "print(json.dumps(out.to_dict(orient='records'), sort_keys=True))\n"
)


def _run_analysis_in_fresh_interpreter(hash_seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    proc = subprocess.run(
        [sys.executable, "-c", _RUN_SNIPPET, str(SAMPLE_PATH)],
        cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_analysis_output_is_identical_across_fresh_interpreters_with_different_hash_seeds():
    outputs = {_run_analysis_in_fresh_interpreter(seed) for seed in ("0", "1", "12345")}
    assert len(outputs) == 1
    assert outputs.pop().strip()  # non-empty output actually produced
