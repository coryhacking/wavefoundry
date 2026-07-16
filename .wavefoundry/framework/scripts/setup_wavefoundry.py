#!/usr/bin/env python3
"""Wavefoundry harness bootstrap entrypoint.

Single command that completes install Phase 1: platform host configs + bin/
launchers (via render_platform_surfaces.py), venv + framework deps + semantic
indexes (via setup_index.py), and an MCP server dry-run smoke test (via
`server.py --dry-run`).

Run after the lifecycle epoch is set in `docs/workflow-config.json` (Phase 1
step 1.1 in `wavefoundry-install-log.md`). On clean exit, restart your AI agent
so the MCP server becomes available; Phase 2 begins.

Forwards argv to setup_index.py for venv / dep / index configuration. The
render and dry-run steps receive the resolved target repository root. Setup
installs prospective framework/carrier behavior only: it never creates,
migrates, repairs, or rewrites target-project wave event state.
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
import subprocess_util  # shared subprocess isolation (wave 1p8gu)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Activate the shared tool venv IN-PROCESS before any heavy work (wave 1p7pl/1p802). This is a
# no-op on a fresh box (the venv does not exist yet). If the existing venv was built for a different
# Python minor, do NOT exit here: setup is the repair path and setup_index will recreate the stale venv.
venv_bootstrap.activate_tool_venv(allow_version_mismatch=True)
# Wave 1p8gv: CLI entry — UTF-8 stdout/stderr so non-ASCII prints never raise on a cp1252 console.
cli_stdio.configure_utf8_stdio()


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


def _run_render_platform_surfaces(repo_root: Path) -> int:
    """Render surfaces for the same explicit target passed to public setup.

    ``setup --root`` may target a repository other than the checkout containing
    this script.  Passing the resolved root through avoids silently rendering
    the framework checkout while indexing the requested target.
    """
    script_path = _SCRIPTS_DIR / "render_platform_surfaces.py"
    if not script_path.exists():
        print(f"ERROR: render_platform_surfaces.py not found at {script_path}", file=sys.stderr)
        return 1
    result = subprocess_util.isolated_run(
        [sys.executable, str(script_path), "--repo-root", str(repo_root)],
        check=False,
    )
    return result.returncode


def _run_mcp_server_dry_run(repo_root: Path) -> int:
    """Invoke `python3 server.py --dry-run` to verify the MCP launch shape.

    This catches startup misconfigurations (missing deps, broken imports, framework
    state issues) before the operator restarts their agent. Use the same `python3`
    command that generated MCP configs use, not `sys.executable`, so setup catches
    PATH/interpreter mismatches before the host does. (Only reached after
    ``ensure_python_resolves`` confirms `python3` resolves to Python 3.11+.)
    """
    script_path = _SCRIPTS_DIR / "server.py"
    if not script_path.exists():
        print(f"ERROR: server.py not found at {script_path}", file=sys.stderr)
        return 1
    result = subprocess_util.isolated_run(
        [
            venv_bootstrap.MCP_PYTHON_COMMAND,
            str(script_path),
            "--root",
            str(repo_root),
            "--dry-run",
        ],
        check=False,
    )
    return result.returncode


def _resolve_setup_root(args: list[str]) -> Path:
    """Resolve the repo root the same way setup_index's --root flag does (default: cwd)."""
    for i, token in enumerate(args):
        if token == "--root" and i + 1 < len(args):
            return Path(args[i + 1]).expanduser().resolve()
        if token.startswith("--root="):
            return Path(token.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


def _provision_lifecycle_policy_if_absent(root: Path) -> int:
    """Fresh repos get the lifecycle-ID scheme-v2 policy automatically — no install step.

    Runs ``materialize_lifecycle_policy`` ONLY when ``docs/workflow-config.json``
    has no ``lifecycle_id_policy`` block (a genuinely un-provisioned repo).
    A repo with an existing block — v1 or v2 — is left untouched here: the v1→v2
    migration of configured repos is the upgrade pipeline's job (Phase 2c), not
    setup's, so re-running setup as a repair step never flips an existing repo's
    ID scheme.

    Anchor guard: provisioning only runs when ``root`` is actually a Wavefoundry
    repo root (the extracted ``.wavefoundry/framework/`` is present — true for
    every install, since the pack is extracted before setup). Without this, a
    setup invoked from a non-root cwd would provision a stray policy into an
    arbitrary directory that then poisons repo-root discovery.
    """
    import json

    if not (root / ".wavefoundry" / "framework").is_dir():
        print(
            f"lifecycle policy: {root} has no .wavefoundry/framework/ — not a "
            "Wavefoundry repo root; skipping provisioning (extract the framework "
            "pack first, or pass --root).",
            flush=True,
        )
        return 0

    cfg = root / "docs" / "workflow-config.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"ERROR: {cfg} exists but could not be parsed ({exc}); "
                "fix the JSON and re-run setup.",
                file=sys.stderr,
            )
            return 1
        if isinstance(data, dict) and isinstance(data.get("lifecycle_id_policy"), dict):
            print(
                "lifecycle policy: existing lifecycle_id_policy found — left unchanged "
                "(configured repos migrate via the upgrade pipeline, not setup).",
                flush=True,
            )
            return 0
    import upgrade_wavefoundry

    try:
        print(upgrade_wavefoundry.materialize_lifecycle_policy(root), flush=True)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


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


def main(argv: list[str] | None = None) -> int:
    # Wave 1p6et: `--check-gpu` prints the GPU/provider diagnostic and exits WITHOUT running setup.
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-gpu" in args:
        return _run_gpu_check()
    # Step 0: provision the lifecycle-ID policy for un-provisioned (fresh) repos.
    # Runs BEFORE indexing so no ID is ever minted pre-policy and the docs index
    # embeds the final config. No-op when a policy block already exists.
    _print_step("Step 0/3: lifecycle-ID policy (fresh repos auto-provision; existing configs untouched)")
    repo_root = _resolve_setup_root(args)
    rc = _provision_lifecycle_policy_if_absent(repo_root)
    if rc != 0:
        print(
            f"\nERROR: lifecycle policy provisioning failed with rc={rc}. Harness setup aborted.",
            file=sys.stderr,
        )
        return rc

    # Step 1: materialize docs/prompt carriers before setup_index walks the
    # repository. Otherwise a fresh install publishes a completed docs epoch
    # and then immediately creates unindexed framework-owned documents.
    _print_step("Step 1/3: render bin/ launchers and host configs (render_platform_surfaces.py)")
    rc = _run_render_platform_surfaces(repo_root)
    if rc != 0:
        print(
            f"\nERROR: render_platform_surfaces.py exited with rc={rc}. "
            f"No semantic index was built; fix the surface error and re-run setup.",
            file=sys.stderr,
        )
        return rc

    # Step 2: venv + framework deps + semantic indexes (via setup_index.py).
    # argv is forwarded so operators can pass --root, --full, etc.
    _print_step("Step 2/3: venv + framework deps + semantic indexes (setup_index.py)")
    setup_index = _load_setup_index()
    rc = int(setup_index.main(argv))
    if rc != 0:
        print(
            f"\nERROR: setup_index.py exited with rc={rc}. Harness setup aborted.",
            file=sys.stderr,
        )
        return rc

    # Step 2b: verify the committed `command: "python3"` launchers resolve (DETECT + GUIDE; setup
    # does NOT create a shim/symlink or edit PATH — operator decision, wave 1p88t). strict=True: a box
    # where `python3 --version` does not work or does not report Python 3.11+ fails loud before
    # rendering surfaces or smoke-testing MCP. The agent/operator must fix the prerequisite before
    # proceeding.
    venv_bootstrap.ensure_python_resolves(strict=True)

    # Step 3: MCP server dry-run smoke test.
    _print_step("Step 3/3: verify MCP server can start (server.py --dry-run)")
    rc = _run_mcp_server_dry_run(repo_root)
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
        "Next: fully quit and reopen your AI agent in this project, or start a fresh "
        "conversation after your host's MCP restart command, so the MCP server becomes available. "
        "Do not resume an old session that started before setup completed. "
        "Then mark Phase 1 complete in .wavefoundry/install-log.md and proceed to Phase 2 "
        "by calling wave_install_audit().",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
