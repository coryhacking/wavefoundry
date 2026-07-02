#!/usr/bin/env python3
from __future__ import annotations

import sys as _wf_sys
from pathlib import Path as _WfPath

_WF_SCRIPTS = _WfPath(__file__).resolve().parents[2] / ".wavefoundry" / "framework" / "scripts"
if _WF_SCRIPTS.is_dir() and str(_WF_SCRIPTS) not in _wf_sys.path:
    _wf_sys.path.insert(0, str(_WF_SCRIPTS))
try:
    import venv_bootstrap as _wf_venv_bootstrap

    _wf_venv_bootstrap.activate_tool_venv()
except Exception:
    pass

import json
import os
import subprocess
import sys
from pathlib import Path

# Wave 1p8gu: shared subprocess isolation. HOOK_BOOTSTRAP (prepended by compose_script) already
# put the framework scripts dir on sys.path, so this resolves at hook runtime; guarded so a hook
# rendered against a transient/old tree still loads (falls back to bare-but-isolated spawns).
try:
    import subprocess_util as _wf_subprocess_util
except Exception:
    _wf_subprocess_util = None

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_OVERRIDES = REPO_ROOT / ".wavefoundry" / "guard-overrides.json"


def hook_python() -> str:
    # Wave 1p8pe: prefer the console-free tool-venv pythonw.exe on Windows so these rendered
    # hook spawns (all output redirected: DEVNULL / PIPE / capture) never flash a console
    # window. Falls back to sys.executable when subprocess_util is unavailable or on POSIX
    # (windowless_pythonw() returns None). Every spawned target self-activates the venv.
    if _wf_subprocess_util is not None:
        try:
            pythonw = _wf_subprocess_util.windowless_pythonw()
            if pythonw is not None:
                return pythonw
        except Exception:
            pass
    return sys.executable


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


def run_command(argv: list[str], timeout=None) -> subprocess.CompletedProcess[str]:
    # Wave 1p9bg: `timeout` (seconds) bounds the child; on expiry subprocess raises
    # TimeoutExpired, which the caller handles. None = unbounded (existing behavior for callers
    # that don't pass one).
    if _wf_subprocess_util is not None:
        return _wf_subprocess_util.isolated_run(
            argv,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
        creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0),
        timeout=timeout,
    )


def maybe_docs_lint(file_path: str) -> tuple[bool, str]:
    if not file_path.startswith("docs/"):
        return False, ""
    # Wave 1p7tz/1p802: the `bin/docs-lint` wrapper was retired — invoke docs_lint.py directly
    # via sys.executable. After in-process activation sys.executable stays the SYSTEM
    # interpreter; the spawned docs_lint.py self-activates the venv first-line, so it reaches
    # the venv packages.
    docs_lint = REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "docs_lint.py"
    # Wave 1p9bg: bound the docs-lint subprocess so a slow whole-tree lint on a large repo can't
    # hang the post-edit hook. The timeout is generous (120s default) and tunable via
    # docs/workflow-config.json `docs_lint.hook_timeout_seconds`. A TIMEOUT is ADVISORY — it does
    # NOT block the edit (wave_validate / wave-close remain the hard docs gate); a real lint
    # FAILURE still blocks below.
    try:
        timeout_s = _load_indexer_hook_helpers().docs_lint_hook_timeout_seconds(REPO_ROOT)
    except Exception:
        timeout_s = 120.0
    # Wave 1p9c1: run docs-lint INCREMENTALLY in the post-edit hook — `--changed` self-detects the
    # git working-tree changed set and lints only the per-file validators on changed docs (a
    # changed config file falls back to the full lint inside the cli). The authoritative full
    # corpus lint stays at wave_validate / wave_close / prepare / install / upgrade, which invoke
    # docs_lint.py WITHOUT `--changed`. Incremental makes a timeout far less likely, but the 1p9bg
    # bound stays as defense-in-depth.
    try:
        result = run_command([hook_python(), str(docs_lint), "--changed"], timeout=timeout_s)
    except subprocess.TimeoutExpired:
        print(
            f"[wavefoundry] docs-lint exceeded {timeout_s:.0f}s and was skipped for this edit "
            f"(advisory — the edit is not blocked). Run `wf docs-lint`, or raise "
            f"docs_lint.hook_timeout_seconds in docs/workflow-config.json.",
            file=sys.stderr,
        )
        return False, ""
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


def _load_indexer_hook_helpers():
    import importlib.util
    indexer = REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer_hook", indexer)
    if spec is None or spec.loader is None:
        raise RuntimeError("indexer hook helpers unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _spawn_reindex() -> None:
    # Spawn ONE detached incremental reindex. No coalescing decision here — callers gate. Wave
    # 1p9am split this out of maybe_trigger_reindex so the mark/flush paths share it.
    indexer = REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
    if not indexer.exists():
        return
    # sys.executable is the SYSTEM interpreter (after in-process activation, wave 1p802) — an
    # absolute path; the spawned indexer.py self-activates the venv first-line so the child
    # reaches the venv packages. Never re-resolve a python3/python token. Wave 1p8pe: prefer the
    # console-free pythonw.exe on Windows (this is a detached all-DEVNULL spawn — textbook
    # flasher); hook_python() falls back to sys.executable on POSIX / when unavailable.
    python_exec = hook_python()
    index_dir = REPO_ROOT / ".wavefoundry" / "index"
    try:
        hook_helpers = _load_indexer_hook_helpers()
        hook_helpers.record_hook_reindex_spawn(index_dir)
    except Exception:
        pass
    # indexer.py reads docs/workflow-config.json itself for project
    # include-prefixes — launchers run bare, no prefix forwarding.
    # 1p4ww: a single bare reindex — indexer folds the framework seeds/README
    # into the project docs index, so no separate framework-index spawn.
    # Wave 1p7pn (M-3): detach per-OS — on Windows start_new_session is a no-op, so without
    # creationflags the child stays in the host's process group and dies with the hook. Mirror
    # server_impl.py / dashboard_server._daemonize.
    _detach_kwargs = {}
    if os.name == "nt":
        _detach_kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    else:
        _detach_kwargs["start_new_session"] = True
    subprocess.Popen(
        [python_exec, str(indexer), "--root", str(REPO_ROOT)],
        stdin=subprocess.DEVNULL,  # wave 1p8gu: detached child never inherits a blocking stdin
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(REPO_ROOT),
        close_fds=os.name != "nt",
        **_detach_kwargs,
    )


def mark_reindex_pending_for(file_path: str) -> None:
    # Wave 1p9am: on an index-worthy edit, MARK the reindex-pending sentinel and DO NOT spawn a
    # reindex. The turn-end Stop hook flushes it once per turn. Used by the Claude post-edit hook.
    if not should_reindex(file_path):
        return
    try:
        hook_helpers = _load_indexer_hook_helpers()
        hook_helpers.mark_reindex_pending(REPO_ROOT / ".wavefoundry" / "index")
    except Exception:
        pass


def maybe_trigger_reindex(file_path: str) -> None:
    # Wave 1p9am: the NON-Stop-host path (Cursor/Copilot/… have no turn-end hook). Mark pending,
    # then flush under the long leading-edge debounce (best coalescing without a turn-end signal).
    if not should_reindex(file_path):
        return
    index_dir = REPO_ROOT / ".wavefoundry" / "index"
    try:
        hook_helpers = _load_indexer_hook_helpers()
        hook_helpers.mark_reindex_pending(index_dir)
        if hook_helpers.should_coalesce_hook_reindex(index_dir):
            return  # within the debounce window or a live build — leave it pending
        if not hook_helpers.consume_reindex_pending(index_dir):
            return  # another consumer already took it
    except Exception:
        return
    _spawn_reindex()

def main() -> int:
    payload = load_payload(read_payload_text())
    file_path = detect_file_path(payload)
    if not file_path:
        return 0
    blocked, message = maybe_docs_lint(file_path)
    if blocked:
        print(message, file=sys.stderr)
        return 1
    # Wave 1p9am: Claude has a turn-end Stop hook — mark the edit pending (no per-edit spawn);
    # the Stop hook flushes one coalesced reindex per turn.
    mark_reindex_pending_for(file_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
