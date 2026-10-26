# Lab 02 Student — MCP Research + Database Operations
**Time:** 75–90 minutes. **Environment:** Ubuntu + VS Code + Claude Code. **Independent from Lab 01.**

## Objectives
1. Distinguish offline model knowledge, built-in web search, and Tavily MCP retrieval.
2. Register three independent MCP servers and inspect available tools.
3. Discover SQLite schema, inspect tickets, research software and safely update synthetic ticket data.
4. Confirm an audit entry and test a blocked write.

## Step 1 — Prepare
Open this folder in VS Code. In an Ubuntu terminal run:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.init_db --reset
python -m unittest discover -s tests -v
cp .env.example .env
nano .env
chmod 600 .env
```
Enter your own Tavily API key into `.env`. **Do not paste keys into Claude messages or Git.**

## Step 2 — Connect tools
From your ordinary Ubuntu terminal (outside Claude Code):
```bash
bash scripts/register_mcp.sh
claude
```
Inside Claude Code run `/mcp`. Verify `service-desk-reader`, `service-desk-writer`, and `tavily-research` are connected. If a tool does not appear, exit and restart Claude Code.

## Step 3 — The Tamil Nadu CM test (three conditions)
**This is a controlled retrieval demonstration, not a contest to make Claude wrong.**

A. No external retrieval: run `/clear`; temporarily disable `tavily-research` using `/mcp`, and in `.claude/settings.json` set `permissions.deny` to include `WebSearch` and `WebFetch` (create directory/file as needed). Restart Claude. Ask:
> Who is the current Chief Minister of Tamil Nadu? Answer using model knowledge only. State clearly that you did not verify this live.

B. Native web tool: keep Tavily disabled, remove the two web denials, restart Claude. Ask:
> Who is the current Chief Minister of Tamil Nadu? Verify using the built-in WebSearch tool and cite the government sources.

C. Tavily MCP: enable `tavily-research` using `/mcp`, re-add `WebSearch` and `WebFetch` denials and restart Claude. Ask:
> Who is the current Chief Minister of Tamil Nadu? Use `search_latest_information` from the Tavily MCP server (not native search). Cite live URLs and compare evidence from official sources.

For every condition, inspect the **actual tool execution trace**. A correct answer without a tool is not live verification. Do not assume the result will differ between conditions.

## Step 4 — Understand MCP tool selection
Ask:
> Discover the registered MCP servers and list their tools, explaining which ones are read-only and which writes to SQLite.

## Step 5 — Real IT operations: schema discovery
Ask:
> Use the service-desk-reader MCP server to show all tables and the most relevant columns. Do not use Bash or raw SQL.
Expected tables: `assets`, `tickets`, `ticket_audit`.

## Step 6 — Retrieve ticket
Ask:
> Through MCP, retrieve INC-1042 including the related asset version and current status. Do not guess any field.
Expected initial status `OPEN`.

## Step 7 — Live Tavily investigation
Ask:
> Use Tavily MCP to research whether the installed software category warrants an upgrade review. First read INC-1042 via MCP. Search live sources, provide URLs, and do not invent a vulnerability for our fictional ExampleSoft product. Suggest a next action, not a security verdict.
Note: the asset vendor and version are fictional: research general vendor-neutral support/security guidance. Do not claim real CVEs for fake products.

## Step 8 — Controlled SQLite update
Ask:
> Prepare a change for INC-1042: status IN_REVIEW, investigation_note "Vendor support and vulnerability review requested", change_reason "Initial triage after evidence review". Explain the proposed change and ask for my approval before using update_ticket.
Approve explicitly only after inspecting the proposed fields. Verify that `service-desk-writer` is the invoked tool.

## Step 9 — Read back and audit
Ask:
> Retrieve INC-1042 again and show ticket_audit history using read-only MCP tools. Confirm whether the change persisted and who/what is recorded.
Note: this *lab* logs change details and reason but does not establish a verified human identity.

## Step 10 — Test guardrails
Ask:
> Can you set INC-1042 straight to RESOLVED without the allowed state progression? Do not modify the database; describe why it is blocked.
Optionally use direct local tests:
```bash
python -m unittest discover -s tests -v
```

## Deliverable
Provide (1) screenshot of `/mcp` showing 3 servers, (2) Tavily CM query trace with source URLs, (3) ticket before-and-after, and (4) audit record. Never include a secret key.

## Common troubleshooting
- `ModuleNotFoundError: mcp.server.fastmcp`: verify `.venv/bin/python -m pip show mcp` shows **1.x** and pip requirements are installed in that same `.venv`.
- Tavily unavailable: check `.env`, API-key validity and internet access; run from within this project root.
- MCP servers show disconnected: restart Claude Code, check `claude mcp list`; ensure scripts are executable and project path is unchanged.
- MCP tool writes unexpectedly: switch out of auto mode (Shift+Tab), inspect `/permissions`, and enforce your own confirmation workflow. This lab does **not** claim enterprise authorization.
- After experiment, restore your preferred `WebSearch` / `WebFetch` settings (remove those deny entries).
