"""L2 service tests: status workflow, priority, resolution note, updated_at.

Covers AC-21..AC-31, AC-33, AC-36, AC-61..AC-64 and FR-09, FR-10, FR-11, FR-13, FR-15.
"""

from __future__ import annotations

import itertools

import pytest

from tests.helpers import SPECIAL_TEXTS, raw_rows
from ticketing import config
from ticketing.models import (
    NotFoundError,
    TicketError,
    TicketStateError,
    ValidationError,
)

# Independent copy of the approved table (requirements-analysis section 5.2 / ASM-06).
EXPECTED_ALLOWED = {
    ("Open", "In Progress"),
    ("In Progress", "Open"),
    ("In Progress", "Resolved"),
    ("Resolved", "In Progress"),
    ("Resolved", "Closed"),
}
ALL_PAIRS = list(itertools.product(config.STATUSES, config.STATUSES))
ALLOWED_PAIRS = [p for p in ALL_PAIRS if p in EXPECTED_ALLOWED]
REJECTED_PAIRS = [p for p in ALL_PAIRS if p not in EXPECTED_ALLOWED]


def pair_id(pair):
    return f"{pair[0]}->{pair[1]}".replace(" ", "")


def test_ac21_fr10_config_transition_table_matches_approved_table():
    """AC-21..27 / FR-10 (ASM-06): config.TRANSITIONS equals the approved 5.2 table."""
    actual = {(f, t) for f, targets in config.TRANSITIONS.items() for t in targets}
    assert actual == EXPECTED_ALLOWED
    assert config.READ_ONLY_STATUSES == ("Closed",)
    assert config.RESOLVED_REQUIRES_NOTE is True
    assert len(ALLOWED_PAIRS) == 5 and len(REJECTED_PAIRS) == 11


# ------------------------------------------------------------- allowed transitions ----------


@pytest.mark.parametrize("pair", ALLOWED_PAIRS, ids=pair_id)
def test_ac21_ac22_ac23_ac24_ac61_fr10_every_allowed_transition_succeeds(
    service, fake_clock, ticket_in_status, pair
):
    """AC-21/22/23/24/61 / FR-09, FR-10, FR-13: each allowed pair works and refreshes updated_at."""
    src, dst = pair
    ticket = ticket_in_status(src)
    fake_clock.advance(120)
    updated = service.change_status(
        ticket.id, dst, "Resolved by QA." if dst == "Resolved" else None
    )
    assert updated.status == dst
    assert updated.updated_at == fake_clock.stamp
    assert updated.updated_at > ticket.updated_at
    assert updated.created_at == ticket.created_at
    assert service.get_ticket(ticket.id).status == dst


def test_ac21_fr10_fr13_open_to_in_progress_refreshes_updated_at(service, make_ticket, fake_clock):
    """AC-21 / FR-09, FR-10, FR-13: explicit scenario with concrete timestamps."""
    t = make_ticket()
    fake_clock.advance(300)
    u = service.change_status(t.id, "In Progress")
    assert (u.status, u.updated_at) == ("In Progress", "2026-10-24 09:05:00")
    assert u.created_at == "2026-10-24 09:00:00"


def test_ac22_fr15_resolved_with_note_supplied_in_same_action(service, ticket_in_status):
    """AC-22 / FR-09, FR-10, FR-15: note supplied in the same call is stored."""
    t = ticket_in_status("In Progress")
    r = service.change_status(t.id, "Resolved", "  Replaced the toner.  ")
    assert r.status == "Resolved"
    assert r.resolution_note == "Replaced the toner."


def test_ac22_fr15_resolved_with_existing_stored_note(service, ticket_in_status):
    """AC-22 / FR-15 (IC 5.2 step 6): a stored note satisfies the rule."""
    t = ticket_in_status("In Progress")
    service.set_resolution_note(t.id, "Stored earlier.")
    r = service.change_status(t.id, "Resolved")
    assert r.status == "Resolved"
    assert r.resolution_note == "Stored earlier."


def test_ac22_fr15_note_in_change_status_replaces_stored_note(service, ticket_in_status):
    """AC-22 / FR-15 (build-time clarification): supplied note replaces the stored one."""
    t = ticket_in_status("In Progress")
    service.set_resolution_note(t.id, "Old note.")
    r = service.change_status(t.id, "Resolved", "New note.")
    assert r.resolution_note == "New note."


@pytest.mark.parametrize("blank", [None, "", "   ", "\n\t"], ids=repr)
def test_ac22_fr15_blank_note_in_change_status_keeps_stored_note(service, ticket_in_status, blank):
    """AC-22 / FR-15 (build-time clarification): blank note = not supplied, stored note kept."""
    t = ticket_in_status("In Progress")
    service.set_resolution_note(t.id, "Keep me.")
    r = service.change_status(t.id, "Resolved", blank)
    assert r.resolution_note == "Keep me."


def test_ac22_fr15_note_may_accompany_any_allowed_transition(service, make_ticket):
    """FR-15 (IC 5 note): note is saved on non-Resolved transitions as well."""
    t = make_ticket()
    r = service.change_status(t.id, "In Progress", "Started investigating.")
    assert (r.status, r.resolution_note) == ("In Progress", "Started investigating.")


def test_ac23_fr10_reopen_resolved_to_in_progress_retains_note(service, ticket_in_status):
    """AC-23 / FR-10, ASM-21: reopen keeps the resolution note."""
    t = ticket_in_status("Resolved")
    r = service.change_status(t.id, "In Progress")
    assert r.status == "In Progress"
    assert r.resolution_note == "Fixed by QA fixture."


def test_ac24_fr10_in_progress_back_to_open(service, ticket_in_status):
    """AC-24 / FR-10: In Progress -> Open."""
    t = ticket_in_status("In Progress")
    assert service.change_status(t.id, "Open").status == "Open"


def test_ac23_ac22_fr10_full_reopen_path_open_to_closed_and_back_down(
    service, make_ticket, fake_clock
):
    """AC-21..24, 61 / FR-10: Open > IP > Resolved > IP > Resolved > Closed."""
    t = make_ticket()
    path = ["In Progress", "Resolved", "In Progress", "Resolved", "Closed"]
    for step in path:
        fake_clock.advance(1)
        t = service.change_status(t.id, step, "Some note." if step == "Resolved" else None)
        assert t.status == step
    assert t.resolution_note == "Some note."


# ----------------------------------------------------------- rejected transitions -----------


@pytest.mark.parametrize("pair", REJECTED_PAIRS, ids=pair_id)
@pytest.mark.parametrize("with_note", [False, True], ids=["nonote", "note"])
def test_ac25_ac26_ac27_ac62_ac63_fr10_every_disallowed_pair_is_rejected_unchanged(
    service, fake_clock, ticket_in_status, snapshot, pair, with_note
):
    """AC-25/26/27/62/63 / FR-10, FR-13: each of the 11 disallowed pairs (same-status, skip,
    backwards, from Closed) raises TicketStateError and leaves the row (incl. updated_at) as is."""
    src, dst = pair
    ticket = ticket_in_status(src)
    before_rows = snapshot()
    fake_clock.advance(500)
    with pytest.raises(TicketStateError):
        service.change_status(ticket.id, dst, "A note." if with_note else None)
    assert service.get_ticket(ticket.id) == ticket
    assert snapshot() == before_rows


def test_ac25_fr10_open_to_resolved_message_names_allowed_target(service, make_ticket):
    """AC-25 / FR-10: message states from/to and allowed list (IC section 4)."""
    t = make_ticket()
    with pytest.raises(TicketStateError) as exc:
        service.change_status(t.id, "Resolved", "note")
    assert str(exc.value) == "Cannot change status from Open to Resolved. Allowed: In Progress."


def test_ac25_fr10_open_to_resolved_without_note_is_state_error_not_note_error(
    service, make_ticket
):
    """AC-25 / FR-10 (IC 5.2): transition check precedes the note rule."""
    t = make_ticket()
    with pytest.raises(TicketStateError):
        service.change_status(t.id, "Resolved")


def test_ac26_fr10_resolved_to_open_message(service, ticket_in_status):
    """AC-26 / FR-10: Resolved -> Open rejected, message lists allowed targets."""
    t = ticket_in_status("Resolved")
    with pytest.raises(TicketStateError) as exc:
        service.change_status(t.id, "Open")
    assert str(exc.value) == (
        "Cannot change status from Resolved to Open. Allowed: In Progress, Closed."
    )


@pytest.mark.parametrize("status", ["Open", "In Progress", "Resolved"])
def test_ac27_fr10_same_status_message(service, ticket_in_status, status):
    """AC-27 / FR-10 (build-time clarification): 'Ticket N is already X.'"""
    t = ticket_in_status(status)
    with pytest.raises(TicketStateError) as exc:
        service.change_status(t.id, status, "note")
    assert str(exc.value) == f"Ticket {t.id} is already {status}."


@pytest.mark.parametrize("status", ["Open", "In Progress"])
def test_ac63_fr10_open_or_in_progress_straight_to_closed_rejected(
    service, ticket_in_status, status
):
    """AC-63 / FR-10: Closed is reachable only from Resolved."""
    t = ticket_in_status(status)
    with pytest.raises(TicketStateError) as exc:
        service.change_status(t.id, "Closed")
    assert "Cannot change status" in str(exc.value)
    assert service.get_ticket(t.id).status == status


# --------------------------------------------------------------- invalid status values ------


@pytest.mark.parametrize(
    "bad",
    ["Pending", "", "   ", "open", "OPEN", "in progress", "Done", " Open", None, 1, ["Open"]],
    ids=repr,
)
@pytest.mark.parametrize("src", ["Open", "Resolved", "Closed"])
def test_ac28_fr09_invalid_status_value_is_validation_error_and_ticket_unchanged(
    service, ticket_in_status, snapshot, bad, src
):
    """AC-28 / FR-09: values outside the list are rejected (even for Closed tickets: value
    validation precedes state checks, IC 5.2)."""
    t = ticket_in_status(src)
    before = snapshot()
    with pytest.raises(ValidationError) as exc:
        service.change_status(t.id, bad)
    assert exc.value.errors == {
        "status": "Status must be one of: Open, In Progress, Resolved, Closed."
    }
    assert snapshot() == before


def test_ac28_fr09_multiple_invalid_inputs_are_collected(service, make_ticket):
    """AC-28 / FR-09 (build-time clarification): ID, status and note errors in one exception."""
    make_ticket()
    with pytest.raises(ValidationError) as exc:
        service.change_status("x", "Pending", "n" * 1001)
    assert set(exc.value.errors) == {"ticket_id", "status", "resolution_note"}


# ------------------------------------------------------------------------ unknown ID --------


@pytest.mark.parametrize("missing", [999, 0, -5, 2**63 - 1])
def test_ac29_fr09_unknown_id_raises_not_found_for_every_update(
    service, make_ticket, snapshot, missing
):
    """AC-29 / FR-09 (service level only): NotFoundError, nothing changes."""
    make_ticket()
    before = snapshot()
    with pytest.raises(NotFoundError) as e1:
        service.change_status(missing, "In Progress")
    with pytest.raises(NotFoundError):
        service.change_priority(missing, "Low")
    with pytest.raises(NotFoundError):
        service.set_resolution_note(missing, "note")
    assert str(e1.value) == f"Ticket {missing} was not found."
    assert snapshot() == before


@pytest.mark.parametrize("huge", [2**63, 2**70])
def test_ac29_fr09_id_beyond_sqlite_integer_range_gives_clean_error(service, make_ticket, huge):
    """AC-29 / FR-09: an unknown (huge) ID gives an error message, not an unhandled exception."""
    make_ticket()
    with pytest.raises(TicketError):
        service.change_status(huge, "In Progress")
    with pytest.raises(TicketError):
        service.change_priority(huge, "Low")
    with pytest.raises(TicketError):
        service.set_resolution_note(huge, "note")


# ---------------------------------------------------------------- Resolved needs a note ----


@pytest.mark.parametrize("blank", [None, "", "  ", "\n\t "], ids=repr)
def test_ac64_fr10_fr15_resolved_without_note_is_rejected_naming_the_note(
    service, fake_clock, ticket_in_status, snapshot, blank
):
    """AC-64 / FR-10, FR-15: In Progress -> Resolved with no stored/supplied note is rejected
    with a message naming the resolution note; status and updated_at unchanged."""
    t = ticket_in_status("In Progress")
    before = snapshot()
    fake_clock.advance(60)
    with pytest.raises(ValidationError) as exc:
        service.change_status(t.id, "Resolved", blank)
    assert set(exc.value.errors) == {"resolution_note"}
    assert exc.value.errors["resolution_note"] == (
        "Resolution note is required to set a ticket to Resolved."
    )
    assert "Resolution note" in str(exc.value)
    after = service.get_ticket(t.id)
    assert after.status == "In Progress" and after.updated_at == t.updated_at
    assert snapshot() == before


# --------------------------------------------------------------------------- priority ------


def test_ac30_fr11_priority_change_visible_in_details_list_and_dashboard(
    service, make_ticket, fake_clock
):
    """AC-30 / FR-11, FR-19: High -> Low shows in details, list and dashboard counts."""
    t = make_ticket(priority="High")
    assert service.get_dashboard_stats().by_priority["High"] == 1
    fake_clock.advance(30)
    u = service.change_priority(t.id, "Low")
    assert u.priority == "Low" and u.updated_at == fake_clock.stamp
    assert service.get_ticket(t.id).priority == "Low"
    assert service.list_tickets()[0].priority == "Low"
    assert service.list_tickets(priority="High") == []
    stats = service.get_dashboard_stats()
    assert (stats.by_priority["High"], stats.by_priority["Low"]) == (0, 1)


@pytest.mark.parametrize("target", [p for p in config.PRIORITIES if p != "Medium"])
def test_ac30_fr11_every_listed_priority_is_reachable(service, make_ticket, target):
    """AC-30 / FR-11: change to each listed priority (from Medium)."""
    t = make_ticket(priority="Medium")
    assert service.change_priority(t.id, target).priority == target


def test_ac31_fr11_same_priority_rejected_unchanged(service, make_ticket, fake_clock, snapshot):
    """AC-31 / FR-11 (ASM-24): same value rejected; ticket and updated_at unchanged."""
    t = make_ticket(priority="High")
    before = snapshot()
    fake_clock.advance(60)
    with pytest.raises(TicketStateError) as exc:
        service.change_priority(t.id, "High")
    assert str(exc.value) == "Priority is already High."
    assert service.get_ticket(t.id) == t
    assert snapshot() == before


@pytest.mark.parametrize(
    "bad", ["Urgent", "", "  ", "low", "LOW", " Low", None, 2, ["Low"], True], ids=repr
)
def test_ac31_fr11_invalid_priority_rejected_unchanged(
    service, make_ticket, fake_clock, snapshot, bad
):
    """AC-31 / FR-11: values outside the list are rejected, ticket unchanged."""
    t = make_ticket(priority="High")
    before = snapshot()
    fake_clock.advance(60)
    with pytest.raises(ValidationError) as exc:
        service.change_priority(t.id, bad)
    assert exc.value.errors == {"priority": "Priority must be one of: Low, Medium, High, Critical."}
    assert snapshot() == before


@pytest.mark.parametrize("status", ["Open", "In Progress", "Resolved"])
def test_ac30_fr11_priority_can_change_on_every_non_closed_status(
    service, ticket_in_status, status
):
    """AC-30 / FR-11, ASM-20: priority is editable on Open/In Progress/Resolved."""
    t = ticket_in_status(status, priority="Low")
    assert service.change_priority(t.id, "Critical").priority == "Critical"


# --------------------------------------------------------------------- Closed read-only ----


def test_ac61_fr10_resolved_to_closed_refreshes_updated_at(service, ticket_in_status, fake_clock):
    """AC-61 / FR-09, FR-10: Resolved -> Closed sets Closed and refreshes updated_at."""
    t = ticket_in_status("Resolved")
    fake_clock.advance(3600)
    u = service.change_status(t.id, "Closed")
    assert u.status == "Closed"
    assert u.updated_at == "2026-10-24 10:00:00"


@pytest.mark.parametrize("target", config.STATUSES)
def test_ac62_fr10_closed_ticket_rejects_every_status_change(
    service, fake_clock, ticket_in_status, snapshot, target
):
    """AC-62 / FR-10: a Closed ticket cannot change status (including to itself)."""
    t = ticket_in_status("Closed")
    before = snapshot()
    fake_clock.advance(60)
    with pytest.raises(TicketStateError) as exc:
        service.change_status(t.id, target, "note")
    assert str(exc.value) == f"Ticket {t.id} is Closed and cannot be changed."
    assert snapshot() == before


@pytest.mark.parametrize("target", config.PRIORITIES)
def test_ac62_fr11_closed_ticket_rejects_every_priority_change(
    service, fake_clock, ticket_in_status, snapshot, target
):
    """AC-62 / FR-11: a Closed ticket cannot change priority (same or different)."""
    t = ticket_in_status("Closed", priority="High")
    before = snapshot()
    fake_clock.advance(60)
    with pytest.raises(TicketStateError) as exc:
        service.change_priority(t.id, target)
    assert str(exc.value) == f"Ticket {t.id} is Closed and cannot be changed."
    assert snapshot() == before


def test_ac62_fr15_closed_ticket_rejects_note_change(
    service, fake_clock, ticket_in_status, snapshot
):
    """AC-62 / FR-15: a Closed ticket cannot get a new/replaced note."""
    t = ticket_in_status("Closed")
    before = snapshot()
    fake_clock.advance(60)
    with pytest.raises(TicketStateError) as exc:
        service.set_resolution_note(t.id, "Late edit")
    assert str(exc.value) == f"Ticket {t.id} is Closed and cannot be changed."
    assert snapshot() == before
    assert service.get_ticket(t.id).resolution_note == "Fixed by QA fixture."


def test_ac62_fr10_closed_check_precedes_value_checks_only_for_valid_values(
    service, ticket_in_status
):
    """AC-62 / IC 5.2: invalid value on Closed -> ValidationError; valid value -> state error."""
    t = ticket_in_status("Closed")
    with pytest.raises(ValidationError):
        service.change_priority(t.id, "Urgent")
    with pytest.raises(TicketStateError):
        service.change_priority(t.id, "Low")


# --------------------------------------------------------------------- resolution note -----


@pytest.mark.parametrize("length", [1, 2, 999, 1000])
def test_ac36_fr15_note_within_limit_is_saved(service, make_ticket, fake_clock, length):
    """AC-36 / FR-15: 1..1000 characters are saved and updated_at refreshed."""
    t = make_ticket()
    fake_clock.advance(45)
    u = service.set_resolution_note(t.id, "n" * length)
    assert u.resolution_note == "n" * length
    assert u.updated_at == "2026-10-24 09:00:45"
    assert service.get_ticket(t.id).resolution_note == "n" * length


def test_ac36_fr15_note_1001_chars_rejected_unchanged(service, make_ticket, fake_clock, snapshot):
    """AC-36 / FR-15: 1001 characters rejected, ticket unchanged."""
    t = make_ticket()
    before = snapshot()
    fake_clock.advance(45)
    with pytest.raises(ValidationError) as exc:
        service.set_resolution_note(t.id, "n" * 1001)
    assert exc.value.errors["resolution_note"] == (
        "Resolution note must be at most 1000 characters (you entered 1001)."
    )
    assert snapshot() == before


@pytest.mark.parametrize("blank", ["", " ", "\t\n  ", None, 5, ["x"]], ids=repr)
def test_ac36_fr15_blank_or_invalid_note_rejected_unchanged(
    service, make_ticket, fake_clock, snapshot, blank
):
    """AC-36 / FR-15: empty / whitespace-only / non-str note is rejected, ticket unchanged."""
    t = make_ticket()
    before = snapshot()
    fake_clock.advance(45)
    with pytest.raises(ValidationError) as exc:
        service.set_resolution_note(t.id, blank)
    assert exc.value.errors == {"resolution_note": "Resolution note is required."}
    assert snapshot() == before


def test_ac36_fr15_note_over_limit_in_change_status_is_rejected(service, make_ticket, snapshot):
    """AC-36 / FR-15: the 1000-character limit also applies to a note given to change_status."""
    t = make_ticket()
    before = snapshot()
    with pytest.raises(ValidationError) as exc:
        service.change_status(t.id, "In Progress", "n" * 1001)
    assert "resolution_note" in exc.value.errors
    assert snapshot() == before
    service.change_status(t.id, "In Progress", "n" * 1000)


@pytest.mark.parametrize("text", SPECIAL_TEXTS, ids=range(len(SPECIAL_TEXTS)))
def test_ac36_fr15_note_special_characters_roundtrip_literally(service, db_path, make_ticket, text):
    """AC-36 / FR-15, NFR-08: special text and line breaks saved and shown exactly as typed."""
    t = make_ticket()
    u = service.set_resolution_note(t.id, text)
    assert u.resolution_note == text.strip()
    assert service.get_ticket(t.id).resolution_note == text.strip()
    assert len(raw_rows(db_path)) == 1


def test_ac36_fr15_note_is_trimmed_and_keeps_line_breaks(service, make_ticket):
    """AC-36 / FR-15: surrounding whitespace removed; inner newlines kept."""
    t = make_ticket()
    u = service.set_resolution_note(t.id, "\n  step 1\nstep 2  \n")
    assert u.resolution_note == "step 1\nstep 2"


def test_ac36_fr15_note_replaces_previous_note(service, make_ticket):
    """AC-36 / FR-15: adding a note again replaces (not appends)."""
    t = make_ticket()
    service.set_resolution_note(t.id, "first")
    assert service.set_resolution_note(t.id, "second").resolution_note == "second"


@pytest.mark.parametrize("status", ["Open", "In Progress", "Resolved"])
def test_ac36_fr15_note_allowed_on_every_non_closed_status(service, ticket_in_status, status):
    """AC-36 / FR-15, ASM-21: notes can be added on Open/In Progress/Resolved."""
    t = ticket_in_status(status)
    assert service.set_resolution_note(t.id, "ok").resolution_note == "ok"


def test_ac36_fr15_unicode_note_at_limit(service, make_ticket):
    """AC-36 / FR-15: 1000 emoji characters accepted (characters, not bytes)."""
    t = make_ticket()
    assert len(service.set_resolution_note(t.id, "\U0001f600" * 1000).resolution_note) == 1000
    with pytest.raises(ValidationError):
        service.set_resolution_note(t.id, "\U0001f600" * 1001)


def test_ac36_fr15_lone_surrogate_note_rejected(service, make_ticket):
    """AC-36 / FR-15: unencodable note rejected cleanly."""
    t = make_ticket()
    with pytest.raises(ValidationError) as exc:
        service.set_resolution_note(t.id, "bad \ud800")
    assert "cannot be stored" in exc.value.errors["resolution_note"]
    with pytest.raises(ValidationError):
        service.change_status(t.id, "In Progress", "bad \ud800")


# ---------------------------------------------------------------------- updated_at ---------


def test_ac33_fr13_updated_at_changes_on_each_successful_update_type(
    service, make_ticket, fake_clock
):
    """AC-33 / FR-13: status, priority and note updates each set updated_at to the clock."""
    t = make_ticket()
    seen = [t.updated_at]
    for action in (
        lambda: service.change_status(t.id, "In Progress"),
        lambda: service.change_priority(t.id, "Critical"),
        lambda: service.set_resolution_note(t.id, "n"),
    ):
        fake_clock.advance(61)
        updated = action()
        assert updated.updated_at == fake_clock.stamp
        assert updated.updated_at > seen[-1]
        seen.append(updated.updated_at)
        assert updated.created_at == t.created_at


def test_ac33_fr13_updated_at_unchanged_after_each_kind_of_rejected_update(
    service, make_ticket, fake_clock, snapshot
):
    """AC-33 / FR-13: rejected updates never touch updated_at."""
    t = make_ticket()
    before = snapshot()
    fake_clock.advance(61)
    rejects = [
        lambda: service.change_status(t.id, "Resolved", "n"),
        lambda: service.change_status(t.id, "Open"),
        lambda: service.change_status(t.id, "Bogus"),
        lambda: service.change_priority(t.id, t.priority),
        lambda: service.change_priority(t.id, "Bogus"),
        lambda: service.set_resolution_note(t.id, " "),
        lambda: service.change_status(t.id + 1, "In Progress"),
    ]
    for call in rejects:
        with pytest.raises(TicketError):
            call()
    assert service.get_ticket(t.id).updated_at == t.updated_at
    assert snapshot() == before


def test_ac33_fr13_update_does_not_alter_other_tickets(service, make_ticket, fake_clock):
    """AC-33 / FR-13: only the addressed ticket's row changes."""
    a, b = make_ticket(), make_ticket(title="Other")
    fake_clock.advance(60)
    service.change_status(a.id, "In Progress")
    assert service.get_ticket(b.id) == b


# ------------------------------------------------------------ allowed_next_statuses ---------


@pytest.mark.parametrize("status", config.STATUSES)
def test_ac21_fr10_allowed_next_statuses_equals_transition_table(service, status):
    """FR-09, FR-10 (IC S9): lookup equals config.TRANSITIONS."""
    expected = tuple(t for f, t in EXPECTED_ALLOWED if f == status)
    assert set(service.allowed_next_statuses(status)) == set(expected)
    assert service.allowed_next_statuses(status) == config.TRANSITIONS[status]


@pytest.mark.parametrize("unknown", ["Pending", "", None, 3, "open"], ids=repr)
def test_ac28_fr10_allowed_next_statuses_unknown_is_empty(service, unknown):
    """FR-10 (IC S9): unknown/non-str status -> empty tuple, no exception."""
    assert service.allowed_next_statuses(unknown) == ()


def test_ac62_fr10_closed_has_no_next_statuses(service):
    """AC-62 / FR-10: Closed offers no further transitions."""
    assert service.allowed_next_statuses("Closed") == ()
