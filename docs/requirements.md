# Requirements: Support Ticket Portal (MVP)

## 1. Purpose
A Streamlit web portal for a retail customer-support team. A user uploads a CSV of
**synthetic** support tickets; the portal summarises them, classifies each ticket with
**deterministic Python rules**, and offers **editable template replies**.

## 2. Constraints (non-goals)
- No external LLM calls, paid APIs, external database, or authentication.
- No real user data. Only synthetic, safe text (no real names, emails, phones, addresses, card numbers).
- Classification is **rule-based (keyword/pattern matching)**. It is NOT machine learning or AI.
  Sentiment is a rough keyword heuristic; no accuracy claim is made anywhere in the UI or docs.
- Everything runs locally; state lives in the Streamlit session only.

## 3. CSV Schema
Required columns (header names exact, case-sensitive, any column order; extra columns ignored):

| Column | Type | Rules |
|---|---|---|
| `ticket_id` | string | Non-empty, unique within file (e.g. `T-1001`) |
| `customer_message` | string | Non-empty, free text, max 2000 chars |
| `created_at` | datetime | ISO 8601, e.g. `2026-03-14T09:30:00` (date-only `2026-03-14` also accepted) |

Validation: missing required column -> whole file rejected with clear error. Row-level problems
(blank message, duplicate id, unparseable date) -> row flagged/skipped with a visible warning
count; valid rows still processed. Max upload size: 5 MB (Streamlit setting).

Derived (not in CSV): `category`, `priority`, `sentiment`, `suggested_response`.

Example rows (synthetic):
```
ticket_id,customer_message,created_at
T-1001,"My order arrived damaged and I want a refund.",2026-03-14T09:30:00
T-1002,"Where is my package? Tracking has not updated in a week.",2026-03-14T10:05:00
```
A full 20+ row sample lives in `data/sample_tickets.csv`.

## 4. Classification Rules (behavioural spec)
- **Category** (first match by fixed precedence, else `General Inquiry`): Shipping/Delivery,
  Refund/Return, Billing/Payment, Product Defect, Account/Login, General Inquiry.
- **Priority** (`High` / `Medium` / `Low`): urgency keywords (e.g. "urgent", "immediately",
  "charged twice", "fraud") -> High; issue-type keywords -> Medium; else Low.
- **Sentiment** (`Negative` / `Neutral` / `Positive`): count of positive vs negative keywords.
  Labelled in UI as "rule-based estimate".
- Same input always yields same output (deterministic, case-insensitive).
- Keyword lists live in one config module so they are easy to review and edit.

## 5. User Stories and Acceptance Tests

### US-1 Upload a CSV
*As a support agent, I upload a ticket CSV so I can review it in the portal.*
- AT-1.1 Uploading `data/sample_tickets.csv` shows no errors and processes all rows.
- AT-1.2 Uploading a CSV lacking `customer_message` shows an error naming the missing column; no dashboard rendered.
- AT-1.3 Uploading an empty file or non-CSV shows a friendly error, app does not crash.
- AT-1.4 Rows with blank message or duplicate `ticket_id` are reported with a count; others still shown.

### US-2 See ticket totals
*As a team lead, I see the total ticket count.*
- AT-2.1 Total equals number of valid rows in the file.
- AT-2.2 Count updates when a different file is uploaded.

### US-3 See priority distribution
- AT-3.1 A chart and counts table show High/Medium/Low; counts sum to total.
- AT-3.2 Priorities with zero tickets still appear with count 0.

### US-4 See category distribution
- AT-4.1 A chart and counts table show every category present; counts sum to total.

### US-5 Browse the ticket table
- AT-5.1 Table shows ticket_id, created_at, customer_message, category, priority, sentiment.
- AT-5.2 User can filter by category and priority; total shown reflects the filter.
- AT-5.3 Table is sorted by created_at (newest first) by default.

### US-6 Deterministic classification
- AT-6.1 "I was charged twice, fix this immediately" -> Billing/Payment, High, Negative.
- AT-6.2 "Thanks, the jacket fits great" -> General Inquiry, Low, Positive.
- AT-6.3 Text matching no rule -> General Inquiry, Low, Neutral.
- AT-6.4 Classifying the same text twice (and in different letter case) gives identical results.
- AT-6.5 UI/README state that classification is rule-based and make no accuracy claims.

### US-7 Editable template responses
*As an agent, I get a draft reply per ticket that I can edit before use.*
- AT-7.1 Selecting a ticket shows a template reply matched to its category (and a softer opener for Negative sentiment).
- AT-7.2 The reply appears in an editable text area; edits persist while the session lasts.
- AT-7.3 A "reset to template" control restores the original text.
- AT-7.4 The reply is only displayed/copyable; nothing is sent anywhere.

### US-8 Safe, offline operation
- AT-8.1 App runs with no network access and no API keys.
- AT-8.2 No dependency on an LLM/ML/HTTP-client library in `requirements.txt`.
- AT-8.3 Sample data contains only synthetic text (reviewed by grep for emails/phones/digits patterns).

## 6. Quality Bar
- Unit tests (pytest) cover classifier rules, CSV validation, summary counts, response templates.
- Pure logic lives in `src/` and is testable without Streamlit.
