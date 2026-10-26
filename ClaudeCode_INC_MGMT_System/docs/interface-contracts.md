# Interface Contracts

Status: DESIGN v1 (awaiting approval). Author: solution-architect, 2026-10-24. Binding contract between frontend-developer, backend-developer and qa-engineer. Changes go through the solution-architect (and the human for material changes). Signatures below are specifications, not code to copy blindly.

Related: `docs/architecture.md` (ARCH), `docs/data-model.md` (DM, data-layer functions in DM section 9), `docs/validation-rules.md` (VR), `docs/ui-design.md` (UI).

## 1. Roles and identity (read first)

- The service has NO concept of role, session, user or permission. No service function takes a `role` argument. The UI decides which service calls each demo role's screens make (UI section 2). This is intentional: a role check inside the service would imply authorization, which BL-10 and NFR-12 say does not exist.
- `creator` is ordinary ticket data typed by the employee. It is not an identity and is not verified. `list_my_tickets(creator_name)` is a convenience filter (FR-26, ASM-23), not a privacy control.
- Docstrings and messages must not use words such as "authorized", "permission" or "secure".

## 2. Configuration constants (`ticketing/config.py`, owner backend-developer)

All rules that depend on unapproved assumptions live here (ARCH section 9). Names are part of the contract (UI and tests import them).

```python
STATUSES   = ("Open", "In Progress", "Resolved", "Closed")             # BL-07
PRIORITIES = ("Low", "Medium", "High", "Critical")                      # BL-08
CATEGORIES = ("Hardware", "Software", "Network", "Account Access", "Other")  # ASM-19
DEFAULT_STATUS, DEFAULT_PRIORITY, DEFAULT_CATEGORY = "Open", "Medium", "Other"
RESOLVED = "Resolved"
LIMITS = {"creator": 100, "title": 100, "description": 2000, "resolution_note": 1000}  # ASM-03
TRANSITIONS = {                                                          # ASM-06, ASM-20
    "Open":        ("In Progress",),
    "In Progress": ("Open", "Resolved"),
    "Resolved":    ("In Progress", "Closed"),
    "Closed":      (),
}
READ_ONLY_STATUSES = ("Closed",)          # ASM-20: no status/priority/note change
RESOLVED_REQUIRES_NOTE = True             # ASM-21
FIELD_LABELS = {"creator": "Your name", "title": "Title", "description": "Description",
                "category": "Category", "priority": "Priority", "status": "Status",
                "resolution_note": "Resolution note", "ticket_id": "Ticket ID"}
STORE_TS_FORMAT   = "%Y-%m-%d %H:%M:%S"   # ASM-15
DISPLAY_TS_FORMAT = "%Y-%m-%d %H:%M"
DB_PATH_ENV_VAR   = "TICKET_DB_PATH"
DEFAULT_DB_PATH   = <repo root> / "data" / "tickets.db"
def get_db_path() -> Path: ...            # env var if set and non-empty, else DEFAULT_DB_PATH
```

`FIELD_LABELS` are also the widget labels in the UI so messages and labels match (NFR-03, AC-51).

## 3. Shared types (`ticketing/models.py`, owner backend-developer)

```python
@dataclass(frozen=True)
class Ticket:
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    creator: str
    created_at: str        # "YYYY-MM-DD HH:MM:SS" local time (DM section 6)
    updated_at: str        # same format; equals created_at on creation (FR-13)
    resolution_note: str   # "" when none (FR-07)

@dataclass(frozen=True)
class DashboardStats:      # FR-16, 18, 19, 20, 23, 24
    total: int
    by_status:   dict[str, int]   # keys = config.STATUSES in order, zero-filled
    by_priority: dict[str, int]   # keys = config.PRIORITIES in order, zero-filled
    by_category: dict[str, int]   # keys = config.CATEGORIES in order, zero-filled

def format_timestamp(value: str) -> str:   # "2026-10-24 09:05:33" -> "2026-10-24 09:05"
```

Invariant (AC-40, 41, 65): `total == sum(by_status.values()) == sum(by_priority.values()) == sum(by_category.values())`. Empty database: `total == 0` and every value `0`, no exception (AC-42). There is no "pending" field (ASM-22).

## 4. Errors (`ticketing/models.py`)

```python
class TicketError(Exception): ...                      # base; str(exc) is a safe, user-readable message
class ValidationError(TicketError):                    # bad input value(s)
    errors: dict[str, str]                             # field name -> message; str(exc) joins messages with " "
class NotFoundError(TicketError): ...                  # unknown ticket ID
class TicketStateError(TicketError): ...               # input is valid but the ticket state forbids it
class StorageError(TicketError): ...                   # unexpected sqlite3.Error (already logged)
```

| Error | Raised when | Requirements |
|---|---|---|
| `ValidationError` | empty/whitespace/too long text; value not in list (priority, category, status, filter values); non-integer ticket ID; resolution note missing when required for Resolved; text that cannot be encoded as UTF-8 | FR-02, FR-03, FR-09, FR-15, FR-25; AC-03..05, 08, 28, 36, 64, 67 |
| `NotFoundError` | ticket ID does not exist | FR-07; AC-15, AC-29 |
| `TicketStateError` | ticket is in a read-only status (Closed); transition not allowed (including same status); priority equals current priority | FR-10, FR-11, FR-15; AC-25..27, 31, 62, 63 |
| `StorageError` | any `sqlite3.Error` | NFR-06; AC-55 |

Message policy:

1. Messages are fixed templates filled only from `config` values, field labels and integers (ticket ID, counts, limits). They never echo user-entered text, so showing them with `st.error` is safe and cannot be broken by special characters.
2. Validation messages name the field using `FIELD_LABELS` (AC-03, AC-51). Templates:
   - required: `"{Label} is required."`
   - too long: `"{Label} must be at most {limit} characters (you entered {n})."`
   - not in list: `"{Label} must be one of: {values joined by ', '}."`
   - ticket id: `"Ticket ID must be a whole number."`
   - note required for Resolved: `"Resolution note is required to set a ticket to Resolved."`
   - unencodable text: `"{Label} contains characters that cannot be stored."`
3. `NotFoundError`: `"Ticket {id} was not found."`
4. `TicketStateError`: `"Ticket {id} is Closed and cannot be changed."`; `"Ticket {id} is already {status}."`; `"Cannot change status from {from} to {to}. Allowed: {list or 'none'}."`; `"Priority is already {priority}."`
5. `StorageError`: `"The ticket data could not be read or saved. Please try again."` Details go to the log, not to the user.
6. Exact wording may be adjusted by the backend-developer if each message keeps the same facts (field/limit/allowed list); tests assert on the field name key in `ValidationError.errors` and on the exception class, plus substring checks of the field label, limit number or "Resolution note", not on full sentences.

## 5. Service API (`ticketing/service.py`, owner backend-developer)

```python
class TicketService:
    def __init__(self, db_path: str | Path | None = None,
                 clock: Callable[[], datetime] | None = None) -> None
```

`db_path=None` means `config.get_db_path()`. `clock=None` means `datetime.now`. The constructor creates the schema (idempotent). No other state is kept; every operation opens its own connection through `db.session` (ARCH D1). All methods are plain synchronous methods.

Common rules: text arguments must be `str` (anything else raises `ValidationError`); text is trimmed with `str.strip()` before validation and storage; lengths count Python characters after trimming; `ticket_id` must be an `int` (not `bool`); every failed call leaves the database unchanged (NFR-06) and does not touch `updated_at` (FR-13).

### 5.1 Operations

| # | Signature | Returns | Raises | Requirements / ACs |
|---|---|---|---|---|
| S1 | `create_ticket(self, creator: str, title: str, description: str, category: str, priority: str) -> Ticket` | the stored ticket: status `Open`, `created_at == updated_at`, empty resolution note | `ValidationError` (all failing fields collected in `errors`), `StorageError` | FR-01, 02, 03, 04, 05, 13, 25; AC-01..11, 33, 67 |
| S2 | `get_ticket(self, ticket_id: int) -> Ticket` | the ticket | `ValidationError` (non-int ID), `NotFoundError` | FR-07; AC-02, 14, 15 |
| S3 | `list_tickets(self, status: str \| None = None, priority: str \| None = None, category: str \| None = None, creator: str \| None = None) -> list[Ticket]` | tickets newest first (descending ID); `None` or blank text means "no filter"; filters combine with AND; `creator` is trimmed and compared case-insensitively and exactly (casefold) | `ValidationError` if a non-blank `status`/`priority`/`category` is not in its list | FR-06, 08; AC-12, 13, 16..20, 60 |
| S4 | `list_my_tickets(self, creator_name: str) -> list[Ticket]` | tickets whose creator equals `creator_name` (trim + casefold, exact), newest first. Blank name is NOT "all tickets" | `ValidationError` on blank/non-text name (`errors["creator"]`) | FR-26, 06, 07; AC-66 |
| S5 | `change_status(self, ticket_id: int, new_status: str, resolution_note: str \| None = None) -> Ticket` | the updated ticket | `ValidationError`, `NotFoundError`, `TicketStateError`, `StorageError` | FR-09, 10, 13, 15; AC-21..29, 33, 61..64 |
| S6 | `change_priority(self, ticket_id: int, new_priority: str) -> Ticket` | the updated ticket | `ValidationError`, `NotFoundError`, `TicketStateError`, `StorageError` | FR-11, 13; AC-30, 31, 33, 62 |
| S7 | `set_resolution_note(self, ticket_id: int, note: str) -> Ticket` | the updated ticket; note replaces any previous note | `ValidationError` (blank, too long), `NotFoundError`, `TicketStateError` (Closed), `StorageError` | FR-15, 13; AC-33, 36, 62 |
| S8 | `get_dashboard_stats(self) -> DashboardStats` | zero-filled stats read in one read transaction (consistent counts) | `StorageError` | FR-16, 18, 19, 20, 23, 24; AC-37..43, 59, 65 |
| S9 | `allowed_next_statuses(self, current_status: str) -> tuple[str, ...]` | `config.TRANSITIONS[current_status]`; empty tuple for unknown or Closed. Pure function, no database access. Lets the UI fill the status dropdown without copying the transition table. | none | FR-09, 10 (supports AC-21..27, 61, 63 in the UI) |

Cross-layer note on S5, `resolution_note` parameter: `None`, `""` or whitespace-only means "no note supplied". A non-blank value is validated (max 1000) and, if the transition is allowed, saved in the same transaction as the status change (AC-22 "supplied in the same action"). The saved note replaces the previous one. Allowed on any allowed transition, not only to Resolved.

### 5.2 Operation order of checks (deterministic, so tests and UI agree)

For S5, S6, S7 inside one write transaction:

1. `ticket_id` is an `int` else `ValidationError["ticket_id"]`.
2. Value validation that does not need the ticket: new status/priority in list, note length/blank rules (`ValidationError`). Done before the transaction.
3. Fetch the ticket; missing -> `NotFoundError`.
4. Read-only status (`current in READ_ONLY_STATUSES`) -> `TicketStateError` ("is Closed and cannot be changed").
5. S5 only: `new_status` not in `TRANSITIONS[current]` (this includes the same status) -> `TicketStateError`.
6. S5 only: `new_status == RESOLVED` and `RESOLVED_REQUIRES_NOTE` and neither a supplied note nor a stored note exists -> `ValidationError["resolution_note"]` (AC-64). Note: a stored note satisfies the rule (AC-22 "existing or supplied").
7. S6 only: `new_priority == current priority` -> `TicketStateError` (ASM-24).
8. `update_ticket(...)` with `updated_at = clock()` formatted; read the row back; commit; return the `Ticket`.

Consequences: status value "Pending" on any ticket gives `ValidationError` (AC-28); Open -> Resolved gives `TicketStateError` even without a note (AC-25); In Progress -> Resolved without any note gives `ValidationError` naming the resolution note (AC-64); any change on a Closed ticket gives `TicketStateError` (AC-62), unless the value itself is invalid (then `ValidationError`, still no change).

### 5.3 `create_ticket` details

1. Trim and validate all five fields; collect all errors; if any, raise `ValidationError` before opening a connection.
2. `now = clock().strftime(STORE_TS_FORMAT)`; insert with `status = DEFAULT_STATUS`, `created_at = updated_at = now`; fetch the new row; return `Ticket`.
3. Identical submissions create separate tickets (ASM-13, AC-10).

### 5.4 Dashboard construction (S8)

In one `db.session(write=False)`: `total = count_all`, three `count_by` calls; for each list in config, build a dict `{value: raw.get(value, 0)}` in config order. Values found in the database but not in the config lists cannot exist because of the `CHECK` constraints.

## 6. Status transition table (single source: `config.TRANSITIONS`; ASM-06, ASM-20 unapproved)

| From \ To | Open | In Progress | Resolved | Closed |
|---|---|---|---|---|
| Open | rejected (same) | allowed | rejected | rejected |
| In Progress | allowed | rejected (same) | allowed (note required) | rejected |
| Resolved | rejected | allowed (reopen; note retained) | rejected (same) | allowed |
| Closed | rejected | rejected | rejected | rejected (same) |

Closed is final and read-only (status, priority and note cannot change). There is no delete.

## 7. UI-to-service call map

| Role view (demo) | Screen / widget | Service call | FR / AC |
|---|---|---|---|
| any | (startup) | `TicketService()` constructed in `app.py` once per rerun | NFR-01 |
| Employee | "Raise a ticket" form submit | `create_ticket(creator, title, description, category, priority)` | FR-01..05, 25; AC-01..11, 67 |
| Employee | "My tickets" list | `list_my_tickets(name)` | FR-26, 06; AC-66 |
| Employee | ticket details | `get_ticket(id)` (or reuse the listed object) | FR-07; AC-14, 66 |
| Engineer | filters + table | `list_tickets(status, priority, category, creator)` | FR-06, 08; AC-12, 13, 16..20, 60 |
| Engineer | details panel | `get_ticket(id)` | FR-07; AC-14 |
| Engineer | status dropdown contents | `allowed_next_statuses(current)` | FR-09, 10 |
| Engineer | "Change status" button | `change_status(id, new_status, note)` | FR-09, 10, 15; AC-21..29, 61..64 |
| Engineer | "Save note only" button | `set_resolution_note(id, note)` | FR-15; AC-36, 62 |
| Engineer | "Change priority" button | `change_priority(id, new_priority)` | FR-11; AC-30, 31, 62 |
| Manager | dashboard | `get_dashboard_stats()` | FR-16..20, 23, 24; AC-37..43, 59, 65 |

The UI may import `ticketing.config` (lists, defaults, labels, `LIMITS` for captions) and `ticketing.models` (types, errors, `format_timestamp`). The UI must not import `ticketing.db` or `sqlite3`.

## 8. Contract with the data layer

Data-layer functions are specified in `docs/data-model.md` section 9. The service is their only caller (and tests, for DB-level checks). Service responsibilities toward the DB layer: always pass trimmed, validated values; always pass the timestamps; casefold the creator key in Python (`str.casefold()`); wrap `sqlite3.Error` into `StorageError` and log it once (`logging.getLogger("ticketing")`, ID and exception class only).

## 9. Contract checklist for reviewers

- No SQL or `sqlite3` import in `app.py` or `ui/` (NFR-08, AC-57; static test in TS section 6).
- No role parameter anywhere in `service.py`.
- All limits, lists, defaults and transition rules are read from `config`, never repeated as literals in `service.py`/`ui/` (exception: DDL generation reads the same constants).
- A failing call changes nothing and returns/raises exactly one of the documented outcomes.
