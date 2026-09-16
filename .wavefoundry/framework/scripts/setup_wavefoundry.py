#!/usr/bin/env python3
"""Wavefoundry harness bootstrap entrypoint.

Single command that completes install Phase 1: platform host configs + bin/
launchers (via render_platform_surfaces.py), venv + framework dependencies,
an MCP server dry-run smoke test, local storage reconciliation, and semantic +
graph index publication (via setup_index.py). Historical-memory validation
remains agent-owned and does not block core setup.

Run after the lifecycle epoch is set in `docs/workflow-config.json` (Phase 1
step 1.1 in the live `.wavefoundry/install-log.md`, created from
`.wavefoundry/framework/install/install-log.template.md`). On clean exit,
restart your AI agent so the MCP server becomes available; Phase 2 begins.

Forwards argv to setup_index.py for venv / dep / index configuration. The
render and dry-run steps receive the resolved target repository root. Setup
installs prospective framework/carrier behavior only: it never creates,
migrates, repairs, or rewrites target-project review event state. Historical
memory backfill writes only rebuildable candidate/disposition state and memory
records selected by an agent.
"""
from __future__ import annotations

import importlib.util
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import subprocess_util  # shared subprocess isolation (wave 1p8gu)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Activation belongs to the ordinary setup branch in main: --check must not
# execute site-packages .pth hooks, including when imported by wf_cli.
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


def _print_help() -> None:
    print(
        "usage: wf setup [--root PATH] [setup-index options]\n\n"
        "Provision Wavefoundry dependencies and surfaces, verify the MCP server, "
        "reconcile local storage, and publish the core indexes. Historical-memory "
        "validation remains agent-owned and may remain pending.\n\n"
        "options:\n"
        "  --root PATH    target repository (defaults to the current project)\n"
        "  --check        assess local setup without repairs (exit 0 ready, 1 action, 2 unknown)\n"
        "  --json         with --check, emit the versioned assessment as JSON\n"
        "  --check-gpu    print the provider diagnostic without running setup\n"
        "  --confirm-hosts-stopped  confirm all repository MCP hosts are stopped\n"
        "  --rebuild-storage  rebuild local storage instead of transferring it\n"
        "  -h, --help     show this help without changing the project\n\n"
        "Other index/provider options are forwarded to setup_index.py. During "
        "candidate-bearing historical-memory publication, --background-code "
        "and --background-docs are intentionally ignored so both semantic "
        "layers converge synchronously under the publication receipt."
    )


def _run_render_platform_surfaces(repo_root: Path) -> int:
    """Render surfaces for the same explicit target passed to public setup.

    ``setup --root`` may target a repository other than the checkout containing
    this script.  Passing the resolved root through avoids silently rendering
    the framework checkout while indexing the requested target.

    Wave 1u2b0 (1u2az): install is one of the two operator-run orchestrations
    allowed to render the MCP permission allowlist, so it passes
    ``--include-permissions``. The agent-invocable ``wf_sync_surfaces`` render
    never passes that switch.
    """
    script_path = _SCRIPTS_DIR / "render_platform_surfaces.py"
    if not script_path.exists():
        print(f"ERROR: render_platform_surfaces.py not found at {script_path}", file=sys.stderr)
        return 1
    result = subprocess_util.isolated_run(
        [sys.executable, str(script_path), "--repo-root", str(repo_root), "--include-permissions"],
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
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--root")
    parsed, _ = parser.parse_known_args(args)
    return Path(parsed.root).expanduser().resolve() if parsed.root else Path.cwd().resolve()


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


def _workflow_defaults_path(root: Path) -> Path:
    """Resolve the shipped workflow defaults per file, target first then module."""

    target = root / ".wavefoundry" / "framework" / "install" / "workflow-config.defaults.json"
    if target.is_file():
        return target
    packaged = Path(__file__).resolve().parent.parent / "install" / "workflow-config.defaults.json"
    if packaged.is_file():
        return packaged
    raise RuntimeError(
        "missing workflow-config defaults: expected "
        f"{target} or packaged fallback {packaged}"
    )


def _provision_workflow_defaults_if_absent(root: Path) -> int:
    """Merge shipped top-level workflow defaults without replacing operator values."""

    if not (root / ".wavefoundry" / "framework").is_dir():
        print("workflow config: no extracted framework — skipping defaults", flush=True)
        return 0
    cfg = root / "docs" / "workflow-config.json"
    try:
        defaults_path = _workflow_defaults_path(root)
        defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
        data = json.loads(cfg.read_text(encoding="utf-8")) if cfg.is_file() else {}
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(
            f"ERROR: workflow config defaults could not be provisioned ({exc}); "
            "fix the JSON or framework install assets and re-run setup.",
            file=sys.stderr,
        )
        return 1
    if not isinstance(defaults, dict) or not isinstance(data, dict):
        print(
            "ERROR: workflow config and workflow-config.defaults.json must contain JSON objects; "
            "fix them and re-run setup.",
            file=sys.stderr,
        )
        return 1

    added = [key for key in defaults if key not in data]
    if not added:
        print("workflow config: already complete", flush=True)
        return 0
    for key in added:
        data[key] = defaults[key]
    cfg.parent.mkdir(parents=True, exist_ok=True)
    # Wave 1viyu (REL-DEL-2 / CODE-DEL-4): reuse the lifecycle-policy writer so
    # the merge is atomic (same-directory temp + os.replace) and non-ASCII
    # operator values survive as-is (`ensure_ascii=False`) instead of being
    # rewritten as \uXXXX escapes; a write-time OSError surfaces as an ERROR
    # line rather than a traceback.
    import upgrade_wavefoundry

    try:
        upgrade_wavefoundry._atomic_write_json(cfg, data)
    except OSError as exc:
        print(f"ERROR: could not write {cfg}: {exc}", file=sys.stderr)
        return 1
    print(f"workflow config: provisioned {len(added)} default section(s)", flush=True)
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
    if "--check" in args or any(arg.startswith("--check=") for arg in args):
        parser = argparse.ArgumentParser(prog="wf setup --check", allow_abbrev=False)
        parser.add_argument("--check", action="store_true", required=True)
        parser.add_argument("--root", default=None)
        parser.add_argument("--json", action="store_true")
        options = parser.parse_args(args)
        import setup_readiness

        root = Path(options.root).expanduser().resolve() if options.root else Path.cwd().resolve()
        result = setup_readiness.assess_setup(root)
        print(json.dumps(result, sort_keys=True) if options.json else setup_readiness.format_text(result))
        return setup_readiness.exit_code(result)
    if "-h" in args or "--help" in args:
        _print_help()
        return 0
    venv_bootstrap.activate_tool_venv(allow_version_mismatch=True)
    if "--check-gpu" in args:
        return _run_gpu_check()
    repo_root = _resolve_setup_root(args)
    import memory_backfill
    import setup_reconciliation

    try:
        # Setup owns its publication scope. An inherited memory run must not
        # gate the core pass or authorize another lifecycle's checkpoint.
        with setup_reconciliation.session(repo_root, args) as reconciliation:
            with memory_backfill.index_publication_scope(""):
                return _run_setup(repo_root, reconciliation.args, reconciliation)
    except setup_reconciliation.MigrationRequired as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1


def _run_setup(repo_root: Path, args: list[str], reconciliation) -> int:
    # Step 0: provision lifecycle policy and required workflow defaults.
    # Runs BEFORE indexing so no ID is ever minted pre-policy and the docs index
    # embeds the final config. No-op when a policy block already exists.
    _print_step("Step 0/4: workflow config policy + required defaults (absent-only)")
    rc = _provision_lifecycle_policy_if_absent(repo_root)
    if rc != 0:
        print(
            f"\nERROR: lifecycle policy provisioning failed with rc={rc}. Harness setup aborted.",
            file=sys.stderr,
        )
        return rc
    rc = _provision_workflow_defaults_if_absent(repo_root)
    if rc != 0:
        print(
            f"\nERROR: workflow config default provisioning failed with rc={rc}. Harness setup aborted.",
            file=sys.stderr,
        )
        return rc

    # Step 1: materialize docs/prompt carriers before setup_index walks the
    # repository. Otherwise a fresh install publishes a completed docs epoch
    # and then immediately creates unindexed framework-owned documents.
    _print_step("Step 1/4: render bin/ launchers and host configs (render_platform_surfaces.py)")
    rc = _run_render_platform_surfaces(repo_root)
    if rc != 0:
        print(
            f"\nERROR: render_platform_surfaces.py exited with rc={rc}. "
            f"No semantic index was built; fix the surface error and re-run setup.",
            file=sys.stderr,
        )
        return rc

    # Wave 1u8r2: older releases generated one archived-memory pointer per
    # body. Migrate that exact generated directory before the first index walk;
    # repositories without it remain untouched.
    import memory_records
    try:
        migrated_manifest = memory_records.migrate_legacy_memory_pointers(repo_root)
    except (OSError, ValueError) as exc:
        print(
            f"\nERROR: legacy memory pointer migration failed: {exc}",
            file=sys.stderr,
        )
        return 1
    if migrated_manifest is not None:
        print(f"Migrated legacy memory pointers to {migrated_manifest}")

    # Storage transfer requires the provisioned runtime, and precedes every
    # smoke test or index reader that could encounter the old format.
    _print_step("Step 2/4: provision framework dependencies (no index publication)")
    setup_index = _load_setup_index()
    rc = int(setup_index.main([*args, "--deps-only"]))
    if rc != 0:
        print(
            f"\nERROR: setup dependency provisioning exited with rc={rc}. Harness setup aborted.",
            file=sys.stderr,
        )
        return rc

    reconciliation.prepare()

    # Step 2b: verify the committed `command: "python3"` launchers resolve (DETECT + GUIDE; setup
    # does NOT create a shim/symlink or edit PATH — operator decision, wave 1p88t). strict=True: a box
    # where `python3 --version` does not work or does not report Python 3.11+ fails loud before
    # rendering surfaces or smoke-testing MCP. The agent/operator must fix the prerequisite before
    # proceeding.
    venv_bootstrap.ensure_python_resolves(strict=True)

    # Step 3: MCP server dry-run smoke test.
    _print_step("Step 3/4: verify MCP server can start (server.py --dry-run)")
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

    import memory_backfill

    try:
        run_id = memory_backfill.ensure_run(repo_root, "setup")
        summary = memory_backfill.sync_inventory(repo_root, run_id)
        summary = memory_backfill.reconcile_index_publication(repo_root, run_id)
    except OSError as exc:
        print(
            f"\nERROR: historical wave inventory was refused: {exc}",
            file=sys.stderr,
        )
        return 1
    index_args = reconciliation.index_args(args)
    partial_options = {
        "--deps-only", "--prewarm-only", "--docs-only", "--code-only", "--graph-only",
    }
    core_requested = not any(arg in partial_options for arg in index_args)
    # A recovered memory receipt proves that publication only. Ordinary code
    # may have changed since then; let incremental indexing refresh it while
    # reusing unchanged vectors, without re-adopting the completed memory run.
    _print_step("Step 4/4: build semantic indexes")
    publication_pending = (
        int(summary.get("candidates_drafted") or 0) > 0
        and summary["state"] == "ready_for_index"
        and core_requested
    )
    if publication_pending:
        # The receipt identifies one foreground epoch. A detached layer
        # could begin before the lifecycle reconciles that receipt and
        # overwrite the latest attempt identity, so lifecycle publication
        # deliberately converges both semantic layers synchronously.
        index_args = [
            arg
            for arg in index_args
            if arg not in {"--background-code", "--background-docs"}
        ]
    with reconciliation.publication():
        with memory_backfill.index_publication_scope(run_id if publication_pending else ""):
            rc = int(setup_index.main(index_args))
    if rc != 0:
        recovered = memory_backfill.reconcile_index_publication(repo_root, run_id)
        if publication_pending and recovered["state"] == "awaiting_validation":
            print(
                "\nHistorical wave sources changed before index publication; "
                "the changed waves were requeued for validation. Rebuilding "
                "the core indexes while memory validation remains pending.",
                file=sys.stderr,
            )
            # One bounded retry, without memory authority. Never turn an
            # unrelated index failure into a successful setup.
            publication_pending = False
            summary = recovered
            with reconciliation.publication():
                with memory_backfill.index_publication_scope(""):
                    rc = int(setup_index.main(index_args))
        if rc != 0:
            return rc
    if publication_pending:
        try:
            memory_backfill.complete_index_publication(repo_root, run_id)
        except Exception as exc:
            print(
                "\nERROR: the index epoch published but its historical-memory "
                f"checkpoint was not confirmed: {exc}. Rerun ordinary `wf setup`; "
                "the durable epoch receipt preserves completed memory publication.",
                file=sys.stderr,
            )
            return 1
    reconciliation.complete()

    if not core_requested or any(arg in {"--background-code", "--background-docs"} for arg in index_args):
        print(
            "\nSelected setup work complete; full core readiness was not verified. "
            "Run ordinary `wf setup` to complete all core indexes.",
            flush=True,
        )
        return 0

    import setup_readiness

    try:
        setup_readiness.write_setup_stamp(repo_root)
    except (OSError, ValueError) as exc:
        print(f"Setup completed, but its advisory assessment stamp could not be written: {exc}", file=sys.stderr)

    if summary["eligible_waves"] > 0 and summary["state"] not in {"ready_for_index", "indexed"}:
        print(
            "\nCore setup is ready; historical-memory validation remains pending.\n"
            + json.dumps(summary, indent=2, sort_keys=True)
            + "\nRun memory_backfill(mode='create', entry_path='setup') and "
            "memory_validate for each candidate, then rerun ordinary `wf setup`. "
            "The durable memory run remains pending until its authoritative "
            "validation census and publication checkpoint complete. "
            "Fully quit and reopen your AI agent, or start a fresh conversation "
            "after restarting MCP, to use the core indexes.",
            flush=True,
        )
        return 0

    print(
        "\n=== Wavefoundry harness setup complete. ===\n"
        "Next: fully quit and reopen your AI agent in this project, or start a fresh "
        "conversation after your host's MCP restart command, so the MCP server becomes available. "
        "Do not resume an old session that started before setup completed. "
        "Then mark Phase 1 complete in .wavefoundry/install-log.md and proceed to Phase 2 "
        "by calling wf_audit_install().",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
