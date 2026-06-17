#!/usr/bin/env python3
"""Render generic Python hook/config surfaces from the wave framework."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from textwrap import dedent


FRAMEWORK_RENDERER_REL = ".wavefoundry/framework/scripts/render_platform_surfaces.py"
GUARD_OVERRIDES_REL = ".wavefoundry/guard-overrides.json"

# Wave 1p590: the module-level absolute-venv-Python helper was removed — every surface now uses a
# project-relative command (hooks) or the .wavefoundry/bin/mcp-server wrapper (MCP), so no tracked
# surface embeds a machine-specific path. Hook .py sources still resolve the venv at RUN time via
# their own inline helper (see git_hook_source / hook bundle sources), which is correct.

_VENV_SH_SNIPPET = """\
WAVEFOUNDRY_VENV="${WAVEFOUNDRY_TOOL_VENV:-$HOME/.wavefoundry/venv}"
PYTHON="${WAVEFOUNDRY_VENV}/bin/python"
if [ ! -x "$PYTHON" ]; then PYTHON="python3"; fi
"""


def discover_repo_root() -> Path:
    """Walk up from CWD to find the repo root for the renderer.

    Intentional differences from the copies in other scripts:
    - Anchors on ``FRAMEWORK_RENDERER_REL`` (presence of this script itself)
      rather than ``docs/workflow-config.json``, so it works even when the
      framework bundle is deployed without a full docs tree.
    - Never returns ``None`` — falls back to the script's own grandparent.

    Cross-reference: ``server._discover_root``, ``indexer._discover_root``,
    ``lifecycle_id.discover_repo_root``, ``docs_gardener.project_root``.
    A future consolidation task should unify these into a shared utility.
    """
    for env_key in ("PROJECT_ROOT", "REPO_ROOT"):
        raw = os.environ.get(env_key)
        if raw:
            candidate = Path(raw).expanduser().resolve()
            if (candidate / FRAMEWORK_RENDERER_REL).is_file():
                return candidate
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / FRAMEWORK_RENDERER_REL).is_file():
            return candidate
    return Path(__file__).resolve().parents[3]


def detect_platforms(repo_root: Path) -> set[str]:
    platforms: set[str] = {"claude"}
    if (repo_root / ".cursor").exists():
        platforms.add("cursor")
    if (repo_root / ".github" / "copilot-instructions.md").exists():
        platforms.add("copilot")
    if (repo_root / ".junie" / "guidelines.md").exists():
        platforms.add("junie")
    if (repo_root / ".windsurf").exists():
        platforms.add("windsurf")
    return platforms


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, executable: bool = False) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | 0o111)


def remove_files(paths: list[Path]) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def remove_copilot_artifacts(repo_root: Path) -> None:
    remove_files(
        [
            repo_root / ".github" / "hooks" / "hooks.json",
            repo_root / ".github" / "hooks" / "pre-tool-use",
            repo_root / ".github" / "hooks" / "pre-tool-use.py",
            repo_root / ".github" / "hooks" / "pre-tool-use.cmd",
            repo_root / ".github" / "hooks" / "post-tool-use",
            repo_root / ".github" / "hooks" / "post-tool-use.py",
            repo_root / ".github" / "hooks" / "post-tool-use.cmd",
            repo_root / ".github" / "hooks" / "pre-tool-use.sh",
            repo_root / ".github" / "hooks" / "post-tool-use.sh",
        ]
    )


def launcher_command(rel_base: str) -> str:
    """Project-relative launcher command for a hook config.

    Wave 1p590: NEVER emit a machine-absolute path — tracked surfaces must work on any clone.
    The command is emitted relative to the project root, which the surface tools resolve against
    the workspace (matching the portable ``.mcp.json`` / ``.wavefoundry/bin`` wrapper pattern).
    Per-tool relative-command resolution is verified on a fresh clone (wave 1p590 AC-2)."""
    if os.name == "nt":
        return f"cmd.exe /c {rel_base.replace('/', os.sep)}.cmd"
    return rel_base


# Single source of truth for Claude hooks. Both the settings renderer
# (render_claude_settings) and the dry-run simulate map (claude_simulate_hooks_source)
# derive from this list so they can NOT drift: every hook rendered into
# .claude/settings.json is also dry-runnable through .claude/hooks/simulate-hooks.py.
# A parity test in tests/test_render_platform_surfaces.py enforces this.
#   name:  the hook script basename under .claude/hooks/ (also the simulate entrypoint key)
#   event: the Claude settings event ("PreToolUse" / "PostToolUse" / "Stop")
#   matcher: tool matcher for the settings entry, or None for unmatched events (Stop)
#   status_message: statusMessage shown by Claude while the hook runs
CLAUDE_HOOKS: tuple[dict[str, object], ...] = (
    {
        "name": "pre-edit",
        "event": "PreToolUse",
        "matcher": "Edit|Write",
        "status_message": "Checking framework edit gates...",
    },
    {
        "name": "post-edit",
        "event": "PostToolUse",
        "matcher": "Edit|Write",
        "status_message": "Running docs gates...",
    },
    # Wave 1p5ti — session-end capture (capture/nudge only; never blocks).
    # Stop only: SubagentStop would fire on every subagent completion (noise +
    # redundant captures); the meaningful capture point is the main session end.
    {
        "name": "session-capture",
        "event": "Stop",
        "matcher": None,
        "status_message": "Capturing session state...",
    },
)


def posix_launcher_source(script_name: str) -> str:
    return dedent(
        f"""#!/usr/bin/env sh
        set -eu
        SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
        WAVEFOUNDRY_VENV="${{WAVEFOUNDRY_TOOL_VENV:-$HOME/.wavefoundry/venv}}"
        PYTHON="${{WAVEFOUNDRY_VENV}}/bin/python"
        if [ ! -x "$PYTHON" ]; then PYTHON="python3"; fi
        exec "$PYTHON" "$SCRIPT_DIR/{script_name}.py" "$@"
        """
    )


def windows_launcher_source(script_name: str) -> str:
    return dedent(
        f"""@echo off
        setlocal
        set "SCRIPT_DIR=%~dp0"
        if defined WAVEFOUNDRY_TOOL_VENV (
          set "PYTHON=%WAVEFOUNDRY_TOOL_VENV%\\Scripts\\python.exe"
        ) else (
          set "PYTHON=%USERPROFILE%\\.wavefoundry\\venv\\Scripts\\python.exe"
        )
        if not exist "%PYTHON%" set "PYTHON=python3"
        "%PYTHON%" "%SCRIPT_DIR%{script_name}.py" %*
        exit /b %ERRORLEVEL%
        """
    )


def write_hook_bundle(base_path: Path, python_source: str) -> None:
    write_text(base_path.with_suffix(".py"), python_source, executable=True)
    write_text(base_path, posix_launcher_source(base_path.name), executable=True)
    write_text(base_path.with_suffix(".cmd"), windows_launcher_source(base_path.name))


def hook_helpers() -> str:
    return dedent(
        """
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
        """
    ).strip()


def compose_script(body: str, include_helpers: bool = True) -> str:
    parts = ["#!/usr/bin/env python3\n"]
    if include_helpers:
        parts.append(hook_helpers())
        parts.append("\n\n")
    parts.append(dedent(body).strip())
    parts.append("\n")
    return "".join(parts)


def claude_pre_edit_source() -> str:
    return compose_script(
        """
        def main() -> int:
            payload = load_payload(read_payload_text())
            file_path = detect_file_path(payload)
            if not file_path:
                return 0
            if is_seed_prompt(file_path) and not guard_enabled("seed_edit_allowed"):
                print(
                    "BLOCKED: Seed prompt edit requires `.wavefoundry/guard-overrides.json` with `seed_edit_allowed.enabled: true` before intentional seed edits.",
                    file=sys.stderr,
                )
                return 2
            if is_framework_maintenance_surface(file_path) and not guard_enabled("framework_edit_allowed"):
                print(
                    "BLOCKED: Broad framework-maintenance edits require `.wavefoundry/guard-overrides.json` with `framework_edit_allowed.enabled: true` after an approved file-level plan.",
                    file=sys.stderr,
                )
                return 2
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def claude_post_edit_source() -> str:
    return compose_script(
        """
        def main() -> int:
            payload = load_payload(read_payload_text())
            file_path = detect_file_path(payload)
            if not file_path:
                return 0
            blocked, message = maybe_docs_lint(file_path)
            if blocked:
                print(message, file=sys.stderr)
                return 1
            maybe_trigger_reindex(file_path)
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def claude_simulate_hooks_source() -> str:
    # Derive the simulate HOOKS map from the shared CLAUDE_HOOKS registry so a hook
    # rendered into .claude/settings.json is always dry-runnable (no drift).
    # 4-space indent: matches the final (post-dedent) body indentation level.
    hook_lines = "\n".join(
        '    "{name}": REPO_ROOT / ".claude" / "hooks" / "{name}.py",'.format(name=hook["name"])
        for hook in CLAUDE_HOOKS
    )
    source = """
        from __future__ import annotations

        import os
        import subprocess
        import sys
        from pathlib import Path

        REPO_ROOT = Path(__file__).resolve().parents[2]
        HOOKS = {
            __HOOK_LINES__
        }


        def _venv_python_path() -> str:
            venv_base = os.environ.get("WAVEFOUNDRY_TOOL_VENV", str(Path.home() / ".wavefoundry" / "venv"))
            if os.name == "nt":
                return str(Path(venv_base) / "Scripts" / "python.exe")
            return str(Path(venv_base) / "bin" / "python")


        def main(argv: list[str]) -> int:
            if len(argv) != 2:
                print("usage: simulate-hooks.py <entrypoint> <json-payload>", file=sys.stderr)
                return 2
            hook_name, payload = argv
            target = HOOKS.get(hook_name)
            if target is None:
                print(f"unknown hook entrypoint: {hook_name}", file=sys.stderr)
                return 2
            python_exec = _venv_python_path()
            if not Path(python_exec).exists():
                python_exec = sys.executable
            result = subprocess.run(
                [python_exec, str(target)],
                cwd=REPO_ROOT,
                input=payload,
                text=True,
                check=False,
            )
            return result.returncode


        if __name__ == "__main__":
            raise SystemExit(main(sys.argv[1:]))
        """
    # Replace after compose_script so the placeholder line is dedented to its final
    # 4-space indent; hook_lines are emitted at that same level.
    composed = compose_script(source, include_helpers=False)
    return composed.replace("    __HOOK_LINES__", hook_lines)


def cursor_seed_warn_source() -> str:
    return compose_script(
        """
        def main() -> int:
            payload = load_payload(read_payload_text())
            file_path = detect_file_path(payload)
            if is_seed_prompt(file_path) and not guard_enabled("seed_edit_allowed"):
                print("Seed prompt edit requires `.wavefoundry/guard-overrides.json` with `seed_edit_allowed.enabled: true` before intentional seed edits.")
                return 10
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def cursor_framework_warn_source() -> str:
    return compose_script(
        """
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
        """
    )


def cursor_docs_lint_source() -> str:
    return compose_script(
        """
        def main() -> int:
            payload = load_payload(read_payload_text())
            file_path = detect_file_path(payload)
            blocked, message = maybe_docs_lint(file_path)
            if blocked:
                print(message)
                return 10
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def cursor_after_file_edit_source() -> str:
    return compose_script(
        """
        GATES = (
            REPO_ROOT / ".cursor" / "hooks" / "seed-warn.py",
            REPO_ROOT / ".cursor" / "hooks" / "framework-plan-warn.py",
            REPO_ROOT / ".cursor" / "hooks" / "docs-lint.py",
        )


        def main() -> int:
            raw = read_payload_text()
            payload = load_payload(raw)
            python_exec = _venv_python_path()
            if not Path(python_exec).exists():
                python_exec = sys.executable
            for gate in GATES:
                result = subprocess.run(
                    [python_exec, str(gate)],
                    cwd=REPO_ROOT,
                    input=raw,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                output = (result.stdout + result.stderr).strip()
                if result.returncode == 10:
                    print(json.dumps({"continue": False, "message": output or "Cursor hook blocked the edit."}))
                    return 0
                if result.returncode != 0:
                    print(json.dumps({"continue": False, "message": output or "Cursor hook failed."}))
                    return 0
            maybe_trigger_reindex(detect_file_path(payload))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def copilot_pre_tool_use_source() -> str:
    return compose_script(
        """
        def main() -> int:
            payload = load_payload(read_payload_text())
            file_path = detect_file_path(payload)
            if not file_path:
                return 0
            if is_seed_prompt(file_path) and not guard_enabled("seed_edit_allowed"):
                print(
                    "BLOCKED: Seed prompt edit requires `.wavefoundry/guard-overrides.json` with `seed_edit_allowed.enabled: true` before intentional seed edits.",
                    file=sys.stderr,
                )
                return 2
            if is_framework_maintenance_surface(file_path) and not guard_enabled("framework_edit_allowed"):
                print(
                    "BLOCKED: Broad framework-maintenance edits require `.wavefoundry/guard-overrides.json` with `framework_edit_allowed.enabled: true` after an approved file-level plan.",
                    file=sys.stderr,
                )
                return 2
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def copilot_post_tool_use_source() -> str:
    return compose_script(
        """
        def main() -> int:
            payload = load_payload(read_payload_text())
            file_path = detect_file_path(payload)
            if not file_path:
                return 0
            blocked, message = maybe_docs_lint(file_path)
            if blocked:
                print(message, file=sys.stderr)
                return 1
            maybe_trigger_reindex(file_path)
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def windsurf_seed_protect_source() -> str:
    return compose_script(
        """
        def main() -> int:
            payload = load_payload(read_payload_text())
            file_path = detect_file_path(payload)
            if is_seed_prompt(file_path) and not guard_enabled("seed_edit_allowed"):
                print(
                    "Seed prompt edit requires `.wavefoundry/guard-overrides.json` with `seed_edit_allowed.enabled: true` before intentional seed edits.",
                    file=sys.stderr,
                )
                return 2
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def windsurf_docs_lint_source() -> str:
    return compose_script(
        """
        def main() -> int:
            payload = load_payload(read_payload_text())
            file_path = detect_file_path(payload)
            blocked, message = maybe_docs_lint(file_path)
            if blocked:
                print(message, file=sys.stderr)
                return 1
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def claude_stop_source() -> str:
    """Session-end capture hook (wave 1p5ti).

    Host-agnostic in intent; this is the Claude `Stop` rendering (main session
    end only — not SubagentStop, which would spam on every subagent completion).
    On session end it writes a capture summary (open wave + AC progress,
    uncommitted-work signal, handoff staleness, and a learnings/memory-candidate
    nudge) to a predictable gitignored location and prints one short line.

    Hard contract: fast, fully fail-safe, ALWAYS exits 0, and NEVER writes
    memory or commits — capture/nudge only, so it can never block session end.
    """
    return dedent(
        '''
        """Wavefoundry session-end capture hook. Capture/nudge only; never blocks."""
        from __future__ import annotations

        import os
        import subprocess
        import sys
        from pathlib import Path


        def _find_repo_root(start: Path) -> Path | None:
            cur = start.resolve()
            for cand in [cur, *cur.parents]:
                if (cand / "docs" / "waves").is_dir() or (cand / ".wavefoundry").is_dir():
                    return cand
            return None


        def _active_wave(root: Path):
            waves = root / "docs" / "waves"
            if not waves.is_dir():
                return None
            for wave_dir in sorted(waves.iterdir()):
                wave_md = wave_dir / "wave.md"
                if not wave_md.is_file():
                    continue
                try:
                    text = wave_md.read_text(encoding="utf-8")
                except Exception:
                    continue
                status = ""
                wave_id = wave_dir.name
                for line in text.splitlines():
                    s = line.strip()
                    if s.lower().startswith("status:"):
                        status = s.split(":", 1)[1].strip().lower()
                    elif s.startswith("wave-id:"):
                        wave_id = s.split(":", 1)[1].strip().strip("`")
                if status in ("active", "implementing"):
                    return (wave_id, wave_dir)
            return None


        def _ac_progress(wave_dir: Path):
            done = total = 0
            for md in sorted(wave_dir.glob("*.md")):
                if md.name == "wave.md":
                    continue
                try:
                    for line in md.read_text(encoding="utf-8").splitlines():
                        st = line.strip()
                        if st.startswith("- [ ] AC") or st.startswith("- [] AC"):
                            total += 1
                        elif st.startswith("- [x] AC") or st.startswith("- [X] AC"):
                            total += 1
                            done += 1
                except Exception:
                    continue
            return done, total


        def _git_dirty_count(root: Path) -> int | None:
            try:
                out = subprocess.run(
                    ["git", "-C", str(root), "status", "--porcelain"],
                    capture_output=True, text=True, timeout=5,
                )
                if out.returncode != 0:
                    return None
                return len([ln for ln in out.stdout.splitlines() if ln.strip()])
            except Exception:
                return None


        def _handoff_stale(root: Path, wave_dir: Path | None) -> bool | None:
            handoff = root / "docs" / "agents" / "session-handoff.md"
            if not handoff.is_file() or wave_dir is None:
                return None
            try:
                hf = handoff.stat().st_mtime
                newest = max(
                    (p.stat().st_mtime for p in wave_dir.glob("*.md")), default=0.0
                )
                return newest > hf
            except Exception:
                return None


        def main() -> int:
            try:
                # Drain stdin so the host never blocks on the pipe; payload unused.
                try:
                    sys.stdin.read()
                except Exception:
                    pass
                root = _find_repo_root(Path(os.getcwd()))
                if root is None:
                    return 0
                wave = _active_wave(root)
                lines = ["# Session capture", ""]
                if wave:
                    wave_id, wave_dir = wave
                    done, total = _ac_progress(wave_dir)
                    lines.append(f"- Open wave: {wave_id}")
                    if total:
                        lines.append(f"- AC progress: {done}/{total} checked")
                    stale = _handoff_stale(root, wave_dir)
                    if stale is True:
                        lines.append("- Session handoff looks STALE vs the wave — update it before stopping.")
                else:
                    lines.append("- No active wave.")
                dirty = _git_dirty_count(root)
                if dirty:
                    lines.append(f"- Uncommitted changes: {dirty} path(s).")
                lines.append("")
                lines.append("Learnings: record any new build/test quirk or decision discovered this")
                lines.append("session as a memory candidate (confirm before writing — never auto-saved).")
                lines.append("")
                try:
                    cache_dir = root / ".wavefoundry" / "logs"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    (cache_dir / "last-session-capture.md").write_text(
                        "\\n".join(lines) + "\\n", encoding="utf-8"
                    )
                except Exception:
                    pass
                summary = wave[0] if wave else "no active wave"
                print(f"[wavefoundry] session capture saved ({summary}); review learnings before next session.")
                return 0
            except Exception:
                # Never let a capture error block the session from ending.
                return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        '''
    )


def render_claude_settings(repo_root: Path) -> None:
    settings_path = repo_root / ".claude" / "settings.json"
    existing: dict[str, object] = {}
    if settings_path.exists():
        try:
            loaded = json.loads(settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except json.JSONDecodeError:
            existing = {}

    # Derive the hooks dict from the shared CLAUDE_HOOKS registry so the rendered
    # settings can never drift from the simulate map (claude_simulate_hooks_source).
    hooks: dict[str, list] = {}
    for hook in CLAUDE_HOOKS:
        entry_hook = {
            "type": "command",
            "command": launcher_command(f".claude/hooks/{hook['name']}"),
            "statusMessage": hook["status_message"],
        }
        entry: dict[str, object] = {"hooks": [entry_hook]}
        if hook["matcher"] is not None:
            entry = {"matcher": hook["matcher"], **entry}
        hooks.setdefault(str(hook["event"]), []).append(entry)
    existing["hooks"] = hooks
    write_text(settings_path, json.dumps(existing, indent=2) + "\n")


def _merge_mcp_server(target: Path, stanza: dict) -> None:
    """Read-modify-write an MCP JSON config file, setting only ``mcpServers["wavefoundry"]``.

    Preserves all other top-level keys and all unrelated ``mcpServers`` entries.
    Creates the file (and any parent directories) when it does not yet exist.
    Safe to call repeatedly — subsequent calls are idempotent for the same stanza.
    """
    existing: dict[str, object] = {}
    if target.exists():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except json.JSONDecodeError:
            existing = {}
    existing.setdefault("mcpServers", {})
    existing["mcpServers"]["wavefoundry"] = stanza
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text(target, json.dumps(existing, indent=2) + "\n")


def render_mcp_json(repo_root: Path) -> None:
    """Merge the Wavefoundry stdio MCP entry into the Claude repo-root ``.mcp.json``.

    Uses the ``mcp-server`` bin wrapper so the stanza is portable: the wrapper
    resolves the repo root and venv Python from its own location, so no machine-
    specific absolute paths are embedded.
    """
    _merge_mcp_server(
        repo_root / ".mcp.json",
        {
            "command": ".wavefoundry/bin/mcp-server",
            "args": [],
        },
    )


def render_junie_mcp_json(repo_root: Path) -> None:
    """Merge the Wavefoundry stdio MCP entry into the Junie ``.junie/mcp/mcp.json``.

    Wave 1p590: uses the project-relative ``.wavefoundry/bin/mcp-server`` wrapper (parity with the
    root ``.mcp.json``) instead of an absolute venv-Python path. The wrapper resolves the repo root
    and venv from its own location, so the stanza embeds no machine-specific absolute path."""
    _merge_mcp_server(
        repo_root / ".junie" / "mcp" / "mcp.json",
        {
            "command": ".wavefoundry/bin/mcp-server",
            "args": [],
        },
    )


def render_cursor_mcp_json(repo_root: Path) -> None:
    """Merge the Wavefoundry stdio MCP entry into the Cursor ``.cursor/mcp.json``.

    Wave 1p590: uses the project-relative ``.wavefoundry/bin/mcp-server`` wrapper (parity with the
    root ``.mcp.json``) instead of an absolute venv-Python path; the wrapper resolves the repo root
    and venv from its own location. ``cwd: ${workspaceFolder}`` lets Cursor resolve the relative
    command against the workspace.
    """
    _merge_mcp_server(
        repo_root / ".cursor" / "mcp.json",
        {
            "type": "stdio",
            "command": ".wavefoundry/bin/mcp-server",
            "args": [],
            "cwd": "${workspaceFolder}",
        },
    )


def render_cursor_hooks(repo_root: Path) -> None:
    config = {
        "version": 1,
        "hooks": {
            "afterFileEdit": [
                {
                    "command": launcher_command(".cursor/hooks/after-file-edit"),
                }
            ]
        },
    }
    write_text(repo_root / ".cursor" / "hooks.json", json.dumps(config, indent=2) + "\n")


def render_copilot_hooks(repo_root: Path) -> None:
    config = {
        "version": 1,
        "hooks": {
            "preToolUse": [
                {
                    "type": "command",
                    "bash": launcher_command(".github/hooks/pre-tool-use"),
                }
            ],
            "postToolUse": [
                {
                    "type": "command",
                    "bash": launcher_command(".github/hooks/post-tool-use"),
                }
            ],
        },
    }
    write_text(repo_root / ".github" / "hooks" / "hooks.json", json.dumps(config, indent=2) + "\n")


def git_hook_source(hook_name: str) -> str:
    """Return Python source for a git hook that fires an incremental reindex."""
    lines = [
        "#!/usr/bin/env python3",
        "from __future__ import annotations",
        "",
        "import os",
        "import subprocess",
        "import sys",
        "from pathlib import Path",
        "",
        "REPO_ROOT = Path(__file__).resolve().parents[2]",
        "",
        "",
        "def _venv_python_path() -> str:",
        "    venv_base = os.environ.get(\"WAVEFOUNDRY_TOOL_VENV\", str(Path.home() / \".wavefoundry\" / \"venv\"))",
        "    if os.name == \"nt\":",
        "        return str(Path(venv_base) / \"Scripts\" / \"python.exe\")",
        "    return str(Path(venv_base) / \"bin\" / \"python\")",
        "",
    ]
    if hook_name == "post-checkout":
        lines += [
            "# Only reindex on branch checkouts (arg 3 == \"1\"); skip file checkouts.",
            "if len(sys.argv) >= 4 and sys.argv[3] != \"1\":",
            "    raise SystemExit(0)",
            "",
        ]
    lines += [
        "",
        "def main() -> int:",
        "    indexer = REPO_ROOT / \".wavefoundry\" / \"framework\" / \"scripts\" / \"indexer.py\"",
        "    if not indexer.exists():",
        "        return 0",
        "    python_exec = _venv_python_path()",
        "    if not Path(python_exec).exists():",
        "        python_exec = sys.executable",
        "    subprocess.Popen(",
        "        [python_exec, str(indexer), \"--root\", str(REPO_ROOT)],",
        "        stdout=subprocess.DEVNULL,",
        "        stderr=subprocess.DEVNULL,",
        "        cwd=str(REPO_ROOT),",
        "        start_new_session=True,",
        "    )",
        "    return 0",
        "",
        "",
        "if __name__ == \"__main__\":",
        "    raise SystemExit(main())",
        "",
    ]
    return "\n".join(lines)


GIT_HOOK_NAMES = ("post-commit", "post-merge", "post-rewrite", "post-checkout")


def render_bin_launchers(repo_root: Path) -> None:
    """Write canonical CLI launchers to .wavefoundry/bin/.

    These are the authoritative entry points for hooks, CI, and operators who
    are not using MCP.  Agents should prefer the MCP tools (wave_validate,
    wave_garden) over invoking these directly.
    """
    bin_dir = repo_root / ".wavefoundry" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    _venv_block = (
        'WAVEFOUNDRY_VENV="${WAVEFOUNDRY_TOOL_VENV:-$HOME/.wavefoundry/venv}"\n'
        'PYTHON="${WAVEFOUNDRY_VENV}/bin/python"\n'
        'if [ ! -x "$PYTHON" ]; then PYTHON="python3"; fi\n'
    )
    _bat_venv_block = (
        'if defined WAVEFOUNDRY_TOOL_VENV (\n'
        '  set "PYTHON=%WAVEFOUNDRY_TOOL_VENV%\\Scripts\\python.exe"\n'
        ') else (\n'
        '  set "PYTHON=%USERPROFILE%\\.wavefoundry\\venv\\Scripts\\python.exe"\n'
        ')\n'
        'if not exist "%PYTHON%" set "PYTHON=python3"\n'
    )
    docs_lint_src = (
        "#!/usr/bin/env bash\n"
        "# Canonical docs-lint launcher — .wavefoundry/bin/docs-lint\n"
        "# Resolves repo root from this script's location and delegates to docs_lint.py.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'cd "$REPO_ROOT"\n'
        'exec "$PYTHON" ".wavefoundry/framework/scripts/docs_lint.py" "$@"\n'
    )
    docs_gardener_src = (
        "#!/usr/bin/env bash\n"
        "# Canonical docs-gardener launcher — .wavefoundry/bin/docs-gardener\n"
        "# Resolves repo root from this script's location and delegates to docs_gardener.py.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'exec "$PYTHON" "$REPO_ROOT/.wavefoundry/framework/scripts/docs_gardener.py" "$@"\n'
    )
    wave_dashboard_src = (
        "#!/usr/bin/env bash\n"
        "# Persistent dashboard launcher — .wavefoundry/bin/wave-dashboard\n"
        "# Starts the local dashboard server under nohup so it survives shell exit.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'LOG="$REPO_ROOT/.wavefoundry/logs/dashboard.log"\n'
        'mkdir -p "$(dirname "$LOG")"\n'
        'nohup "$PYTHON" "$REPO_ROOT/.wavefoundry/framework/scripts/dashboard_server.py" --root "$REPO_ROOT" --open "$@" >"$LOG" 2>&1 &\n'
        'echo "Wave dashboard started (pid $!). Log: $LOG"\n'
    )
    update_indexes_src = (
        "#!/usr/bin/env bash\n"
        "# Incremental index updater — .wavefoundry/bin/update-indexes\n"
        "# Runs the normal post-edit docs/code refresh through setup_index.py.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'cd "$REPO_ROOT"\n'
        'exec "$PYTHON" ".wavefoundry/framework/scripts/setup_index.py" --root "$REPO_ROOT" --background-code --verbose\n'
    )
    setup_wavefoundry_src = (
        "#!/usr/bin/env bash\n"
        "# Canonical setup-wavefoundry launcher — .wavefoundry/bin/setup-wavefoundry\n"
        "# Resolves repo root from this script's location and delegates to setup_wavefoundry.py.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'cd "$REPO_ROOT"\n'
        'exec "$PYTHON" ".wavefoundry/framework/scripts/setup_wavefoundry.py" "$@"\n'
    )
    upgrade_wavefoundry_src = (
        "#!/usr/bin/env bash\n"
        "# Canonical upgrade-wavefoundry launcher — .wavefoundry/bin/upgrade-wavefoundry\n"
        "# Resolves repo root from this script's location and delegates to upgrade_wavefoundry.py.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'cd "$REPO_ROOT"\n'
        'exec "$PYTHON" ".wavefoundry/framework/scripts/upgrade_wavefoundry.py" "$@"\n'
    )
    mcp_server_src = (
        "#!/usr/bin/env bash\n"
        "# Canonical MCP server launcher — .wavefoundry/bin/mcp-server\n"
        "# Resolves repo root from this script's location and starts the Wavefoundry MCP server.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'cd "$REPO_ROOT"\n'
        'exec "$PYTHON" ".wavefoundry/framework/scripts/server.py" --root . "$@"\n'
    )
    wave_gate_src = (
        "#!/usr/bin/env bash\n"
        "# Canonical wave-gate launcher — .wavefoundry/bin/wave-gate\n"
        "# Resolves repo root from this script's location and delegates to wave_gate.py.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'cd "$REPO_ROOT"\n'
        'exec "$PYTHON" ".wavefoundry/framework/scripts/wave_gate.py" "$@"\n'
    )
    lifecycle_id_src = (
        "#!/usr/bin/env bash\n"
        "# Canonical lifecycle-id launcher — .wavefoundry/bin/lifecycle-id\n"
        "# Mints lifecycle prefixes for waves and changes. Prefer the MCP wave_new_*\n"
        "# tools (they borrow from future buckets on collision); this CLI is the\n"
        "# venv-aware fallback when the MCP server is unavailable.\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        + _venv_block
        + 'cd "$REPO_ROOT"\n'
        'exec "$PYTHON" ".wavefoundry/framework/scripts/lifecycle_id.py" "$@"\n'
    )
    write_text(bin_dir / "docs-lint", docs_lint_src, executable=True)
    write_text(bin_dir / "docs-gardener", docs_gardener_src, executable=True)
    write_text(bin_dir / "wave-dashboard", wave_dashboard_src, executable=True)
    write_text(bin_dir / "update-indexes", update_indexes_src, executable=True)
    write_text(bin_dir / "setup-wavefoundry", setup_wavefoundry_src, executable=True)
    write_text(bin_dir / "upgrade-wavefoundry", upgrade_wavefoundry_src, executable=True)
    write_text(bin_dir / "mcp-server", mcp_server_src, executable=True)
    write_text(bin_dir / "wave-gate", wave_gate_src, executable=True)
    write_text(bin_dir / "lifecycle-id", lifecycle_id_src, executable=True)
    for stale in ["upgrade-wavefoundry.bat", "wave_dashboard", "register-codex-mcp", "wave-id"]:
        stale_path = bin_dir / stale
        if stale_path.exists():
            stale_path.unlink()


def render_git_hooks(repo_root: Path) -> None:
    """Write git hook scripts to .wavefoundry/git-hooks/ for indexer integration.

    Install with: git config core.hooksPath .wavefoundry/git-hooks
    """
    hooks_dir = repo_root / ".wavefoundry" / "git-hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in GIT_HOOK_NAMES:
        write_text(hooks_dir / name, git_hook_source(name), executable=True)


def render_windsurf_hooks(repo_root: Path) -> None:
    config = {
        "hooks": {
            "pre_write_code": [
                {"command": launcher_command(".windsurf/hooks/seed-protect"), "show_output": True}
            ],
            "post_write_code": [
                {"command": launcher_command(".windsurf/hooks/docs-lint"), "show_output": True}
            ],
        }
    }
    write_text(repo_root / ".windsurf" / "hooks.json", json.dumps(config, indent=2) + "\n")


def render_aiignore(repo_root: Path) -> None:
    """Keep ``.aiignore`` focused on local index artifacts.

    Framework seed prompts are intentionally **not** listed: hosts that honor
    ``.aiignore`` would block reads; canonical seeds should stay readable. Seed
    edits use ``seed_edit_allowed`` and platform hooks where installed.
    """
    aiignore = repo_root / ".aiignore"
    index_block = [
        "# Wavefoundry semantic index (binary and per-machine — not project source)",
        ".wavefoundry/index/",
        ".wavefoundry/framework/index/",
        "",
        "# Wavefoundry runtime lock files (host-local process/test locks — not project source)",
        ".wavefoundry/*.lock",
        ".wavefoundry/framework/*.lock",
    ]
    lines: list[str] = []
    if aiignore.exists():
        for line in aiignore.read_text(encoding="utf-8").splitlines():
            if ".wavefoundry/framework/seeds/*.prompt.md" in line:
                continue
            if "Protect seed prompts" in line:
                continue
            if "Protect wave seed prompts" in line:
                continue
            if "Junie to edit seed prompts" in line:
                continue
            if "Junie reads or writes" in line:
                continue
            if "explicitly updating the seed pack" in line:
                continue
            lines.append(line)

    def _is_index_meta_line(line: str) -> bool:
        s = line.strip()
        return s in (
            ".wavefoundry/index/",
            ".wavefoundry/framework/index/",
            ".wavefoundry/*.lock",
            ".wavefoundry/framework/*.lock",
        ) or s.startswith("# Wavefoundry semantic index") or s.startswith(
            "# Wavefoundry runtime lock files"
        )

    rest = [ln for ln in lines if not _is_index_meta_line(ln)]
    while rest and rest[-1] == "":
        rest.pop()
    lines_out = list(index_block)
    if rest:
        lines_out.append("")
        lines_out.extend(rest)
    write_text(aiignore, "\n".join(lines_out).rstrip() + "\n")


def render_upgrade_skill(repo_root: Path) -> None:
    content = """# Claude skill: Upgrade wave framework

**Backwards-compatible operator phrase:** *Upgrade wave context* — same checklist.

Use this checklist when intentionally editing the wave framework or repo-local wave surfaces.

## Gate sequence

1. Read `AGENTS.md` and `docs/prompts/upgrade-wavefoundry.prompt.md`.
2. Produce a file-level patch plan and wait for operator approval before broad framework-maintenance edits.
3. Create or update `.wavefoundry/guard-overrides.json` before editing:
   - `.wavefoundry/framework/`
   - `docs/prompts/`
   - `AGENTS.md`
   - tracked hook config files
4. Set `framework_edit_allowed.enabled: true` after the operator approves the file-level plan.
5. Set `seed_edit_allowed.enabled: true` before editing any `.wavefoundry/framework/seeds/*.prompt.md` file.
6. Delete the override file or set both flags back to `false` when the maintenance pass is complete.

## Verification sequence

1. Run framework tests when the test suite is present (development installs only — not included in distribution packs): `python3 -B .wavefoundry/framework/scripts/run_tests.py` (skip if `run_tests.py` does not exist)
2. `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` (hooks, MCP, bin launchers, and `render_agent_surfaces.py` when `docs/agents/guru.md` exists)
3. Backfill `AGENTS.md` auto-Guru tier-1 sections per `seed-050` when missing; ensure `docs/agents/guru.md` exists; re-run step 2 if tier-1 was just added
4. `.wavefoundry/bin/docs-gardener`
5. `.wavefoundry/bin/docs-lint`

## Guardrails

- Keep inventory and drift-detection lanes read-only unless explicit write ownership was granted.
- Update existing canonical docs in place instead of creating parallel files when a topical home already exists.
- Preserve journals, personas, wave archives, and historical records unless the upgrade explicitly retires a live replacement surface.
"""
    write_text(repo_root / ".claude" / "skills" / "upgrade-wave.md", content)


def render_platform_entrypoints(repo_root: Path, platform: str) -> None:
    if platform == "claude":
        remove_files(
            [
                repo_root / ".claude" / "hooks" / "common.sh",
                repo_root / ".claude" / "hooks" / "pre-edit",
                repo_root / ".claude" / "hooks" / "pre-edit.sh",
                repo_root / ".claude" / "hooks" / "pre-edit.cmd",
                repo_root / ".claude" / "hooks" / "post-edit",
                repo_root / ".claude" / "hooks" / "post-edit.sh",
                repo_root / ".claude" / "hooks" / "post-edit.cmd",
                repo_root / ".claude" / "hooks" / "pycache-cleanup",
                repo_root / ".claude" / "hooks" / "pycache-cleanup.py",
                repo_root / ".claude" / "hooks" / "pycache-cleanup.sh",
                repo_root / ".claude" / "hooks" / "pycache-cleanup.cmd",
                repo_root / ".claude" / "hooks" / "simulate-hooks",
                repo_root / ".claude" / "hooks" / "simulate-hooks.sh",
                repo_root / ".claude" / "hooks" / "simulate-hooks.cmd",
            ]
        )
        write_hook_bundle(repo_root / ".claude" / "hooks" / "pre-edit", claude_pre_edit_source())
        write_hook_bundle(repo_root / ".claude" / "hooks" / "post-edit", claude_post_edit_source())
        write_hook_bundle(repo_root / ".claude" / "hooks" / "simulate-hooks", claude_simulate_hooks_source())
        write_hook_bundle(repo_root / ".claude" / "hooks" / "session-capture", claude_stop_source())
        render_claude_settings(repo_root)
        render_mcp_json(repo_root)
        render_upgrade_skill(repo_root)
    elif platform == "cursor":
        remove_files(
            [
                repo_root / ".cursor" / "hooks" / "after-file-edit",
                repo_root / ".cursor" / "hooks" / "after-file-edit.sh",
                repo_root / ".cursor" / "hooks" / "after-file-edit.cmd",
                repo_root / ".cursor" / "hooks" / "seed-warn",
                repo_root / ".cursor" / "hooks" / "seed-warn.sh",
                repo_root / ".cursor" / "hooks" / "seed-warn.cmd",
                repo_root / ".cursor" / "hooks" / "framework-plan-warn",
                repo_root / ".cursor" / "hooks" / "framework-plan-warn.sh",
                repo_root / ".cursor" / "hooks" / "framework-plan-warn.cmd",
                repo_root / ".cursor" / "hooks" / "docs-lint",
                repo_root / ".cursor" / "hooks" / "docs-lint.sh",
                repo_root / ".cursor" / "hooks" / "docs-lint.cmd",
                repo_root / ".cursor" / "hooks" / "reformat.sh",
                repo_root / ".cursor" / "hooks" / "reformat.py",
                repo_root / ".cursor" / "hooks" / "reformat.cmd",
            ]
        )
        write_hook_bundle(repo_root / ".cursor" / "hooks" / "after-file-edit", cursor_after_file_edit_source())
        write_hook_bundle(repo_root / ".cursor" / "hooks" / "seed-warn", cursor_seed_warn_source())
        write_hook_bundle(repo_root / ".cursor" / "hooks" / "framework-plan-warn", cursor_framework_warn_source())
        write_hook_bundle(repo_root / ".cursor" / "hooks" / "docs-lint", cursor_docs_lint_source())
        render_cursor_hooks(repo_root)
        render_cursor_mcp_json(repo_root)
    elif platform == "copilot":
        remove_files(
            [
                repo_root / ".github" / "hooks" / "pre-tool-use",
                repo_root / ".github" / "hooks" / "pre-tool-use.sh",
                repo_root / ".github" / "hooks" / "pre-tool-use.cmd",
                repo_root / ".github" / "hooks" / "post-tool-use",
                repo_root / ".github" / "hooks" / "post-tool-use.sh",
                repo_root / ".github" / "hooks" / "post-tool-use.cmd",
            ]
        )
        write_hook_bundle(repo_root / ".github" / "hooks" / "pre-tool-use", copilot_pre_tool_use_source())
        write_hook_bundle(repo_root / ".github" / "hooks" / "post-tool-use", copilot_post_tool_use_source())
        render_copilot_hooks(repo_root)
    elif platform == "windsurf":
        write_hook_bundle(repo_root / ".windsurf" / "hooks" / "seed-protect", windsurf_seed_protect_source())
        write_hook_bundle(repo_root / ".windsurf" / "hooks" / "docs-lint", windsurf_docs_lint_source())
        render_windsurf_hooks(repo_root)
    elif platform == "junie":
        render_aiignore(repo_root)
        render_junie_mcp_json(repo_root)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render repo-local hook/config surfaces from the wave framework.")
    parser.add_argument("--repo-root", default="", help="Override the repository root.")
    parser.add_argument("--platform", action="append", choices=("claude", "cursor", "copilot", "junie", "windsurf"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or [])
    repo_root = Path(args.repo_root).resolve() if args.repo_root else discover_repo_root()
    platforms = set(args.platform or detect_platforms(repo_root))
    if "copilot" not in platforms:
        remove_copilot_artifacts(repo_root)
    for platform in sorted(platforms):
        render_platform_entrypoints(repo_root, platform)
    from render_agent_surfaces import render_agent_surfaces

    render_agent_surfaces(repo_root)
    render_bin_launchers(repo_root)
    render_git_hooks(repo_root)
    for ds in repo_root.rglob(".DS_Store"):
        try:
            ds.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
