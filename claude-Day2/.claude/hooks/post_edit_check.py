#!/usr/bin/env python3
"""TicketOps PostToolUse hook: log Python file edits and run checks."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys


def main():
    try:
        event = json.load(sys.stdin)
    except (ValueError, TypeError) as exc:
        print(f"Hook input is not valid JSON: {exc}", file=sys.stderr)
        return 1

    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".").resolve()
    file_name = (event.get("tool_input") or {}).get("file_path")
    if not isinstance(file_name, str) or not file_name:
        return 0

    target = Path(file_name)
    if not target.is_absolute():
        target = project / target
    try:
        relative = target.resolve().relative_to(project)
    except ValueError:
        return 0  # Ignore files outside TicketOps.

    if not relative.parts or relative.parts[0] not in {"app", "tests"} or relative.suffix != ".py":
        return 0  # Only validate Python source and tests.

    checks = [
        ("syntax", [sys.executable, "-m", "compileall", "-q", "app", "tests"]),
        ("unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ]
    outcomes = {}
    for name, command in checks:
        try:
            completed = subprocess.run(command, cwd=project, text=True,
                                       capture_output=True, timeout=35, check=False)
            outcomes[name] = {
                "passed": completed.returncode == 0,
                "exit_code": completed.returncode,
                "output_tail": (completed.stdout + completed.stderr)[-1200:],
            }
        except subprocess.TimeoutExpired:
            outcomes[name] = {"passed": False, "exit_code": None,
                              "output_tail": "Check exceeded the 35-second timeout."}
        if not outcomes[name]["passed"]:
            break

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "session_id": event.get("session_id", "unknown"),
        "event": event.get("hook_event_name", "PostToolUse"),
        "tool": event.get("tool_name", "unknown"),
        "file": relative.as_posix(),
        "checks": outcomes,
        "overall": "PASS" if all(x["passed"] for x in outcomes.values()) else "FAIL",
    }
    log_path = project / "logs" / "hook_events.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")

    if record["overall"] == "FAIL":
        failure = next((key for key, value in outcomes.items() if not value["passed"]), "unknown")
        print(f"TicketOps PostToolUse check FAILED ({failure}) after editing {relative}", file=sys.stderr)
        print(outcomes[failure]["output_tail"][-900:], file=sys.stderr)
        return 2  # PostToolUse feedback; it does not undo the edit.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())