# Lab 02 — Enterprise Operations Agent using MCP

Independent Ubuntu + VS Code project. No Lab 01 files needed. All records are synthetic. Requires Claude Code, Python 3.10+, Tavily API key for the live research exercise.

## Quick start (ordinary Ubuntu terminal)
```bash
cd Lab02_Enterprise_MCP_Operations
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.init_db --reset
python -m unittest discover -s tests -v
python -m scripts.smoke_test
cp .env.example .env
nano .env  # add TAVILY_API_KEY, save
chmod 600 .env
bash scripts/register_mcp.sh
claude
```
In Claude Code run `/mcp` and check all three servers. Configuration affects this workspace's local Claude Code MCP registrations; you can remove any using `claude mcp remove <name>` from a terminal.

**Special note:** `mcp>=1.9,<2` is deliberate; installed MCP 2.x may not expose `mcp.server.fastmcp`.

See `LAB02_STUDENT.md` for guided exercises. See instructor pack for answer key.
