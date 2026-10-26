"""Manager dashboard: metrics and charts from DashboardStats only (FR-16..20, 23, 24)."""

import pandas as pd
import streamlit as st

from app.common import show_error
from ticketing.models import TicketError
from ticketing.service import TicketService


def _bar_chart(counts: dict[str, int], label: str) -> None:
    frame = pd.DataFrame({label: list(counts), "Tickets": list(counts.values())})
    st.bar_chart(frame, x=label, y="Tickets", sort=False)


def render(service: TicketService) -> None:
    head, refresh = st.columns([5, 1])
    head.subheader("Dashboard")
    refresh.button("Refresh", key="dashboard_refresh")
    try:
        stats = service.get_dashboard_stats()
    except TicketError as exc:
        show_error(exc)
        return
    columns = st.columns(1 + len(stats.by_status))
    columns[0].metric("Total", stats.total)
    for column, (status, count) in zip(columns[1:], stats.by_status.items(), strict=True):
        column.metric(status, count)
    if stats.total == 0:
        st.caption("No tickets yet.")
    left, middle, right = st.columns(3)
    with left:
        st.text("By priority")
        _bar_chart(stats.by_priority, "Priority")
    with middle:
        st.text("By category")
        _bar_chart(stats.by_category, "Category")
    with right:
        st.text("By status")
        _bar_chart(stats.by_status, "Status")
