# Architecture (MVP)

Principle: Streamlit only in `app.py`; all logic is pure Python in `src/`, unit-testable.

## Layout
```
app.py                  # Streamlit UI: upload, metrics, charts, table, response editor
src/
  __init__.py
  config.py             # keyword lists, category precedence, priority/sentiment labels, limits
  loader.py             # parse + validate CSV -> DataFrame, return (df, warnings)
  classifier.py         # classify_category / classify_priority / classify_sentiment / classify_ticket
  analytics.py          # total count, priority & category distributions, filtering
  responses.py          # template replies by category/sentiment; render + reset
tests/
  test_loader.py
  test_classifier.py
  test_analytics.py
  test_responses.py
data/sample_tickets.csv # synthetic examples
requirements.txt        # streamlit, pandas, pytest (no AI/ML/HTTP libs)
README.md  .gitignore  CLAUDE.md
```

## Data flow
```
uploaded CSV -> loader.load_tickets() -> validated DataFrame
             -> classifier.classify_dataframe() -> + category, priority, sentiment
             -> analytics (totals, distributions, filters) -> app.py renders
selected ticket -> responses.build_response(category, sentiment) -> editable text area
```

## Module contracts
- `loader.load_tickets(file_like) -> LoadResult(df, warnings: list[str])`; raises `SchemaError` if required columns missing.
- `classifier.classify_ticket(text: str) -> TicketLabels(category, priority, sentiment)`; pure, deterministic, case-insensitive, no I/O.
- `analytics.summarize(df) -> Summary(total, by_priority, by_category)`; `filter_tickets(df, category=None, priority=None)`.
- `responses.build_response(category, sentiment, ticket_id) -> str`; templates are plain string constants with placeholders.

## Design decisions
- **Rules in `config.py`**: single place to audit/edit keywords; no hidden logic.
- **Precedence is explicit** (ordered list) so ties are deterministic.
- **Session state only**: edited replies stored in `st.session_state` keyed by `ticket_id`; no persistence.
- **Honesty**: UI caption "Rule-based classification; sentiment is a rough keyword estimate, not AI/ML."
- **Dependencies**: streamlit, pandas, pytest. Nothing that makes network calls on behalf of the app.

## Out of scope
Authentication, databases, exports/sending emails, LLMs, multi-language, real data, deployment.
