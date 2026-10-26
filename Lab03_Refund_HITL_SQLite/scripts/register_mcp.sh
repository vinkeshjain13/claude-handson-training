#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then echo 'Create .venv and install dependencies first' >&2; exit 1; fi
claude mcp remove refund-investigator -s local 2>/dev/null || true
claude mcp add --transport stdio refund-investigator -- "$(pwd)/.venv/bin/python" -m mcp_servers.refund_mcp
claude mcp list
