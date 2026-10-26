"""L3 UI tests for the FR-27 listing search (AC-71..AC-81) in the Engineer and Employee views.

Search is implemented in app/common.py (search_tickets); widget keys: engineer_search, my_search.
"""

from __future__ import annotations

import pytest

from tests.helpers import VALID
from tests.ui_helpers import (
    NO_MATCH,
    NO_TICKETS_EMPLOYEE,
    info_texts,
    listed_ids,
    listed_titles,
)

# ------------------------------------------------------------------------ unit level -----


def make_tickets():
    from ticketing.models import Ticket

    def t(i, title, description="plain", creator="Tester"):
        return Ticket(i, title, description, "Other", "Low", "Open", creator, "x", "x", "")

    return [t(3, "Printer jam"), t(2, "VPN down"), t(1, "Other")]


def test_ac71_ac72_fr27_search_tickets_function_is_case_insensitive_substring_and_keeps_order():
    """AC-71, AC-72 / FR-27: pure function: substring, case-insensitive, input order kept."""
    from app.common import search_tickets

    tickets = make_tickets()
    for query in ("print", "PRINT", "PrInTeR", "  print  "):
        assert [t.id for t in search_tickets(tickets, query)] == [3]
    assert [t.id for t in search_tickets(tickets, "o")] == [2, 1]  # order of input kept


@pytest.mark.parametrize("query", ["", " ", "\t\n  ", None])
def test_ac76_fr27_empty_or_whitespace_query_returns_the_same_list(query):
    """AC-76 / FR-27 (ASM-25a): empty / whitespace-only query applies no search."""
    from app.common import search_tickets

    tickets = make_tickets()
    assert search_tickets(tickets, query) == tickets


def test_ac77_fr27_search_tickets_does_not_modify_its_input_and_treats_text_literally():
    """AC-77 / FR-27, NFR-08: no wildcard/regex meaning for special characters."""
    from app.common import search_tickets

    tickets = make_tickets()
    snapshot = list(tickets)
    for query in ("%", "_", ".*", "[a-z]", "\\", "' OR 1=1 --", "(", "["):
        assert search_tickets(tickets, query) == []
    assert tickets == snapshot


def test_ac74_fr27_search_matches_id_text_substring():
    """AC-74 / FR-27 (ASM-25b): '12' matches 12 (and would match 112/120), '2' matches 2 and 12."""
    from app.common import search_tickets
    from ticketing.models import Ticket

    def t(i):
        return Ticket(i, "title", "d", "Other", "Low", "Open", "C", "x", "x", "")

    tickets = [t(120), t(112), t(12), t(5), t(2)]
    assert [x.id for x in search_tickets(tickets, "12")] == [120, 112, 12]
    assert [x.id for x in search_tickets([t(12), t(5), t(2)], "12")] == [12]
    assert [x.id for x in search_tickets([t(12), t(5), t(2)], "2")] == [12, 2]
    assert [x.id for x in search_tickets([t(12), t(5), t(2)], "#12")] == []


# ------------------------------------------------------------- Engineer view (AppTest) ----


@pytest.fixture
def printer_vpn(ui_service):
    printer = ui_service.create_ticket("Alice", "Printer jam", "Paper stuck", "Hardware", "Low")
    vpn = ui_service.create_ticket("Bob", "VPN down", "Cannot connect", "Network", "High")
    return printer, vpn


def engineer_search(at, text):
    at.text_input(key="engineer_search").input(text).run()
    return at


def test_ac71_fr27_engineer_search_title_substring_lists_only_matching_ticket(new_app, printer_vpn):
    """AC-71 / FR-27: 'print' lists only 'Printer jam'; same columns as FR-06."""
    printer, vpn = printer_vpn
    at = new_app("Support Engineer")
    assert listed_ids(at) == [vpn.id, printer.id]
    engineer_search(at, "print")
    assert listed_ids(at) == [printer.id]
    assert list(at.dataframe[0].value.columns) == [
        "ID", "Title", "Creator", "Category", "Priority", "Status", "Created",
    ]  # fmt: skip


def test_ac71_fr27_engineer_search_keeps_newest_first_order(new_app, ui_service):
    """AC-71 / FR-27: several matches keep newest-first order."""
    ids = [
        ui_service.create_ticket("A", f"Printer {w}", "d", "Other", "Low").id
        for w in ("one", "two", "three")
    ]
    at = engineer_search(new_app("Support Engineer"), "printer")
    assert listed_ids(at) == sorted(ids, reverse=True)


@pytest.mark.parametrize("query", ["PRINTER", "printer", "pRiNtEr"])
def test_ac72_fr27_engineer_search_is_case_insensitive(new_app, printer_vpn, query):
    """AC-72 / FR-27: any letter case finds the same ticket."""
    printer, _ = printer_vpn
    at = engineer_search(new_app("Support Engineer"), query)
    assert listed_ids(at) == [printer.id]


def test_ac73_fr27_engineer_search_covers_description_and_creator_only(new_app, ui_service):
    """AC-73 / FR-27 (ASM-25c): description and creator match; category/status/priority/note
    are not searched."""
    desc = ui_service.create_ticket("Zed", "Printing", "toner is low", "Other", "Low")
    creator = ui_service.create_ticket("Marlene", "Mouse", "broken", "Other", "Low")
    other = ui_service.create_ticket("Tester", "Cable", "loose", "Network", "Critical")
    ui_service.change_status(other.id, "In Progress", "Network cable replaced")
    at = new_app("Support Engineer")
    engineer_search(at, "toner")
    assert listed_ids(at) == [desc.id]
    engineer_search(at, "marlene")
    assert listed_ids(at) == [creator.id]
    for query in ("Network", "In Progress", "Critical", "replaced"):
        engineer_search(at, query)
        assert listed_ids(at) == [], query
        assert NO_MATCH in info_texts(at)


def test_ac74_fr27_engineer_search_by_ticket_id_text(new_app, ui_service):
    """AC-74 / FR-27: tickets 1..12; '12' -> only 12; '2' -> 12 and 2."""
    for letter in "ABCDEFGHIJKL":
        ui_service.create_ticket("Tester", f"Item {letter}", "plain", "Other", "Low")
    at = new_app("Support Engineer")
    engineer_search(at, "12")
    assert listed_ids(at) == [12]
    engineer_search(at, "2")
    assert listed_ids(at) == [12, 2]
    engineer_search(at, "5")
    assert listed_ids(at) == [5]


def test_ac75_fr27_fr08_search_combines_with_filters_and_clearing_restores(new_app, ui_service):
    """AC-75 / FR-27, FR-08: status filter + search; clearing the search keeps the filter."""
    a = ui_service.create_ticket("A", "VPN one", "d", "Network", "Low")
    b = ui_service.create_ticket("B", "VPN two", "d", "Network", "Low")
    c = ui_service.create_ticket("C", "Other thing", "d", "Network", "Low")
    ui_service.change_status(b.id, "In Progress")
    at = new_app("Support Engineer")
    at.selectbox(key="flt_status").set_value("Open").run()
    engineer_search(at, "vpn")
    assert listed_ids(at) == [a.id]
    engineer_search(at, "")
    assert listed_ids(at) == [c.id, a.id]
    assert at.selectbox(key="flt_status").value == "Open"


def test_ac75_fr27_search_combines_with_each_other_filter(new_app, ui_service):
    """AC-75 / FR-27: priority, category and creator filters AND with the search."""
    a = ui_service.create_ticket("Ann", "VPN", "d", "Network", "High")
    ui_service.create_ticket("Bob", "VPN", "d", "Hardware", "Low")
    at = new_app("Support Engineer")
    engineer_search(at, "vpn")
    at.selectbox(key="flt_priority").set_value("High").run()
    assert listed_ids(at) == [a.id]
    at.selectbox(key="flt_priority").set_value("All").run()
    at.selectbox(key="flt_category").set_value("Network").run()
    assert listed_ids(at) == [a.id]
    at.selectbox(key="flt_category").set_value("All").run()
    at.text_input(key="flt_creator").input("bob").run()
    assert listed_ids(at) == [a.id + 1]


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_ac76_fr27_engineer_empty_or_blank_search_shows_full_list_without_messages(
    new_app, printer_vpn, blank
):
    """AC-76 / FR-27: empty / whitespace-only search = unchanged list, no no-match message."""
    at = new_app("Support Engineer")
    full = listed_ids(at)
    engineer_search(at, blank)
    assert listed_ids(at) == full
    assert NO_MATCH not in info_texts(at) and len(at.error) == 0 and len(at.exception) == 0


SPECIAL_TITLES = ["100% sure", "a_c cable", "abc", "it's broken", 'say "hi"',
                  "back\\slash", "<b>x</b>"]  # fmt: skip


@pytest.mark.parametrize(
    ("query", "expected_title"),
    [
        ("%", "100% sure"),
        ("a_c", "a_c cable"),
        ("'", "it's broken"),
        ('"hi"', 'say "hi"'),
        ("\\", "back\\slash"),
        ("<b>", "<b>x</b>"),
    ],
)
def test_ac77_fr27_nfr08_special_characters_are_matched_literally(
    new_app, ui_service, ui_snapshot, query, expected_title
):
    """AC-77 / FR-27, NFR-08: %, a_c, ', "hi", \\, <b> list only tickets containing that text;
    `%` is no wildcard, `a_c` does not match `abc`; stored data unchanged."""
    for title in SPECIAL_TITLES:
        ui_service.create_ticket("Tester", title, "plain", "Other", "Low")
    before = ui_snapshot()
    at = engineer_search(new_app("Support Engineer"), query)
    assert len(at.exception) == 0 and len(at.error) == 0
    assert listed_titles(at) == [expected_title]
    assert ui_snapshot() == before


def test_ac77_fr27_nfr08_sql_looking_search_matches_nothing_and_changes_nothing(
    new_app, ui_service, ui_snapshot
):
    """AC-77 / FR-27, NFR-08: ' OR 1=1 -- matches nothing; '; DROP TABLE matches only a ticket
    that really contains it; the table survives."""
    for title in SPECIAL_TITLES:
        ui_service.create_ticket("Tester", title, "plain", "Other", "Low")
    ui_service.create_ticket("Tester", "x'; DROP TABLE tickets; --", "plain", "Other", "Low")
    before = ui_snapshot()
    at = new_app("Support Engineer")
    engineer_search(at, "' OR 1=1 --")
    assert listed_ids(at) == [] and NO_MATCH in info_texts(at)
    engineer_search(at, "'; DROP TABLE tickets; --")
    assert listed_titles(at) == ["x'; DROP TABLE tickets; --"]
    assert ui_snapshot() == before
    assert len(ui_service.list_tickets()) == 8


def test_ac77_fr27_percent_does_not_match_everything(new_app, ui_service):
    """AC-77 / FR-27: '%' lists 1 of 3 tickets, not all of them."""
    ui_service.create_ticket("T", "100% sure", "d", "Other", "Low")
    ui_service.create_ticket("T", "plain", "d", "Other", "Low")
    ui_service.create_ticket("T", "also plain", "d", "Other", "Low")
    at = engineer_search(new_app("Support Engineer"), "%")
    assert len(listed_ids(at)) == 1


def test_ac78_fr27_no_match_shows_message_and_clearing_restores_list(new_app, printer_vpn):
    """AC-78 / FR-27: unmatched text -> 'No matching tickets.'; clearing shows the list again."""
    at = new_app("Support Engineer")
    full = listed_ids(at)
    engineer_search(at, "zzz-not-there")
    assert NO_MATCH in info_texts(at) and listed_ids(at) == [] and len(at.exception) == 0
    at.selectbox(key="flt_status").set_value("Open").run()
    assert NO_MATCH in info_texts(at)  # search combined with a filter
    engineer_search(at, "")
    assert listed_ids(at) == full


def test_ac78_fr27_overlong_search_text_simply_matches_nothing(new_app, printer_vpn):
    """AC-78 / FR-27 (ASM-25g): an overlong term is not an error."""
    at = engineer_search(new_app("Support Engineer"), "x" * 5000)
    assert NO_MATCH in info_texts(at) and len(at.error) == 0 and len(at.exception) == 0


def test_ac78_fr27_search_on_empty_database_shows_no_tickets_not_an_error(new_app):
    """AC-13, AC-78 / FR-27: empty DB with a search term still shows the 'no tickets' message."""
    at = engineer_search(new_app("Support Engineer"), "anything")
    assert len(at.exception) == 0 and len(at.error) == 0
    assert "No tickets yet." in info_texts(at)


@pytest.mark.parametrize("text", ["ünïcode", "日本語", "\U0001f600"])
def test_ac72_fr27_search_handles_unicode_text(new_app, ui_service, text):
    """AC-72 / FR-27: unicode search terms match literally (case-folded)."""
    t = ui_service.create_ticket("T", f"Ticket {text.upper()}", "d", "Other", "Low")
    ui_service.create_ticket("T", "Plain", "d", "Other", "Low")
    at = engineer_search(new_app("Support Engineer"), text.lower())
    assert listed_ids(at) == [t.id]


def test_ac81_fr27_search_does_not_change_stored_data(new_app, ui_service, ui_snapshot):
    """AC-81 / FR-27: a snapshot of stored data is identical after many searches."""
    ui_service.create_ticket(**VALID)
    ui_service.create_ticket(**{**VALID, "title": "VPN %"})
    before = ui_snapshot()
    at = new_app("Support Engineer")
    for query in ("vpn", "%", "'", "zzz", "", "1"):
        engineer_search(at, query)
    assert ui_snapshot() == before


# --------------------------------------------------------------- Employee view (AppTest) -


@pytest.fixture
def ann_bob_search(ui_service):
    ann_vpn = ui_service.create_ticket(
        "Ann", "VPN down", "Cannot connect to vpn", "Network", "High"
    )
    ann_mail = ui_service.create_ticket("Ann", "Mail slow", "Outlook hangs", "Software", "Low")
    bob = ui_service.create_ticket(
        "Bob", "Gateway issue", "firewall blocks port", "Network", "High"
    )
    return ann_vpn, ann_mail, bob


def employee_search(at, name, text):
    at.text_input(key="my_tickets_name").input(name)
    at.text_input(key="my_search").input(text).run()
    return at


def test_ac79_fr27_fr26_employee_search_never_shows_other_peoples_tickets(new_app, ann_bob_search):
    """AC-79 / FR-27, FR-26: 'firewall' exists only in Bob's ticket; Ann never sees it."""
    ann_vpn, ann_mail, bob = ann_bob_search
    at = employee_search(new_app("Employee"), "Ann", "firewall")
    assert listed_ids(at) == [] and bob.id not in listed_ids(at)
    assert NO_MATCH in info_texts(at)
    assert all("Gateway" not in str(t) for t in listed_titles(at))
    employee_search(at, "Ann", "outlook")
    assert listed_ids(at) == [ann_mail.id]


def test_ac79_fr27_fr26_employee_search_matching_every_ticket_still_only_lists_own(
    new_app, ann_bob_search
):
    """AC-79 / FR-27, FR-26: a term present in both people's tickets lists only Ann's."""
    ann_vpn, ann_mail, bob = ann_bob_search
    from app.common import search_tickets

    assert bob.id in [t.id for t in search_tickets(list(ann_bob_search), "o")]
    at = employee_search(new_app("Employee"), " ann ", "o")  # 'o' appears in all three tickets
    assert listed_ids(at) == [ann_mail.id, ann_vpn.id]
    assert bob.id not in listed_ids(at)


def test_ac80_fr27_fr26_employee_messages_for_no_match_no_tickets_and_cleared_search(
    new_app, ann_bob_search
):
    """AC-80 / FR-27, FR-26: no-match message, no-tickets message, list restored on clear."""
    ann_vpn, ann_mail, _ = ann_bob_search
    at = employee_search(new_app("Employee"), "Ann", "zzz")
    assert NO_MATCH in info_texts(at) and NO_TICKETS_EMPLOYEE not in info_texts(at)
    employee_search(at, "Nobody", "zzz")
    assert NO_TICKETS_EMPLOYEE in info_texts(at) and NO_MATCH not in info_texts(at)
    employee_search(at, "Ann", "")
    assert listed_ids(at) == [ann_mail.id, ann_vpn.id]


def test_ac71_ac72_fr27_employee_search_title_case_insensitive(new_app, ann_bob_search):
    """AC-71, AC-72 / FR-27: employee list search by title, any case."""
    ann_vpn, _, _ = ann_bob_search
    for query in ("vpn", "VPN", "vPn"):
        at = employee_search(new_app("Employee"), "Ann", query)
        assert listed_ids(at) == [ann_vpn.id]


def test_ac76_fr27_employee_blank_search_shows_all_own_tickets(new_app, ann_bob_search):
    """AC-76 / FR-27: whitespace-only search in the Employee view changes nothing."""
    ann_vpn, ann_mail, _ = ann_bob_search
    at = employee_search(new_app("Employee"), "Ann", "    ")
    assert listed_ids(at) == [ann_mail.id, ann_vpn.id]
    assert NO_MATCH not in info_texts(at)


def test_ac77_fr27_employee_search_special_characters_literal(new_app, ui_service, ui_snapshot):
    """AC-77 / FR-27: '%' and SQL-looking text in the Employee search are literal."""
    ui_service.create_ticket("Ann", "100% done", "d", "Other", "Low")
    ui_service.create_ticket("Ann", "normal", "d", "Other", "Low")
    before = ui_snapshot()
    at = employee_search(new_app("Employee"), "Ann", "%")
    assert listed_titles(at) == ["100% done"]
    employee_search(at, "Ann", "' OR 1=1 --")
    assert listed_ids(at) == [] and NO_MATCH in info_texts(at)
    assert ui_snapshot() == before


def test_ac81_fr27_employee_search_leaves_stored_data_unchanged(
    new_app, ann_bob_search, ui_snapshot
):
    """AC-81 / FR-27: data identical after Employee searches."""
    before = ui_snapshot()
    at = new_app("Employee")
    for query in ("vpn", "firewall", "%", ""):
        employee_search(at, "Ann", query)
    assert ui_snapshot() == before
