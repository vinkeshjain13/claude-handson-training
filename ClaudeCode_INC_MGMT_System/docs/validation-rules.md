# Validation Rules

Status: DESIGN v1 (awaiting approval). Author: solution-architect, 2026-10-24. Limits and lists come from `ticketing/config.py` (unapproved: ASM-03, ASM-16, ASM-19). Error classes and message templates are in `docs/interface-contracts.md` (IC) sections 4 and 5.

## 1. Where validation is enforced

| Layer | Role | Notes |
|---|---|---|
| Service (`ticketing/service.py`) | The ONLY validation gate. Trims, checks required/length/allowed values, applies the status workflow. | FR-02, FR-10, FR-15; NFR-06, NFR-07 |
| Database (`CHECK` constraints) | Defence in depth for enum values and non-blank text; a violation would surface as `StorageError`, never as an expected user message. | DM section 2 |
| UI (Streamlit) | Does not validate. It renders widgets with the allowed lists (selectbox) and shows the service's messages. It must NOT set `max_chars` on text widgets, otherwise over-limit input could never reach the service and AC-05 could not be demonstrated. | FR-02, AC-05, AC-51 |

## 2. Field table (create ticket, FR-01/02)

Trimming: `str.strip()` on every text input before validation and storage; whitespace-only counts as empty (AC-04). Internal whitespace and line breaks are kept. Length counts Python characters (code points) after trimming.

| Field | Required | Min | Max | Allowed values | Special characters | Error key (`ValidationError.errors`) | Requirements / ACs |
|---|---|---|---|---|---|---|---|
| `creator` ("Your name") | yes | 1 | 100 | any text | stored literally | `creator` | FR-01, 02; AC-03, 04, 05, 06 |
| `title` | yes | 1 | 100 | any text | stored literally | `title` | FR-01, 02; AC-03, 04, 05, 06 |
| `description` | yes | 1 | 2000 | any text; line breaks allowed | stored literally | `description` | FR-01, 02; AC-03, 04, 05, 06 |
| `category` | yes | - | - | one of `config.CATEGORIES`; exact, case-sensitive; default (UI only) Other | n/a | `category` | FR-25, 02; AC-67 |
| `priority` | yes | - | - | one of `config.PRIORITIES`; exact, case-sensitive; default (UI only) Medium | n/a | `priority` | FR-03; AC-07, 08 |

Boundary behaviour (AC-05): exactly the limit is accepted; limit + 1 is rejected with a message containing the limit number. Trailing/leading spaces do not count toward the limit (a 100-character title with surrounding spaces is accepted).

## 3. Field table (update operations)

| Input | Operation | Required | Rule | Error | Requirements / ACs |
|---|---|---|---|---|---|
| `ticket_id` | all single-ticket calls | yes | `int` (not `bool`) | `ValidationError["ticket_id"]`; unknown ID -> `NotFoundError` | FR-07; AC-15, 29 |
| `new_status` | `change_status` | yes | one of `config.STATUSES` (else `ValidationError["status"]`); then must be in `TRANSITIONS[current]` (else `TicketStateError`), which also rejects same-status and any change from Closed | as stated | FR-09, 10; AC-21..28, 61, 62, 63 |
| `resolution_note` (in `change_status`) | `change_status` | only when moving to Resolved and no stored note exists (ASM-21) | blank = not supplied; non-blank must be <= 1000 characters | `ValidationError["resolution_note"]` | FR-15; AC-22, 64 |
| `note` | `set_resolution_note` | yes | 1..1000 characters after trimming; line breaks allowed; special characters literal; not allowed on Closed (`TicketStateError`) | `ValidationError["resolution_note"]` | FR-15; AC-36, 62 |
| `new_priority` | `change_priority` | yes | one of `config.PRIORITIES` (else `ValidationError["priority"]`); not equal to current (else `TicketStateError`, ASM-24); not on Closed | as stated | FR-11; AC-30, 31, 62 |
| filter `status`/`priority`/`category` | `list_tickets` | no | `None` or blank = no filter; otherwise must be in the list | `ValidationError[...]` | FR-08; AC-16, 17, 18, 60 |
| filter `creator` | `list_tickets` | no | `None` or blank = no filter; otherwise trimmed, casefolded exact match | none | FR-08; AC-19 |
| `creator_name` | `list_my_tickets` | yes | blank rejected (never means "all") | `ValidationError["creator"]` | FR-26; AC-66 |

System-set values (`id`, `status` at creation, `created_at`, `updated_at`) are never accepted from the caller (FR-04, FR-05, FR-13).

## 4. Message examples

| Case | Example message | Requirement |
|---|---|---|
| Empty title | `Title is required.` | AC-03 |
| 101-character title | `Title must be at most 100 characters (you entered 101).` | AC-05 |
| Priority "Urgent" | `Priority must be one of: Low, Medium, High, Critical.` | AC-08 |
| Category "Printers" | `Category must be one of: Hardware, Software, Network, Account Access, Other.` | AC-67 |
| Open -> Resolved | `Cannot change status from Open to Resolved. Allowed: In Progress.` | AC-25 |
| Resolved without a note | `Resolution note is required to set a ticket to Resolved.` | AC-64 |
| Change on Closed | `Ticket 7 is Closed and cannot be changed.` | AC-62 |
| Same priority | `Priority is already High.` | AC-31 |
| Unknown ID | `Ticket 999 was not found.` | AC-15, 29 |

## 5. Special characters and safe rendering (FR-02, AC-06, AC-36)

- Accepted and stored exactly as typed (after trimming): quotes, semicolons, angle brackets, HTML/markup, SQL-looking text, unicode and emoji, line breaks (description and note; for other fields they are stored if supplied).
- Never interpreted: SQL values are bound as parameters (NFR-08); the UI shows user text only via `st.text`, a disabled `st.text_area`, or `st.dataframe`, never `st.markdown`, `st.write`, `st.header`/`st.subheader` with user text, or `unsafe_allow_html=True`. Messages never echo user input (IC section 4).
- The only text rejected for its content is text that cannot be encoded as UTF-8 (for example a lone surrogate), with `"{Label} contains characters that cannot be stored."`
- No claim is made that this is a security control (NFR-08, NFR-12).

## 6. Rejected operations leave data unchanged (NFR-06, AC-55)

Validation runs before any write. State checks run inside the write transaction before the `UPDATE`. Any exception rolls the transaction back. A rejected call therefore never alters any column, including `updated_at`.
