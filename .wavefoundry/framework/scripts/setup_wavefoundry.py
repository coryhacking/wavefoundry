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


def main(argv: list[str] | None = None) -> int:
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
