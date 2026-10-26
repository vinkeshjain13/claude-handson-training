"""L3 UI smoke tests with streamlit.testing.v1.AppTest on app/main.py (temp database only).

Covers AC-01, AC-03..AC-07 (UI parts), AC-13, AC-37, AC-39..AC-45, AC-47, AC-48, AC-51 (labels),
AC-52, AC-59, AC-65, AC-66, AC-67 and FR-21, FR-26, NFR-03, NFR-12.
Visual / browser items are in docs/manual-test-checklist.md.
"""

from __future__ import annotations

import pytest

from tests.helpers import SPECIAL_TEXTS, VALID
from tests.ui_helpers import (
    ENTER_NAME,
    NO_TICKETS_EMPLOYEE,
    NO_TICKETS_ENGINEER,
    by_label,
    error_texts,
    has_label,
    info_texts,
    listed_ids,
    listed_titles,
    metrics,
    role,
)

ROLES = ["Employee", "Support Engineer", "Manager"]


def fill_form(at, creator="Alice", title="Printer jam", description="Jammed.",
              category="Hardware", priority="High"):  # fmt: skip
    at.text_input(key="create_creator_0").input(creator)
    at.text_input(key="create_title_0").input(title)
    at.text_area(key="create_description_0").input(description)
    at.selectbox(key="create_category_0").set_value(category)
    at.selectbox(key="create_priority_0").set_value(priority)
    return at


def submit(at):
    at.button(key="create_submit_0").click().run()
    return at


# ------------------------------------------------------------- startup, roles, notice ------


def test_ac44_fr21_app_starts_without_exception(new_app):
    """AC-44 / FR-21: the app starts on a fresh temp DB with no uncaught exception."""
    at = new_app()
    assert len(at.exception) == 0
    assert at.title[0].value == "IT Support Ticket System"


@pytest.mark.parametrize("role_name", ROLES)
def test_ac45_fr21_nfr12_demo_notice_is_visible_in_every_role(new_app, role_name):
    """AC-45 / FR-21, NFR-12: a DEMO warning stating 'not authentication or access control' is
    shown on the screen of every role."""
    at = role(new_app(), role_name)
    assert len(at.exception) == 0
    assert at.sidebar.radio(key="demo_role").value == role_name
    warnings = [w.value for w in at.warning]
    assert len(warnings) == 1
    assert "DEMO" in warnings[0]
    assert "not authentication or access control" in warnings[0]
    assert "No security or privacy is provided" in warnings[0]
    assert any("No authentication" in c.value for c in at.sidebar.caption)


def test_ac44_fr21_role_selector_options_and_label(new_app):
    """AC-44 / FR-21: three roles, default Employee, label states it is not a login."""
    at = new_app()
    radio = at.sidebar.radio(key="demo_role")
    assert radio.options == ROLES
    assert radio.value == "Employee"
    assert radio.label == "Demo role (not a login)"


def test_ac44_fr21_employee_screen_has_form_and_my_tickets_but_no_update_controls(new_app):
    """AC-44 / FR-21: Employee: raise ticket plus My tickets; no engineer/manager controls."""
    at = new_app("Employee")
    assert [t.label for t in at.tabs] == ["Raise a ticket", "My tickets"]
    assert at.button(key="create_submit_0").label == "Submit ticket"
    assert at.text_input(key="my_tickets_name").label == "Your name"
    assert len(at.metric) == 0
    labels = [b.label for b in at.button]
    assert labels == ["Submit ticket"]
    for forbidden in ("New status", "New priority"):
        assert not has_label(at.selectbox, forbidden)


def test_ac44_fr21_engineer_screen_has_filters_search_and_update_controls(new_app, ui_service):
    """AC-44 / FR-21: Support Engineer: list with filters and status/priority/note controls."""
    ui_service.create_ticket(**VALID)
    at = new_app("Support Engineer")
    assert len(at.exception) == 0
    for key in ("flt_status", "flt_priority", "flt_category"):
        assert at.selectbox(key=key).value == "All"
    assert at.text_input(key="flt_creator").label == "Your name"
    assert at.text_input(key="engineer_search")
    assert has_label(at.selectbox, "New status") and has_label(at.selectbox, "New priority")
    assert {b.label for b in at.button} == {"Change status", "Save note only", "Change priority"}
    assert len(at.metric) == 0
    assert not has_label(at.text_input, "Title *")


def test_ac44_fr21_manager_screen_is_dashboard_only(new_app, ui_service):
    """AC-44 / FR-21: Manager sees the dashboard only (metrics, charts, refresh)."""
    ui_service.create_ticket(**VALID)
    at = new_app("Manager")
    assert len(at.exception) == 0
    assert len(at.metric) == 5
    assert [b.label for b in at.button] == ["Refresh"]
    assert len(at.text_input) == 0 and len(at.text_area) == 0
    assert len(at.dataframe) == 0


def test_ac44_fr21_switching_roles_back_and_forth_keeps_app_healthy(new_app):
    """AC-44 / FR-21: role switching via key demo_role, repeatedly, never raises."""
    at = new_app()
    for name in ROLES + ROLES[::-1] + ["Employee"]:
        role(at, name)
        assert len(at.exception) == 0
        assert at.sidebar.radio(key="demo_role").value == name
        assert len(at.warning) == 1


# ------------------------------------------------------------ Employee: raise a ticket ----


def test_ac07_ac67_fr03_fr25_form_options_and_defaults(new_app):
    """AC-07, AC-67 / FR-03, FR-25: priority and category lists and defaults in the form."""
    at = new_app("Employee")
    priority = at.selectbox(key="create_priority_0")
    category = at.selectbox(key="create_category_0")
    assert priority.options == ["Low", "Medium", "High", "Critical"]
    assert priority.value == "Medium"
    assert category.options == ["Hardware", "Software", "Network", "Account Access", "Other"]
    assert category.value == "Other"


def test_ac51_nfr03_required_fields_are_labelled_and_marked(new_app):
    """AC-51 / NFR-03: every form field has a label and a required marker (visual check manual)."""
    at = new_app("Employee")
    assert at.text_input(key="create_creator_0").label == "Your name *"
    assert at.text_input(key="create_title_0").label == "Title *"
    assert at.text_area(key="create_description_0").label == "Description *"
    assert at.selectbox(key="create_category_0").label == "Category *"
    assert at.selectbox(key="create_priority_0").label == "Priority *"
    assert any(c.value == "* required" for c in at.caption)


def test_ac01_fr01_submit_valid_ticket_shows_id_and_ticket_is_stored(new_app, ui_service):
    """AC-01 / FR-01: success message shows the new ID; ticket exists with status Open."""
    at = fill_form(new_app("Employee"))
    submit(at)
    assert len(at.exception) == 0
    assert [s.value for s in at.success] == ["Ticket #1 was created with status Open."]
    (ticket,) = ui_service.list_tickets()
    assert (ticket.creator, ticket.title, ticket.category, ticket.priority, ticket.status) == (
        "Alice", "Printer jam", "Hardware", "High", "Open",
    )  # fmt: skip
    assert ticket.description == "Jammed."


def test_ac01_fr01_created_ticket_appears_in_engineer_list(new_app):
    """AC-01 / FR-01, FR-06: after creating in Employee view, the Engineer list shows it."""
    at = submit(fill_form(new_app("Employee")))
    role(at, "Support Engineer")
    assert listed_ids(at) == [1]
    assert listed_titles(at) == ["Printer jam"]


def test_ac01_fr01_form_is_reset_with_fresh_widgets_after_success(new_app):
    """AC-01 / NFR-03: after a successful submit the form is empty again (new nonce)."""
    at = submit(fill_form(new_app("Employee")))
    assert at.text_input(key="create_title_1").value == ""
    assert at.text_area(key="create_description_1").value == ""
    assert at.selectbox(key="create_priority_1").value == "Medium"


def test_ac01_ac09_two_submissions_create_two_tickets_with_increasing_ids(new_app, ui_service):
    """AC-01, AC-09, AC-10 / FR-04: two UI submissions -> two distinct increasing IDs."""
    at = new_app("Employee")
    at.text_input(key="create_creator_0").input("A")
    at.text_input(key="create_title_0").input("Same")
    at.text_area(key="create_description_0").input("Same")
    submit(at)
    at.text_input(key="create_creator_1").input("A")
    at.text_input(key="create_title_1").input("Same")
    at.text_area(key="create_description_1").input("Same")
    at.button(key="create_submit_1").click().run()
    assert [t.id for t in ui_service.list_tickets()] == [2, 1]


@pytest.mark.parametrize(
    ("empty_field", "label"),
    [("creator", "Your name"), ("title", "Title"), ("description", "Description")],
)
def test_ac03_ac52_fr02_empty_field_shows_named_error_and_keeps_other_values(
    new_app, ui_service, empty_field, label
):
    """AC-03, AC-52 / FR-02, NFR-03: error names the field; the other typed values stay."""
    values = {"creator": "Alice", "title": "Printer jam", "description": "Jammed."}
    values[empty_field] = ""
    at = fill_form(new_app("Employee"), category="Network", priority="Critical", **values)
    submit(at)
    assert error_texts(at) == [f"{label} is required."]
    assert len(ui_service.list_tickets()) == 0
    assert len(at.success) == 0
    kept = {
        "creator": at.text_input(key="create_creator_0").value,
        "title": at.text_input(key="create_title_0").value,
        "description": at.text_area(key="create_description_0").value,
    }
    assert kept == values
    assert at.selectbox(key="create_category_0").value == "Network"
    assert at.selectbox(key="create_priority_0").value == "Critical"


def test_ac03_ac52_fr02_all_empty_reports_every_missing_field(new_app, ui_service):
    """AC-03 / FR-02: submitting an empty form lists all three missing fields."""
    at = submit(new_app("Employee"))
    assert error_texts(at) == [
        "Your name is required.",
        "Title is required.",
        "Description is required.",
    ]
    assert ui_service.list_tickets() == []


def test_ac04_fr02_whitespace_only_title_is_rejected_in_the_form(new_app, ui_service):
    """AC-04 / FR-02: whitespace-only counts as empty in the UI as well."""
    at = submit(fill_form(new_app("Employee"), title="     "))
    assert error_texts(at) == ["Title is required."]
    assert ui_service.list_tickets() == []


def test_ac05_fr02_over_limit_title_shows_limit_message_and_widget_has_no_max_chars(
    new_app, ui_service
):
    """AC-05 / FR-02 (VR section 1): no max_chars on widgets, so the service message appears."""
    at = new_app("Employee")
    assert at.text_input(key="create_title_0").max_chars in (
        None,
        0,
    )  # 0 = unset in the AppTest proto
    assert at.text_input(key="create_creator_0").max_chars in (
        None,
        0,
    )  # 0 = unset in the AppTest proto
    assert at.text_area(key="create_description_0").max_chars in (
        None,
        0,
    )  # 0 = unset in the AppTest proto
    submit(fill_form(at, title="t" * 101))
    assert error_texts(at) == ["Title must be at most 100 characters (you entered 101)."]
    assert ui_service.list_tickets() == []


def test_ac05_fr02_exactly_at_limit_is_created_through_the_form(new_app, ui_service):
    """AC-05 / FR-02: 100 / 100 / 2000 characters accepted via the UI."""
    at = fill_form(new_app("Employee"), creator="c" * 100, title="t" * 100,
                   description="d" * 2000)  # fmt: skip
    submit(at)
    assert len(at.exception) == 0 and len(at.error) == 0
    (ticket,) = ui_service.list_tickets()
    assert (len(ticket.creator), len(ticket.title), len(ticket.description)) == (100, 100, 2000)


@pytest.mark.parametrize("text", SPECIAL_TEXTS[:12], ids=range(12))
def test_ac06_fr02_special_characters_are_created_and_shown_literally(new_app, ui_service, text):
    """AC-06 / FR-02: special text submits without error and is displayed exactly as typed."""
    at = submit(fill_form(new_app("Employee"), creator="Zed", title=text, description=text))
    assert len(at.exception) == 0 and len(at.error) == 0
    (ticket,) = ui_service.list_tickets()
    assert ticket.title == text.strip()
    at.text_input(key="my_tickets_name").input("Zed").run()
    assert listed_titles(at) == [text.strip()]
    description = by_label(at.text_area, "Description")
    assert description.value == text.strip() and description.disabled
    assert f"Title: {text.strip()}" in [t.value for t in at.text]


def test_ac06_fr02_multiline_description_roundtrips_in_details(new_app):
    """AC-06 / FR-02: line breaks in the description are kept in the details view."""
    at = fill_form(new_app("Employee"), creator="Zed", description="line one\nline two\n\nend")
    submit(at)
    at.text_input(key="my_tickets_name").input("Zed").run()
    assert by_label(at.text_area, "Description").value == "line one\nline two\n\nend"


def test_ac06_nfr08_sql_injection_text_in_form_leaves_table_and_other_tickets_intact(
    new_app, ui_service
):
    """AC-06 / NFR-08: injection-looking text is data; earlier tickets unchanged."""
    first = ui_service.create_ticket(**VALID)
    evil = "x'); DROP TABLE tickets; --"
    at = submit(fill_form(new_app("Employee"), creator=evil, title=evil, description=evil))
    assert len(at.exception) == 0
    tickets = ui_service.list_tickets()
    assert len(tickets) == 2 and ui_service.get_ticket(first.id) == first
    assert tickets[0].title == evil


# ------------------------------------------------------------------ My tickets (FR-26) -----


@pytest.fixture
def ann_bob(ui_service):
    ann = ui_service.create_ticket("Ann", "VPN down", "Cannot connect", "Network", "High")
    bob = ui_service.create_ticket("Bob", "Printer jam", "Paper stuck", "Hardware", "Low")
    ann2 = ui_service.create_ticket("ann", "Excel crash", "Closes at once", "Software", "Medium")
    ui_service.change_status(ann.id, "In Progress", "Looking into it")
    return ann, bob, ann2


def test_ac66_fr26_my_tickets_asks_for_a_name_first(new_app, ann_bob):
    """AC-66 / FR-26: with no name entered nothing is listed and the user is prompted."""
    at = new_app("Employee")
    assert ENTER_NAME in info_texts(at)
    assert listed_ids(at) == []


def test_ac66_fr26_my_tickets_lists_only_own_tickets_case_and_space_insensitive(new_app, ann_bob):
    """AC-66 / FR-26: ' ann ' lists only Ann's tickets (both spellings), newest first."""
    ann, bob, ann2 = ann_bob
    at = new_app("Employee")
    at.text_input(key="my_tickets_name").input(" ann ").run()
    assert listed_ids(at) == [ann2.id, ann.id]
    assert bob.id not in listed_ids(at)
    frame = at.dataframe[0].value
    assert list(frame.columns) == ["ID", "Title", "Creator", "Category", "Priority", "Status",
                                   "Created"]  # fmt: skip


def test_ac66_fr07_fr26_my_tickets_details_show_status_and_resolution_note(new_app, ann_bob):
    """AC-66 / FR-07, FR-26: status and resolution note are visible for the selected ticket."""
    ann, _, ann2 = ann_bob
    at = new_app("Employee")
    at.text_input(key="my_tickets_name").input("Ann").run()
    by_label(at.selectbox, "Show details for").set_value(ann.id).run()
    texts = [t.value for t in at.text]
    assert "Status: In Progress" in texts and f"ID: {ann.id}" in texts
    assert by_label(at.text_area, "Resolution note").value == "Looking into it"
    by_label(at.selectbox, "Show details for").set_value(ann2.id).run()
    assert "Status: Open" in [t.value for t in at.text]
    assert by_label(at.text_area, "Resolution note (none)").value == ""


def test_ac66_fr26_unknown_name_shows_no_tickets_message(new_app, ann_bob):
    """AC-66 / FR-26: a name with no tickets shows the 'no tickets' message."""
    at = new_app("Employee")
    at.text_input(key="my_tickets_name").input("Nobody").run()
    assert NO_TICKETS_EMPLOYEE in info_texts(at)
    assert listed_ids(at) == []


def test_ac66_fr26_employee_view_has_no_update_controls_even_with_a_name_entered(new_app, ann_bob):
    """AC-66 / FR-26: no status/priority/note controls anywhere in the Employee view."""
    at = new_app("Employee")
    at.text_input(key="my_tickets_name").input("Ann").run()
    assert [b.label for b in at.button] == ["Submit ticket"]
    for forbidden in ("New status", "New priority"):
        assert not has_label(at.selectbox, forbidden)
    disabled = [t for t in at.text_area if t.label.startswith("Resolution note")]
    assert disabled and all(t.disabled for t in disabled)


def test_ac66_fr26_my_tickets_disclaimer_says_convenience_not_privacy(new_app):
    """AC-66 / FR-26 (ASM-23, RISK-12): the UI states 'not a privacy feature'."""
    at = new_app("Employee")
    assert any("not a privacy feature" in c.value for c in at.caption)


# ----------------------------------------------------------- persistence through the UI ----


def test_ac47_ac48_nfr01_second_app_session_shows_tickets_created_by_the_first(new_app):
    """AC-47, AC-48 / NFR-01: a new app session on the same file lists the earlier tickets."""
    first = submit(fill_form(new_app("Employee"), creator="Persist", title="Survives"))
    assert [s.value for s in first.success]
    second = new_app("Support Engineer")
    assert listed_titles(second) == ["Survives"]
    assert metrics(role(second, "Manager"))["Total"] == "1"


# --------------------------------------------------------------------- Manager dashboard ---


def test_ac42_fr20_fr24_manager_dashboard_on_empty_database_shows_zeros(new_app):
    """AC-42 / FR-20, FR-24: empty DB -> total and status counts 0, 'No tickets yet.', no error."""
    at = new_app("Manager")
    assert len(at.exception) == 0 and len(at.error) == 0
    assert metrics(at) == {"Total": "0", "Open": "0", "In Progress": "0", "Resolved": "0",
                           "Closed": "0"}  # fmt: skip
    assert any(c.value == "No tickets yet." for c in at.caption)
    assert len(at.get("vega_lite_chart")) == 3


def test_ac37_ac39_ac40_ac59_fr16_fr18_fr23_manager_metrics_match_data(
    new_app, ui_service, ticket_in_status
):
    """AC-37, AC-39, AC-40, AC-59 / FR-16, FR-18, FR-23: total and the four status counts."""
    svc = ui_service
    svc.create_ticket(**VALID)
    svc.create_ticket(**VALID)
    t = svc.create_ticket(**VALID)
    svc.change_status(t.id, "In Progress")
    r = svc.create_ticket(**VALID)
    svc.change_status(r.id, "In Progress")
    svc.change_status(r.id, "Resolved", "ok")
    c = svc.create_ticket(**VALID)
    for step in ("In Progress", "Resolved", "Closed"):
        svc.change_status(c.id, step, "n" if step == "Resolved" else None)
    at = new_app("Manager")
    shown = metrics(at)
    assert shown == {"Total": "5", "Open": "2", "In Progress": "1", "Resolved": "1",
                     "Closed": "1"}  # fmt: skip
    assert sum(int(v) for k, v in shown.items() if k != "Total") == int(shown["Total"])
    assert not any(c.value == "No tickets yet." for c in at.caption)


def test_ac41_ac65_manager_shows_priority_and_category_sections_with_charts(new_app, ui_service):
    """AC-41, AC-65 / FR-19, FR-24: breakdown headings and three charts are rendered."""
    ui_service.create_ticket(**VALID)
    at = new_app("Manager")
    texts = [t.value for t in at.text]
    assert {"By priority", "By category", "By status"} <= set(texts)
    assert len(at.get("vega_lite_chart")) == 3


def test_ac43_fr20_manager_refresh_shows_data_created_after_first_load(new_app, ui_service):
    """AC-43 / FR-20: figures update on refresh without restarting the app."""
    at = new_app("Manager")
    assert metrics(at)["Total"] == "0"
    ui_service.create_ticket(**VALID)
    at.button(key="dashboard_refresh").click().run()
    assert metrics(at)["Total"] == "1" and metrics(at)["Open"] == "1"


def test_ac43_fr20_dashboard_reflects_a_ticket_raised_in_the_employee_view(new_app):
    """AC-43 / FR-20: create via the Employee form, switch to Manager, counts changed."""
    at = submit(fill_form(new_app("Employee")))
    assert metrics(role(at, "Manager"))["Total"] == "1"


# ------------------------------------------------------------- Engineer list basics --------


def test_ac13_fr06_engineer_view_on_empty_database_shows_no_tickets_message(new_app):
    """AC-13 / FR-06: empty DB -> 'No tickets yet.' and no error/table."""
    at = new_app("Support Engineer")
    assert len(at.exception) == 0
    assert NO_TICKETS_ENGINEER in info_texts(at)
    assert listed_ids(at) == []


def test_ac12_fr06_engineer_table_columns_and_newest_first(new_app, ui_service):
    """AC-12 / FR-06: ID, title, creator, category, priority, status, created; newest first."""
    for n in range(3):
        ui_service.create_ticket("Ann", f"T{n}", "d", "Other", "Low")
    at = new_app("Support Engineer")
    assert listed_ids(at) == [3, 2, 1]
    assert list(at.dataframe[0].value.columns) == [
        "ID", "Title", "Creator", "Category", "Priority", "Status", "Created",
    ]  # fmt: skip


def test_ac14_fr07_engineer_details_show_all_fields(new_app, ui_service):
    """AC-14 / FR-07: details panel shows ID, title, creator, category, priority, status,
    created/updated, description and resolution note."""
    t = ui_service.create_ticket("Ann", "VPN down", "Cannot connect", "Network", "High")
    ui_service.set_resolution_note(t.id, "Rebooted router")
    at = new_app("Support Engineer")
    texts = [x.value for x in at.text]
    for expected in ("ID: 1", "Title: VPN down", "Creator: Ann", "Category: Network",
                     "Priority: High", "Status: Open"):  # fmt: skip
        assert expected in texts
    assert any(x.startswith("Created: ") for x in texts)
    assert any(x.startswith("Updated: ") for x in texts)
    assert by_label(at.text_area, "Description").value == "Cannot connect"
    shown = [x for x in at.text_area if x.key.startswith("note_eng_")]
    assert len(shown) == 1 and shown[0].disabled is True
    assert shown[0].value == "Rebooted router"


def test_ac16_ac17_ac18_ac19_ac20_ac60_fr08_engineer_filters_and_no_match_message(
    new_app, ui_service
):
    """AC-16..20, AC-60 / FR-08: status, priority, category, creator filters; combos; no match."""
    a = ui_service.create_ticket("Ann", "VPN down", "d", "Network", "High")
    b = ui_service.create_ticket("Bob", "Printer jam", "d", "Hardware", "Low")
    c = ui_service.create_ticket("ann", "Wifi slow", "d", "Network", "Low")
    ui_service.change_status(b.id, "In Progress")
    at = new_app("Support Engineer")
    assert listed_ids(at) == [c.id, b.id, a.id]

    at.selectbox(key="flt_status").set_value("Open").run()
    assert listed_ids(at) == [c.id, a.id]
    at.selectbox(key="flt_priority").set_value("High").run()
    assert listed_ids(at) == [a.id]
    at.selectbox(key="flt_priority").set_value("All").run()
    at.selectbox(key="flt_status").set_value("All").run()
    at.selectbox(key="flt_category").set_value("Network").run()
    assert listed_ids(at) == [c.id, a.id]
    at.selectbox(key="flt_status").set_value("In Progress").run()
    assert listed_ids(at) == [] and "No matching tickets." in info_texts(at)
    assert len(at.exception) == 0
    at.selectbox(key="flt_status").set_value("All").run()
    at.selectbox(key="flt_category").set_value("All").run()
    at.text_input(key="flt_creator").input("  ANN ").run()
    assert listed_ids(at) == [c.id, a.id]
    at.text_input(key="flt_creator").input("nobody").run()
    assert listed_ids(at) == [] and "No matching tickets." in info_texts(at)
    at.text_input(key="flt_creator").input("").run()
    assert listed_ids(at) == [c.id, b.id, a.id]


def test_ac58_nfr09_app_makes_no_outbound_network_connection_during_a_full_walkthrough(
    new_app, ui_service, monkeypatch
):
    """AC-58 / NFR-09: with socket connect/DNS instrumented to fail, the app runs every role
    and a create/update flow without attempting any outbound connection."""
    import socket

    attempts: list[object] = []

    def blocked_connect(self, address, *args, **kwargs):
        attempts.append(address)
        raise OSError("outbound connections are blocked in this test")

    def blocked_getaddrinfo(*args, **kwargs):
        attempts.append(("dns", args[:1]))
        raise OSError("DNS is blocked in this test")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked_connect)
    monkeypatch.setattr(socket, "getaddrinfo", blocked_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", blocked_connect)

    ui_service.create_ticket(**VALID)
    at = fill_form(new_app("Employee"), creator="Net", title="No network")
    submit(at)
    for name in ROLES:
        role(at, name)
        assert len(at.exception) == 0
    assert attempts == []
