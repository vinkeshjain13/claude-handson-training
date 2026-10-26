#!/usr/bin/env bash
set -euo pipefail
python -m pytest -q
python -m src.main
cat reports/summary.json
