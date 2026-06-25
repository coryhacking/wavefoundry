#!/usr/bin/env python3
"""Wavefoundry harness bootstrap entrypoint.

Single command that completes install Phase 1: venv + framework deps + semantic
indexes (via setup_index.py), platform host configs + bin/ launchers (via
render_platform_surfaces.py), and an MCP server dry-run smoke test (via
`server.py --dry-run`).

Run after the lifecycle epoch is set in `docs/workflow-config.json` (Phase 1
step 1.1 in `wavefoundry-install-log.md`). On clean exit, restart your AI agent
so the MCP server becomes available; Phase 2 begins.

Forwards argv to setup_index.py for venv / dep / index configuration. The
render and dry-run steps take no arguments.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)

# Re-exec into the shared tool venv before any heavy work (wave 1p7pl). This is a
# no-op on a fresh box (the venv does not exist yet), so it never blocks setup_index
# from creating the venv; once the venv exists, re-running setup uses the venv Python.
venv_bootstrap.reexec_into_tool_venv()


def _load_setup_index():
    script_path = _SCRIPTS_DIR / "setup_index.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_setup_index", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load setup_index.py from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _print_step(label: str) -> None:
    print(f"\n=== {label} ===", flush=True)


def _run_render_platform_surfaces() -> int:
    """Invoke render_platform_surfaces.py to materialize bin/ launchers and host configs."""
    script_path = _SCRIPTS_DIR / "render_platform_surfaces.py"
    if not script_path.exists():
        print(f"ERROR: render_platform_surfaces.py not found at {script_path}", file=sys.stderr)
        return 1
    result = subprocess.run([sys.executable, str(script_path)], check=False)
    return result.returncode


def _run_mcp_server_dry_run() -> int:
    """Invoke `server.py --dry-run` to verify the MCP server can initialize cleanly.

    This catches startup misconfigurations (missing deps, broken imports, framework
    state issues) before the operator restarts their agent. Failure here means the
    restart would land on a broken MCP server.
    """
    script_path = _SCRIPTS_DIR / "server.py"
    if not script_path.exists():
        print(f"ERROR: server.py not found at {script_path}", file=sys.stderr)
        return 1
    result = subprocess.run(
        [sys.executable, str(script_path), "--dry-run"],
        check=False,
    )
    return result.returncode


def _load_provider_policy():
    # Plain import (not importlib spec): registers as "provider_policy" in sys.modules so the
    # frozen @dataclass annotation evaluation resolves; provider_policy imports onnxruntime lazily
    # so this is cheap and works pre-setup.
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    import provider_policy
    return provider_policy


def _run_gpu_check() -> int:
    """Wave 1p6et: print the embedding-provider / GPU capability diagnostic and exit (no setup).

    Does NOT run the venv/dep/index setup steps. Invoked via ``setup_wavefoundry.py --check-gpu``
    (or ``.wavefoundry/bin/wf setup --check-gpu``).
    """
    provider_policy = _load_provider_policy()
    setup_index = _load_setup_index()
    # Pass setup's bounded probe so the report's selected provider matches what setup/runtime pick
    # (e.g. CoreML on Apple Silicon). The probe loads a model; absent a cached model it degrades to CPU.
    report = provider_policy.diagnostic_report(provider_probe=setup_index._probe_embedding_provider)
    print(provider_policy.format_diagnostic_report(report))
    return 0


def _repo_root_from_args(args: list[str]) -> Path:
    """Repo root from a ``--root <path>`` arg if present, else the scripts dir's grandparent."""
    for i, tok in enumerate(args):
        if tok == "--root" and i + 1 < len(args):
            return Path(args[i + 1]).expanduser().resolve()
        if tok.startswith("--root="):
            return Path(tok.split("=", 1)[1]).expanduser().resolve()
    # _SCRIPTS_DIR = <repo>/.wavefoundry/framework/scripts → repo root is parents[2].
    return _SCRIPTS_DIR.parents[2]


def _print_gui_fallback_guidance(repo_root: Path) -> None:
    """Print the per-machine absolute-venv-path MCP stanza for GUI-launched hosts (wave 1p7pm AC-4/5).

    The committed configs name ``command: "python"``, resolvable for CLI hosts (they inherit the shell
    PATH where setup just symlinked ``python``). GUI-launched hosts (Claude Desktop, Cursor.app) inherit
    only a minimal launchd/registry PATH, so ``python`` may not resolve. This is GUIDANCE only — it does
    NOT overwrite the committed ``.mcp.json`` (the override path is host-specific + per-machine)."""
    import json as _json

    stanza = venv_bootstrap.gui_fallback_mcp_stanza(repo_root)
    print(
        "\nGUI-host note: if a GUI-launched MCP host (Claude Desktop, Cursor.app) can't find `python` "
        "on PATH, set its Wavefoundry MCP command to this absolute-path form (per-machine — do NOT "
        "commit it; the committed `python` form is for CLI hosts):\n"
        f"{_json.dumps(stanza, indent=2)}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    # Wave 1p6et: `--check-gpu` prints the GPU/provider diagnostic and exits WITHOUT running setup.
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-gpu" in args:
        return _run_gpu_check()
    # Step 1: venv + framework deps + semantic indexes (via setup_index.py).
    # argv is forwarded so operators can pass --root, --full, etc.
    _print_step("Step 1/3: venv + framework deps + semantic indexes (setup_index.py)")
    setup_index = _load_setup_index()
    rc = int(setup_index.main(argv))
    if rc != 0:
        print(
            f"\nERROR: setup_index.py exited with rc={rc}. Harness setup aborted.",
            file=sys.stderr,
        )
        return rc

    # Step 1b: make the committed `command: "python"` launchers resolvable (wave 1p7pm; 1p7pb-adr).
    # The venv now exists (Step 1), so on macOS/Linux this symlinks `~/.local/bin/python` -> the
    # stable `python3` and ensures it's on PATH; on Windows it verifies `python` is present + >=3.11.
    # strict=True at setup: a no-Python box fails loud (the committed configs would be dead-on-arrival).
    # Runs on the system interpreter (this script does NOT depend on `python` already resolving — P0).
    venv_bootstrap.ensure_python_resolves(strict=True)
    _print_gui_fallback_guidance(_repo_root_from_args(args))

    # Step 2: render bin/ launchers and platform host configs.
    _print_step("Step 2/3: render bin/ launchers and host configs (render_platform_surfaces.py)")
    rc = _run_render_platform_surfaces()
    if rc != 0:
        print(
            f"\nERROR: render_platform_surfaces.py exited with rc={rc}. "
            f"venv + indexes are in place, but the launchers and host configs were not rendered. "
            f"Re-run setup_wavefoundry after fixing the issue (idempotent).",
            file=sys.stderr,
        )
        return rc

    # Step 3: MCP server dry-run smoke test.
    _print_step("Step 3/3: verify MCP server can start (server.py --dry-run)")
    rc = _run_mcp_server_dry_run()
    if rc != 0:
        print(
            f"\nERROR: MCP server dry-run failed with rc={rc}. "
            f"venv, indexes, and launchers are in place, but the server cannot start. "
            f"Common causes: missing/incompatible deps in the venv, framework state "
            f"corruption. Check the dry-run output above for details.",
            file=sys.stderr,
        )
        return rc

    print(
        "\n=== Wavefoundry harness setup complete. ===\n"
        "Next: restart your AI agent so the MCP server becomes available. "
        "Then mark Phase 1 complete in .wavefoundry/install-log.md and proceed to Phase 2 "
        "by calling wave_install_audit().",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
