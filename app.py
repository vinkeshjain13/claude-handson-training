"""Streamlit entrypoint for the support ticket portal (rule-based, offline)."""
import pandas as pd
import streamlit as st

from src.ticket_logic import (
    CATEGORIES, MAX_UPLOAD_BYTES, PRIORITIES, TicketDataError,
    analyze_tickets, count_by, parse_csv, to_safe_csv,
)

st.set_page_config(page_title="Support Ticket Portal", layout="wide")
st.title("Support Ticket Portal")
st.caption("Rule-based classification; sentiment is a rough keyword estimate, not AI/ML. Use synthetic data only; this app has no authentication.")

upload = st.file_uploader("Upload a tickets CSV (ticket_id, customer_message, created_at)", type=["csv"])
if upload is None:
    st.info("Upload a CSV to begin. A sample is available at data/sample_tickets.csv.")
    st.stop()

try:
    if upload.size > MAX_UPLOAD_BYTES:
        raise TicketDataError("The file is larger than the 5 MB limit.")
    df, warnings = analyze_tickets(parse_csv(upload.getvalue()))
except TicketDataError as err:
    st.error(str(err))
    st.stop()
except Exception:
    st.error("Something went wrong while processing the file. Please check it is a valid tickets CSV.")
    st.stop()

for w in warnings:
    st.warning(w)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total tickets", len(df))
for col, label, value in ((c2, "High priority", "High"), (c3, "Negative sentiment", "Negative")):
    column = "priority" if value == "High" else "sentiment"
    col.metric(label, int((df[column] == value).sum()))
c4.metric("Categories present", int(df["category"].nunique()))

left, right = st.columns(2)
cat_counts = count_by(df, "category", CATEGORIES)
pri_counts = count_by(df, "priority", PRIORITIES)
left.subheader("Tickets by category")
left.bar_chart(cat_counts.set_index("category")["count"])
right.subheader("Tickets by priority")
right.bar_chart(pri_counts.set_index("priority")["count"])

st.download_button(
    "Download analyzed CSV", to_safe_csv(df), file_name="analyzed_tickets.csv", mime="text/csv",
)

st.subheader("Tickets")
f1, f2 = st.columns(2)
cat_sel = f1.multiselect("Category", CATEGORIES)
pri_sel = f2.multiselect("Priority", PRIORITIES)
view = df
if cat_sel:
    view = view[view["category"].isin(cat_sel)]
if pri_sel:
    view = view[view["priority"].isin(pri_sel)]
view = view.sort_values("created_at", ascending=False)
st.caption(f"Showing {len(view)} of {len(df)} tickets")
st.dataframe(
    view[["ticket_id", "created_at", "customer_message", "category", "priority", "sentiment", "suggested_response"]],
    use_container_width=True, hide_index=True,
)
