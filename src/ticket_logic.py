"""Pure, deterministic support-ticket logic (no Streamlit, no network, no ML).

Classification is keyword/pattern matching only. Sentiment is a rough keyword
heuristic. No accuracy claim is made.
"""
from __future__ import annotations

import io
import re

import pandas as pd

REQUIRED_COLUMNS = ["ticket_id", "customer_message", "created_at"]
MAX_MESSAGE_LENGTH = 2000
MAX_ID_LENGTH = 64
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

CATEGORIES = [
    "Billing/Payment",
    "Refund/Return",
    "Product Defect",
    "Shipping/Delivery",
    "Account/Login",
    "General Inquiry",
]  # order = precedence; first match wins
PRIORITIES = ["High", "Medium", "Low"]
SENTIMENTS = ["Negative", "Neutral", "Positive"]

CATEGORY_KEYWORDS = {
    "Billing/Payment": ["charged", "overcharged", "invoice", "billing", "payment", "fraud", "receipt"],
    "Refund/Return": ["refund", "return", "money back", "cancel", "exchange"],
    "Product Defect": ["damaged", "broken", "defective", "cracked", "stopped working", "faulty", "malfunction"],
    "Shipping/Delivery": ["delivery", "delivered", "package", "parcel", "tracking", "shipping", "shipped", "courier"],
    "Account/Login": ["log in", "login", "password", "username", "sign in", "account locked"],
}
HIGH_PRIORITY_KEYWORDS = [
    "urgent", "immediately", "asap", "charged twice", "double charged", "fraud", "unauthorized", "emergency",
]
POSITIVE_KEYWORDS = ["thank", "great", "love", "perfect", "helpful", "happy", "excellent", "wonderful", "awesome"]
NEGATIVE_KEYWORDS = [
    "terrible", "worst", "disappointed", "angry", "unacceptable", "broken", "damaged", "worried", "not arrived",
    "wrong", "defective", "fraud", "charged twice", "immediately", "urgent", "never", "useless", "stopped working",
]


class TicketDataError(ValueError):
    """User-facing data problem; the message is safe to show as-is."""


def _compile(keywords: list[str]) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(re.escape(k) for k in keywords) + ")", re.IGNORECASE)


_CATEGORY_RE = {c: _compile(k) for c, k in CATEGORY_KEYWORDS.items()}
_HIGH_RE = _compile(HIGH_PRIORITY_KEYWORDS)
_POS_RE = _compile(POSITIVE_KEYWORDS)
_NEG_RE = _compile(NEGATIVE_KEYWORDS)


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def parse_csv(raw: bytes) -> pd.DataFrame:
    """Parse uploaded CSV bytes into an all-string DataFrame or raise TicketDataError."""
    if not raw or not raw.strip():
        raise TicketDataError("The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise TicketDataError("The file is larger than the 5 MB limit.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise TicketDataError("The file is not valid UTF-8 text. Please upload a CSV file.") from None
    try:
        return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError):
        raise TicketDataError("The file could not be read as a CSV.") from None


def normalize_tickets(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Validate headers and rows. Returns (clean_df, warnings).

    Raises TicketDataError for missing/invalid input. Bad rows are skipped and counted.
    """
    if dataframe is None or not isinstance(dataframe, pd.DataFrame) or len(dataframe.columns) == 0:
        raise TicketDataError("No data found in the file.")
    df = dataframe.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise TicketDataError(
            "Missing required column(s): " + ", ".join(missing) + ". Expected: " + ", ".join(REQUIRED_COLUMNS) + "."
        )
    if df.empty:
        raise TicketDataError("The file has headers but no ticket rows.")

    df = df[REQUIRED_COLUMNS].copy()
    for col in REQUIRED_COLUMNS:
        df[col] = df[col].map(lambda v: _text(v).strip() if isinstance(v, str) else ("" if pd.isna(v) else str(v).strip()))
    total = len(df)
    warnings: list[str] = []

    def drop(mask: pd.Series, reason: str) -> None:
        nonlocal df
        n = int(mask.sum())
        if n:
            warnings.append(f"{n} row(s) skipped: {reason}.")
            df = df[~mask]

    drop(df["ticket_id"] == "", "missing ticket_id")
    drop(df["ticket_id"].str.len() > MAX_ID_LENGTH, f"ticket_id longer than {MAX_ID_LENGTH} characters")
    drop(df["customer_message"] == "", "blank customer_message")
    drop(df["customer_message"].str.len() > MAX_MESSAGE_LENGTH, f"message longer than {MAX_MESSAGE_LENGTH} characters")
    drop(df["ticket_id"].duplicated(keep="first"), "duplicate ticket_id (first occurrence kept)")
    parsed = pd.to_datetime(df["created_at"], errors="coerce", format="ISO8601")
    drop(parsed.isna(), "missing or invalid created_at (use ISO 8601, e.g. 2026-03-14T09:30:00)")
    if df.empty:
        raise TicketDataError(f"No valid ticket rows were found in {total} row(s). " + " ".join(warnings))
    df["created_at"] = pd.to_datetime(df["created_at"], format="ISO8601")
    return df.reset_index(drop=True), warnings


def classify_ticket(message: str) -> dict[str, str]:
    """Return {'category', 'priority', 'sentiment'} for a message. Deterministic, case-insensitive."""
    text = _text(message)
    category = next((c for c in CATEGORIES[:-1] if _CATEGORY_RE[c].search(text)), "General Inquiry")
    if _HIGH_RE.search(text):
        priority = "High"
    elif category != "General Inquiry":
        priority = "Medium"
    else:
        priority = "Low"
    pos, neg = len(_POS_RE.findall(text)), len(_NEG_RE.findall(text))
    sentiment = "Positive" if pos > neg else "Negative" if neg > pos else "Neutral"
    return {"category": category, "priority": priority, "sentiment": sentiment}


_TEMPLATES = {
    "Billing/Payment": "We have flagged the charge on your account and our billing team will review it. We will confirm the corrected amount or next steps shortly.",
    "Refund/Return": "We can help with your refund or return. Please keep your order number handy; we will send the return instructions and confirm the refund timeline.",
    "Product Defect": "We are sorry the item did not meet expectations. We can arrange a replacement or repair; a photo of the problem will help us speed this up.",
    "Shipping/Delivery": "We are checking the delivery status of your order with the carrier and will update you as soon as we have a confirmed location or date.",
    "Account/Login": "For your security, please use the 'Forgot password' option on the sign-in page. If that does not work, we will help you regain access.",
    "General Inquiry": "Thanks for getting in touch. We have received your message and will reply with the information you asked for.",
}


def draft_response(message: str, category: str, priority: str) -> str:
    """Return an editable template reply. Never echoes the customer's text; nothing is sent."""
    body = _TEMPLATES.get(category, _TEMPLATES["General Inquiry"])
    sentiment = classify_ticket(message)["sentiment"]
    opener = "Hello,"
    if sentiment == "Negative":
        opener = "Hello, we are very sorry for the trouble this has caused."
    elif sentiment == "Positive":
        opener = "Hello, thank you for the kind words."
    urgency = " We are treating this as a priority." if priority == "High" else ""
    return f"{opener} {body}{urgency}\n\nKind regards,\nSupport Team"


def analyze_tickets(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Normalize then label every ticket. Returns (analyzed_df, warnings)."""
    df, warnings = normalize_tickets(dataframe)
    labels = df["customer_message"].map(classify_ticket)
    for key in ("category", "priority", "sentiment"):
        df[key] = labels.map(lambda d, k=key: d[k])
    df["suggested_response"] = [
        draft_response(m, c, p) for m, c, p in zip(df["customer_message"], df["category"], df["priority"])
    ]
    return df, warnings


def count_by(df: pd.DataFrame, column: str, order: list[str]) -> pd.DataFrame:
    """Counts per label in a fixed order, including zero-count labels."""
    counts = df[column].value_counts()
    return pd.DataFrame({column: order, "count": [int(counts.get(o, 0)) for o in order]})


def to_safe_csv(df: pd.DataFrame) -> str:
    """CSV text with spreadsheet-formula prefixes neutralised (CSV injection)."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].map(
                lambda v: "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v
            )
    return out.to_csv(index=False)
