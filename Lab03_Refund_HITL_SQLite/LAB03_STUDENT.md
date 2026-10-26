# PwC — Lab 03 Student Guide | Banking Refund HITL + SQLite
**Duration:** 65–75 minutes | **Independent lab** | **Environment:** VS Code + Ubuntu + Claude Code

## Learning goals
- Distinguish model suggestion, tool permission and *business authorization*.
- Create a persisted proposal through MCP; have an authenticated **human** accept, modify or reject it.
- See state transitions and audit history in SQLite; test forbidden operations.
- Work only with synthetic records, never actual payments.

## Scenario
A customer disputes TX1001 for **₹12,500** (stored as **1,250,000 paise**). The evidence indicates a duplicate settlement. Claude investigates and suggests a refund, but the business requires a human manager to decide. In this demonstration the reviewer changes the refund to **₹8,000**, and the database stores that approved amount.

## Step 1 — Prepare the standalone workspace (10 min)
1. Unzip this package. Open `Lab03_Refund_HITL_SQLite/` as the VS Code workspace.
2. Run in the Ubuntu terminal:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.init_db --reset
```
3. Create a reviewer username (e.g. `manager1`) and a **unique local passphrase of 12+ characters**. Keep it private. Do **not** give it to Claude Code. The passphrase is entered using hidden input.
4. Run baseline tests:
```bash
python -m unittest discover -s tests -v
```
Expected: **10 tests OK**.

## Step 2 — Understand the architecture (5 min)
Open `src/core.py`, `mcp_servers/refund_mcp.py`, `scripts/reviewer.py`.
The MCP server exposes read and proposal tools, **not an approval tool**. The local human reviewer console has an entirely separate authentication step.

## Step 3 — Connect the MCP server (10 min)
Make sure you are at project root with the virtual environment active:
```bash
bash scripts/register_mcp.sh
claude mcp list
claude
```
Inside Claude Code, enter `/mcp`. Confirm `refund-investigator` is connected. If prior labs have other tools, ignore or disable them for this standalone demonstration.

## Step 4 — Agent investigates and proposes (10 min)
In Claude Code, enter:
> Use ONLY refund-investigator MCP tools. Look up transaction TX1001 and check its refund policy. Explain the duplicate settlement evidence, then create a proposal for the full ₹12,500 refund. Note that the tool expects integer paise, and give me the request ID. Do not approve the refund.

Check response for `PENDING_APPROVAL`, request ID (usually 1 on a new DB), and proposed value `1250000` paise. Confirm actual `lookup_transaction`, `check_refund_policy`, `submit_refund_proposal` calls in the tool trace. If the model reports approval, challenge it using the actual request state.

## Step 5 — Demonstrate that Claude cannot approve (5 min)
> Can you approve refund request 1 yourself without any human review? Use only MCP. If you cannot, explain the missing authorization capability.

Expected: It cannot approve. No exposed MCP approval tool. **Do not** share the reviewer passphrase with Claude. It is not a legitimate way for the agent to become a reviewer.

## Step 6 — Human modifies the refund (15 min)
Open a **separate Ubuntu terminal**, outside Claude Code. Keep project venv activated:
```bash
source .venv/bin/activate
python -m scripts.reviewer
```
At prompts enter:
```text
Request ID: 1              # use actual ID returned in Step 4
Decision: MODIFY
Authorized amount in PAISE: 800000
Reason: Partial goodwill refund after manual review
Reviewer username: manager1
Reviewer passphrase: [hidden private entry]
```
Expected: database state becomes `APPROVED` with `approved_paise=800000`. Note: **no payment is issued**.

## Step 7 — Verify persistence via MCP (5 min)
Ask Claude Code:
> Using refund-investigator MCP, retrieve request 1 and its complete audit history. Compare proposal versus approved amount and identify the human reviewer.

Expected history events `PROPOSED` then `MODIFY`; proposal 1,250,000 paise; approved 800,000 paise.

## Step 8 — Explore denied scenarios (10 min)
- Propose ₹20,000 for TX1001; it must be rejected as exceeding ₹12,500.
- Propose a refund for TX1003; incomplete evidence must block it.
- Create another valid proposal for TX1002, then use human console to **REJECT**.
- Try reviewing an already approved request; it must be rejected. Instructor will demo using trusted test code.

## Expected result / deliverable
Provide screenshots of (1) MCP connection, (2) PENDING_APPROVAL, (3) human MODIFICATION, (4) approved state and audit entries, (5) rejected over-ceiling proposal.

## Reset and troubleshooting
- Reset with `python -m scripts.init_db --reset` **deletes all lab state and reviewer registration**; set up a fresh reviewer afterward.
- If `No module named mcp.server.fastmcp`, run `python -m pip install 'mcp>=1,<2'` in the correct venv. This project intentionally uses MCP 1.x.
- If MCP tool doesn't show: leave Claude Code, run `claude mcp list`, re-run `bash scripts/register_mcp.sh`, relaunch Claude Code.
- If request ID differs from 1, use the actual ID; resetting isn't required.
- Amounts are in **paise**, not rupees. ₹8,000 = 800,000 paise.
- Use only dummy credentials for training. SQLite + local CLI is a teaching pattern, **not production identity governance**.
