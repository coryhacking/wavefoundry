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

# Wave 1p7pm (1p7pb-adr): no tracked surface embeds a machine-specific venv path. The MCP configs
# + hook commands name the byte-identical `python` command on a repo-relative script/`.py` body, and
# the bin shims are thin `exec python <script>` forwarders. Each rendered `.py` body self-bootstraps
# into the tool venv first-line via the single `venv_bootstrap` resolver (goal B). The only surface
# still carrying its own venv resolver is `git_hook_source` (out of scope — owned by 1p7pn).


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
    if (repo_root / ".agents").exists():
        platforms.add("antigravity")
    return platforms


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, executable: bool = False) -> None:
    ensure_parent(path)
    # newline="" disables newline translation so the embedded line terminators are written VERBATIM,
    # byte-identical on every rendering host (wave 1p7tz). With the default newline=None, a re-render
    # on native Windows translates every "\n" → os.linesep ("\r\n"): the `wf.cmd` source (which
    # embeds "\r\n") would become "\r\r\n" (doubled CR, breaks %REPO_ROOT%), and the `wf` bash shim +
    # rendered `.py` hooks would gain CRLF shebangs (break git-bash/WSL2). The source strings already
    # carry the correct terminators per file (cmd=CRLF, bash/.py=LF), so newline="" is right for all.
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(content)
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


def launcher_command(rel_base: str, project_dir_var: str | None = None) -> str:
    """Launcher command for a hook config — ``python`` invoking the ``.py`` hook body directly.

    Wave 1p7pm (1p7pb-adr): the committed launcher names the byte-identical ``python`` interpreter
    on the project-relative ``.py`` body — no ``.cmd``/``.sh`` trampoline, no ``cmd.exe /c`` wrapper.
    The ``.py`` body self-bootstraps into the tool venv (first-line ``venv_bootstrap`` import), so the
    only allowed per-OS difference here is the **env-var sigil** used to anchor the path: POSIX shells
    expand ``$VAR`` while ``cmd.exe`` expands ``%VAR%``. The interpreter (``python``) and the ``.py``
    path are identical across every render host.

    Wave 1p590: NEVER emit a machine-absolute path — tracked surfaces must work on any clone.

    ``project_dir_var`` (1p6dx): a host's project-root env var (e.g. ``"CLAUDE_PROJECT_DIR"``) to
    ANCHOR the command so it resolves regardless of the host's working directory. A host runs the
    hook command through a shell (``/bin/sh -c`` / ``cmd /c``) from a cwd that is NOT guaranteed to
    be the repo root, so a BARE relative path fails with ``No such file or directory`` (observed on
    Claude Code Stop hooks). The anchored form is quoted so a repo path with spaces still works.
    ``None`` keeps the legacy project-relative form for hosts whose project-root var is unverified
    (Cursor/Copilot/Windsurf) — those likely have the same latent issue and should each be anchored
    on their own var once verified."""
    if os.name == "nt":
        # The interpreter (`python`) and the `.py` path are byte-identical with the POSIX branch; the
        # ONLY per-OS difference is the env-var sigil (`%VAR%` vs `$VAR`), which is shell-specific.
        if project_dir_var:
            return f'python "%{project_dir_var}%/{rel_base}.py"'
        return f'python "{rel_base}.py"'
    if project_dir_var:
        return f'python "${project_dir_var}/{rel_base}.py"'
    return f'python "{rel_base}.py"'


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


def write_hook_bundle(base_path: Path, python_source: str) -> None:
    """Render only the ``.py`` hook body — the host launches it via ``python <body>.py`` directly.

    Wave 1p7pm (1p7pb-adr): the ``.sh``/``.cmd`` trampolines are retired. ``launcher_command``
    now names ``python`` on the project-relative ``.py`` path, and the body self-bootstraps into
    the tool venv (first-line ``venv_bootstrap`` import via ``compose_script``), so no shell
    wrapper is needed and the committed launcher is byte-identical across render hosts. Any stale
    trampolines left by an older render are removed here so a re-render cleans up the cutover."""
    write_text(base_path.with_suffix(".py"), python_source, executable=True)
    remove_files([base_path, base_path.with_suffix(".cmd"), base_path.with_suffix(".sh")])


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
            # Wave 1p7tz: the `bin/docs-lint` wrapper was retired — invoke docs_lint.py directly under
            # the venv interpreter (the body already re-exec'd into the venv first-line, so
            # sys.executable IS the venv Python).
            docs_lint = REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "docs_lint.py"
            result = run_command([sys.executable, str(docs_lint)])
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


        def maybe_trigger_reindex(file_path: str) -> None:
            if not should_reindex(file_path):
                return
            indexer = REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
            if not indexer.exists():
                return
            # The body has already re-exec'd into the tool venv (first-line bootstrap), so
            # sys.executable IS the venv Python — an absolute path; never re-resolve a token.
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
            # Wave 1p7pn (M-3): detach per-OS — on Windows start_new_session is a no-op, so without
            # creationflags the child stays in the host's process group and dies with the hook. Mirror
            # server_impl.py / dashboard_server._daemonize.
            _detach_kwargs = {}
            if os.name == "nt":
                _detach_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                _detach_kwargs["start_new_session"] = True
            subprocess.Popen(
                [python_exec, str(indexer), "--root", str(REPO_ROOT)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(REPO_ROOT),
                close_fds=os.name != "nt",
                **_detach_kwargs,
            )
        """
    ).strip()


# Wave 1p7pm (1p7pb-adr): the host launches each hook body via `python <body>.py` directly (no
# `.sh`/`.cmd` trampoline). The first thing every rendered body does — after the mandatory
# `from __future__` directive, which must stay the genuine first statement — is re-exec into the
# shared tool venv via the single `venv_bootstrap` resolver: stdlib-only, no-op when already in the
# venv or when it does not exist yet. The hook lives at `.claude/hooks/`, `.cursor/hooks/`, … (so
# parents[2] == repo root); the framework scripts dir is added to sys.path so the import resolves.
_FUTURE_LINE = "from __future__ import annotations"
HOOK_BOOTSTRAP = dedent(
    """
    import sys as _wf_sys
    from pathlib import Path as _WfPath

    _WF_SCRIPTS = _WfPath(__file__).resolve().parents[2] / ".wavefoundry" / "framework" / "scripts"
    if _WF_SCRIPTS.is_dir() and str(_WF_SCRIPTS) not in _wf_sys.path:
        _wf_sys.path.insert(0, str(_WF_SCRIPTS))
    try:
        import venv_bootstrap as _wf_venv_bootstrap

        _wf_venv_bootstrap.reexec_into_tool_venv()
    except Exception:
        pass
    """
).strip()


def _strip_leading_future(text: str) -> str:
    """Drop a leading ``from __future__ import annotations`` so ``compose_script`` can hoist it.

    The directive must be the genuine first statement of the file; ``compose_script`` emits exactly
    one copy at the top, ahead of the venv bootstrap, so any copy carried by a helper/body section is
    removed here to avoid a misplaced (illegal) second occurrence."""
    lines = text.split("\n")
    out = [ln for ln in lines if ln.strip() != _FUTURE_LINE]
    # Collapse a blank line left at the very top after stripping a leading future import.
    while out and out[0].strip() == "":
        out.pop(0)
    return "\n".join(out)


def compose_script(body: str, include_helpers: bool = True) -> str:
    # `from __future__` MUST be the first statement (compiler rule); the venv bootstrap follows as the
    # first *executable* statement, then the helpers/body (with any duplicate future import stripped).
    parts = ["#!/usr/bin/env python3\n", _FUTURE_LINE, "\n\n", HOOK_BOOTSTRAP, "\n\n"]
    if include_helpers:
        parts.append(_strip_leading_future(hook_helpers()))
        parts.append("\n\n")
    parts.append(_strip_leading_future(dedent(body).strip()))
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


        def main(argv: list[str]) -> int:
            if len(argv) != 2:
                print("usage: simulate-hooks.py <entrypoint> <json-payload>", file=sys.stderr)
                return 2
            hook_name, payload = argv
            target = HOOKS.get(hook_name)
            if target is None:
                print(f"unknown hook entrypoint: {hook_name}", file=sys.stderr)
                return 2
            # The body re-exec'd into the tool venv (first-line bootstrap) → sys.executable IS the
            # venv Python (an absolute path); never re-resolve a token.
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
            # The body re-exec'd into the tool venv (first-line bootstrap) → sys.executable IS the
            # venv Python (an absolute path); never re-resolve a token.
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

    Wave 1p7pm: routed through ``compose_script`` (``include_helpers=False`` — it defines its own
    ``_find_repo_root`` etc.) so the rendered body gets the shebang + first-line ``HOOK_BOOTSTRAP``
    and self-bootstraps into the tool venv like every other hook. The body's leading module docstring
    and its own ``from __future__`` line are dropped here — ``compose_script`` emits the canonical
    first-statement ``from __future__`` ahead of the bootstrap.
    """
    return compose_script(
        '''
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
        ''',
        include_helpers=False,
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
            # 1p6dx: anchor on $CLAUDE_PROJECT_DIR — Claude Code runs hooks via /bin/sh from a cwd
            # that is not guaranteed to be the repo root, so a bare relative command fails with
            # "No such file or directory" (observed on the Stop hook every turn).
            "command": launcher_command(f".claude/hooks/{hook['name']}", "CLAUDE_PROJECT_DIR"),
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

    Wave 1p7pm (1p7pb-adr): names the byte-identical ``python`` command on the repo-relative
    ``server.py`` — never a pathed bash launcher (unspawnable on native Windows; the old
    ``bin/mcp-server`` wrapper was retired in 1p7tz). ``setup_wavefoundry.py`` makes ``python``
    resolvable (macOS/Linux symlink, native on Windows); the server then self-bootstraps into the tool
    venv first-line. No machine-specific absolute path is embedded, and the stanza is byte-identical
    across every render host.

    No ``--root .`` arg: ``server_impl._discover_root`` anchors on the server script's OWN install
    location (``server.py`` always lives at ``<root>/.wavefoundry/framework/scripts/``), so the root
    is resolved cwd-independently — more robust than a ``.``-relative ``--root`` and avoids a
    host-specific ``${CLAUDE_PROJECT_DIR}`` that would re-fragment the byte-identical config.
    """
    _merge_mcp_server(
        repo_root / ".mcp.json",
        {
            "command": "python",
            "args": [".wavefoundry/framework/scripts/server.py"],
        },
    )


def render_junie_mcp_json(repo_root: Path) -> None:
    """Merge the Wavefoundry stdio MCP entry into the Junie ``.junie/mcp/mcp.json``.

    Wave 1p7pm (1p7pb-adr): names the byte-identical ``python`` command on the repo-relative
    ``server.py`` (parity with the root ``.mcp.json``) — never a pathed bash launcher (the old
    ``bin/mcp-server`` wrapper was retired in 1p7tz). The server self-bootstraps into the tool venv
    first-line; no absolute path is embedded."""
    _merge_mcp_server(
        repo_root / ".junie" / "mcp" / "mcp.json",
        {
            "command": "python",
            "args": [".wavefoundry/framework/scripts/server.py"],
        },
    )


def render_cursor_mcp_json(repo_root: Path) -> None:
    """Merge the Wavefoundry stdio MCP entry into the Cursor ``.cursor/mcp.json``.

    Wave 1p7pm (1p7pb-adr): names the byte-identical ``python`` command on the repo-relative
    ``server.py`` (parity with the root ``.mcp.json``) — never a pathed bash launcher (the old
    ``bin/mcp-server`` wrapper was retired in 1p7tz). ``cwd: ${workspaceFolder}`` lets Cursor resolve
    the relative script arg against the workspace; ``type: stdio`` is Cursor-specific. The server
    self-bootstraps into the tool venv.
    """
    _merge_mcp_server(
        repo_root / ".cursor" / "mcp.json",
        {
            "type": "stdio",
            "command": "python",
            "args": [".wavefoundry/framework/scripts/server.py"],
            "cwd": "${workspaceFolder}",
        },
    )


def render_antigravity_mcp_json(repo_root: Path) -> None:
    """Merge the Wavefoundry stdio MCP entry into the Antigravity workspace-local config.

    Wave 1p7pm (1p7pb-adr): names the byte-identical ``python`` command on the repo-relative
    ``server.py`` (parity with Claude/Junie) — never a pathed bash launcher (the old
    ``bin/mcp-server`` wrapper was retired in 1p7tz).
    """
    _merge_mcp_server(
        repo_root / ".agents" / "mcp_config.json",
        {
            "command": "python",
            "args": [".wavefoundry/framework/scripts/server.py"],
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
    """Return Python source for a git hook that fires an incremental reindex.

    Wave 1p7pm/1p7pn (1p7pb-adr, M-3): the hook body self-bootstraps into the tool venv first-line via
    the single ``venv_bootstrap`` resolver (``HOOK_BOOTSTRAP``) — venv discovery (``Scripts\\python.exe``
    on Windows, ``bin/python`` on POSIX) is Python's job in ONE place; the old hardcoded
    ``bin/python``/``python3`` body (which re-derived the tool-venv path itself and broke on
    python.org-Windows git-bash) is gone. Shebang is ``#!/usr/bin/env python`` (NOT ``python3`` —
    git-for-Windows git-bash ships ``python``, not ``python3``). The detached reindex spawn uses
    ``sys.executable`` (the re-exec'd venv Python), never a re-resolved token, and never ``os.execv``
    on the Windows path."""
    # Reuse the canonical first-line bootstrap (parents[2] == repo root for `.wavefoundry/git-hooks/<name>`),
    # but with the `python` shebang git-bash needs — so compose_script (which hardcodes `python3`) is not used.
    lines = [
        "#!/usr/bin/env python",
        _FUTURE_LINE,
        "",
        HOOK_BOOTSTRAP,
        "",
        "import os",
        "import subprocess",
        "import sys",
        "from pathlib import Path",
        "",
        "REPO_ROOT = Path(__file__).resolve().parents[2]",
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
        "    # The body re-exec'd into the tool venv (first-line bootstrap) → sys.executable IS the",
        "    # venv Python (an absolute path); never re-resolve a python3/python token.",
        "    # Wave 1p7pn (M-3): detach per-OS — on Windows start_new_session is a no-op, so without",
        "    # creationflags the child stays in git's process group and dies with the hook.",
        "    detach_kwargs = {}",
        "    if os.name == \"nt\":",
        "        detach_kwargs[\"creationflags\"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP",
        "    else:",
        "        detach_kwargs[\"start_new_session\"] = True",
        "    subprocess.Popen(",
        "        [sys.executable, str(indexer), \"--root\", str(REPO_ROOT)],",
        "        stdout=subprocess.DEVNULL,",
        "        stderr=subprocess.DEVNULL,",
        "        cwd=str(REPO_ROOT),",
        "        close_fds=os.name != \"nt\",",
        "        **detach_kwargs,",
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


# Wave 1p7tz: the nine POSIX-only `.wavefoundry/bin/*` operator wrappers were RETIRED (hard cutover,
# operator-directed) in favor of one cross-OS `wf` dispatcher (`wf_cli.py`). Their committed files are
# removed on re-render via this list so a re-render cleans up the cutover.
_RETIRED_BIN_WRAPPERS = (
    "docs-lint",
    "docs-gardener",
    "wave-gate",
    "update-indexes",
    "lifecycle-id",
    "wave-dashboard",
    "upgrade-wavefoundry",
    "setup-wavefoundry",
    "mcp-server",
)


def render_bin_launchers(repo_root: Path) -> None:
    """Write the cross-OS `wf` operator CLI shim pair to .wavefoundry/bin/.

    Wave 1p7tz: a single `wf` (bash) + `wf.cmd` (Windows) shim pair dispatches to `wf_cli.py`
    (which routes each subcommand — `docs-lint`, `docs-gardener`, `gate`, `dashboard`,
    `update-indexes`, `lifecycle-id`, `upgrade`, `setup` — to its existing entry script). This
    replaces the nine POSIX-only bash wrappers retired in this wave (hard cutover). The ONLY per-OS
    difference is the shell wrapper itself (bash vs cmd) — no per-OS *logic* duplication; `wf_cli.py`
    owns the dispatch + the three-tier venv bootstrap (every subcommand re-execs into the venv except
    `setup`, which stays pre-symlink-safe). The `wf` bash shim uses the same `python3`→`python`
    fallback as the retired `setup-wavefoundry` shim so `wf setup` works on a fresh box *before* the
    `python` symlink exists.

    These are the no-MCP operator/CI/terminal CLI fallback. Agents should prefer the MCP tools
    (`wave_validate`, `wave_garden`, …) over invoking `wf` directly.
    """
    bin_dir = repo_root / ".wavefoundry" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    # `wf` (bash): resolve REPO_ROOT from this shim's own location, cd, then run the dispatcher with a
    # `python3`→`python` fallback (P0 setup circularity: `wf setup` runs PRE-symlink on a fresh box, so
    # the shim must not name bare `python`; `wf_cli.py` keeps `setup` on the system interpreter).
    wf_src = (
        "#!/usr/bin/env bash\n"
        "# Wavefoundry operator CLI — .wavefoundry/bin/wf (wave 1p7tz)\n"
        "# Cross-OS dispatcher to the framework entry scripts. `wf <subcommand>` — see `wf --help`.\n"
        "# Uses a python3->python fallback so `wf setup` works PRE-symlink on a fresh box (P0).\n"
        "set -euo pipefail\n"
        'REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        'cd "$REPO_ROOT"\n'
        'if command -v python3 >/dev/null 2>&1; then PYTHON="python3"; else PYTHON="python"; fi\n'
        'exec "$PYTHON" "$REPO_ROOT/.wavefoundry/framework/scripts/wf_cli.py" "$@"\n'
    )

    # `wf.cmd` (Windows): resolve the repo root from %~dp0 and run the dispatcher. Native Windows has
    # `python` (python.org installer), not `python3`. Forward-slash path execution is Windows-smoke-
    # deferred (native Windows is the AC-6 operator gate) but the form mirrors the POSIX shim.
    wf_cmd_src = (
        "@echo off\r\n"
        "REM Wavefoundry operator CLI -- .wavefoundry\\bin\\wf.cmd (wave 1p7tz)\r\n"
        "setlocal\r\n"
        'set "REPO_ROOT=%~dp0..\\.."\r\n'
        'cd /d "%REPO_ROOT%"\r\n'
        'python "%REPO_ROOT%\\.wavefoundry\\framework\\scripts\\wf_cli.py" %*\r\n'
        "exit /b %ERRORLEVEL%\r\n"
    )

    write_text(bin_dir / "wf", wf_src, executable=True)
    write_text(bin_dir / "wf.cmd", wf_cmd_src)

    # Hard cutover: remove the nine retired wrappers' committed files + older stale launchers.
    for stale in (
        *_RETIRED_BIN_WRAPPERS,
        "upgrade-wavefoundry.bat",
        "wave_dashboard",
        "register-codex-mcp",
        "wave-id",
        "register-antigravity-mcp",
    ):
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
    content = """# Claude skill: Upgrade Wavefoundry

**Backwards-compatible operator phrases:** *Upgrade wave framework*, *Upgrade wave context* — same checklist.

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
4. `.wavefoundry/bin/wf docs-gardener`
5. `.wavefoundry/bin/wf docs-lint`

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
    elif platform == "antigravity":
        render_antigravity_mcp_json(repo_root)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render repo-local hook/config surfaces from the wave framework.")
    parser.add_argument("--repo-root", default="", help="Override the repository root.")
    parser.add_argument("--platform", action="append", choices=("claude", "cursor", "copilot", "junie", "windsurf", "antigravity"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or [])
    repo_root = Path(args.repo_root).resolve() if args.repo_root else discover_repo_root()
    # Wave 1p7pm (1p7pb-adr): self-heal `python` resolution on every render so the committed
    # `command: "python"` configs we are about to write stay spawnable (re-points a stale/dangling
    # symlink at the current python3). strict=False — warn (non-fatal) if `python` still won't
    # resolve, never hard-fail a render. Imported lazily so a missing helper can't break rendering.
    try:
        import venv_bootstrap  # the single venv resolver + python-resolution heal (wave 1p7pl/1p7pm)

        venv_bootstrap.ensure_python_resolves(strict=False)
    except Exception:
        pass
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
