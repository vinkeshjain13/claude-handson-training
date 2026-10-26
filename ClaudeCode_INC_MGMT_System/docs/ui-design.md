# UI Design and Navigation

Status: DESIGN v1 (awaiting approval). Author: solution-architect, 2026-10-24. Owner of the implementation: frontend-developer (`app.py`, `ui/*`). The UI calls `TicketService` only (IC section 7); it contains no SQL and does not import `sqlite3` or `ticketing.db` (NFR-08, AC-57).

Roles are a DEMO selector, not authentication or authorization (BL-10, FR-21, NFR-12). Nothing in the UI may suggest otherwise (no "log in", "sign in", "permission denied", "secure" wording).

## 1. App shell (`app.py`, FR-21, AC-44, AC-45)

Single-page Streamlit app. Order of rendering on every run:

1. `st.set_page_config(page_title="IT Support Tickets (DEMO)", layout="wide")`.
2. Title `st.title("IT Support Ticket System")`.
3. DEMO notice: `st.warning(DEMO_NOTICE)` rendered before any role content, so it is visible on every screen of every role. Text (constant in `ui/common.py`): "DEMO ONLY: the role selector below is a demonstration switch, not authentication or access control. Anyone can pick any role. No security or privacy is provided. Do not enter confidential information."
4. Sidebar: `st.sidebar.radio("Demo role (not a login)", ["Employee", "Support Engineer", "Manager"], key="demo_role")` with the caption "Demo selector only. No authentication." Default is Employee (first option).
5. `service = TicketService()`.
6. `ROLE_VIEWS = {"Employee": employee_view.render, "Support Engineer": engineer_view.render, "Manager": manager_view.render}`; call `ROLE_VIEWS[role](service)` (AC-44).
7. Unexpected exceptions that are not `TicketError` are not caught by views; Streamlit shows its standard error box (acceptable for a demo; the service already converts `sqlite3.Error` into `StorageError`).

No SQL, no business rules, no persistence in `app.py`.

## 2. Role screens at a glance (ASM-18)

| Role | Screens | Service calls | Does NOT show |
|---|---|---|---|
| Employee | tabs "Raise a ticket", "My tickets" | `create_ticket`, `list_my_tickets`, `get_ticket` | status/priority/note controls, other people's tickets list, dashboard |
| Support Engineer | filters, ticket table, details, update panels | `list_tickets`, `get_ticket`, `allowed_next_statuses`, `change_status`, `set_resolution_note`, `change_priority` | raise-ticket form, dashboard |
| Manager | dashboard | `get_dashboard_stats` | any ticket list, any update control |

"Does not show" means the control is not rendered. It is not an access control (anyone can switch roles).

## 3. Shared UI helpers (`ui/common.py`)

| Helper | Purpose | FR / AC |
|---|---|---|
| `DEMO_NOTICE: str`, `render_demo_notice()` | notice text and renderer used by `app.py` | FR-21; AC-45 |
| `show_error(exc: TicketError)` | for `ValidationError` renders one `st.error` per `errors` entry; otherwise one `st.error(str(exc))` | FR-02; AC-03, 51 |
| `ticket_rows(tickets: list[Ticket]) -> list[dict]` | rows with columns "ID", "Title", "Creator", "Category", "Priority", "Status", "Created" (display-formatted via `format_timestamp`), in the order given (newest first) for `st.dataframe(rows, hide_index=True, use_container_width=True)` | FR-06; AC-12 |
| `render_ticket_details(ticket: Ticket)` | read-only details: ID, Title, Creator, Category, Priority, Status, Created, Updated, Description, Resolution note (empty shown as "(none)" label with empty content). Uses `st.text` / disabled `st.text_area` for user text | FR-07; AC-14, 66 |
| `flash(message)` / `show_flash()` | stores a success message in `st.session_state["flash"]` before `st.rerun()`, shows and clears it on the next run | AC-01 |
| `ticket_option_label(ticket) -> str` | label for ticket selectboxes: `f"#{id} - {title}"` (plain text) | FR-07 |

Rendering rule (FR-02, AC-06): user-supplied text (title, description, creator, note) is shown only through `st.text`, disabled `st.text_area`, `st.dataframe` cells, or selectbox option labels. Never `st.markdown`, `st.write`, `st.caption`, `st.header`/`st.subheader` or `unsafe_allow_html=True` with user text. Confirmation messages include only the integer ID.

## 4. Employee view (`ui/employee_view.py`)

```
+-- DEMO ONLY notice (warning box) ---------------------------------+
| Sidebar: (o) Employee  ( ) Support Engineer  ( ) Manager          |
+-------------------------------------------------------------------+
| [ Raise a ticket ] [ My tickets ]                                 |
|                                                                   |
| Raise a ticket                                                    |
|  Your name *       [______________________]                       |
|  Title *           [______________________]                       |
|  Description *     [______________________]                       |
|                    [______________________]                       |
|  Category *        [ Other            v ]                         |
|  Priority *        [ Medium           v ]                         |
|  [ Submit ticket ]                                                |
|  (* required)                                                     |
|  st.error: "Title is required."                                   |
+-------------------------------------------------------------------+
```

"Raise a ticket" tab (FR-01, 02, 03, 25, 05; AC-01..11, 51, 52, 67):

| Widget | Key | Details |
|---|---|---|
| `st.form` | `create_form_{nonce}` | `clear_on_submit=False`, so typed values survive a validation error (AC-52) |
| `st.text_input("Your name *")` | `create_creator_{nonce}` | label from `FIELD_LABELS` plus " *" for required |
| `st.text_input("Title *")` | `create_title_{nonce}` | no `max_chars` (VR section 1) |
| `st.text_area("Description *")` | `create_description_{nonce}` | no `max_chars` |
| `st.selectbox("Category *", config.CATEGORIES, index=<DEFAULT_CATEGORY>)` | `create_category_{nonce}` | Other preselected (AC-67) |
| `st.selectbox("Priority *", config.PRIORITIES, index=<DEFAULT_PRIORITY>)` | `create_priority_{nonce}` | Medium preselected (AC-07) |
| `st.form_submit_button("Submit ticket")` | `create_submit_{nonce}` | on click calls `service.create_ticket(...)` |

Behaviour: on `ValidationError` call `show_error`, keep the form values (no nonce change). On success: increment `st.session_state["create_nonce"]` (new widget keys give an empty form with defaults), `flash(f"Ticket #{id} was created with status Open.")`, `st.rerun()`. A repeated click creates another ticket (ASM-13, AC-10); no guard is added.

"My tickets" tab (FR-26, 06, 07; AC-66, AC-13):

| Widget | Key | Details |
|---|---|---|
| `st.text_input("Your name")` | `my_tickets_name` | caption: "Matches the name used when raising tickets (not case sensitive). This is a convenience filter, not a privacy feature." |
| `st.dataframe` | - | `ticket_rows(list_my_tickets(name))` |
| `st.selectbox("Show details for")` | `employee_selected_ticket` | options = the listed tickets (by ID) |
| details | - | `render_ticket_details` (read only, includes resolution note) |

Empty states: name blank -> `st.info("Enter your name to see your tickets.")` (service is not called); no tickets -> `st.info("No tickets found for that name.")`. `ValidationError` -> `show_error`.

## 5. Support Engineer view (`ui/engineer_view.py`)

```
+-- DEMO ONLY notice ------------------------------------------------+
| Sidebar: ( ) Employee  (o) Support Engineer  ( ) Manager           |
+--------------------------------------------------------------------+
| Filters:  Status [All v] Priority [All v] Category [All v]         |
|           Creator [______]                                         |
| Tickets (newest first)                                             |
|  ID | Title | Creator | Category | Priority | Status | Created     |
|  12 | ...                                                          |
| Select ticket: [ #12 - Printer jam            v ]                  |
| ------------------------------------------------------------------ |
| Details (read only): ID, Title, Creator, Category, Priority,       |
|   Status, Created, Updated, Description, Resolution note           |
| ------------------------------------------------------------------ |
| Update status / note            (form)                             |
|   New status [ In Progress v ]  Resolution note [ text area ]      |
|   [ Change status ] [ Save note only ]                             |
| Update priority                 (form)                             |
|   New priority [ High v ] [ Change priority ]                      |
+--------------------------------------------------------------------+
```

| Widget | Key | Details |
|---|---|---|
| Status filter `st.selectbox` | `flt_status` | options `["All", *config.STATUSES]`; "All" -> `None` |
| Priority filter | `flt_priority` | same pattern |
| Category filter | `flt_category` | same pattern |
| Creator filter `st.text_input` | `flt_creator` | blank -> `None` |
| Table | - | `ticket_rows(service.list_tickets(...))` (FR-06, AC-12) |
| Ticket selector `st.selectbox` | `engineer_selected_ticket` | options = IDs of the filtered list, label `ticket_option_label` |
| Details | - | `render_ticket_details(service.get_ticket(id))` (fresh read) |
| Status form `st.form` | `status_form_{id}_{updated_at}` | contains: `st.selectbox("New status", service.allowed_next_statuses(t.status))` key `status_new_{id}_{updated_at}`; `st.text_area("Resolution note", value=t.resolution_note)` key `status_note_{id}_{updated_at}`; submit buttons `st.form_submit_button("Change status")` and `st.form_submit_button("Save note only")` |
| Priority form `st.form` | `priority_form_{id}_{updated_at}` | `st.selectbox("New priority", config.PRIORITIES, index=<current>)` + `st.form_submit_button("Change priority")` |

Behaviour:

- "Change status" -> `change_status(id, new, note_text or None)`; "Save note only" -> `set_resolution_note(id, note_text)`; "Change priority" -> `change_priority(id, new)`. Catch `TicketError` -> `show_error`. On success `flash("Ticket #{id} updated.")` and `st.rerun()`.
- Including `updated_at` in widget keys makes the text area and dropdowns refresh with stored values after each successful update.
- Closed ticket: no forms are shown; instead `st.info("This ticket is Closed and is read-only.")` (AC-62 from the user's point of view; the service still rejects if called). If `allowed_next_statuses` is empty the status selectbox is replaced by the same message.
- Empty states: no tickets and no filter set -> `st.info("No tickets yet.")`; filters set and nothing matches -> `st.info("No matching tickets.")` (AC-13, AC-20). No selector or forms are shown when the list is empty.
- The Engineer UI only offers IDs that exist, so AC-15/AC-29 (unknown ID) are verified at service level; if a `NotFoundError` ever occurs it is shown with `show_error`.
- The "Closed" option appears only as an allowed transition from Resolved (service-provided list); no UI-side workflow logic.

## 6. Manager view (`ui/manager_view.py`, FR-16..20, 23, 24; AC-37..43, 59, 65)

```
+-- DEMO ONLY notice ------------------------------------------------+
| Sidebar: ( ) Employee  ( ) Support Engineer  (o) Manager           |
+--------------------------------------------------------------------+
| Dashboard                                   [ Refresh ]            |
| Total [ 12 ]  Open [ 3 ]  In Progress [ 4 ]  Resolved [ 3 ]  Closed [ 2 ] |
| By priority:  Low [2] Medium [5] High [3] Critical [2]   (bar chart)       |
| By category:  Hardware [4] Software [3] Network [2] Account Access [2] Other [1] (bar chart) |
| (caption "No tickets yet." when total == 0)                        |
+--------------------------------------------------------------------+
```

- `stats = service.get_dashboard_stats()` is called on every run, so data is current on each load/refresh (FR-20, AC-43). The "Refresh" `st.button` (key `dashboard_refresh`) only triggers a rerun.
- Numbers: `st.metric` per figure (always visible as numbers; charts are additional, AC-41, AC-65). Columns built with `st.columns(len(...))` from the stats dict keys, so no list is hard-coded in the UI.
- Charts: `st.bar_chart` over `stats.by_priority` and `stats.by_category` (dicts converted to a one-column dataframe/Series with the category as index, preserving config order is not required for charts).
- Empty database: all metrics show 0 and charts show zero bars or are omitted; no error (AC-42).
- Dashboard only: no ticket list and no update controls (ASM-18). No "pending" figure (ASM-22); the four status counts are shown.

## 7. Session state

| Key | Type | Used by | Purpose |
|---|---|---|---|
| `demo_role` | str | `app.py` (radio key) | selected demo role |
| `create_nonce` | int (default 0) | Employee form | bumping it creates fresh empty form widgets after a successful submit |
| `flash` | str or absent | all views | one-shot success message across `st.rerun()` |
| `my_tickets_name` | str | Employee | name typed for "My tickets" |
| `employee_selected_ticket`, `engineer_selected_ticket` | int | views | selected ticket |
| `flt_status`, `flt_priority`, `flt_category`, `flt_creator` | str | Engineer | filters |

Session state is UI convenience only. It holds no tickets and no authoritative data; the database is the only store (NFR-01). Closing the browser loses session state but not tickets (AC-48).

## 8. Error display and usability (NFR-03, AC-51, AC-52)

- Required fields are marked with " *" in the label and a caption "* required".
- Validation errors: `st.error` with the service message (names the field, mentions the limit or the allowed values).
- `TicketStateError`, `NotFoundError`, `StorageError`: `st.error(str(exc))`.
- Success: `st.success` (via flash) naming the ticket ID.
- The Employee form does not clear on error (AC-52).

## 9. Out of scope for the UI

Login screens, per-role permissions, search box, pagination, ticket editing of title/description/category, delete, export, attachments, notifications, history view, manager ticket list, multipage navigation, custom CSS/theming.

## 10. Browser support (NFR-02, ASM-12)

Streamlit served on localhost, verified manually in current Chrome, Firefox and Edge (AC-49, manual checklist in TS section 7). No client software.
