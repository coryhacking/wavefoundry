"""TechDocs response handlers; registration and shared helpers stay in server_impl."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from lifecycle_gate_support import _diagnostic


TECHDOCS_AUDIT_FINDING_CAP = 200
TECHDOCS_AUDIT_SURVIVOR_CAP = 200


def _bounded_techdocs_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Cap the tree-sized report lists and SAY what was dropped.

    The report is unbounded in the size of the published tree: a 3000-page
    docs_dir with no metadata blocks produced 12001 findings in a 1.8MB
    envelope, which overruns host response limits and floods agent context.
    Following the bounded-snapshot precedent set for ``wf_audit`` (wave 1t59p),
    the MCP entry truncates and reports totals; the CLI entry streams to stdout
    and is deliberately left whole. Never silently: a truncated payload that
    reads like a complete one is worse than a large one.
    """
    bounded = dict(payload)
    findings = list(payload.get("findings") or [])
    if len(findings) > TECHDOCS_AUDIT_FINDING_CAP:
        bounded["findings"] = findings[:TECHDOCS_AUDIT_FINDING_CAP]
        bounded["findings_omitted"] = len(findings) - TECHDOCS_AUDIT_FINDING_CAP
    bounded["findings_total"] = len(findings)

    publication = dict(payload.get("publication") or {})
    survivors = list(publication.get("survivor_pages") or [])
    if len(survivors) > TECHDOCS_AUDIT_SURVIVOR_CAP:
        publication["survivor_pages"] = survivors[:TECHDOCS_AUDIT_SURVIVOR_CAP]
        publication["survivor_pages_omitted"] = len(survivors) - TECHDOCS_AUDIT_SURVIVOR_CAP
    unsafe_survivors = list(publication.get("unsafe_survivor_targets") or [])
    if unsafe_survivors:
        publication["unsafe_survivor_targets_total"] = len(unsafe_survivors)
        if len(unsafe_survivors) > TECHDOCS_AUDIT_SURVIVOR_CAP:
            publication["unsafe_survivor_targets"] = unsafe_survivors[:TECHDOCS_AUDIT_SURVIVOR_CAP]
            publication["unsafe_survivor_targets_omitted"] = (
                len(unsafe_survivors) - TECHDOCS_AUDIT_SURVIVOR_CAP
            )
    bounded["publication"] = publication
    bounded["truncated"] = bool(
        bounded.get("findings_omitted")
        or publication.get("survivor_pages_omitted")
        or publication.get("unsafe_survivor_targets_omitted")
    )
    return bounded


def wf_techdocs_audit_response(root: Path, compare_to: str = "") -> dict[str, Any]:
    """Wave 1vqqi: the MCP entry for the TechDocs publication audit.

    Wraps ``techdocs_audit_lib.run_techdocs_audit`` (the same bounded runner
    ``wf techdocs-audit`` calls; its private worker invokes the one raw
    ``audit_techdocs`` implementation). Read tier: it takes no lock, registers no
    publication writer, and writes nothing. Findings live in ``data.findings`` and are NEVER blocking
    diagnostics, because this tool gates nothing. Degrade reasons and the
    not-applicable verdict surface as ``advisory=True`` diagnostics, each emitted from
    its own call site with a literal code, which the sanctioned-advisory-site gate
    requires (it resolves codes by AST and only when they are literals).
    """
    from wf_server import server_impl
    import techdocs_audit_lib  # noqa: PLC0415  (public module, call-time binding)

    usage = "wf_techdocs_audit()"
    try:
        report = techdocs_audit_lib.run_techdocs_audit(root, compare_to=compare_to or None)
    except (RuntimeError, OSError, ValueError, re.error) as exc:
        return server_impl._response(
            "error",
            {"compare_to": compare_to},
            diagnostics=[_diagnostic(
                "techdocs_audit_failed",
                f"the audit could not run: {exc}",
                recovery_tools=["wf_techdocs_audit", "wf_validate_docs"],
                recovery_usage=usage,
            )],
            next_tools=["wf_techdocs_audit"],
            usage=usage,
        )

    payload = _bounded_techdocs_payload(report.as_dict())
    diagnostics = []
    if report.summary["verdict"] == techdocs_audit_lib.VERDICT_NOT_APPLICABLE:
        diagnostics.append(_diagnostic(
            "techdocs_audit_not_applicable",
            "no mkdocs.yml at the repository root, so there is no publication boundary to audit; "
            "the trio state is still reported. Generate the baseline first if TechDocs is wanted.",
            recovery_tools=["wf_techdocs_baseline"],
            recovery_usage="wf_techdocs_baseline(mode='dry_run')",
            advisory=True,
        ))
    elif report.degraded:
        diagnostics.append(_diagnostic(
            "techdocs_audit_degraded",
            "the audit could not compute part of its answer: " + ", ".join(report.degraded)
            + ". A degraded run never reports a clean verdict.",
            recovery_tools=["wf_techdocs_audit"],
            recovery_usage=usage,
            advisory=True,
        ))
    if report.summary["verdict"] == techdocs_audit_lib.VERDICT_NOT_APPLICABLE:
        next_tools = ["wf_techdocs_baseline"]
    else:
        owned = report.trio.get("members", {}).get("docs/index.md") == "project_owned"
        next_tools = ["wf_validate_docs"] if owned else ["wf_techdocs_baseline"]
    return server_impl._response("ok", payload, diagnostics=diagnostics, next_tools=next_tools, usage=usage)


def wf_techdocs_baseline_response(
    root: Path, mode: str = "dry_run", cache: Optional[server_impl.McpRepoCache] = None
) -> dict[str, Any]:
    """Wave 1vj4e (1vj4d Requirement 10): the MCP entry for the Backstage/TechDocs baseline.

    Wraps ``render_agent_surfaces.render_techdocs_baseline`` (the same function the
    ``wf techdocs-baseline`` CLI calls; nothing is re-implemented here, and the module is
    imported by its public name so one patch is observed by both entry points).
    ``dry_run`` (default, read-first) runs the precondition and the containment classification
    and reports what ``run`` would write (``absent_paths``) plus the CURRENT tree's marker-derived
    ``partial`` record, writing nothing (``status: "dry_run"``); ``run`` writes the absent members
    missing-only (``status: "ok"``). Precondition failure (``techdocs_precondition_unmet``) and a
    preflight refusal (``techdocs_destination_refused``) are ``status: error`` with nothing
    written; any ``RuntimeError``, ``OSError``, or ``UnicodeDecodeError`` raised after preflight
    (an unreadable packaged template, one saved in another encoding, an ``O_EXCL`` collision on a
    later member, a write error) is
    ``techdocs_write_failed``, carrying ``written_paths`` from ``TechdocsWriteFailed`` and every
    member's current state from ``techdocs_member_states``, with the repo cache invalidated.
    """
    from wf_server import server_impl
    import render_agent_surfaces  # noqa: PLC0415  (public module, call-time binding)

    mode_s = (mode or "dry_run").strip().lower()
    usage_dry = "wf_techdocs_baseline(mode='dry_run')"
    if mode_s not in ("dry_run", "run"):
        return server_impl._response(
            "error",
            {"mode": mode},
            diagnostics=[_diagnostic(
                "invalid_arguments",
                f"wf_techdocs_baseline's mode must be 'dry_run' or 'run' (got {mode!r}); nothing written.",
                recovery_tools=["wf_techdocs_baseline"],
                recovery_usage=usage_dry,
            )],
            next_tools=["wf_techdocs_baseline"],
            usage=usage_dry,
        )
    dry = mode_s == "dry_run"
    payload: dict[str, Any] = {
        "mode": mode_s,
        "written_paths": [],
        "preserved_paths": [],
        "generated_paths": [],
        "absent_paths": [],
        "missing_targets": [],
        "partial": None,
        "refusal": None,
    }
    try:
        result = render_agent_surfaces.render_techdocs_baseline(root, dry_run=dry)
    except render_agent_surfaces.TechdocsDestinationRefused as exc:
        payload["refusal"] = str(exc)
        return server_impl._response(
            "error",
            payload,
            diagnostics=[_diagnostic(
                "techdocs_destination_refused",
                f"{exc}; nothing written. An in-root symlink to a regular file is preserved; an "
                "escaping symlink, a directory, a dangling symlink, or another non-regular object "
                "at a destination is refused. Repair the destination and rerun.",
                recovery_tools=["wf_techdocs_baseline"],
                recovery_usage=usage_dry,
            )],
            next_tools=["wf_techdocs_baseline"],
            usage=usage_dry,
        )
    except (render_agent_surfaces.TechdocsWriteFailed, RuntimeError, OSError) as exc:
        # After preflight: an unreadable packaged template, a non-UTF-8 one, an O_EXCL
        # collision, or any other write error on a later member. The module normalizes
        # all of them into TechdocsWriteFailed, which carries what this run wrote;
        # the wider tuple covers anything raised outside that loop.
        payload["refusal"] = str(exc)
        payload["written_paths"] = list(getattr(exc, "written_paths", ()))
        generated, preserved, absent = render_agent_surfaces.techdocs_member_states(root)
        payload["preserved_paths"] = list(preserved)
        payload["generated_paths"] = list(generated)
        payload["absent_paths"] = list(absent)
        payload["partial"] = render_agent_surfaces.classify_techdocs_baseline(root)
        if cache:
            cache.invalidate()
        return server_impl._response(
            "error",
            payload,
            diagnostics=[_diagnostic(
                "techdocs_write_failed",
                f"{exc}. Preflight passed, so an earlier member may have been written; "
                "written_paths names what this run wrote before failing and "
                "preserved_paths/generated_paths/absent_paths report every member as it is on "
                "disk now (independent of whether the trio is mixed). Repair and rerun "
                "(missing-only, so a rerun writes only what is still absent).",
                recovery_tools=["wf_techdocs_baseline", "wf_validate_docs"],
                recovery_usage=usage_dry,
            )],
            next_tools=["wf_techdocs_baseline", "wf_validate_docs"],
            usage=usage_dry,
        )
    payload.update(
        written_paths=list(result.written_paths),
        preserved_paths=list(result.preserved_paths),
        generated_paths=list(result.generated_paths),
        absent_paths=list(result.absent_paths),
        missing_targets=list(result.missing_targets),
        partial=result.partial,
    )
    if result.missing_targets:
        return server_impl._response(
            "error",
            payload,
            diagnostics=[_diagnostic(
                "techdocs_precondition_unmet",
                "missing navigation targets: " + ", ".join(result.missing_targets)
                + "; nothing written. The landing page links these documents, so they must exist "
                "first (a fresh install creates them in Phase 2; see the Refresh TechDocs prompt); "
                "then rerun.",
                recovery_tools=["wf_audit_install", "wf_techdocs_baseline"],
                recovery_usage=usage_dry,
            )],
            next_tools=["wf_audit_install", "wf_techdocs_baseline"],
            usage=usage_dry,
        )
    diagnostics: list[dict[str, Any]] = []
    if result.partial:
        diagnostics.append(_diagnostic(
            "backstage_techdocs_partial",
            str(result.partial.get("detail") or ""),
            recovery_tools=["wf_techdocs_baseline"],
            recovery_usage=usage_dry,
            advisory=True,
        ))
    if dry:
        if result.absent_paths:
            message = (
                "Pass mode='run' to write the absent members missing-only: "
                + ", ".join(result.absent_paths)
                + ". Present members are preserved byte-for-byte."
            )
        else:
            message = "All three members are present; mode='run' would write nothing."
        diagnostics.append(_diagnostic(
            "dry_run",
            message,
            recovery_tools=[],
            recovery_usage="wf_techdocs_baseline(mode='run')",
        ))
    if not dry and result.written_paths:
        if cache:
            cache.invalidate()
        if "docs/index.md" in result.written_paths:
            server_impl._trigger_background_index_refresh_for_paths(root, ["docs/index.md"])
    wants_run = dry and bool(result.absent_paths)
    envelope = server_impl._response(
        "dry_run" if dry else "ok",
        payload,
        diagnostics=diagnostics,
        next_tools=["wf_techdocs_baseline"] if wants_run else ["wf_validate_docs"],
        usage="wf_techdocs_baseline(mode='run')" if wants_run else "wf_validate_docs()",
    )
    return server_impl._attach_lint_to_response(envelope, root, "dry_run" if dry else "create")
