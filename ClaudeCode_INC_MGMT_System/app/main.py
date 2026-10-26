"""Streamlit entry point: python -m streamlit run app/main.py (run from the repo root)."""

import sys
from pathlib import Path

# Streamlit puts app/ on sys.path, not the repo root; make `app` and `ticketing` importable.
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st  # noqa: E402

from app import employee_view, engineer_view, manager_view  # noqa: E402
from app.common import render_demo_notice, show_error, show_flash  # noqa: E402
from ticketing.models import TicketError  # noqa: E402
from ticketing.service import TicketService  # noqa: E402

ROLE_VIEWS = {
    "Employee": employee_view.render,
    "Support Engineer": engineer_view.render,
    "Manager": manager_view.render,
}


def main() -> None:
    st.set_page_config(page_title="IT Support Tickets (DEMO)", layout="wide")
    st.title("IT Support Ticket System")
    render_demo_notice()
    role = st.sidebar.radio("Demo role (not a login)", list(ROLE_VIEWS), key="demo_role")
    st.sidebar.caption("Demo selector only. No authentication.")
    try:
        service = TicketService()
    except TicketError as exc:
        show_error(exc)
        st.stop()
    show_flash()
    ROLE_VIEWS[role](service)


main()
