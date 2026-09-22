"""Docs handlers: extracted response ownership."""
from __future__ import annotations

from lifecycle_gate_support import SUBPROCESS_OPS_TIMEOUT_DEFAULT
from lifecycle_gate_support import _diagnostic
from lifecycle_gate_support import subprocess_ops_timeout_seconds
from pathlib import Path
from review_evidence import project_state_publication_lock
from typing import Any
from typing import Optional
import json
import os
import tempfile


def _subprocess_timeout_summary(op: str, timeout_s: float) -> str:
    return (
        f"{op} subprocess exceeded its {timeout_s:.0f}s bound and was stopped. "
        "No partial output is trusted. Re-run the tool; on a legitimately "
        f"slower machine raise docs/workflow-config.json subprocess_ops."
        f"{op}_timeout_seconds (the bound is config-tunable, default "
        f"{SUBPROCESS_OPS_TIMEOUT_DEFAULT:.0f}s)."
    )


def run_garden(root: Path) -> dict:
    """Run docs_gardener and return structured summary (bounded; wave 1seax)."""
    import server_impl

    import subprocess as _subprocess

    script = Path(server_impl.__file__).resolve().parent / "docs_gardener.py"
    timeout_s = subprocess_ops_timeout_seconds(root, "gardener")
    try:
        result = server_impl._mcp_subprocess_run(
            [server_impl._preferred_python(), str(script)],
            cwd=str(root),
            env={**os.environ, "PROJECT_ROOT": str(root)},
            timeout=timeout_s,
        )
    except _subprocess.TimeoutExpired:
        return {
            "passed": False,
            "timed_out": True,
            "files_updated": 0,
            "updated": [],
            "output": _subprocess_timeout_summary("gardener", timeout_s),
        }
    output, truncated = server_impl._bounded_subprocess_output(result.stdout + result.stderr)
    # Stable output contract with docs_gardener.py (wave 1tbvo): one
    # `docs-gardener: updated <path>` line per updated file. Exact-prefix
    # parse — the old "wrote" grep silently matched nothing once the
    # gardener's prose changed, dropping the index-refresh trigger.
    # Parse the COMPLETE stdout, never the bounded text: the bound exists for
    # the human-facing `output` field only, and parsing the shortened value
    # under-counted large runs and emitted a corrupted final path fragment
    # (operator reproduction: 6,000 records -> 2,273 reported).
    _updated_prefix = "docs-gardener: updated "
    updated = [
        l[len(_updated_prefix):].strip()
        for l in result.stdout.splitlines()
        if l.startswith(_updated_prefix)
    ]
    summary = {
        "passed": result.returncode == 0,
        "files_updated": len(updated),
        "updated": updated,
        "output": output,
    }
    if truncated:
        summary["output_truncated"] = True
    return summary


def run_sync_surfaces(root: Path) -> dict:
    """Run render_platform_surfaces and return structured summary.

    Wave 1t72b (1t729): the renderer emits a JSON manifest of the files it
    actually changed via --manifest (recorded inside its write chokepoints);
    the old files_written prose-line grep is retired (it held log lines, not
    paths, and had no consumers).

    Wave 1u2b0 (1u2az) SECURITY INVARIANT: this agent-invocable render must
    NEVER pass the renderer's opt-in permission-allowlist CLI switch (the one
    the operator-run upgrade and install orchestrations pass). Permissions
    rendering (the MCP allowlist merged into .claude/settings.json) is
    reachable only from those orchestrations; adding that switch here would
    reopen the agent permission-escalation channel wave 1u2b0 closed. A test
    pins that this module never names the switch, so keep its spelling out of
    this file entirely, prose included.
    """
    import server_impl

    import subprocess as _subprocess

    script = Path(server_impl.__file__).resolve().parent / "render_platform_surfaces.py"
    timeout_s = subprocess_ops_timeout_seconds(root, "surface_render")
    with tempfile.TemporaryDirectory() as manifest_dir:
        manifest_path = Path(manifest_dir) / "render-manifest.json"
        try:
            result = server_impl._mcp_subprocess_run(
                [server_impl._preferred_python(), str(script), "--manifest", str(manifest_path)],
                cwd=str(root),
                env={**os.environ, "PROJECT_ROOT": str(root)},
                timeout=timeout_s,
            )
        except _subprocess.TimeoutExpired:
            return {
                "passed": False,
                "timed_out": True,
                "written": [],
                "output": _subprocess_timeout_summary("surface_render", timeout_s),
            }
        written: list[str] = []
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            written = [
                str(entry) for entry in payload.get("written") or []
                if isinstance(entry, str)
            ]
        except (OSError, ValueError):
            written = []
    output, truncated = server_impl._bounded_subprocess_output(result.stdout + result.stderr)
    summary = {
        "passed": result.returncode == 0,
        "written": written,
        "output": output,
    }
    if truncated:
        summary["output_truncated"] = True
    return summary


def wf_validate_docs_response(root: Path) -> dict[str, Any]:
    import server_impl

    result = server_impl.run_validate(root)
    status = "ok" if result["passed"] else "error"
    diagnostics = [
        _diagnostic("docs_lint_error", error, recovery_tools=["wf_validate_docs"])
        for error in result["errors"]
    ] + [
        _diagnostic("docs_lint_warning", warning, recovery_tools=["wf_validate_docs"], advisory=True)
        for warning in result["warnings"]
    ]
    return server_impl._response(
        status,
        result,
        diagnostics=diagnostics,
        next_tools=["wf_garden_docs"] if result["passed"] else ["wf_help"],
        usage="wf_garden_docs()" if result["passed"] else "wf_help(goal='maintain_framework')",
    )


def wf_garden_docs_response(root: Path, mode: str = "dry_run", cache: Optional[server_impl.McpRepoCache] = None) -> dict[str, Any]:
    import server_impl

    if (mode or "").strip().lower() == "dry_run":
        return server_impl._response(
            "ok",
            {"mode": "dry_run", "skipped": True},
            diagnostics=[_diagnostic(
                "dry_run",
                "Pass mode='run' to execute the docs gardener.",
                recovery_tools=[],
                recovery_usage="wf_garden_docs(mode='run')",
            )],
            next_tools=["wf_garden_docs"],
            usage="wf_garden_docs(mode='run')",
        )
    with project_state_publication_lock(root):
        result = run_garden(root)
    status = "ok" if result["passed"] else "error"
    diagnostics = [] if result["passed"] else [
        _diagnostic(
            "docs_gardener_failed",
            result["output"].strip() or "docs_gardener failed",
            recovery_tools=["wf_validate_docs"],
            recovery_usage="wf_validate_docs()",
        )
    ]
    # 1ro43 Req 7: gardening has a drift worklist — point at it. The gardener's
    # `Last verified` stamps are mechanical and carry no verification meaning;
    # drift disposal is a deliberate review recorded via `Verified against:`.
    if result["passed"]:
        try:
            _drift = server_impl._load_script("index_state_store").drift_worklist(
                root / ".wavefoundry" / "index", limit=3
            )
            if _drift.get("flagged_count", 0) > 0:
                diagnostics.append(_diagnostic(
                    "doc_code_drift_flagged",
                    (
                        f"{_drift['flagged_count']} living doc(s) are drift-flagged (gardener "
                        "stamps do NOT clear drift — only a doc content update or a deliberate "
                        "`Verified against: <hex-sha>` review stamp resets the clock). See "
                        "wf_audit's `doc_drift` worklist for the ordered entries."
                    ),
                    recovery_tools=["wf_audit"],
                    recovery_usage="wf_audit()",
                ))
        except Exception:
            pass
    if cache and result["passed"]:
        cache.invalidate()
    if result["passed"] and result.get("files_updated", 0):
        server_impl._trigger_background_index_refresh_for_paths(root, ["docs/"])
    return server_impl._response(
        status,
        result,
        diagnostics=diagnostics,
        next_tools=["wf_validate_docs", "wf_sync_surfaces"] if result["passed"] else ["wf_validate_docs"],
        usage="wf_sync_surfaces()" if result["passed"] else "wf_validate_docs()",
    )


def wf_sync_surfaces_response(root: Path, mode: str = "dry_run", cache: Optional[server_impl.McpRepoCache] = None) -> dict[str, Any]:
    import server_impl

    if (mode or "").strip().lower() == "dry_run":
        return server_impl._response(
            "ok",
            {"mode": "dry_run", "skipped": True},
            diagnostics=[_diagnostic(
                "dry_run",
                "Pass mode='run' to execute render_platform_surfaces.",
                recovery_tools=[],
                recovery_usage="wf_sync_surfaces(mode='run')",
            )],
            next_tools=["wf_sync_surfaces"],
            usage="wf_sync_surfaces(mode='run')",
        )
    result = run_sync_surfaces(root)
    status = "ok" if result["passed"] else "error"
    diagnostics = [] if result["passed"] else [
        _diagnostic(
            "render_platform_surfaces_failed",
            result["output"].strip() or "render_platform_surfaces failed",
            recovery_tools=["wf_validate_docs"],
            recovery_usage="wf_validate_docs()",
        )
    ]
    if cache and result["passed"]:
        cache.invalidate()
    envelope = server_impl._response(
        status,
        result,
        diagnostics=diagnostics,
        next_tools=["wf_validate_docs"],
        usage="wf_validate_docs()",
    )
    # wf_sync_surfaces is a write-side tool (renders host config + native
    # wrappers); attach lint regardless of mode_s for consistency with other
    # gated tools.
    mode_for_lint = "create" if status != "dry_run" else "dry_run"
    return server_impl._attach_lint_to_response(envelope, root, mode_for_lint)


def wf_scan_secrets_response(root: Path, mode: str = "incremental") -> dict[str, Any]:
    """Run the secrets scanner and return a structured findings summary.

    mode: "incremental" uses git-changed files; "full" scans all tracked files.
    New findings are appended to docs/scan-findings.json as status 'pending'.

    Runs in a subprocess (matching the graph indexer architecture) so that
    ProcessPoolExecutor workers and the multiprocessing resource_tracker belong
    to the child process and exit when it does — the MCP server never acquires
    a resource_tracker of its own.
    """
    import server_impl

    import sys as _sys
    scripts_dir = Path(server_impl.__file__).resolve().parent
    if str(scripts_dir) not in _sys.path:
        _sys.path.insert(0, str(scripts_dir))

    try:
        from wave_lint_lib.constants import SCAN_FINDINGS_PATH
    except ImportError as exc:
        return server_impl._response(
            "error",
            {"error": f"secrets scanner not available: {exc}"},
            diagnostics=[_diagnostic("import_error", str(exc))],
        )

    import time as _time, json as _json

    scan_script = scripts_dir / "run_secrets_scan.py"
    _t0 = _time.monotonic()
    failures: list[str] = []

    try:
        proc = server_impl._mcp_subprocess_run(
            [server_impl._preferred_python(), str(scan_script), "--root", str(root), "--mode", mode],
            timeout=300, cwd=str(root),
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"exit {proc.returncode}")
        _out = _json.loads(proc.stdout)
        failures = _out.get("failures", [])
        rules_hash_changed = _out.get("rules_hash_changed", False)
        escalated_to_full = _out.get("escalated_to_full", False)
    except Exception as _exc:
        # Subprocess unavailable or failed — fall back to in-process serial scan.
        rules_hash_changed = False
        escalated_to_full = False
        try:
            from wave_lint_lib.secrets_validators import check_hardcoded_secrets
            failures = check_hardcoded_secrets(root, scan_all=(mode == "full"), max_workers=1)
        except Exception:
            return server_impl._response(
                "error",
                {"error": f"secrets scan failed: {_exc}"},
                diagnostics=[_diagnostic("scan_error", str(_exc))],
            )

    elapsed_s = round(_time.monotonic() - _t0, 3)

    import json as _json
    findings_path = root / SCAN_FINDINGS_PATH
    findings: list[dict] = []
    if findings_path.exists():
        try:
            data = _json.loads(findings_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                findings = data
        except Exception:
            pass

    by_status: dict[str, int] = {}
    for entry in findings:
        s = entry.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

    all_ok = len(failures) == 0
    return server_impl._response(
        "ok" if all_ok else "error",
        {
            "mode": mode,
            "effective_mode": "full" if (mode == "full" or escalated_to_full) else mode,
            "rules_hash_changed": rules_hash_changed,
            "escalated_to_full": escalated_to_full,
            "clean": all_ok,
            "elapsed_s": elapsed_s,
            "total_findings": len(findings),
            "by_status": by_status,
            "failures_total": len(failures),
            "failures": failures[:20] if failures else [],
            "findings_file": SCAN_FINDINGS_PATH,
        },
        diagnostics=[
            _diagnostic(
                "secrets_scan_failures",
                f"{len(failures)} secrets check failure(s) — review {SCAN_FINDINGS_PATH}",
                recovery_tools=["wf_scan_secrets"],
                recovery_usage="wf_scan_secrets(mode='full')",
            )
        ] if failures else [],
        next_tools=["wf_audit"] if all_ok else ["wf_scan_secrets"],
        usage="wf_audit()" if all_ok else "wf_scan_secrets(mode='full')",
    )
