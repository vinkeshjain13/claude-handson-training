# Data Model and SQLite Schema

Status: DESIGN v1 (awaiting approval). Author: solution-architect, 2026-10-24. Companion of `docs/architecture.md` (ARCH). Specification only; the DDL below is implemented by backend-developer in `ticketing/db.py`.

## 1. Scope

One table, `tickets` (BL-06, BL-09, NFR-01). No other tables.

- Audit/history: none (status history was retired: FR-14, ASM-09). `created_at` and `updated_at` are the only time information.
- Seed data: none. The database starts empty and every view must work empty (FR-20, AC-13, AC-42). Tests create their own data.
- Foreign keys: none (no employee, category or user tables: ASM-02, ASM-19 use fixed lists in config).
- Roles are not stored (BL-10).

## 2. DDL (specification)

The value lists inside the `CHECK` clauses are generated at schema-creation time from `ticketing/config.py` (`STATUSES`, `PRIORITIES`, `CATEGORIES`), so the lists exist in one place. The generated text for the default lists is:

```sql
CREATE TABLE IF NOT EXISTS tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    description     TEXT    NOT NULL CHECK (length(trim(description)) > 0),
    category        TEXT    NOT NULL
                    CHECK (category IN ('Hardware','Software','Network','Account Access','Other')),
    priority        TEXT    NOT NULL DEFAULT 'Medium'
                    CHECK (priority IN ('Low','Medium','High','Critical')),
    status          TEXT    NOT NULL DEFAULT 'Open'
                    CHECK (status IN ('Open','In Progress','Resolved','Closed')),
    creator         TEXT    NOT NULL CHECK (length(trim(creator)) > 0),
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    resolution_note TEXT    NOT NULL DEFAULT ''
);
```

Notes on the DDL:

- Column order follows BL-06.
- The `trim()` checks are defence in depth only: SQLite `trim()` strips spaces but not tabs/newlines, so the service remains the real gate (VR).
- No length limits in the DDL: limits live only in `config.LIMITS` and are enforced by the service (ASM-03 is changeable in one place).
- `category` has no DEFAULT in the table; the service requires an explicit value (FR-25; the UI preselects Other). `priority` and `status` defaults are safety nets; the service always passes them explicitly (FR-05 status Open, FR-03 priority).
- No UNIQUE constraint beyond the primary key: duplicate tickets are allowed (ASM-13, AC-10).
- No `CHECK (updated_at >= created_at)`: a system clock change must not make updates fail (risk R6).
- The DDL string is the only SQL not using bound parameters; it contains only `config` constants, never user input. Statements are executed with `execute`, one per call (no `executescript` with interpolated text).
- No `PRAGMA` is required. `connect()` sets `timeout=5.0` (busy timeout), `row_factory = sqlite3.Row`, `isolation_level = None` (explicit `BEGIN`), and registers `casefold(text)`.

## 3. Columns

| Column | Type | Null | Default | Constraint | Set by | Requirement |
|---|---|---|---|---|---|---|
| `id` | INTEGER | no | autoincrement | PRIMARY KEY AUTOINCREMENT | database | FR-04, FR-07 |
| `title` | TEXT | no | - | not blank | user, trimmed by service | FR-01, FR-02 |
| `description` | TEXT | no | - | not blank; may contain line breaks | user, trimmed | FR-01, FR-02 |
| `category` | TEXT | no | - | IN category list; never updated | user at creation | FR-25, FR-24 |
| `priority` | TEXT | no | `'Medium'` | IN priority list | user at creation; engineer later | FR-03, FR-11 |
| `status` | TEXT | no | `'Open'` | IN status list | service (`'Open'` at creation; transitions later) | FR-05, FR-09, FR-10 |
| `creator` | TEXT | no | - | not blank | user, trimmed | FR-01, FR-26 |
| `created_at` | TEXT | no | - | - | service clock | FR-04 |
| `updated_at` | TEXT | no | - | - | service clock | FR-13 |
| `resolution_note` | TEXT | no | `''` | empty string means "none" | engineer, trimmed | FR-15, FR-07 |

## 4. Enumerations

Defined once in `ticketing/config.py` and echoed in the `CHECK` clauses.

| Enum | Values (order is display order) | Source |
|---|---|---|
| Status | Open, In Progress, Resolved, Closed | BL-07 |
| Priority | Low, Medium, High, Critical | BL-08 |
| Category | Hardware, Software, Network, Account Access, Other | ASM-19 (unapproved) |

Status workflow: see `docs/interface-contracts.md` (IC) section 6. It is not in the schema; the DB accepts any valid status value and the service enforces transitions (FR-10).

## 5. ID strategy (FR-04)

`INTEGER PRIMARY KEY AUTOINCREMENT`. SQLite's AUTOINCREMENT guarantees an ID is never reused, even if rows were ever deleted, and IDs increase over time (AC-09). The UI shows the plain integer (for example `#12`). No delete exists in the MVP anyway.

## 6. Timestamp format and `updated_at` maintenance (FR-13, ASM-15)

- Stored: local system time as text `YYYY-MM-DD HH:MM:SS` (`config.STORE_TS_FORMAT`). Fixed-width text sorts chronologically.
- Displayed: `YYYY-MM-DD HH:MM` (`config.DISPLAY_TS_FORMAT`, via `models.format_timestamp`).
- Created: service reads its `clock()` once and writes the same text to `created_at` and `updated_at` (AC-33: equal on creation).
- Updated: every successful `change_status`, `change_priority` and `set_resolution_note` sets `updated_at = clock()` in the same `UPDATE` statement that changes the field, inside the same transaction. A rejected operation performs no `UPDATE`, so `updated_at` is unchanged (AC-33, AC-55).
- No database trigger (kept in one place, the service/db function pair, so it is testable with an injected clock).

## 7. Indexes

None beyond the primary key. Justification: NFR-05 and ASM-11 assume about 1,000 tickets; full scans of that size take milliseconds, and the ordering `ORDER BY id DESC` uses the primary key. If AC-54 measurement fails, add `idx_tickets_status`, `idx_tickets_priority`, `idx_tickets_category` (the counts and filters) and re-measure. Not added now to avoid unjustified complexity.

## 8. Schema creation and evolution

- `db.init_schema(db_path)` runs the generated `CREATE TABLE IF NOT EXISTS` and creates the parent directory of the file. Called from `TicketService.__init__`; idempotent.
- No migrations. If the DDL or the `config` lists change, delete the database file (classroom data only) so it is recreated (risk R2).
- Backup/retention: none; "permanent" means local-file persistence (ASM-14, RISK-05).

## 9. Data-layer function contract (`ticketing/db.py`)

All functions are synchronous, take an open connection except where noted, use static SQL strings with `?` placeholders only, return plain Python values, and raise only `sqlite3.Error` (the service translates). The data layer contains no validation or workflow rules.

| Function | Signature | Behaviour | SQL (specification) |
|---|---|---|---|
| `connect` | `connect(db_path: str \| Path) -> sqlite3.Connection` | Opens a connection with the settings in section 2. Does not create tables. | n/a |
| `session` | `session(db_path, write: bool = False)` context manager yielding a connection | `write=True` runs `BEGIN IMMEDIATE`, commits on normal exit, rolls back on any exception; `write=False` runs `BEGIN` (consistent read snapshot) and always ends with rollback/commit. Always closes the connection. | `BEGIN IMMEDIATE` / `BEGIN` |
| `init_schema` | `init_schema(db_path) -> None` | Creates the parent directory and the table. | DDL in section 2 |
| `insert_ticket` | `insert_ticket(conn, *, title, description, category, priority, status, creator, created_at, updated_at) -> int` | Inserts one row and returns the new ID. | `INSERT INTO tickets (title, description, category, priority, status, creator, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)` (resolution_note uses its default) |
| `fetch_ticket` | `fetch_ticket(conn, ticket_id: int) -> dict \| None` | One row as a dict with all ten columns, or `None`. | `SELECT * FROM tickets WHERE id = ?` (the implementation should list the ten columns explicitly) |
| `select_tickets` | `select_tickets(conn, *, status=None, priority=None, category=None, creator_key=None) -> list[dict]` | Rows ordered newest first; each `None` filter is ignored; filters combine with AND. `creator_key` must already be case-folded by the caller. | `SELECT ... FROM tickets WHERE (? IS NULL OR status = ?) AND (? IS NULL OR priority = ?) AND (? IS NULL OR category = ?) AND (? IS NULL OR casefold(creator) = ?) ORDER BY id DESC` (each value bound twice) |
| `update_ticket` | `update_ticket(conn, ticket_id: int, *, updated_at: str, status=None, priority=None, resolution_note=None) -> int` | Sets only the non-`None` fields plus `updated_at`; returns affected row count (0 if the ID is missing). | `UPDATE tickets SET status = COALESCE(?, status), priority = COALESCE(?, priority), resolution_note = COALESCE(?, resolution_note), updated_at = ? WHERE id = ?` |
| `count_by` | `count_by(conn, column: str) -> dict[str, int]` | `column` must be one of `"status"`, `"priority"`, `"category"` (looked up in a dict of three fixed statements; anything else raises `ValueError`; the column name is never concatenated into SQL). Returns only values that occur. | `SELECT status, COUNT(*) FROM tickets GROUP BY status` (and the two analogues) |
| `count_all` | `count_all(conn) -> int` | Total rows. | `SELECT COUNT(*) FROM tickets` |

Mapping to requirements: `insert_ticket` FR-01/04/05; `fetch_ticket` FR-07; `select_tickets` FR-06/08/26; `update_ticket` FR-09/11/13/15; `count_by`, `count_all` FR-16/18/19/20/23/24; `session` NFR-06; `init_schema`/`connect` NFR-01; all NFR-08.
