# Lab 01 — Claude Code Custom Subagents (60 minutes)
## Business task
A fictional payment gateway has intermittent charge failures after a recent deployment. Use **three specialized Claude Code subagents** to investigate independently, then consolidate an evidence-backed Root Cause Analysis (RCA). Do not modify any files.

## Step 1 — Verify project (5 min)
Open this lab folder in VS Code (Ubuntu terminal). Run:
```bash
pwd
ls .claude/agents
python3 -m unittest discover -s tests -v
```
Confirm three definitions and fixture tests pass.

## Step 2 — Inspect and personalize subagents (15 min)
Open `.claude/agents/log-analyst.md`, `infrastructure-analyst.md`, and `security-analyst.md`. For each, identify YAML name, description, allowed tools and body instructions. **Student task:** Add one relevant analysis instruction in each body (do not grant Write, Edit, or Bash permissions). Save, then restart Claude Code if already running so definitions reload.

## Step 3 — Invoke individually (15 min)
Start `claude` from this project root. Enter these prompts separately:

**Prompt A:**
> Use the **log-analyst** subagent to investigate INC-2026-104 using the application log. Return first error time, affected endpoints, error types, citations and an uncertainty note. Read-only; no edits.

**Prompt B:**
> Delegate to **infrastructure-analyst**: compare pre/post-deployment metrics and release details. Give a causal hypothesis backed by precise timestamps and data fields. No file modifications.

**Prompt C:**
> Delegate to **security-analyst**: assess security alerts and whether evidence supports a security-caused outage. Provide indicators, limitations and independent security follow-ups. Read-only.

**Verification:** Confirm you see **named subagent execution** (not merely Claude reading the markdown files). If unavailable, record this as a blocker rather than claiming success.

## Step 4 — Main-agent orchestration (10 min)
> You are Incident Commander for INC-2026-104. Invoke the log-analyst, infrastructure-analyst and security-analyst subagents for independent investigations. Consolidate their findings. Clearly identify primary hypothesis, contributing factors, rejected explanations and confidence. Cite evidence by file and timestamp/field. Produce an incident timeline and operator-approval-only recovery steps. Do not modify project files or any system.

If the runtime cannot delegate all three at once, run sequentially and request consolidation. Parallel execution is not a required learning outcome.

## Step 5 — Deliver report (10 min)
Ask Claude to **display** a report in chat with sections: Executive Summary; Timeline; Observations; Root Cause Hypothesis; Alternate Explanations; Risk; Recovery Recommendations (human approval required); Preventive Actions; Evidence Index. Do not ask Claude to write into `reports/` (agents are read-only).

## Step 6 — Verification & submission (5 min)
- Confirm three named subagent calls appear in execution activity.
- Verify each conclusion has evidence and distinguishes hypothesis from established fact.
- Confirm no incident files changed; if Git is initialized, check `git diff` against a baseline.
- Submit screenshot(s) of delegation plus RCA text and one paragraph explaining **subagent vs. MCP tool**.

**Stretch:** Ask the main agent to reconcile what might look like conflicting security and infrastructure evidence without asserting causality from coincidence.
