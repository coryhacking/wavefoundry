"""Upgrade handlers: extracted response ownership."""
from __future__ import annotations

from lifecycle_gate_support import _diagnostic
from lifecycle_gate_support import _docs_lint_warning_diagnostics
from lifecycle_gate_support import _repo_rel
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Optional
import json
import os
import re
import sys
import uuid


UPGRADE_OUTPUT_CAP_CHARS = 60_000


UPGRADE_SUMMARY_CAP_CHARS = 24_000


UPGRADE_SUMMARY_VALUE_CAP_CHARS = 2_000


UPGRADE_SUMMARY_MAX_ITEMS_PER_COLLECTION = 100


UPGRADE_RESPONSE_CAP_CHARS = 100_000


UPGRADE_BRIDGE_ARGV_CAP_CHARS = 24_000


UPGRADE_SUMMARY_KEY_CAP_CHARS = 128


UPGRADE_SUMMARY_METADATA_CAP_CHARS = 4_000


RETIRED_MODEL_CLEANUP_KEYS = (
    "retired_model_cleanup_status",
    "retired_model_cleanup_removed",
    "retired_model_cleanup_absent",
    "retired_model_cleanup_unowned",
    "retired_model_cleanup_failed",
)


_RETIRED_MODEL_CLEANUP_ITEM_RE = re.compile(
    r"^(?:fastembed|clean-onnx|static-onnx|coreml):"
    r"(?:default|custom):[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"
)


def _project_retired_model_cleanup_fields(value: object) -> dict[str, Any]:
    """Project the five terminal fields onto their path-free public vocabulary."""
    projected: dict[str, Any] = {
        "retired_model_cleanup_status": "not_applicable",
        "retired_model_cleanup_removed": [],
        "retired_model_cleanup_absent": [],
        "retired_model_cleanup_unowned": [],
        "retired_model_cleanup_failed": [],
    }
    if not isinstance(value, Mapping):
        return projected
    status = value.get("retired_model_cleanup_status")
    if status in {"not_applicable", "dry_run", "complete", "failed"}:
        projected["retired_model_cleanup_status"] = status
    for key in RETIRED_MODEL_CLEANUP_KEYS[1:]:
        items = value.get(key)
        if not isinstance(items, list):
            continue
        accepted: set[str] = set()
        for item in items:
            if not isinstance(item, str):
                continue
            base, separator, suffix = item.partition("|")
            expected_failure = key == "retired_model_cleanup_failed"
            if expected_failure != (separator == "|" and suffix == "remove_failed"):
                continue
            if _RETIRED_MODEL_CLEANUP_ITEM_RE.fullmatch(base):
                accepted.add(item)
        projected[key] = sorted(accepted)
    return projected


UPGRADE_SUMMARY_TERMINAL_KEYS = {
    "review_sidecar_cleanup",
    "from_version",
    "to_version",
    "zip_applied",
    "pruned_count",
    "docs_gate",
    "index_update",
    "failed_phase",
    "is_major_or_minor",
    # Wave 1u44o: the delegated-summary degradation marker must never be
    # silently dropped by bounding; it is the field that DISCLOSES that the
    # summary fell back to the pre-extraction in-process builder. Kept flat and
    # small on the producer side so it also survives the unknown-scalar budget
    # path on a server launched before this registration existed.
    "summary_source_degraded",
    # Wave 1uf68: the summary-schema freshness token. A dropped token yields
    # None, which reads as ABSENT to any consumer not also checking the
    # truncation flag, exactly the ambiguity between "no token" and "old code"
    # that carrying the token at the cleanup emit site exists to remove. This
    # registration lives in the MCP server's in-process module, so it takes
    # effect only after a full host restart; emission is unaffected by that.
    "summary_schema_version",
    *RETIRED_MODEL_CLEANUP_KEYS,
}


def _install_artifact_display(root: Path, artifact: Path) -> str:
    """Repo-relative artifact path for the install audit's operator-facing envelope.

    Wave 1wybs (1wybr): the 1uu9z convention renders repository paths
    repo-relative. An operator-authored row can name an artifact that resolves
    outside the repository, where ``_repo_rel`` raises ``ValueError``; the
    envelope then carries a ``..``-relative path (delivery review CODE-DEL-5)
    and, only for a path with no common anchor (a different Windows drive),
    the resolved string, rather than crashing.
    """
    try:
        return _repo_rel(root, artifact)
    except ValueError:
        pass
    try:
        relative = os.path.relpath(artifact.resolve(strict=False), root.resolve())
    except ValueError:
        return str(artifact)
    return relative.replace("\\", "/")


def wf_audit_install_response(root: Path, phase: Optional[int] = None) -> dict[str, Any]:
    """Run the three-check install audit and return the first failure or the next step.

    Check sequence (stops on first failure):
      0. resolve and parse the install log.
      1. docs-lint — block on real findings while carrying expected pending absences.
      2. checked-row artifact validation — for every ``[x]`` row, verify its
         expected artifact exists on disk. Mismatch surfaces the agent-recovery
         path.
      3. first unchecked row — when both checks pass, return the next pending
         row with its seed pointer and the instruction to mark ``[x]`` and
         re-call. When no pending rows remain, return ``status: complete``.

    The ``phase`` argument optionally limits the audit (and the next-step return)
    to a single phase. Missing log file returns an actionable error pointing at
    ``install-wavefoundry.md``.
    """
    from wf_server import server_impl
    # Local import to avoid a hard cycle if install_log_lib later imports
    # from server_impl (it currently doesn't, but defensive).
    import install_log_lib

    log_text = install_log_lib.read_install_log(root)
    if log_text is None:
        return server_impl._response(
            "error",
            {
                "status": "missing_log",
                "expected_path": str(root / install_log_lib.INSTALL_LOG_REL_PATH),
            },
            diagnostics=[
                _diagnostic(
                    "install_log_missing",
                    (
                        "No install log at .wavefoundry/install-log.md. "
                        "If this is a fresh install, copy the template at "
                        ".wavefoundry/framework/install/install-log.template.md to "
                        ".wavefoundry/install-log.md (substitute {{generated_at}} with "
                        "today's date), then re-call wf_audit_install. See "
                        "install-wavefoundry.md at the repo root for bootstrap "
                        "instructions."
                    ),
                    recovery_tools=[],
                )
            ],
            next_tools=[],
            usage="wf_audit_install()",
        )

    rows = install_log_lib.parse_log(log_text)

    # Wave 1p9bh: a present log that parsed to ZERO rows is corrupted (typically a non-UTF-8 write
    # mojibake'd the em-dash row separators). Fail loudly here rather than sailing through CHECK 2/3 to a
    # vacuous "complete" (the empty-input vacuous-truth defect).
    if install_log_lib.is_unparseable(log_text, rows):
        return server_impl._response(
            "error",
            {
                "status": "unparseable_log",
                "expected_path": str(root / install_log_lib.INSTALL_LOG_REL_PATH),
                "next_action": (
                    "The install log exists but no rows could be parsed — its row separators are "
                    "likely mojibake from a non-UTF-8 write. Rewrite it as UTF-8 (the framework "
                    "install-log writer, or an explicit `-Encoding utf8` write on Windows PowerShell), "
                    "then re-call wf_audit_install. Do NOT treat the install as complete."
                ),
            },
            diagnostics=[
                _diagnostic(
                    "install_log_unparseable",
                    (
                        "Install log present but zero rows parsed — likely an encoding corruption "
                        "(a non-UTF-8 write mojibake'd the em-dash row separators). Rewrite as UTF-8."
                    ),
                    recovery_tools=["wf_audit_install"],
                )
            ],
            next_tools=[],
            usage="wf_audit_install()",
        )

    # CHECK 1 — docs-lint. Expected missing future artifacts are carried as
    # pending context; every other finding still blocks advancement.
    lint_result = server_impl.run_validate(root)
    lint_errors = list(lint_result.get("errors", []))
    # Wave 1wuju (QA-DEL-2): a synthesized verdict-gap entry bypasses the
    # expected-absence classifier below (RTD-1 again: its tail may quote an
    # absence-marker phrase and it can never be deferred).
    verdict_gap_errors = [e for e in lint_errors if e.startswith(server_impl.DOCS_LINT_VERDICT_GAP_PREFIX)]
    classifiable_errors = [e for e in lint_errors if not e.startswith(server_impl.DOCS_LINT_VERDICT_GAP_PREFIX)]
    # Wave 1wuju (1wujs AC-1; delivery review ARCH-DEL-2): the install audit runs
    # the full-corpus lint, which includes docs/waves, so an advisory sensor's
    # finding on an activated carrier surfaces here too, flagged and non-blocking.
    lint_warning_diagnostics = _docs_lint_warning_diagnostics(
        lint_result, recovery_tools=["wf_audit_install", "wf_validate_docs"]
    )
    blocking, expected_pending = install_log_lib.classify_lint_errors(
        classifiable_errors, rows, root
    )
    # Wave 1wybs (1wybr): the 1viyu passed-false-with-no-errors branch that
    # used to sit here is unreachable, because run_validate synthesizes a
    # verdict-gap entry on every non-zero exit and its timeout branch returns
    # an error entry; the real-parser test in the lifecycle suite proves that
    # contract end to end (RTD-1: the entry is never deferred).
    blocking = [*verdict_gap_errors, *blocking]
    pending_cap = 25
    pending_lint = {
        "count": len(expected_pending),
        "errors": expected_pending[:pending_cap],
        "truncated": len(expected_pending) > pending_cap,
        "note": (
            "These missing artifacts are expected while Phase 2 seed rows remain pending; "
            "they become blocking at the final install gate."
        ),
    }
    if blocking:
        return server_impl._response(
            "error",
            {
                "status": "lint_errors",
                "phase": phase,
                "errors": blocking,
                "warnings": lint_result.get("warnings", []),
                "pending_lint": pending_lint,
                "next_action": (
                    "Fix the blocking docs-lint errors above before advancing the install log. "
                    "After fixing, re-call wf_audit_install."
                ),
            },
            diagnostics=[
                _diagnostic(
                    "docs_lint_error",
                    error,
                    recovery_tools=["wf_audit_install", "wf_validate_docs"],
                )
                for error in blocking
            ] + lint_warning_diagnostics,
            next_tools=["wf_audit_install"],
            usage="wf_audit_install()",
        )

    scope_rows = install_log_lib.filter_phase(rows, phase)

    # CHECK 2 — checked-row artifact validation. Block on missing artifacts.
    missing = install_log_lib.checked_rows_missing_artifact(scope_rows, root)
    if missing:
        first_row, first_path = missing[0]
        first_display = _install_artifact_display(root, first_path)
        return server_impl._response(
            "error",
            {
                "status": "checked_but_missing",
                "phase": phase,
                "row": _install_audit_row_brief(first_row),
                "expected_artifact": first_display,
                "all_missing": [
                    {
                        "row": _install_audit_row_brief(r),
                        "expected_artifact": _install_artifact_display(root, p),
                    }
                    for r, p in missing
                ],
                "pending_lint": pending_lint,
                "next_action": (
                    f"Row {first_row.number} is marked [x] but its expected artifact "
                    f"({first_row.target}) does not exist at {first_display}. "
                    f"Re-execute the step ({first_row.source}), confirm the artifact, "
                    f"then re-call wf_audit_install."
                ),
            },
            diagnostics=[
                _diagnostic(
                    "install_log_checked_but_missing",
                    (
                        f"Row {r.number} ({r.source}) marked [x] but artifact "
                        f"{r.target!r} does not exist at {_install_artifact_display(root, p)}."
                    ),
                    recovery_tools=["wf_audit_install"],
                )
                for r, p in missing
            ] + lint_warning_diagnostics,
            next_tools=["wf_audit_install"],
            usage="wf_audit_install()",
        )

    # CHECK 3 — first unchecked row, or complete.
    next_row = install_log_lib.first_unchecked_row(scope_rows)
    if next_row is None:
        # All rows in scope are terminal.
        complete_overall = install_log_lib.is_complete(rows)
        return server_impl._response(
            "ok",
            {
                "status": "complete" if complete_overall else "phase_complete",
                "phase": phase,
                "message": (
                    "Install complete: every row is [x] or [~]."
                    if complete_overall
                    else f"Phase {phase} complete; other phases still have pending rows."
                ),
                "pending_lint": pending_lint,
            },
            diagnostics=lint_warning_diagnostics or None,
            next_tools=[],
            usage="wf_audit_install()",
        )

    return server_impl._response(
        "ok",
        {
            "status": "next_step",
            "phase": phase,
            "row": _install_audit_row_brief(next_row),
            "instructions": (
                f"Execute the step indicated by row {next_row.number} "
                f"({next_row.source}: {next_row.slug}). When the expected outcome is "
                f"reached, mark this row [x] in .wavefoundry/install-log.md and call "
                f"wf_audit_install again."
            ),
            "pending_lint": pending_lint,
        },
        diagnostics=lint_warning_diagnostics or None,
        next_tools=["wf_audit_install"],
        usage="wf_audit_install()",
    )


def _install_audit_row_brief(row: Any) -> dict[str, Any]:
    """Return a JSON-friendly summary of an install-log row."""
    return {
        "number": row.number,
        "slug": row.slug,
        "kind": row.kind,
        "source": row.source,
        "target": row.target,
        "phase": row.phase,
        "state": row.state,
        # Wave 1p8gw: expose the parsed field classification so consumers can tell a stat-able artifact
        # PATH apart from a prose verification DESCRIPTION (the description-as-path defect).
        "field": getattr(row, "field", None),
        "artifact_path": getattr(row, "artifact_path", None),
        "description": getattr(row, "description", None),
    }


def _load_upgrade_lib() -> Any:
    """Import upgrade_lib from the scripts directory, ensuring it is on sys.path."""
    from wf_server import server_impl
    _scripts_dir = str(server_impl.SCRIPTS_DIR)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    try:
        import upgrade_lib as _ulib  # noqa: PLC0415
        return _ulib
    except ImportError:
        return None


def _upgrade_summary_sentinel() -> str:
    """Return the canonical ``WAVE_UPGRADE_SUMMARY_JSON:`` sentinel from upgrade_wavefoundry."""
    from wf_server import server_impl
    _scripts_dir = str(server_impl.SCRIPTS_DIR)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    try:
        import upgrade_wavefoundry as _uw  # noqa: PLC0415
        return _uw.WAVE_UPGRADE_SUMMARY_SENTINEL
    except Exception:  # noqa: BLE001 — fail-safe; the round-trip test pins the fallback to canonical
        return "WAVE_UPGRADE_SUMMARY_JSON:"


def _parse_upgrade_summary(output: str) -> dict[str, Any] | None:
    """Parse the structured operator summary from the upgrade subprocess output (wave 1p8eu).

    Scans ``output`` for the last ``WAVE_UPGRADE_SUMMARY_JSON:`` sentinel line and returns the parsed
    JSON dict. FAIL-SAFE: returns ``None`` when the sentinel is absent or the JSON is malformed (any
    parse error, including RecursionError on a pathological payload) — the caller then falls back to
    the raw ``output`` with no exception. The last occurrence wins so a re-run that appends to the log
    surfaces the most recent summary.
    """
    if not output:
        return None
    sentinel = _upgrade_summary_sentinel()
    found: dict[str, Any] | None = None
    for line in output.splitlines():
        if line.startswith(sentinel):
            payload = line[len(sentinel):].strip()
            # F1 — broaden to Exception so a RecursionError (deeply-nested JSON) cannot escape and
            # violate the AC-3 "malformed → no exception" guarantee.
            try:
                parsed = json.loads(payload)
            except Exception:  # noqa: BLE001 — any parse failure → skip this line, fall back to output
                continue
            if isinstance(parsed, dict):
                found = parsed
    return found


def _bounded_upgrade_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Bound repo-sized summary collections without hiding terminal scalars.

    The upgrade log retains the complete sentinel.  MCP callers receive every
    scalar plus bounded list fields and explicit per-field counts.  The
    collection budget is shared so several large result sets cannot each
    consume the full response allowance.
    """
    from wf_server import server_impl
    summary = {
        **dict(summary),
        **_project_retired_model_cleanup_fields(summary),
    }
    cleanup_list_keys = RETIRED_MODEL_CLEANUP_KEYS[1:]
    collection_keys = tuple(
        key
        for key, value in summary.items()
        if isinstance(value, list) and key not in cleanup_list_keys
    )
    # The cleanup lists are finite by construction (20 exact default/custom
    # targets) and reserve capacity ahead of repo-sized generic collections.
    bounded: dict[str, Any] = {
        key: list(summary.get(key) or [])[:20]
        for key in cleanup_list_keys
    }
    original_chars = len(json.dumps(summary, ensure_ascii=False, default=str))
    collection_chars = len(
        json.dumps(bounded, ensure_ascii=False, default=str)
    )
    scalar_items = [
        (key, value)
        for key, value in summary.items()
        if key not in collection_keys
    ]
    scalar_entry_chars = {
        key: (
            len(json.dumps(key, ensure_ascii=False))
            + len(json.dumps(value, ensure_ascii=False, default=str))
        )
        for key, value in scalar_items
    }
    terminal_chars = sum(
        chars
        for key, chars in scalar_entry_chars.items()
        if key in server_impl.UPGRADE_SUMMARY_TERMINAL_KEYS
        and chars <= UPGRADE_SUMMARY_VALUE_CAP_CHARS
    )
    unknown_scalar_budget = max(0, UPGRADE_SUMMARY_CAP_CHARS - terminal_chars)
    scalar_returned_chars = 0
    scalar_returned_fields = 0
    scalar_omitted_fields = 0
    scalar_omitted_value_chars = 0
    scalar_metadata_chars = 0
    scalar_metadata_fields_omitted = 0
    oversized_key_fields = 0
    oversized_key_chars = 0
    collection_returned_fields = 0
    collection_omitted_fields = 0
    any_truncated = False

    for key, value in scalar_items:
        key_chars = len(key)
        value_chars = len(json.dumps(value, ensure_ascii=False, default=str))
        entry_chars = scalar_entry_chars[key]
        if key_chars > UPGRADE_SUMMARY_KEY_CAP_CHARS:
            oversized_key_fields += 1
            oversized_key_chars += key_chars
            scalar_omitted_fields += 1
            scalar_omitted_value_chars += value_chars
            any_truncated = True
            continue
        is_terminal = key in server_impl.UPGRADE_SUMMARY_TERMINAL_KEYS
        fits_aggregate = is_terminal or entry_chars <= unknown_scalar_budget
        if value_chars <= UPGRADE_SUMMARY_VALUE_CAP_CHARS and fits_aggregate:
            bounded[key] = value
            scalar_returned_chars += entry_chars
            scalar_returned_fields += 1
            if not is_terminal:
                unknown_scalar_budget -= entry_chars
            continue
        # The trusted current producer emits only small terminal scalars and a
        # tiny cleanup mapping. Future/malformed sentinel detail is observable
        # by count but cannot defeat either the per-value or aggregate cap.
        scalar_omitted_fields += 1
        scalar_omitted_value_chars += value_chars
        metadata = {
            key: None,
            f"{key}_total_chars": value_chars,
            f"{key}_truncated": True,
        }
        metadata_chars = len(
            json.dumps(metadata, ensure_ascii=False, default=str)
        )
        if (
            scalar_metadata_chars + metadata_chars
            <= UPGRADE_SUMMARY_METADATA_CAP_CHARS
        ):
            bounded.update(metadata)
            scalar_metadata_chars += metadata_chars
        else:
            scalar_metadata_fields_omitted += 1
        any_truncated = True

    for key in collection_keys:
        key_chars = len(key)
        if key_chars > UPGRADE_SUMMARY_KEY_CAP_CHARS:
            oversized_key_fields += 1
            oversized_key_chars += key_chars
            collection_omitted_fields += 1
            any_truncated = True
            continue
        values = list(summary.get(key) or [])
        returned = values[:UPGRADE_SUMMARY_MAX_ITEMS_PER_COLLECTION]
        total = len(values)
        candidate: dict[str, Any] = {}
        candidate_chars = 0
        while True:
            returned_count = len(returned)
            remaining = total - returned_count
            truncated = remaining > 0
            candidate = {
                key: returned,
                f"{key}_total": total,
                f"{key}_returned": returned_count,
                f"{key}_remaining": remaining,
                f"{key}_truncated": truncated,
            }
            candidate_chars = len(
                json.dumps(candidate, ensure_ascii=False, default=str)
            )
            if collection_chars + candidate_chars + 1 <= UPGRADE_SUMMARY_CAP_CHARS:
                break
            if not returned:
                candidate = {}
                break
            returned.pop()
        if not candidate:
            collection_omitted_fields += 1
            any_truncated = True
            continue
        collection_chars += candidate_chars + 1
        collection_returned_fields += 1
        any_truncated = any_truncated or truncated
        bounded.update(candidate)

    bounded["summary_total_chars"] = original_chars
    bounded["summary_collection_cap_chars"] = UPGRADE_SUMMARY_CAP_CHARS
    bounded["summary_scalar_cap_chars"] = UPGRADE_SUMMARY_CAP_CHARS
    bounded["summary_scalar_returned_chars"] = scalar_returned_chars
    bounded["summary_scalar_fields_total"] = len(scalar_items)
    bounded["summary_scalar_fields_returned"] = scalar_returned_fields
    bounded["summary_scalar_fields_truncated"] = (
        len(scalar_items) - scalar_returned_fields
    )
    bounded["summary_scalar_fields_omitted"] = scalar_omitted_fields
    bounded["summary_scalar_omitted_value_chars"] = scalar_omitted_value_chars
    bounded["summary_scalar_metadata_cap_chars"] = UPGRADE_SUMMARY_METADATA_CAP_CHARS
    bounded["summary_scalar_metadata_returned_chars"] = scalar_metadata_chars
    bounded["summary_scalar_metadata_fields_omitted"] = (
        scalar_metadata_fields_omitted
    )
    bounded["summary_oversized_key_fields_omitted"] = oversized_key_fields
    bounded["summary_oversized_key_chars_total"] = oversized_key_chars
    bounded["summary_collection_fields_total"] = len(collection_keys)
    bounded["summary_collection_fields_returned"] = collection_returned_fields
    bounded["summary_collection_fields_omitted"] = collection_omitted_fields
    bounded["summary_key_cap_chars"] = UPGRADE_SUMMARY_KEY_CAP_CHARS
    bounded["summary_value_cap_chars"] = UPGRADE_SUMMARY_VALUE_CAP_CHARS
    bounded["summary_max_items_per_collection"] = (
        UPGRADE_SUMMARY_MAX_ITEMS_PER_COLLECTION
    )
    bounded["summary_truncated"] = any_truncated
    return bounded


def _bounded_upgrade_response_envelope(response: dict[str, Any]) -> dict[str, Any]:
    """Keep the complete public upgrade envelope within its named host cap."""

    diagnostics = response.get("diagnostics")
    if isinstance(diagnostics, list):
        bounded_diagnostics: list[dict[str, Any]] = []
        for diagnostic in diagnostics:
            if not isinstance(diagnostic, dict):
                continue
            code = diagnostic.get("code")
            normalized: dict[str, Any] = {
                "code": (
                    code[:UPGRADE_SUMMARY_KEY_CAP_CHARS]
                    if isinstance(code, str)
                    else "upgrade_diagnostic"
                )
            }
            message = diagnostic.get("message")
            if isinstance(message, str):
                if len(message) > UPGRADE_SUMMARY_VALUE_CAP_CHARS:
                    normalized["message"] = (
                        message[:UPGRADE_SUMMARY_VALUE_CAP_CHARS]
                        + "\n[... diagnostic truncated; see log_path when available ...]"
                    )
                    normalized["message_total_chars"] = len(message)
                    normalized["message_truncated"] = True
                else:
                    normalized["message"] = message
            recovery_tools = diagnostic.get("recovery_tools")
            if isinstance(recovery_tools, list):
                normalized["recovery_tools"] = [
                    item[:UPGRADE_SUMMARY_KEY_CAP_CHARS]
                    for item in recovery_tools[:20]
                    if isinstance(item, str)
                ]
            recovery_usage = diagnostic.get("recovery_usage")
            if isinstance(recovery_usage, str):
                normalized["recovery_usage"] = recovery_usage[
                    :UPGRADE_SUMMARY_VALUE_CAP_CHARS
                ]
            omitted = len(set(diagnostic) - {
                "code",
                "message",
                "recovery_tools",
                "recovery_usage",
            })
            if omitted:
                normalized["omitted_field_count"] = omitted
            bounded_diagnostics.append(normalized)
        response["diagnostics"] = bounded_diagnostics

    data = response.get("data")
    if not isinstance(data, dict):
        return response
    memory_gate = data.get("memory_backfill")
    if isinstance(memory_gate, Mapping):
        data["memory_backfill"] = _bounded_upgrade_summary(memory_gate)

    data["response_cap_chars"] = UPGRADE_RESPONSE_CAP_CHARS
    data["response_truncated"] = False
    data["response_total_chars_before_bound"] = 0
    total_before = len(json.dumps(response, ensure_ascii=False, default=str))
    data["response_total_chars_before_bound"] = total_before
    if total_before <= UPGRADE_RESPONSE_CAP_CHARS:
        return response

    data["response_truncated"] = True
    output = data.get("output")
    if isinstance(output, str) and output:
        # Leave headroom for the count metadata and JSON escaping in the final
        # serialization. The complete child stream remains in ``log_path``.
        current = len(json.dumps(response, ensure_ascii=False, default=str))
        excess = max(0, current - UPGRADE_RESPONSE_CAP_CHARS)
        keep = max(0, len(output) - excess - 2_000)
        marker = (
            "\n[... response envelope capped; see log_path for the complete run ...]"
        )
        data["output"] = output[:keep] + marker if keep else marker.strip()
        data["output_truncated"] = True

    # Legitimate upgrade envelopes fit after the repo-sized summary/worklist
    # collections and raw output are bounded. Keep a fail-safe for unusually
    # verbose reload metadata without sacrificing terminal/recovery fields.
    if (
        len(json.dumps(response, ensure_ascii=False, default=str))
        > UPGRADE_RESPONSE_CAP_CHARS
        and "mcp_reload" in data
    ):
        data["mcp_reload"] = {
            "omitted_from_response": True,
            "reason": "upgrade response envelope cap",
        }

    if (
        len(json.dumps(response, ensure_ascii=False, default=str))
        > UPGRADE_RESPONSE_CAP_CHARS
    ):
        essential_data_keys = (
            "phase",
            "exit_code",
            "state",
            "log_path",
            "output_total_chars",
            "summary",
            "memory_backfill",
            "bridge_release_required",
            "response_cap_chars",
            "response_total_chars_before_bound",
        )
        compacted_data = {
            key: data[key] for key in essential_data_keys if key in data
        }
        retained_source_fields = len(compacted_data)
        compacted_data["response_truncated"] = True
        compacted_data["response_hard_compacted"] = True
        compacted_data["response_fields_omitted"] = (
            len(data) - retained_source_fields
        )
        compacted: dict[str, Any] = {
            "status": response.get("status", "error"),
            "data": compacted_data,
            "diagnostics": response.get("diagnostics", []),
        }
        next_step = response.get("next_step")
        if isinstance(next_step, str):
            compacted["next_step"] = next_step[:UPGRADE_SUMMARY_VALUE_CAP_CHARS]
        next_tools = response.get("next_tools")
        if isinstance(next_tools, list):
            compacted["next_tools"] = next_tools[:20]
        response = compacted

    # Terminal compaction is the final serialization authority after all
    # field-specific bounds. It progressively removes non-terminal detail
    # while retaining state, log location, diagnostics, and a valid recovery
    # argv.
    if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:
        data = response.get("data")
        if isinstance(data, dict):
            summary = data.get("summary")
            if isinstance(summary, Mapping):
                data["summary"] = {
                    **{
                        key: summary.get(key)
                        for key in RETIRED_MODEL_CLEANUP_KEYS
                    },
                    "other_fields_omitted_from_response": True,
                    "reason": "upgrade response envelope cap",
                }
            if "memory_backfill" in data:
                data["memory_backfill"] = {
                    "omitted_from_response": True,
                    "reason": "upgrade response envelope cap",
                }
    if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:
        data = response.get("data")
        terminal_data_keys = (
            "phase",
            "exit_code",
            "state",
            "log_path",
            "bridge_release_required",
            "response_cap_chars",
            "response_total_chars_before_bound",
            "summary",
        )
        terminal_data = (
            {key: data[key] for key in terminal_data_keys if key in data}
            if isinstance(data, dict)
            else {}
        )
        terminal_data["response_truncated"] = True
        terminal_data["response_hard_compacted"] = True
        response = {
            "status": response.get("status", "error"),
            "data": terminal_data,
            "diagnostics": list(response.get("diagnostics") or [])[:10],
        }
    if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:
        data = response.get("data")
        if isinstance(data, dict):
            log_path = data.get("log_path")
            if isinstance(log_path, str):
                data["log_path"] = log_path[:4_096]
        response["diagnostics"] = [
            {
                "code": str(item.get("code") or "upgrade_diagnostic")[
                    :UPGRADE_SUMMARY_KEY_CAP_CHARS
                ],
                "message": str(item.get("message") or "")[
                    :UPGRADE_SUMMARY_VALUE_CAP_CHARS
                ],
            }
            for item in list(response.get("diagnostics") or [])[:10]
            if isinstance(item, Mapping)
        ]
    if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:
        data = response.get("data")
        bridge = data.get("bridge_release_required") if isinstance(data, dict) else None
        compact_bridge: dict[str, Any] | None = None
        if isinstance(bridge, Mapping):
            argv = bridge.get("command_argv")
            safe_argv = (
                list(argv)
                if isinstance(argv, list)
                and len(argv) <= 32
                and all(
                    isinstance(item, str) and len(item) <= 4_096
                    for item in argv
                )
                and len(json.dumps(argv, ensure_ascii=False))
                <= UPGRADE_BRIDGE_ARGV_CAP_CHARS
                else None
            )
            compact_bridge = {
                "status": str(bridge.get("status") or "error")[
                    :UPGRADE_SUMMARY_KEY_CAP_CHARS
                ],
                "code": "bridge_release_required",
                "package": str(bridge.get("package") or "")[:4_096],
                "package_present": bool(bridge.get("package_present")),
                "command_argv": safe_argv,
                "handoff_compacted": True,
            }
        terminal_data = {
            "phase": str(data.get("phase") or "")[:UPGRADE_SUMMARY_KEY_CAP_CHARS]
            if isinstance(data, dict)
            else "",
            "state": str(data.get("state") or "")[:UPGRADE_SUMMARY_KEY_CAP_CHARS]
            if isinstance(data, dict)
            else "",
            "log_path": str(data.get("log_path") or "")[:4_096]
            if isinstance(data, dict)
            else "",
            "response_cap_chars": UPGRADE_RESPONSE_CAP_CHARS,
            "response_truncated": True,
            "response_hard_compacted": True,
        }
        if compact_bridge is not None:
            terminal_data["bridge_release_required"] = compact_bridge
        response = {
            "status": str(response.get("status") or "error")[
                :UPGRADE_SUMMARY_KEY_CAP_CHARS
            ],
            "data": terminal_data,
            "diagnostics": [
                {
                    "code": "upgrade_response_compacted",
                    "message": (
                        "Non-terminal upgrade response detail exceeded the public "
                        "envelope cap; inspect log_path for the complete run."
                    ),
                }
            ],
        }
    if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:
        data = response.get("data")
        response = {
            "status": "error",
            "data": {
                "phase": str(data.get("phase") or "")[
                    :UPGRADE_SUMMARY_KEY_CAP_CHARS
                ]
                if isinstance(data, dict)
                else "",
                "state": str(data.get("state") or "")[
                    :UPGRADE_SUMMARY_KEY_CAP_CHARS
                ]
                if isinstance(data, dict)
                else "",
                "log_path": str(data.get("log_path") or "")[:4_096]
                if isinstance(data, dict)
                else "",
                "response_cap_chars": UPGRADE_RESPONSE_CAP_CHARS,
                "response_truncated": True,
                "response_hard_compacted": True,
            },
            "diagnostics": [
                {
                    "code": "upgrade_response_cap_exceeded",
                    "message": (
                        "The structured recovery carrier exceeded the public response "
                        "cap and was refused; inspect log_path for the complete run."
                    ),
                }
            ],
        }

    return response


def _parse_bridge_release_required(output: str) -> dict[str, Any] | None:
    """Return the last well-formed protocol-bridge handoff in subprocess output."""

    found: dict[str, Any] | None = None
    allowed_fields = {
        "status",
        "code",
        "runner_protocol",
        "minimum_runner_protocol",
        "why",
        "package",
        "package_present",
        "command_argv",
        "command",
        "hosts_to_stop",
        "restart_guidance",
        "legacy_wrapper_limitation",
        "acquisition",
    }
    prose_fields = {
        "why",
        "command",
        "hosts_to_stop",
        "restart_guidance",
        "legacy_wrapper_limitation",
        "acquisition",
    }
    integer_fields = {"runner_protocol", "minimum_runner_protocol"}
    short_text_fields = {"status", "code"}
    for line in (output or "").splitlines():
        try:
            parsed = json.loads(line.strip())
        except Exception:  # noqa: BLE001 — unknown output retains generic handling
            continue
        if (
            isinstance(parsed, dict)
            and parsed.get("code") == "bridge_release_required"
            and isinstance(parsed.get("package"), str)
            and isinstance(parsed.get("package_present"), bool)
        ):
            package = parsed["package"]
            argv = parsed.get("command_argv")
            if len(package) > 4_096:
                continue
            if any(
                key in parsed
                and (
                    not isinstance(parsed[key], int)
                    or isinstance(parsed[key], bool)
                )
                for key in integer_fields
            ):
                continue
            if any(
                key in parsed
                and (
                    not isinstance(parsed[key], str)
                    or len(parsed[key]) > UPGRADE_SUMMARY_KEY_CAP_CHARS
                )
                for key in short_text_fields
            ):
                continue
            if any(
                key in parsed and not isinstance(parsed[key], str)
                for key in prose_fields
            ):
                continue
            if argv is not None and (
                not isinstance(argv, list)
                or len(argv) > 32
                or any(not isinstance(item, str) or len(item) > 4_096 for item in argv)
                or len(json.dumps(argv, ensure_ascii=False))
                > UPGRADE_BRIDGE_ARGV_CAP_CHARS
            ):
                continue
            normalized = {
                key: value for key, value in parsed.items() if key in allowed_fields
            }
            truncated_fields: list[str] = []
            for key in prose_fields:
                value = normalized.get(key)
                if isinstance(value, str) and len(value) > UPGRADE_SUMMARY_VALUE_CAP_CHARS:
                    normalized[key] = (
                        value[:UPGRADE_SUMMARY_VALUE_CAP_CHARS]
                        + "\n[... bridge text truncated; see log_path ...]"
                    )
                    truncated_fields.append(key)
            if truncated_fields:
                normalized["text_truncated_fields"] = truncated_fields
            omitted_count = len(set(parsed) - allowed_fields)
            if omitted_count:
                normalized["omitted_field_count"] = omitted_count
            found = normalized
    return found


_CUTOVER_RESTART_INSTRUCTION = (
    "The 1.15 review-evidence cutover acted on this repository: fully restart "
    "every attached MCP/agent host (including this one) before lifecycle "
    "mutation resumes. An in-process wf_reload_mcp is not sufficient and was "
    "not performed."
)


def _cutover_restart_required(root: Path, summary: dict[str, Any] | None) -> bool:
    """True when this upgrade run was cutover-active (full restart required).

    Detection reads the ``review_sidecar_cleanup`` counts recorded by the
    upgrade in its machine-readable channels: the parsed summary sentinel
    first (the only channel that survives cleanup's lock removal), then the
    retained upgrade lock state. Absent counts mean the run never reached the
    cutover phase — reload behavior stays untouched.
    """
    counts: Any = None
    if isinstance(summary, dict):
        counts = summary.get("review_sidecar_cleanup")
    if not isinstance(counts, dict):
        try:
            _ulib = _load_upgrade_lib()
            lock = _ulib.read_upgrade_lock(root) if _ulib is not None else None
            counts = (
                lock.get("review_sidecar_cleanup")
                if isinstance(lock, dict)
                else None
            )
        except Exception:
            counts = None
    return isinstance(counts, dict) and bool(counts.get("restart_required"))


def _upgrade_next_step(phase: str) -> tuple[str, list[str]]:
    """Return a phase-aware ``(next_step, next_tools)`` for the wf_upgrade response (wave 1p8eu)."""
    if phase == "preflight_to_docs_gate":
        return (
            "Run the agent editing pass (drift/journal/spec reconciliation per seed-160), then "
            "call wf_upgrade(phase='update_index') and wf_upgrade(phase='cleanup').",
            ["wf_upgrade_status", "wf_reload_mcp"],
        )
    if phase in ("update_index", "rebuild_index"):
        return (
            "Call wf_upgrade(phase='cleanup') to remove the upgrade lock and print the summary.",
            ["wf_upgrade_status", "wf_reload_mcp"],
        )
    if phase == "cleanup":
        return (
            "Upgrade complete. Call wf_reload_mcp() if the in-process server code is not yet "
            "reloaded; review the summary's reconciliation findings and resolve stale references.",
            ["wf_reload_mcp", "wf_upgrade_status"],
        )
    if phase == "resume_after_gate":
        return (
            "Docs gate recovery also established or refreshed the historical-memory "
            "checkpoint. Inspect the returned memory worklist; validate any pending "
            "candidates, then call wf_upgrade(phase='resume_after_memory').",
            ["memory_backfill", "memory_validate", "wf_upgrade_status"],
        )
    if phase == "resume_after_memory":
        return (
            "When the response reports indexed, call wf_upgrade(phase='cleanup'). "
            "If it remains awaiting validation, continue bounded backfill and "
            "memory_validate calls first.",
            ["memory_backfill", "memory_validate", "wf_upgrade_status"],
        )
    return ("Check wf_upgrade_status for the current lock state.", ["wf_upgrade_status"])


def wf_upgrade_response(
    root: Path,
    phase: str = "preflight_to_docs_gate",
    mode: str = "apply",
    confirm_hosts_stopped: bool = False,
    rebuild_storage: bool = False,
) -> dict[str, Any]:
    """Invoke upgrade_wavefoundry.py for the requested phase (12r0b).

    mode values:
      "dry_run" — print the full upgrade plan + hook inventory (seed diffs,
          extension module source, convention hook scripts) without modifying
          anything on disk. Use this before the real upgrade to review what
          will change and inspect any hook code. The phase parameter is
          ignored in dry_run mode.
      "apply" (default) — execute the requested phase for real.

    phase values (apply mode only):
      "preflight_to_docs_gate" — phases 0–3 (default): pre-flight, surface
          rendering, pruning, docs gate. Non-interactive (--yes).
      "update_index" — phase 4 (default): incremental docs index update
          (blocking) + code index (background). Re-embeds only files that
          changed; auto-escalates to full rebuild when chunker or embedding
          model version changed. Use for normal post-editing-pass runs.
      "rebuild_index" — phase 4 (full): re-embeds every file from scratch.
          Use when update_index is insufficient (e.g. index corruption, or
          a chunker bump that the auto-escalation did not catch).
      "cleanup" — phase 5: remove upgrade lock + print operator summary.
      "resume_after_gate" — rebuild and persist current review-status projection,
          then re-run docs-gardener + docs-lint against the already-extracted
          tree (no extract/render/prune). Recovers a retained lock whose
          failed_phase is "review_status_projection" or "docs_gate"; preserves
          the actual failing phase on retry and, after the gate passes,
          establishes or refreshes the historical-memory checkpoint. It may
          return action-required memory work; continue with "resume_after_memory".
      "resume_after_memory" — recompute the authoritative historical-memory
          pending set and publish Phase 4 only after it reaches zero. This and
          every index/cleanup phase refuse while review projection or docs lint
          has a retained failed phase; recover through "resume_after_gate".
    """
    from wf_server import server_impl
    if type(confirm_hosts_stopped) is not bool:
        return server_impl._response("error", {}, diagnostics=[_diagnostic(
            "invalid_arguments", "confirm_hosts_stopped must be an explicit boolean.")])
    if type(rebuild_storage) is not bool:
        return server_impl._response("error", {}, diagnostics=[_diagnostic(
            "invalid_arguments", "rebuild_storage must be an explicit boolean.")])
    if rebuild_storage and mode == "apply" and phase != "preflight_to_docs_gate":
        return server_impl._response("error", {}, diagnostics=[_diagnostic(
            "invalid_arguments", "Select rebuild_storage during ordinary upgrade resume (preflight_to_docs_gate); the receipt retains it for later phases.")])
    valid_modes = ("apply", "dry_run")
    if mode not in valid_modes:
        return server_impl._response(
            "error",
            {"mode": mode, "valid_modes": list(valid_modes)},
            diagnostics=[_diagnostic("invalid_mode", f"Unknown mode {mode!r}. Valid: {valid_modes}")],
        )

    valid_phases = (
        "preflight_to_docs_gate",
        "update_index",
        "rebuild_index",
        "cleanup",
        "resume_after_gate",
        "resume_after_memory",
    )
    if mode == "apply" and phase not in valid_phases:
        return server_impl._response(
            "error",
            {"phase": phase, "valid_phases": list(valid_phases)},
            diagnostics=[_diagnostic("invalid_phase", f"Unknown phase {phase!r}. Valid: {valid_phases}")],
        )

    upgrade_script = server_impl.SCRIPTS_DIR / "upgrade_wavefoundry.py"
    if not upgrade_script.exists():
        return server_impl._response(
            "error",
            {},
            diagnostics=[_diagnostic("script_not_found", f"upgrade_wavefoundry.py not found at {upgrade_script}")],
        )

    if mode == "dry_run":
        cmd = [server_impl._preferred_python(), str(upgrade_script), "--root", str(root), "--dry-run"]
    else:
        # Pre-create the log file so log_path in the response is always valid,
        # even if the upgrade fails before the script opens it.  The upgrade
        # script manages truncation (mode="w") and appending (mode="a") itself.
        _log_path = root / ".wavefoundry" / "logs" / "upgrade.log"
        try:
            _log_path.parent.mkdir(parents=True, exist_ok=True)
            _log_path.touch(exist_ok=True)
        except OSError:
            pass

        # All apply-mode phases run non-interactively (no TTY in MCP).
        cmd = [server_impl._preferred_python(), str(upgrade_script), "--root", str(root), "--yes"]
        if phase == "update_index":
            cmd.append("--update-index")
        elif phase == "rebuild_index":
            cmd.append("--rebuild-index")
        elif phase == "cleanup":
            cmd.append("--cleanup")
        elif phase == "resume_after_gate":
            cmd.append("--resume-after-gate")  # rebuild review projection, then re-run docs gate
        elif phase == "resume_after_memory":
            cmd.append("--resume-after-memory")
        if confirm_hosts_stopped:
            cmd.append("--confirm-hosts-stopped")
        if rebuild_storage:
            cmd.append("--rebuild-storage")
        # phase == "preflight_to_docs_gate": --yes only (default run)

    # Bind an expected restart response to this child invocation. A previous
    # receipt (or exit 3 by itself) must never disguise a new upgrade failure.
    storage_invocation = uuid.uuid4().hex
    try:
        result = server_impl._mcp_subprocess_run(
            cmd,
            cwd=str(root),
            check=False,
            env={**os.environ, "WAVEFOUNDRY_STORAGE_OLD_MCP_PID": str(os.getpid()),
                 "WAVEFOUNDRY_STORAGE_INVOCATION": storage_invocation},
        )
    except OSError as exc:
        return _bounded_upgrade_response_envelope(
            server_impl._response(
                "error",
                {"phase": phase},
                diagnostics=[_diagnostic("spawn_failed", str(exc))],
            )
        )

    output = (result.stdout or "") + (result.stderr or "")
    # log_path is deterministic and always present for apply-mode phases;
    # dry_run is read-only so it writes no log file.
    log_path = (
        str(root / ".wavefoundry" / "logs" / "upgrade.log")
        if mode == "apply"
        else None
    )
    displayed_output, output_truncated = server_impl._bounded_subprocess_output(
        output,
        cap_chars=UPGRADE_OUTPUT_CAP_CHARS,
        truncation_hint=(
            "see log_path for the complete run"
            if log_path is not None
            else "full output is available only from an apply-mode upgrade log"
        ),
    )
    data = {
        "phase": phase,
        "exit_code": result.returncode,
        "output": displayed_output.strip(),
        "output_truncated": output_truncated,
        "output_total_chars": len(output),
        "log_path": log_path,
    }

    # Wave 1p8eu — parse the structured operator summary emitted by upgrade_wavefoundry.py on its
    # WAVE_UPGRADE_SUMMARY_JSON: sentinel line into data['summary'] so agents read computed fields
    # (from/to version, pruned_count, docs_gate, index_update, failed_phase, is_major_or_minor, the
    # 1p8et reconciliation findings) instead of regex-scraping prose. FAIL-SAFE: an absent or
    # malformed sentinel leaves 'output' as the only payload — never raises; 'output' and 'exit_code'
    # stay unchanged (back-compatible).
    summary = _parse_upgrade_summary(output)
    if summary is not None:
        data["summary"] = _bounded_upgrade_summary(summary)

    # Wave 1u44n: an OBSERVED failed/refused Phase 4 publication must reach the
    # caller as a diagnostic naming index_health, on the success AND failure
    # envelopes. The summary's `index_update` value domain carries it for the
    # sentinel-emitting phases; the standalone --update/--rebuild-index phases
    # (no sentinel) are detected from the child's printed failure marker.
    _index_pub_failed = bool(
        (
            summary is not None
            and str(summary.get("index_update") or "").startswith(
                "publication failed"
            )
        )
        or "Index publication FAILED" in output
    )
    _index_pub_diag = (
        _diagnostic(
            "index_publication_failed",
            "Index publication did not complete; the semantic index epoch is "
            "incomplete and readers fail closed. Run index_build, then "
            "confirm with index_health.",
            recovery_tools=["index_health", "index_build"],
            recovery_usage="index_health()",
        )
        if _index_pub_failed
        else None
    )
    _retired_cleanup_failed = bool(
        (
            summary is not None
            and summary.get("retired_model_cleanup_status") == "failed"
        )
        or "retired_model_cleanup_failed" in output
    )
    _retired_cleanup_diag = (
        _diagnostic(
            "retired_model_cleanup_failed",
            "An owned retired model component could not be removed; the "
            "upgrade lock was retained for an exact cleanup retry.",
            recovery_tools=["wf_upgrade_status", "wf_upgrade"],
            recovery_usage="wf_upgrade(phase='cleanup')",
        )
        if _retired_cleanup_failed
        else None
    )

    # Wave 1p8eu / F2 — compute the phase-aware next step + next_tools BEFORE the returncode check so
    # both the success AND the failure response carry them.
    _next_step, _next_tools = _upgrade_next_step(phase)
    if result.returncode != 0 and (
        phase == "resume_after_gate" or "--resume-after-gate" in output
    ):
        _next_step = (
            "Resolve the typed review-state or docs findings, then retry "
            "wf_upgrade(phase='resume_after_gate'). Index publication and "
            "cleanup remain blocked until that recovery succeeds."
        )
        _next_tools = ["wf_upgrade_status", "wf_upgrade"]

    if result.returncode == 3 and mode == "apply":
        try:
            migration = server_impl._load_script("sqlite_storage_migration")
            storage_action = migration.read_restart_action(root, 3, storage_invocation)
        except (OSError, RuntimeError, ValueError, AttributeError):
            storage_action = None
        if isinstance(storage_action, dict):
            storage_action = dict(storage_action)
            hosts = storage_action.get("old_hosts", [])
            storage_action["old_hosts"] = hosts[:50]
            storage_action["old_hosts_total"] = len(hosts)
            storage_action["old_hosts_omitted"] = max(0, len(hosts) - 50)
            storage_action["receipt_path"] = str(root / ".wavefoundry/index/sqlite-migration.json")
            response = server_impl._response(
                "ok",
                {**data, "state": "restart_required", "restart_required": True,
                 "code": "storage_restart_required", "action_required": storage_action,
                 "failed_phase": None},
                diagnostics=[],
                next_tools=["wf_upgrade_status"],
            )
            response["next_step"] = (
                "Save action_required.command_argv before stopping MCP. Stop all "
                "Wavefoundry dashboard and MCP servers for this repository, including "
                "other editors and this invoking server. Run the exact command through "
                "the ordinary non-MCP shell; do not start another MCP server to resume. "
                "Preserve the migration receipt and selected package. Follow the CLI "
                "recovery instructions before restarting hosts."
            )
            return _bounded_upgrade_response_envelope(response)

    if result.returncode == 3 and mode == "apply":
        try:
            extensions = server_impl._load_script("upgrade_extensions")
            guard_action = extensions.read_index_guard_action(root, 3, storage_invocation)
        except (OSError, RuntimeError, ValueError, AttributeError):
            guard_action = None
        if isinstance(guard_action, dict):
            guard_action = dict(guard_action)
            hosts = guard_action.get("old_hosts", [])
            guard_action["old_hosts"] = hosts[:50]
            guard_action["old_hosts_total"] = len(hosts)
            guard_action["old_hosts_omitted"] = max(0, len(hosts) - 50)
            response = server_impl._response(
                "action_required", {**data, "state": "restart_required", "restart_required": True,
                       "code": "index_guard_restart_required", "action_required": guard_action,
                       "failed_phase": None},
                diagnostics=[], next_tools=["wf_upgrade_status"],
            )
            response["next_step"] = extensions.INDEX_GUARD_NEXT_STEP
            return _bounded_upgrade_response_envelope(response)

    if result.returncode == 4:
        memory_gate: dict[str, Any] = {}
        action_required: dict[str, Any] = {}
        try:
            _ulib = _load_upgrade_lib()
            lock = _ulib.read_upgrade_lock(root) if _ulib is not None else None
            run_id = (
                str(lock.get("memory_backfill_run_id") or "").strip()
                if isinstance(lock, dict)
                else ""
            )
            if run_id:
                backfill = server_impl._load_script("memory_backfill")
                memory_gate = {
                    **backfill.run_summary(root, run_id),
                    **backfill.validation_worklist(root, run_id),
                }
            if isinstance(lock, dict) and isinstance(lock.get("action_required"), dict):
                action_required = dict(lock["action_required"])
        except (OSError, RuntimeError, ValueError) as exc:
            memory_gate = {"status_error": str(exc)}
        action_valid = (
            action_required.get("kind") == "historical_memory"
            and action_required.get("resume_phase") == "resume_after_memory"
            and bool(action_required.get("token"))
            and bool(action_required.get("run_id"))
            and action_required.get("run_id") == run_id
            and action_required.get("state") in {
                "awaiting_memory_validation", "awaiting_memory_publication"
            }
        )
        if not action_valid:
            # A code-4 child exit without the durable, self-identifying memory
            # checkpoint is not a normal pause.  Fall through to generic error
            # handling so malformed bridges and real Phase-4 failures stay
            # visible rather than being relabelled as validation work.
            result.returncode = 1
        if result.returncode != 4:
            pass
        else:
            publication_ready = action_required.get("state") == "awaiting_memory_publication"
            state = "awaiting_memory_publication" if publication_ready else "awaiting_memory_validation"
            next_tools = (
            ["wf_reload_mcp", "wf_upgrade_status", "wf_upgrade"]
            if publication_ready
            else ["wf_reload_mcp", "memory_backfill", "memory_validate"]
            )
            action = server_impl._response(
            "ok",
            {
                **data,
                "state": state,
                "memory_backfill": memory_gate,
                "action_required": action_required,
                "failed_phase": None,
            },
            diagnostics=[],
            next_tools=next_tools,
            )
            action["next_step"] = (
            "Reload the newly installed MCP implementation, then call "
            "wf_upgrade(phase='resume_after_memory') to publish the prepared historical memory."
            if publication_ready else
            "Reload the newly installed MCP implementation, run bounded historical "
            "memory backfill and focused validation, then call "
            "wf_upgrade(phase='resume_after_memory')."
            )
            return _bounded_upgrade_response_envelope(action)
    if result.returncode != 0:
        bridge_handoff = _parse_bridge_release_required(output)
        if bridge_handoff is not None:
            handoff = server_impl._response(
                "error",
                {**data, "bridge_release_required": bridge_handoff},
                diagnostics=[
                    _diagnostic(
                        "bridge_release_required",
                        str(bridge_handoff.get("why") or "A protocol bridge is required."),
                    )
                ],
                next_tools=["wf_stop_dashboard"],
            )
            handoff["next_step"] = (
                "Stop the dashboard through wf_stop_dashboard, disconnect/stop every "
                "Wavefoundry MCP server for this repository, keep the agent session idle, "
                "and have the agent run command_argv through its ordinary non-MCP shell. "
                "Then fully restart every attached host and follow the package's structured "
                "recovery result."
                if bridge_handoff.get("package_present")
                else "Download the named single Wavefoundry package, then repeat this upgrade call."
            )
            return _bounded_upgrade_response_envelope(handoff)
        exit_meanings = {1: "docs gate failed", 2: "surface rendering failed", 3: "pre-flight check failed"}
        reason = exit_meanings.get(result.returncode, f"exited {result.returncode}")
        if result.returncode == 1 and (
            phase == "resume_after_gate" or "--resume-after-gate" in output
        ):
            reason = "review-state projection or docs gate failed"
        if result.returncode == 1 and _index_pub_failed:
            # 1u44n: the standalone index phases reuse exit 1; do not mislabel
            # an observed publication failure as a docs-gate failure.
            reason = "index publication failed"
        err = server_impl._response(
            "error",
            data,
            diagnostics=[_diagnostic("upgrade_failed", f"Upgrade phase '{phase}' failed: {reason}")],
            next_tools=_next_tools,
        )
        if _index_pub_diag is not None:
            err.setdefault("diagnostics", []).append(_index_pub_diag)
        err["next_step"] = _next_step
        if _retired_cleanup_diag is not None:
            err.setdefault("diagnostics", []).append(_retired_cleanup_diag)
            err["next_step"] = (
                "Resolve the exact component ownership or filesystem removal "
                "failure, then retry wf_upgrade(phase='cleanup')."
            )
            err["next_tools"] = ["wf_upgrade_status", "wf_upgrade"]
        return _bounded_upgrade_response_envelope(err)

    # 1.15 cutover scoping: when this run's review-sidecar cleanup was
    # cutover-active (counts carry restart_required), the in-process reload
    # below must NOT fire and the wf_reload_mcp suggestion is replaced by the
    # full-restart instruction. Non-cutover runs keep the established reload
    # flow and guidance untouched.
    cutover_restart = mode == "apply" and _cutover_restart_required(root, summary)
    if cutover_restart:
        _next_tools = [t for t in _next_tools if t != "wf_reload_mcp"]
        if phase == "cleanup":
            _next_step = (
                "Upgrade complete. " + _CUTOVER_RESTART_INSTRUCTION + " After "
                "restarting, review the summary's reconciliation findings and "
                "resolve stale references."
            )
        else:
            _next_step = _next_step + " " + _CUTOVER_RESTART_INSTRUCTION

    resp = server_impl._response("ok", data, usage=f"wf_upgrade(phase='{phase}')", next_tools=_next_tools)
    if _index_pub_diag is not None:
        # 1u44n: a zero-exit run whose summary reports a failed publication
        # still carries the index_health-naming diagnostic.
        resp.setdefault("diagnostics", []).append(_index_pub_diag)
    resp["next_step"] = _next_step
    # Wave 1p3dk / 1p3ho: reload the MCP server's in-process code after the
    # main upgrade phase or cleanup so subsequent MCP calls (index_health,
    # code_ask, etc.) use the freshly-extracted server_impl. Without this, the
    # parent MCP process keeps the old code in memory even though the new
    # framework files are on disk. Phase `preflight_to_docs_gate` now runs
    # Phase 4 (index update) inside the subprocess too, so reload here is the
    # final step that brings the running server in sync with everything else.
    if mode == "apply" and phase in ("preflight_to_docs_gate", "cleanup"):
        if cutover_restart:
            resp.setdefault("diagnostics", []).append(
                _diagnostic(
                    "mcp_reload_suppressed",
                    "In-process MCP reload suppressed: "
                    + _CUTOVER_RESTART_INSTRUCTION,
                )
            )
        else:
            try:
                import server as _srv
                reload_resp = _srv.perform_mcp_reload()
                if reload_resp.get("status") == "ok":
                    resp.setdefault("data", {})["mcp_reload"] = reload_resp.get("data", {})
                    resp.setdefault("diagnostics", []).extend(
                        reload_resp.get("diagnostics", [])
                    )
                else:
                    resp.setdefault("diagnostics", []).extend(reload_resp.get("diagnostics", []))
            except Exception as exc:
                resp.setdefault("diagnostics", []).append(
                    _diagnostic("mcp_reload_skipped", f"In-process MCP reload skipped: {exc}")
                )
    return _bounded_upgrade_response_envelope(resp)


def wf_upgrade_status_response(root: Path) -> dict[str, Any]:
    """Return the current upgrade lock state (R5 — 12r08)."""
    from wf_server import server_impl
    _ulib = _load_upgrade_lib()
    if _ulib is not None:
        lock = _ulib.read_upgrade_lock(root)
    else:
        lock = None

    if lock is None:
        data: dict[str, Any] = {
            "in_progress": False,
            "started_at": None,
            "from_version": None,
            "to_version": None,
            "pid": None,
            "retired_model_cleanup_status": "not_applicable",
            "retired_model_cleanup_removed": [],
            "retired_model_cleanup_absent": [],
            "retired_model_cleanup_unowned": [],
            "retired_model_cleanup_failed": [],
        }
    else:
        cleanup_projection = _project_retired_model_cleanup_fields(lock)
        data = {
            "in_progress": True,
            "started_at": lock.get("started_at"),
            "from_version": lock.get("from_version"),
            "to_version": lock.get("to_version"),
            "pid": lock.get("pid"),
            "current_phase": lock.get("current_phase"),
            "failed_phase": None if isinstance(lock.get("action_required"), dict) else lock.get("failed_phase"),
            "failed_at": None if isinstance(lock.get("action_required"), dict) else lock.get("failed_at"),
            "action_required": lock.get("action_required"),
            **cleanup_projection,
        }
        run_id = str(lock.get("memory_backfill_run_id") or "").strip()
        if run_id:
            try:
                backfill = server_impl._load_script("memory_backfill")
                data["memory_backfill"] = {
                    **backfill.run_summary(root, run_id),
                    **backfill.validation_worklist(root, run_id),
                }
            except (OSError, RuntimeError, ValueError) as exc:
                data["memory_backfill"] = {
                    "run_id": run_id,
                    "status_error": str(exc),
                }
    return server_impl._response("ok", data, usage="wf_upgrade_status()")
