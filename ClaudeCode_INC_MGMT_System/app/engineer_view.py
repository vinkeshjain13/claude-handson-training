"""Support Engineer screen: filters, search, ticket table, details and update forms
(FR-06..11, 13, 15)."""

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
from ticketing.models import Ticket, TicketError
from ticketing.service import TicketService

ALL = "All"


def _filter_value(value: str) -> str | None:
    return None if value == ALL else value


def _render_filters() -> dict:
    c1, c2, c3, c4 = st.columns(4)
    status = c1.selectbox("Status", [ALL, *config.STATUSES], key="flt_status")
    priority = c2.selectbox("Priority", [ALL, *config.PRIORITIES], key="flt_priority")
    category = c3.selectbox("Category", [ALL, *config.CATEGORIES], key="flt_category")
    creator = c4.text_input(config.FIELD_LABELS["creator"], key="flt_creator")
    return {
        "status": _filter_value(status),
        "priority": _filter_value(priority),
        "category": _filter_value(category),
        "creator": creator.strip() or None,
    }


def _done(ticket_id: int) -> None:
    flash(f"Ticket #{ticket_id} updated.")
    st.rerun()


def _render_status_form(service: TicketService, ticket: Ticket, suffix: str) -> None:
    st.subheader("Update status / note")
    allowed = service.allowed_next_statuses(ticket.status)
    with st.form(f"status_form_{suffix}"):
        if allowed:
            new_status = st.selectbox("New status", allowed, key=f"status_new_{suffix}")
        else:
            new_status = None
            st.info(f"This ticket is {ticket.status} and has no further status changes.")
        note = st.text_area(
            config.FIELD_LABELS["resolution_note"],
            value=ticket.resolution_note,
            key=f"status_note_{suffix}",
        )
        c1, c2 = st.columns(2)
        change = c1.form_submit_button(
            "Change status", key=f"status_submit_{suffix}", disabled=new_status is None
        )
        save_note = c2.form_submit_button("Save note only", key=f"note_submit_{suffix}")
    if not (change or save_note):
        return
    try:
        if change:
            service.change_status(ticket.id, new_status, note.strip() or None)
        else:
            service.set_resolution_note(ticket.id, note)
    except TicketError as exc:
        show_error(exc)
        return
    _done(ticket.id)


def _render_priority_form(service: TicketService, ticket: Ticket, suffix: str) -> None:
    st.subheader("Update priority")
    with st.form(f"priority_form_{suffix}"):
        new_priority = st.selectbox(
            "New priority",
            config.PRIORITIES,
            index=config.PRIORITIES.index(ticket.priority),
            key=f"priority_new_{suffix}",
        )
        submitted = st.form_submit_button("Change priority", key=f"priority_submit_{suffix}")
    if not submitted:
        return
    try:
        service.change_priority(ticket.id, new_priority)
    except TicketError as exc:
        show_error(exc)
        return
    _done(ticket.id)


def render(service: TicketService) -> None:
    st.subheader("Tickets")
    filters = _render_filters()
    search = st.text_input("Search (ID, title, description, creator)", key="engineer_search")
    try:
        tickets = service.list_tickets(**filters)
    except TicketError as exc:
        show_error(exc)
        return
    if not tickets and not any(filters.values()):
        st.info("No tickets yet.")
        return
    shown = search_tickets(tickets, search)
    if not shown:
        st.info("No matching tickets.")
        return
    st.dataframe(ticket_rows(shown), hide_index=True, width="stretch")
    ticket_id = select_ticket(shown, "engineer_selected_ticket")
    try:
        ticket = service.get_ticket(ticket_id)
    except TicketError as exc:
        show_error(exc)
        return
    render_ticket_details(ticket, "eng")
    if ticket.status in config.READ_ONLY_STATUSES:
        st.info(f"This ticket is {ticket.status} and is read-only.")
        return
    suffix = f"{ticket.id}_{ticket.updated_at}"
    _render_status_form(service, ticket, suffix)
    _render_priority_form(service, ticket, suffix)
