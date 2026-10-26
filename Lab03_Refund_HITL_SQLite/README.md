# Lab 03: Human-in-the-Loop Banking Refund Approval
Independent from Labs 01/02. Requires Ubuntu, VS Code, Python, Claude Code and MCP 1.x.

Quick start:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.init_db --reset
python -m unittest discover -s tests -v
bash scripts/register_mcp.sh
claude
```
**Run the human reviewer in a separate terminal, not through Claude Code.**
Credentials are hashed in local SQLite, never entered into Claude. You must use `--reset` only when willing to delete local demo state.

MCP only exposes lookup/policy/propose/read tools. There is deliberately no `approve_refund` MCP tool.
No payment is ever executed.
