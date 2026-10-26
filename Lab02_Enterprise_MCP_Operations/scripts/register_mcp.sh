#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="$(pwd)/.venv/bin/python"
if [[ ! -x "$PY" ]]; then echo 'First create .venv and install dependencies.'; exit 1; fi
# These are local-scope connections. Run from an ordinary terminal (outside Claude Code).
claude mcp add --transport stdio service-desk-reader -- "$PY" -m mcp_servers.reader
claude mcp add --transport stdio service-desk-writer -- "$PY" -m mcp_servers.writer
# Tavily key is loaded into the process by this wrapper, never put on a command line.
claude mcp add --transport stdio tavily-research -- bash "$(pwd)/scripts/run_research.sh"
claude mcp list
