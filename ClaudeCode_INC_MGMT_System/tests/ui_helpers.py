"""Small helpers for locating widgets and reading results in Streamlit AppTest runs."""

from __future__ import annotations

NO_MATCH = "No matching tickets."
NO_TICKETS_ENGINEER = "No tickets yet."
NO_TICKETS_EMPLOYEE = "No tickets found for that name."
ENTER_NAME = "Enter your name to see your tickets."


def by_label(elements, label):
    matches = [e for e in elements if e.label == label]
    assert len(matches) == 1, f"expected exactly one widget labelled {label!r}, got {len(matches)}"
    return matches[0]


def has_label(elements, label) -> bool:
    return any(e.label == label for e in elements)


def listed_ids(at) -> list[int]:
    """IDs shown in the ticket table (empty list when no table is rendered)."""
    if not len(at.dataframe):
        return []
    return [int(i) for i in at.dataframe[0].value["ID"].tolist()]


def listed_titles(at) -> list[str]:
    if not len(at.dataframe):
        return []
    return list(at.dataframe[0].value["Title"].tolist())


def info_texts(at) -> list[str]:
    return [i.value for i in at.info]


def error_texts(at) -> list[str]:
    return [e.value for e in at.error]


def metrics(at) -> dict[str, str]:
    return {m.label: m.value for m in at.metric}


def role(at, name):
    at.sidebar.radio(key="demo_role").set_value(name).run()
    return at
