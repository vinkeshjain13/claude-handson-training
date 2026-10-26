"""Employee screens: raise a ticket and list own tickets (FR-01..03, 05..07, 25, 26)."""

import streamlit as st

from app.common import (
    flash,
    render_ticket_details,
    search_tickets,
    select_ticket,
    show_error,
    ticket_rows,
)
from ticketing import config
from ticketing.models import TicketError
from ticketing.service import TicketService


def _label(field: str) -> str:
    return f"{config.FIELD_LABELS[field]} *"


def _render_create(service: TicketService) -> None:
    st.subheader("Raise a ticket")
    nonce = st.session_state.setdefault("create_nonce", 0)
    with st.form(f"create_form_{nonce}", clear_on_submit=False):
        creator = st.text_input(_label("creator"), key=f"create_creator_{nonce}")
        title = st.text_input(_label("title"), key=f"create_title_{nonce}")
        description = st.text_area(_label("description"), key=f"create_description_{nonce}")
        category = st.selectbox(
            _label("category"),
            config.CATEGORIES,
            index=config.CATEGORIES.index(config.DEFAULT_CATEGORY),
            key=f"create_category_{nonce}",
        )
        priority = st.selectbox(
            _label("priority"),
            config.PRIORITIES,
            index=config.PRIORITIES.index(config.DEFAULT_PRIORITY),
            key=f"create_priority_{nonce}",
        )
        submitted = st.form_submit_button("Submit ticket", key=f"create_submit_{nonce}")
        st.caption("* required")
    if not submitted:
        return
    try:
        ticket = service.create_ticket(creator, title, description, category, priority)
    except TicketError as exc:
        show_error(exc)
        return
    st.session_state["create_nonce"] = nonce + 1
    flash(f"Ticket #{ticket.id} was created with status {ticket.status}.")
    st.rerun()


def _render_my_tickets(service: TicketService) -> None:
    st.subheader("My tickets")
    name = st.text_input(config.FIELD_LABELS["creator"], key="my_tickets_name")
    st.caption(
        "Matches the name used when raising tickets (not case sensitive). "
        "This is a convenience filter, not a privacy feature."
    )
    search = st.text_input("Search (ID, title, description, creator)", key="my_search")
    if not name.strip():
        st.info("Enter your name to see your tickets.")
        return
    try:
        tickets = service.list_my_tickets(name)
    except TicketError as exc:
        show_error(exc)
        return
    if not tickets:
        st.info("No tickets found for that name.")
        return
    shown = search_tickets(tickets, search)
    if not shown:
        st.info("No matching tickets.")
        return
    st.dataframe(ticket_rows(shown), hide_index=True, width="stretch")
    ticket_id = select_ticket(shown, "employee_selected_ticket")
    try:
        ticket = service.get_ticket(ticket_id)
    except TicketError as exc:
        show_error(exc)
        return
    render_ticket_details(ticket, "emp")


def render(service: TicketService) -> None:
    create_tab, my_tab = st.tabs(["Raise a ticket", "My tickets"])
    with create_tab:
        _render_create(service)
    with my_tab:
        _render_my_tickets(service)
