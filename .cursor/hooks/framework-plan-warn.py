#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_OVERRIDES = REPO_ROOT / ".wavefoundry" / "guard-overrides.json"


def read_payload_text() -> str:
    try:
        if sys.stdin.isatty():
            return ""
    except Exception:
        return ""
    return sys.stdin.read()


def load_payload(raw: str) -> dict[str, object]:
    if not raw.strip():
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def load_guard_overrides() -> dict[str, object]:
    if not GUARD_OVERRIDES.exists():
        return {}
    try:
        loaded = json.loads(GUARD_OVERRIDES.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def guard_enabled(flag_name: str) -> bool:
    loaded = load_guard_overrides()
    value = loaded.get(flag_name)
    if not isinstance(value, dict):
        return False
    enabled = value.get("enabled")
    return enabled if isinstance(enabled, bool) else False


def get_nested(mapping: dict[str, object], *path: str) -> str:
    value: object = mapping
    for part in path:
        if not isinstance(value, dict):
            return ""
        value = value.get(part)
    return value if isinstance(value, str) else ""


def detect_file_path(payload: dict[str, object]) -> str:
    for path in (
        ("tool_input", "file_path"),
        ("tool_input", "path"),
        ("tool_info", "file_path"),
        ("file_path",),
        ("path",),
    ):
        candidate = get_nested(payload, *path)
        if candidate:
            return candidate
    return ""


def detect_command(payload: dict[str, object]) -> str:
    for path in (
        ("tool_input", "command"),
        ("command",),
        ("bash",),
    ):
        candidate = get_nested(payload, *path)
        if candidate:
            return candidate
    return ""


def is_seed_prompt(path: str) -> bool:
    return path.startswith(".wavefoundry/framework/seeds/") and path.endswith(".prompt.md")


def is_framework_maintenance_surface(path: str) -> bool:
    if path == "AGENTS.md":
        return True
    prefixes = (
        ".wavefoundry/framework/",
        "docs/prompts/",
        ".claude/hooks/",
        ".cursor/hooks/",
        ".github/hooks/",
        ".windsurf/hooks/",
    )
    if path.startswith(prefixes):
        return True
    exact = {
        ".claude/settings.json",
        ".claude/skills/upgrade-wave.md",
        ".cursor/hooks.json",
        ".github/hooks/hooks.json",
        ".windsurf/hooks.json",
    }
    return path in exact


def run_command(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def maybe_docs_lint(file_path: str) -> tuple[bool, str]:
    if not file_path.startswith("docs/"):
        return False, ""
    result = run_command([str(REPO_ROOT / ".wavefoundry" / "bin" / "docs-lint")])
    if result.returncode == 0:
        return False, ""
    message = (result.stdout + result.stderr).strip()
    return True, message or "docs-lint failed"


def should_reindex(path: str) -> bool:
    if not path:
        return False
    if path.startswith(".wavefoundry/index/"):
        return False
    if path.startswith(".wavefoundry/framework/index/"):
        return False
    suffix = Path(path).suffix.lower()
    skip_suffixes = {".pyc", ".npy", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                     ".ico", ".woff", ".woff2", ".ttf", ".eot", ".zip"}
    return suffix not in skip_suffixes


def _venv_python_path() -> str:
    import os
    venv_base = os.environ.get("WAVEFOUNDRY_TOOL_VENV", str(Path.home() / ".wavefoundry" / "venv"))
    if os.name == "nt":
        return str(Path(venv_base) / "Scripts" / "python.exe")
    return str(Path(venv_base) / "bin" / "python")


def _load_indexer_hook_helpers():
    import importlib.util
    indexer = REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer_hook", indexer)
    if spec is None or spec.loader is None:
        raise RuntimeError("indexer hook helpers unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def maybe_trigger_reindex(file_path: str) -> None:
    if not should_reindex(file_path):
        return
    indexer = REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
    if not indexer.exists():
        return
    python_exec = _venv_python_path()
    if not Path(python_exec).exists():
        python_exec = sys.executable
    index_dir = REPO_ROOT / ".wavefoundry" / "index"
    try:
        hook_helpers = _load_indexer_hook_helpers()
        if hook_helpers.should_coalesce_hook_reindex(index_dir):
            return
        hook_helpers.record_hook_reindex_spawn(index_dir)
    except Exception:
        pass
    # indexer.py reads docs/workflow-config.json itself for project
    # include-prefixes — launchers run bare, no prefix forwarding.
    # 1p4ww: a single bare reindex — indexer folds the framework seeds/README
    # into the project docs index, so no separate framework-index spawn.
    subprocess.Popen(
        [python_exec, str(indexer), "--root", str(REPO_ROOT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(REPO_ROOT),
        start_new_session=True,
        close_fds=os.name != "nt",
    )

def main() -> int:
    payload = load_payload(read_payload_text())
    file_path = detect_file_path(payload)
    if is_framework_maintenance_surface(file_path) and not guard_enabled("framework_edit_allowed"):
        print(
            "Broad framework-maintenance edits require `.wavefoundry/guard-overrides.json` with `framework_edit_allowed.enabled: true` after an approved file-level plan."
        )
        return 10
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
