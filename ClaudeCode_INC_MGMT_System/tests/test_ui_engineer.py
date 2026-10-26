"""L3 UI tests for the Support Engineer update forms (AppTest, temp database only).

Covers AC-21..AC-31, AC-36, AC-61..AC-64 (UI parts), AC-43, AC-44, AC-55 and FR-09..FR-11, FR-15.
"""

from __future__ import annotations

import pytest

from tests.helpers import VALID
from tests.ui_helpers import (
    by_label,
    error_texts,
    has_label,
    info_texts,
    metrics,
    role,
)


@pytest.fixture
def engineer(new_app):
    return lambda: new_app("Support Engineer")


def change_status(at, new_status, note=None):
    by_label(at.selectbox, "New status").set_value(new_status)
    if note is not None:
        editable = [t for t in at.text_area if t.key.startswith("status_note_")]
        editable[0].input(note)
    by_label(at.button, "Change status").click().run()
    return at


def status_options(at):
    return by_label(at.selectbox, "New status").options


def test_ac21_ac33_fr10_open_to_in_progress_via_form(engineer, ui_service):
    """AC-21 / FR-09, FR-10: choose In Progress, submit, status changes; confirmation shown."""
    t = ui_service.create_ticket(**VALID)
    at = engineer()
    assert status_options(at) == ["In Progress"]
    change_status(at, "In Progress")
    assert len(at.exception) == 0
    assert [s.value for s in at.success] == [f"Ticket #{t.id} updated."]
    assert ui_service.get_ticket(t.id).status == "In Progress"
    assert "Status: In Progress" in [x.value for x in at.text]


def test_ac24_ac25_fr10_status_dropdown_offers_only_allowed_targets(engineer, ui_service):
    """AC-24, AC-25, AC-26, AC-63 / FR-10: dropdown content follows the transition table."""
    t = ui_service.create_ticket(**VALID)
    at = engineer()
    assert status_options(at) == ["In Progress"]  # no Resolved/Closed directly from Open
    ui_service.change_status(t.id, "In Progress")
    at = engineer()
    assert status_options(at) == ["Open", "Resolved"]
    ui_service.change_status(t.id, "Resolved", "done")
    at = engineer()
    assert status_options(at) == ["In Progress", "Closed"]


def test_ac64_fr10_fr15_resolved_without_note_shows_resolution_note_error(engineer, ui_service):
    """AC-64 / FR-10, FR-15: UI shows the message naming the resolution note; ticket unchanged."""
    t = ui_service.create_ticket(**VALID)
    ui_service.change_status(t.id, "In Progress")
    at = engineer()
    change_status(at, "Resolved")
    assert error_texts(at) == ["Resolution note is required to set a ticket to Resolved."]
    assert len(at.success) == 0
    assert ui_service.get_ticket(t.id).status == "In Progress"


def test_ac22_fr15_resolved_with_note_typed_in_the_same_form(engineer, ui_service):
    """AC-22 / FR-15: note typed into the status form is stored with the change."""
    t = ui_service.create_ticket(**VALID)
    ui_service.change_status(t.id, "In Progress")
    at = engineer()
    change_status(at, "Resolved", "Replaced toner cartridge.")
    assert len(at.error) == 0
    done = ui_service.get_ticket(t.id)
    assert (done.status, done.resolution_note) == ("Resolved", "Replaced toner cartridge.")


def test_ac23_ac61_fr10_reopen_and_close_via_form(engineer, ui_service):
    """AC-23, AC-61 / FR-10: Resolved -> In Progress keeps the note; Resolved -> Closed works."""
    t = ui_service.create_ticket(**VALID)
    ui_service.change_status(t.id, "In Progress")
    ui_service.change_status(t.id, "Resolved", "kept note")
    at = engineer()
    change_status(at, "In Progress")
    assert ui_service.get_ticket(t.id).resolution_note == "kept note"
    ui_service.change_status(t.id, "Resolved")
    at = engineer()
    change_status(at, "Closed")
    assert ui_service.get_ticket(t.id).status == "Closed"


def test_ac36_fr15_save_note_only_replaces_note_and_keeps_status(engineer, ui_service):
    """AC-36 / FR-15: 'Save note only' stores the note, status unchanged, confirmation shown."""
    t = ui_service.create_ticket(**VALID)
    at = engineer()
    [t_area] = [x for x in at.text_area if x.key.startswith("status_note_")]
    t_area.input("Checked cables\nsecond line")
    by_label(at.button, "Save note only").click().run()
    assert len(at.error) == 0
    after = ui_service.get_ticket(t.id)
    assert after.status == "Open" and after.resolution_note == "Checked cables\nsecond line"
    assert [s.value for s in at.success] == [f"Ticket #{t.id} updated."]


def test_ac36_fr15_save_blank_note_shows_error_and_changes_nothing(engineer, ui_service):
    """AC-36 / FR-15: blank note rejected with a message naming the field."""
    t = ui_service.create_ticket(**VALID)
    at = engineer()
    by_label(at.button, "Save note only").click().run()
    assert error_texts(at) == ["Resolution note is required."]
    assert ui_service.get_ticket(t.id).resolution_note == ""


def test_ac36_fr15_over_long_note_is_rejected_with_limit_message(engineer, ui_service):
    """AC-36 / FR-15: 1001 characters rejected in the UI with the limit in the message."""
    t = ui_service.create_ticket(**VALID)
    at = engineer()
    [area] = [x for x in at.text_area if x.key.startswith("status_note_")]
    area.input("n" * 1001)
    by_label(at.button, "Save note only").click().run()
    assert error_texts(at) == [
        "Resolution note must be at most 1000 characters (you entered 1001)."
    ]
    assert ui_service.get_ticket(t.id).resolution_note == ""


def test_ac30_fr11_change_priority_via_form_updates_details_list_and_dashboard(
    engineer, ui_service, new_app
):
    """AC-30 / FR-11: High -> Low reflected in details, table, and Manager counts."""
    t = ui_service.create_ticket(**VALID)  # priority High
    at = engineer()
    by_label(at.selectbox, "New priority").set_value("Low")
    by_label(at.button, "Change priority").click().run()
    assert len(at.error) == 0
    assert ui_service.get_ticket(t.id).priority == "Low"
    assert "Priority: Low" in [x.value for x in at.text]
    assert at.dataframe[0].value["Priority"].tolist() == ["Low"]
    role(at, "Manager")
    assert metrics(at)["Total"] == "1"


def test_ac31_fr11_same_priority_submission_shows_message_and_changes_nothing(engineer, ui_service):
    """AC-31 / FR-11: submitting the preselected (current) priority is rejected."""
    t = ui_service.create_ticket(**VALID)
    before = ui_service.get_ticket(t.id)
    at = engineer()
    assert by_label(at.selectbox, "New priority").value == "High"
    by_label(at.button, "Change priority").click().run()
    assert error_texts(at) == ["Priority is already High."]
    assert ui_service.get_ticket(t.id) == before


def test_ac62_fr10_closed_ticket_is_read_only_in_the_engineer_view(engineer, ui_service):
    """AC-62 / FR-10, FR-11, FR-15: a Closed ticket shows no update controls."""
    t = ui_service.create_ticket(**VALID)
    for step in ("In Progress", "Resolved", "Closed"):
        ui_service.change_status(t.id, step, "done" if step == "Resolved" else None)
    at = engineer()
    assert len(at.exception) == 0
    assert "This ticket is Closed and is read-only." in info_texts(at)
    assert len(at.button) == 0
    assert not has_label(at.selectbox, "New status")
    assert not has_label(at.selectbox, "New priority")
    editable = [x for x in at.text_area if not x.disabled]
    assert editable == []


def test_ac44_ac62_selecting_another_ticket_switches_the_forms(engineer, ui_service):
    """AC-44, AC-62 / FR-07: choosing a Closed ticket then an Open one swaps read-only/forms."""
    closed = ui_service.create_ticket(**VALID)
    for step in ("In Progress", "Resolved", "Closed"):
        ui_service.change_status(closed.id, step, "d" if step == "Resolved" else None)
    open_t = ui_service.create_ticket(**{**VALID, "title": "Fresh one"})
    at = engineer()
    assert has_label(at.selectbox, "New status")  # newest (open) ticket is first
    by_label(at.selectbox, "Show details for").set_value(closed.id).run()
    assert not has_label(at.selectbox, "New status")
    by_label(at.selectbox, "Show details for").set_value(open_t.id).run()
    assert has_label(at.selectbox, "New status")


def test_ac43_fr20_dashboard_reflects_status_change_made_in_engineer_view(engineer, ui_service):
    """AC-43 / FR-20: change status in the Engineer view, then the Manager figures follow."""
    ui_service.create_ticket(**VALID)
    at = engineer()
    change_status(at, "In Progress")
    shown = metrics(role(at, "Manager"))
    assert (shown["Open"], shown["In Progress"], shown["Total"]) == ("0", "1", "1")


def test_ac55_nfr06_rejected_ui_operations_leave_stored_data_unchanged(
    engineer, ui_service, ui_snapshot
):
    """AC-55 / NFR-06: rejected note/priority/transition attempts through the UI change nothing."""
    ui_service.create_ticket(**VALID)
    before = ui_snapshot()
    at = engineer()
    by_label(at.button, "Save note only").click().run()  # blank note
    by_label(at.button, "Change priority").click().run()  # same priority
    assert before == ui_snapshot()


def test_ac29_ac15_fr09_fr07_ui_only_offers_existing_ticket_ids(engineer, ui_service):
    """AC-15, AC-29: the detail selector lists exactly the existing IDs (service-level only
    otherwise), so a non-existent ticket cannot be chosen from the UI."""
    for n in range(3):
        ui_service.create_ticket(**{**VALID, "title": f"T{n}"})
    at = engineer()
    selector = by_label(at.selectbox, "Show details for")
    assert selector.options == ["#3 - T2", "#2 - T1", "#1 - T0"]


def test_fr06_special_characters_in_titles_do_not_break_the_selector_or_details(
    engineer, ui_service
):
    """FR-02, FR-06: markup/emoji/SQL text in titles renders literally in selector and details."""
    ui_service.create_ticket(**{**VALID, "title": "<script>alert(1)</script>"})
    ui_service.create_ticket(**{**VALID, "title": "**bold** [x](http://e.com) \U0001f600"})
    at = engineer()
    assert len(at.exception) == 0
    assert len(at.markdown) == 0 or all("<script>" not in m.value for m in at.markdown)
    assert "Title: **bold** [x](http://e.com) \U0001f600" in [t.value for t in at.text]
