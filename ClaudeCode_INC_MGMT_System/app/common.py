"""Shared UI helpers. User-supplied text is rendered only via st.text, disabled text areas,
dataframe cells or selectbox labels (never markdown)."""

import streamlit as st

from ticketing.models import Ticket, TicketError, ValidationError, format_timestamp

DEMO_NOTICE = (
    "DEMO ONLY: the role selector below is a demonstration switch, not authentication or "
    "access control. Anyone can pick any role. No security or privacy is provided. "
    "Do not enter confidential information."
)

FLASH_KEY = "flash"


def render_demo_notice() -> None:
    st.warning(DEMO_NOTICE)


def show_error(exc: TicketError) -> None:
    if isinstance(exc, ValidationError) and exc.errors:
        for message in exc.errors.values():
            st.error(message)
    else:
        st.error(str(exc))


def flash(message: str) -> None:
    st.session_state[FLASH_KEY] = message


def show_flash() -> None:
    message = st.session_state.pop(FLASH_KEY, None)
    if message:
        st.success(message)


def ticket_rows(tickets: list[Ticket]) -> list[dict]:
    return [
        {
            "ID": t.id,
            "Title": t.title,
            "Creator": t.creator,
            "Category": t.category,
            "Priority": t.priority,
            "Status": t.status,
            "Created": format_timestamp(t.created_at),
        }
        for t in tickets
    ]


def ticket_option_label(ticket: Ticket) -> str:
    return f"#{ticket.id} - {ticket.title}"


def search_tickets(tickets: list[Ticket], query: str) -> list[Ticket]:
    """In-memory, case-insensitive literal substring search (ID, title, description, creator)."""
    needle = (query or "").strip().casefold()
    if not needle:
        return tickets
    return [
        t
        for t in tickets
        if any(
            needle in field.casefold() for field in (str(t.id), t.title, t.description, t.creator)
        )
    ]


def select_ticket(tickets: list[Ticket], key: str) -> int:
    """Selectbox over the given tickets; returns the chosen ticket ID."""
    ids = [t.id for t in tickets]
    labels = {t.id: ticket_option_label(t) for t in tickets}
    if st.session_state.get(key) not in ids:
        st.session_state.pop(key, None)
    return st.selectbox("Show details for", ids, format_func=labels.get, key=key)


def render_ticket_details(ticket: Ticket, key_prefix: str) -> None:
    suffix = f"{key_prefix}_{ticket.id}_{ticket.updated_at}"
    left, right = st.columns(2)
    with left:
        st.text(f"ID: {ticket.id}")
        st.text(f"Title: {ticket.title}")
        st.text(f"Creator: {ticket.creator}")
        st.text(f"Category: {ticket.category}")
    with right:
        st.text(f"Priority: {ticket.priority}")
        st.text(f"Status: {ticket.status}")
        st.text(f"Created: {format_timestamp(ticket.created_at)}")
        st.text(f"Updated: {format_timestamp(ticket.updated_at)}")
    st.text_area("Description", ticket.description, disabled=True, key=f"desc_{suffix}")
    if ticket.resolution_note:
        st.text_area("Resolution note", ticket.resolution_note, disabled=True, key=f"note_{suffix}")
    else:
        st.text_area("Resolution note (none)", "", disabled=True, key=f"note_{suffix}")
