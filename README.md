# Support Ticket Portal (MVP)

A small Streamlit app that analyses a CSV of **synthetic** support tickets. It runs fully offline:
no LLM or external API calls, no API keys, no database, no authentication.

## Features
- Upload a CSV (max 5 MB) with columns `ticket_id`, `customer_message`, `created_at`.
- Summary metrics, ticket counts by category and by priority (charts), filterable table.
- Rule-based category (Billing/Payment, Refund/Return, Product Defect, Shipping/Delivery,
  Account/Login, General Inquiry), priority (High/Medium/Low) and sentiment
  (Positive/Neutral/Negative) from keyword rules.
- Template draft replies per ticket (shown in the table and CSV only; nothing is sent).
- Download the analyzed CSV (spreadsheet-formula prefixes are neutralised).

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Then upload `data/sample_tickets.csv` (22 fictional tickets) in the browser.

## Run tests
```bash
python -m pytest
```

## CSV rules
- Headers are exact and case-sensitive; extra columns are ignored.
- A missing required column rejects the whole file with a message naming it.
- Rows with a blank message, a blank/over-long ID, a message over 2000 characters, a duplicate
  `ticket_id` (first kept) or an invalid ISO 8601 `created_at` are skipped and counted in a warning.
- Empty files, non-UTF-8 files and unreadable CSVs show a friendly error instead of a traceback.

## Layout
```
app.py                  Streamlit UI only
src/ticket_logic.py     Pure, deterministic logic (normalize_tickets, classify_ticket,
                        analyze_tickets, draft_response, plus helpers)
tests/test_ticket_logic.py
data/sample_tickets.csv Synthetic examples
```

## Limitations
- Classification is **keyword matching, not AI/ML**; no accuracy claim is made. Sentiment is a rough
  keyword estimate. Expect misses (negation, sarcasm, typos, non-English text).
- Category uses fixed precedence, so a message matching several categories gets the first one.
- Replies are generic templates meant to be edited by a person; there is no in-app reply editor yet.
- No persistence: everything lives in the Streamlit session.
- Use synthetic data only. Do not upload real customer information.
