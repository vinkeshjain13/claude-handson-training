"""L4 static / code-rule checks (no browser, no database).

Covers AC-57 (NFR-08), AC-58 (NFR-09), AC-69 (NFR-10), AC-68 (NFR-12, README part), AC-70 (NFR-11),
AC-45 (DEMO notice text), AC-81 (FR-27 no backend capability), AC-56 and FR-21.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers import REPO_ROOT
from ticketing.service import TicketService

APP_FILES = sorted((REPO_ROOT / "app").glob("*.py"))
TICKETING_FILES = sorted((REPO_ROOT / "ticketing").glob("*.py"))
SQL_WORDS = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|PRAGMA|WHERE|FROM|VALUES)\b"
)
NEGATION = re.compile(r"\b(not|no|nor|without|never)\b", re.IGNORECASE)


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def string_constants(path: Path) -> list[str]:
    out = []
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
    return out


def imported_modules(path: Path) -> set[str]:
    mods = set()
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Import):
            mods.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
            mods.update(f"{node.module}.{alias.name}" for alias in node.names)
    return mods


def test_code_rules_sources_were_found():
    """Sanity: the scans below actually see the code base."""
    assert {p.name for p in APP_FILES} >= {"main.py", "common.py", "employee_view.py"}
    assert {p.name for p in TICKETING_FILES} >= {"config.py", "db.py", "models.py", "service.py"}


# ------------------------------------------------------------------ AC-57 / NFR-08 ---------


@pytest.mark.parametrize("path", APP_FILES, ids=lambda p: p.name)
def test_ac57_nfr08_ui_does_not_import_sqlite3_or_the_db_layer(path):
    """AC-57 / NFR-08: no sqlite3 / ticketing.db import in app/."""
    mods = imported_modules(path)
    assert not {m for m in mods if m == "sqlite3" or m.startswith("sqlite3.")}
    assert not {m for m in mods if m == "ticketing.db" or m.startswith("ticketing.db.")}
    source = path.read_text(encoding="utf-8")
    assert "sqlite3" not in source


@pytest.mark.parametrize("path", APP_FILES, ids=lambda p: p.name)
def test_ac57_nfr08_ui_contains_no_sql_keywords_in_string_literals(path):
    """AC-57 / NFR-08: no SQL statement text (upper-case keywords) anywhere in app/ strings."""
    offenders = [s for s in string_constants(path) if SQL_WORDS.search(s)]
    assert offenders == []


@pytest.mark.parametrize("path", APP_FILES, ids=lambda p: p.name)
def test_ac57_nfr08_ui_never_calls_execute_or_cursor(path):
    """AC-57: no .execute/.executemany/.cursor calls in app/."""
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"execute", "executemany", "executescript", "cursor"}


def _execute_calls(path: Path):
    for func in ast.walk(parse(path)):
        if isinstance(func, ast.FunctionDef):
            for node in ast.walk(func):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"execute", "executemany", "executescript"}
                ):
                    yield func.name, node


def test_ac57_nfr08_sql_only_executed_in_db_layer():
    """AC-57 / NFR-08: no .execute* call in service/config/models."""
    for name in ("service.py", "config.py", "models.py", "__init__.py"):
        assert list(_execute_calls(REPO_ROOT / "ticketing" / name)) == []


def test_ac57_nfr08_db_statements_are_static_with_question_mark_placeholders():
    """AC-57 / NFR-08: every execute() takes a constant string (or the fixed DDL/lookup),
    never an f-string, concatenation, % or .format; ? count equals the bound-parameter count."""
    path = REPO_ROOT / "ticketing" / "db.py"
    calls = list(_execute_calls(path))
    assert len(calls) >= 8
    for func_name, call in calls:
        arg = call.args[0]
        allowed = (
            isinstance(arg, ast.Constant)
            or (
                isinstance(arg, ast.IfExp)
                and isinstance(arg.body, ast.Constant)
                and isinstance(arg.orelse, ast.Constant)
            )
            or (isinstance(arg, ast.Call) and getattr(arg.func, "id", "") == "_build_ddl")
            or (isinstance(arg, ast.Name) and arg.id == "sql" and func_name == "count_by")
        )
        assert allowed, f"{func_name}: non-constant SQL argument {ast.dump(arg)[:80]}"
        if isinstance(arg, ast.Constant) and len(call.args) > 1:
            params = call.args[1]
            if isinstance(params, ast.Tuple):
                assert arg.value.count("?") == len(params.elts), f"{func_name}: ? count mismatch"
        if isinstance(arg, ast.Constant) and SQL_WORDS.search(arg.value):
            assert not re.search(r"%[sd(]|\{\}|\{[a-z_]+\}", arg.value), func_name


def test_ac57_nfr08_db_module_builds_no_sql_with_fstrings_or_format_or_percent():
    """AC-57 / NFR-08: outside the DDL builder, no f-string / .format / % / + near SQL text."""
    path = REPO_ROOT / "ticketing" / "db.py"
    tree = parse(path)
    allowed_funcs = {"_build_ddl", "_sql_list"}
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if func.name in allowed_funcs:
            continue
        for node in ast.walk(func):
            assert not isinstance(node, ast.JoinedStr), f"f-string in {func.name}"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "format", f".format in {func.name}"
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod | ast.Add):
                for side in (node.left, node.right):
                    if isinstance(side, ast.Constant) and isinstance(side.value, str):
                        assert not SQL_WORDS.search(side.value), f"string math in {func.name}"


def test_ac57_nfr08_ddl_is_generated_only_from_config_constants():
    """AC-57 / NFR-08 (DM section 2): _sql_list is only called with config.<CONSTANT>."""
    tree = parse(REPO_ROOT / "ticketing" / "db.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_sql_list":
            (arg,) = node.args
            assert isinstance(arg, ast.Attribute)
            assert getattr(arg.value, "id", "") == "config" and arg.attr.isupper()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_ddl":
            assert node.args.args == []  # takes no input at all


def test_ac57_nfr08_service_imports_sqlite3_only_for_error_handling():
    """AC-57 / NFR-08: service.py uses sqlite3 only as sqlite3.Error / type hints."""
    tree = parse(REPO_ROOT / "ticketing" / "service.py")
    used = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "sqlite3"
    }
    assert used <= {"Error", "Connection"}


@pytest.mark.parametrize("path", TICKETING_FILES, ids=lambda p: p.name)
def test_ac57_nfr08_ticketing_does_not_import_streamlit(path):
    """AC-57 / IC section 7: the backend has no Streamlit dependency."""
    assert not {m for m in imported_modules(path) if m.split(".")[0] == "streamlit"}


def test_ac57_ic1_service_has_no_role_concept():
    """IC section 1 / FR-21: no service method takes a role/user/permission argument."""
    tree = parse(REPO_ROOT / "ticketing" / "service.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args + node.args.kwonlyargs:
                assert not re.search(r"role|user|permission|auth", arg.arg, re.IGNORECASE)


# ----------------------------------------------------------------- AC-81 / FR-27 ----------


def test_ac81_fr27_service_offers_no_search_operation():
    """AC-81 / FR-27: the public service interface is exactly S1..S9, no search method."""
    public = {n for n in dir(TicketService) if not n.startswith("_")}
    assert public == {
        "create_ticket",
        "get_ticket",
        "list_tickets",
        "list_my_tickets",
        "change_status",
        "change_priority",
        "set_resolution_note",
        "get_dashboard_stats",
        "allowed_next_statuses",
    }
    assert not any("search" in n for n in public)


def test_ac81_fr27_search_runs_in_ui_layer_on_already_returned_tickets():
    """AC-81 / FR-27: search_tickets lives in app/common.py, takes tickets, builds no SQL."""
    path = REPO_ROOT / "app" / "common.py"
    tree = parse(path)
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "search_tickets" in funcs
    assert [a.arg for a in funcs["search_tickets"].args.args] == ["tickets", "query"]
    segment = ast.get_source_segment(path.read_text(encoding="utf-8"), funcs["search_tickets"])
    assert "execute" not in segment and "sqlite" not in segment and "service" not in segment
    assert not any("search" in p.name for p in (REPO_ROOT / "ticketing").glob("*.py"))
    assert "search" not in (REPO_ROOT / "ticketing" / "db.py").read_text().lower()
    assert "search" not in (REPO_ROOT / "ticketing" / "service.py").read_text().lower()


# --------------------------------------------------------------------- AC-58 / NFR-09 -----

NETWORK_MODULES = {
    "requests", "urllib", "urllib3", "http", "socket", "boto3", "botocore", "smtplib",
    "ftplib", "httpx", "aiohttp", "paramiko", "telnetlib", "xmlrpc", "azure", "google",
    "pymysql", "psycopg2", "pymongo", "redis",
}  # fmt: skip


@pytest.mark.parametrize(
    "path", APP_FILES + TICKETING_FILES, ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_ac58_nfr09_no_network_or_cloud_imports(path):
    """AC-58 / NFR-09: no network/cloud/remote-DB libraries imported by application code."""
    roots = {m.split(".")[0] for m in imported_modules(path)}
    assert roots & NETWORK_MODULES == set()


@pytest.mark.parametrize(
    "path", APP_FILES + TICKETING_FILES, ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_ac58_nfr09_no_urls_in_application_string_literals(path):
    """AC-58 / NFR-09: no http(s):// endpoints in code strings."""
    assert [s for s in string_constants(path) if re.search(r"https?://", s)] == []


def test_ac58_nfr09_streamlit_usage_statistics_are_disabled_and_server_is_local():
    """AC-58 / NFR-09: .streamlit/config.toml disables telemetry and binds to localhost."""
    text = (REPO_ROOT / ".streamlit" / "config.toml").read_text()
    assert re.search(r"^\s*gatherUsageStats\s*=\s*false\s*$", text, re.MULTILINE)
    assert re.search(r'^\s*address\s*=\s*"localhost"\s*$', text, re.MULTILINE)


SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bsk-[A-Za-z0-9]{20,}",
    r"ghp_[A-Za-z0-9]{30,}",
    r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|token)\b\s*[:=]\s*[\"'][^\"']+[\"']",
    r"(?i)(postgres|mysql|mongodb|redis)://",
]


def test_ac58_nfr09_no_secret_like_strings_in_source_config_and_readme():
    """AC-58 / NFR-09: no credentials/keys in application source, config, README or requirements."""
    files = [*APP_FILES, *TICKETING_FILES, REPO_ROOT / "README.md", REPO_ROOT / "requirements.txt",
             REPO_ROOT / "ruff.toml", REPO_ROOT / ".streamlit" / "config.toml"]  # fmt: skip
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            assert not re.search(pattern, text), f"{path.name}: matches {pattern}"


def test_ac58_nfr09_no_env_key_or_credential_files_in_repository():
    """AC-58 / NFR-09: no .env / key / credential files outside .venv, .git and caches."""
    skip = {".venv", ".git", ".ruff_cache", ".pytest_cache", "__pycache__", "data"}
    bad = []
    for path in REPO_ROOT.rglob("*"):
        if any(part in skip for part in path.relative_to(REPO_ROOT).parts):
            continue
        name = path.name.lower()
        if path.is_file() and (
            name == ".env"
            or name.startswith(".env.")
            or name.endswith((".pem", ".key", ".p12", ".pfx"))
            or name in {"credentials.json", "secrets.toml", "id_rsa", "id_ed25519"}
        ):
            bad.append(str(path))
    assert bad == []


# ---------------------------------------------------------------- AC-45 / FR-21 -----------


def test_ac45_fr21_demo_notice_text_is_present_and_clear():
    """AC-45 / FR-21, NFR-12: notice says DEMO, not authentication, not access control."""
    path = REPO_ROOT / "app" / "common.py"
    tree = parse(path)
    notice = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "DEMO_NOTICE" for t in node.targets
        ):
            notice = ast.literal_eval(node.value)
    assert notice, "DEMO_NOTICE constant missing"
    low = notice.lower()
    assert "demo" in low
    assert "not authentication" in low
    assert "access control" in low
    assert "no security" in low or "not security" in low


def test_ac45_fr21_main_renders_notice_before_any_role_view():
    """AC-45 / FR-21: main() calls render_demo_notice() before the role views are invoked."""
    tree = parse(REPO_ROOT / "app" / "main.py")
    main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    order = []
    for node in ast.walk(main_fn):
        if isinstance(node, ast.Call):
            if getattr(node.func, "id", "") == "render_demo_notice":
                order.append(("notice", node.lineno))
            if isinstance(node.func, ast.Subscript):  # ROLE_VIEWS[role](service)
                order.append(("view", node.lineno))
    kinds = [k for k, _ in sorted(order, key=lambda x: x[1])]
    assert kinds[:1] == ["notice"] and "view" in kinds


UI_CLAIM = re.compile(
    r"\b(log ?in|sign ?in|signin|secure[d]?|security|"
    r"authori[sz]\w*|authenticat\w*|permission\w*)\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize("path", APP_FILES, ids=lambda p: p.name)
def test_ac45_ac68_fr21_ui_strings_make_no_login_or_security_claim(path):
    """AC-45, AC-68 / FR-21, NFR-12: any UI string mentioning login/secure/authorized/etc. must
    be an explicit disclaimer (contains a negation such as 'not a login' / 'No authentication')."""
    for text in string_constants(path):
        if UI_CLAIM.search(text):
            assert NEGATION.search(text), f"possible security/login claim in UI text: {text!r}"


def test_ac45_fr21_login_wording_only_appears_as_the_explicit_not_a_login_disclaimer():
    """AC-45 / FR-21: the only 'login' text in the UI is the 'not a login' selector label."""
    hits = []
    for path in APP_FILES:
        hits += [s for s in string_constants(path) if re.search(r"log ?in|sign ?in", s, re.I)]
    assert hits == ["Demo role (not a login)"]


@pytest.mark.parametrize("path", TICKETING_FILES, ids=lambda p: p.name)
def test_ic1_backend_docstrings_and_messages_avoid_security_words(path):
    """IC section 1: no 'authorized'/'permission'/'secure' wording in backend strings."""
    for text in string_constants(path):
        assert not re.search(r"\b(authori[sz]\w*|permission\w*|secure[d]?)\b", text, re.I), text


# ---------------------------------------------------------------- AC-68 / AC-69 / AC-70 ----


def test_ac69_nfr10_python_streamlit_sqlite_pytest_baseline():
    """AC-69 / NFR-10: Python >= 3.10; Streamlit in the UI; built-in sqlite3 in the data layer."""
    assert sys.version_info >= (3, 10)
    assert "streamlit" in {m.split(".")[0] for m in imported_modules(REPO_ROOT / "app" / "main.py")}
    assert "sqlite3" in imported_modules(REPO_ROOT / "ticketing" / "db.py")
    assert "streamlit" in (REPO_ROOT / "requirements.txt").read_text()
    assert "pytest" in (REPO_ROOT / "requirements.txt").read_text()


def test_ac69_nfr10_entry_point_is_app_main_py_and_readme_states_launch_command():
    """AC-69 / NFR-10, BL-12: app/main.py exists, no app.py at root, README has the command."""
    assert (REPO_ROOT / "app" / "main.py").is_file()
    assert not (REPO_ROOT / "app.py").exists()
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m streamlit run app/main.py" in readme


def test_ac68_nfr12_readme_discloses_demo_roles_and_makes_no_security_claim():
    """AC-68 / NFR-12: README states demo selector, not authentication/authorization; every
    line mentioning security/access control/privacy is a disclaimer."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    low = readme.lower()
    assert "demo" in low
    assert "not authentication" in low
    assert "not authorization" in low or "not authorisation" in low
    claim = re.compile(r"secur|access[- ]control|privacy|confidential|encrypt|authori|authenticat",
                       re.IGNORECASE)  # fmt: skip
    for line in readme.splitlines():
        if claim.search(line):
            assert NEGATION.search(line), f"README line may read as a security claim: {line!r}"


def test_ac69_nfr10_readme_documents_pytest_and_ruff_commands():
    """AC-69 / NFR-10, NFR-11: README lists the test and lint commands."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "pytest" in readme and "ruff check" in readme


def test_ac70_nfr11_ruff_reports_no_errors_with_project_configuration():
    """AC-70 / NFR-11: `ruff check .` from the repository root exits 0."""
    exe = Path(sys.executable).parent / "ruff"
    exe_path = str(exe) if exe.exists() else shutil.which("ruff")
    assert exe_path, "ruff executable not found"
    result = subprocess.run(  # noqa: S603 - fixed local command
        [exe_path, "check", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_ac56_nfr07_meta_tests_run_without_a_browser_and_conftest_guards_exist():
    """AC-56 / NFR-07: conftest defines the temp-DB guards; suite imports no browser driver."""
    conftest = (REPO_ROOT / "tests" / "conftest.py").read_text()
    for needle in ("TICKET_DB_PATH", "guard_default_db", "tmp_path", "FakeClock"):
        assert needle in conftest or needle in (REPO_ROOT / "tests" / "helpers.py").read_text()
    for path in (REPO_ROOT / "tests").glob("*.py"):
        mods = {m.split(".")[0] for m in imported_modules(path)}
        assert not mods & {"selenium", "playwright", "pyppeteer"}
