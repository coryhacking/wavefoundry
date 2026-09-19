"""Named lifecycle checks; sequencing and writes remain in the orchestrator."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, NotRequired, Optional, TypedDict

import lifecycle_gate_support
import review_evidence
import sensor_runner
from public_contract import CONFIGURED_GATE_OUTCOMES
from review_policy import has_reprepare_marker
from review_evidence import (
    REVIEW_EVIDENCE_INDEPENDENCE_INVALID,
    REVIEW_STATUS_MARKER_BEGIN,
    REVIEW_STATUS_MARKER_END,
    canonicalize_finding_synthesis_markers,
    render_review_evidence_projection,
    render_review_status_projection,
    repair_independence_violations,
    resolve_review_authority,
    review_status_rows,
    validate_external_review_evidence,
)


class GateDiagnostic(TypedDict):
    code: str
    message: str
    recovery_tools: NotRequired[list[str]]
    recovery_usage: NotRequired[str]
    advisory: NotRequired[bool]


@dataclass
class GateContext:
    root: Path
    wave_md: Path
    wave_text: str
    mode: str
    lint_result: Mapping[str, Any]
    phase: str


@dataclass
class GateResult:
    diagnostics: list[GateDiagnostic] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


Gate = Callable[[GateContext], GateResult]


def has_blocking_diagnostics(diagnostics: Iterable[Mapping[str, Any]]) -> bool:
    """Whether any diagnostic blocks, treating an advisory as non-blocking.

    The single implementation of the advisory-aware blocking predicate.  Wave
    ``1yd98`` extracted it from the close envelope's inline test and prepare's
    local closure so the close sensor precondition, the close envelope and the
    prepare early return cannot drift apart.  A diagnostic blocks unless it
    carries ``advisory: True``; the direction matters, because a missing
    ``advisory`` key means blocking.
    """

    return any(diagnostic.get("advisory") is not True for diagnostic in diagnostics)


def _wave_review_policy_diagnostics(root: Path) -> list[dict[str, Any]]:
    policy = lifecycle_gate_support._read_wave_council_policy(root)
    if not policy.get("invalid"):
        return []
    return [
        lifecycle_gate_support._diagnostic(
            "review_policy_reprepare_required",
            str(error),
            recovery_tools=["wf_get_change", "wf_validate_docs"],
            recovery_usage="Fix docs/workflow-config.json wave_review.enabled/delivery_mode, then call wf_validate_docs().",
        )
        for error in policy.get("errors", ["wave_review policy is invalid"])
    ]


def _review_evidence_diagnostics(
    text: str,
    *,
    root: Path | None = None,
    wave_md: Path | None = None,
    closure: bool = False,
    required_run_kind: str | None = None,
) -> list[dict[str, Any]]:
    """Translate the external-ledger validator's errors into lifecycle diagnostics."""

    if root is None or wave_md is None:
        errors = ["external review evidence validation requires repository root and wave record path"]
        result = None
    else:
        if not lifecycle_gate_support._wave_uses_external_review_evidence(root, wave_md):
            errors = []
            result = None
        else:
            result = validate_external_review_evidence(wave_md, closure=closure)
            errors = list(result.errors)
            if not result.errors:
                # Wave 1v0lw: the projection re-read routes through the seam;
                # a failure keeps the historical message shape with the
                # sanitized cause instead of raising or leaking the path.
                raw_projection, projection_read_error = lifecycle_gate_support._read_wave_record_text(wave_md)
                if raw_projection is None:
                    errors.append(
                        "Finding Synthesis projection could not be checked: "
                        f"{projection_read_error}"
                    )
            if not result.errors and raw_projection is not None:
                try:
                    # Compare in canonical form (wave 1tb4z, same seam as the
                    # lint and dashboard paths): legacy marker namespaces and
                    # the retired bodyless-details projection are current, not
                    # stale — archives are never rewritten or flagged.
                    canonical_projection = canonicalize_finding_synthesis_markers(
                        raw_projection
                    )
                    if render_review_evidence_projection(canonical_projection, result.records) != canonical_projection:
                        errors.append(
                            f"Finding Synthesis projection is stale relative to canonical {review_evidence.EVENTS_FILENAME}; "
                            "replay the last typed review event to reconcile it"
                        )
                    marker_present = (
                        REVIEW_STATUS_MARKER_BEGIN in canonical_projection
                        or REVIEW_STATUS_MARKER_END in canonical_projection
                    )
                    closed_archive = bool(
                        re.search(r"(?mi)^Status:\s*closed\s*$", raw_projection)
                    )
                    if marker_present and not closed_archive and render_review_status_projection(
                        canonical_projection,
                        result.records,
                        lifecycle_gate_support._review_status_signoff_keys(
                            root, canonical_projection, result.records
                        ),
                    ) != canonical_projection:
                        errors.append(
                            "Review Status projection is stale relative to canonical "
                            f"{review_evidence.EVENTS_FILENAME}; replay the last typed review event to reconcile it"
                        )
                except (OSError, ValueError) as exc:
                    errors.append(f"Finding Synthesis projection could not be checked: {exc}")
    if result is not None and required_run_kind is not None:
        has_required_run = any(
            record.get("record_type") == "review_run"
            and record.get("run_kind") == required_run_kind
            for record in result.records
        )
        if not has_required_run:
            errors.append(
                f"marked wave requires a `{required_run_kind}` Review Run Record at this lifecycle phase"
            )
    diagnostics = [
        lifecycle_gate_support._diagnostic(
            "review_evidence_invalid",
            error,
            recovery_tools=["wf_current_wave", "wf_validate_docs"],
            recovery_usage="wf_current_wave()",
        )
        for error in errors
    ]
    # Wave 1tmb2: close-time repair/reverification independence audit.  Runs
    # ONLY at the close gate (closure=True) and only while the target wave's
    # lifecycle status is non-closed: sealed/closed archives are never
    # retroactively invalidated by validation or upgrade — an archive becomes
    # forward-audited only if an operator explicitly reopens it.  Generic
    # ledger validation never runs this audit.
    if (
        closure
        and result is not None
        and not re.search(r"(?mi)^Status:\s*closed\s*$", text)
    ):
        for violation in repair_independence_violations(result.records):
            diagnostics.append(
                lifecycle_gate_support._diagnostic(
                    REVIEW_EVIDENCE_INDEPENDENCE_INVALID,
                    violation,
                    recovery_tools=["wf_review_event"],
                    recovery_usage=(
                        f"wf_review_event(wave_id={wave_md.parent.name!r}, event='finding', "
                        "run_kind='repair_start', cycle=<next cycle>, ...)  # then a "
                        "distinct-role/context reverification"
                    ),
                )
            )
    return diagnostics


def _approval_evidence_diagnostics(
    text: str,
    required_signoff_keys: Iterable[str],
    *,
    root: Path | None = None,
    wave_md: Path | None = None,
    records: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Bind prose lane/council signoffs to executed evidence on marked waves."""

    if records is None:
        if root is None or wave_md is None:
            return []
        if not lifecycle_gate_support._wave_uses_external_review_evidence(root, wave_md):
            return []
        result = validate_external_review_evidence(wave_md)
        if result.errors:
            return []
        rows = result.records
    else:
        rows = tuple(records)
    status = review_status_rows(rows, required_signoff_keys)
    blocked = [row for row in status if row["state"] != "approved"]
    if not blocked:
        return []
    details = "; ".join(
        f"{row['signoff_key']}={row['state']} ({row['why']})" for row in blocked
    )
    return [
        lifecycle_gate_support._diagnostic(
            "missing_executable_approval_evidence",
            "Marked wave approval signoffs require executed delivery Evidence Records with "
            "claim_kind `approval`, claim_id `approval:<signoff-key>`, and a matching actor "
            "(`operator` for operator-signoff, `wave-council` for council signoffs, or the exact "
            "specialist lane); specialist/council evidence must be fresh and independent, and its "
            f"chronology must follow every affected repair; {details}.",
            recovery_tools=["wf_review_wave", "wf_current_wave"],
            recovery_usage="wf_review_wave()",
        )
    ]


SHARED_DELIVERY_DIAGNOSTIC_CODES = (
    "review_evidence_invalid",
    "missing_executable_approval_evidence",
    "docs_lint_error",
    "missing_operator_signoff",
    "missing_required_lane",
    "missing_wave_council_signoff",
    "review_policy_receipt_stale",
    "review_policy_reprepare_required",
)


CLOSURE_ONLY_DIAGNOSTIC_CODES = (
    "docs_gardener_failed",
    "open_changes_remaining",
    "missing_signoff_evidence",
    "review_evidence_independence_invalid",
    "memory_validation_candidates_missing",
    "memory_validation_required",
    "memory_validation_check_failed",
    "secrets_gate_unresolved",
    "silent_unchecked_items_at_close",
    "gates_forced_closed",
    "review_projection_failed",
)


def _evaluate_shared_delivery_state(
    root: Path,
    wave_md: Path,
    wave_text: str,
    lint_result: Mapping[str, Any],
    *,
    lifecycle_phase: str = "review",
) -> dict[str, Any]:
    """Return the one shared delivery-gate result consumed by Review and Close."""

    wave_id = wave_md.parent.name
    authority = resolve_review_authority(root, wave_md, wave_text=wave_text)
    wave_lanes = lifecycle_gate_support._extract_required_review_lanes(wave_text)
    project_lanes = lifecycle_gate_support._read_project_required_review_lanes(root)
    required_lanes = list(
        dict.fromkeys([*wave_lanes, *project_lanes])
    )
    required_council = lifecycle_gate_support._required_wave_council_signoffs(
        root, lifecycle_phase, wave_text=wave_text, wave_md=wave_md
    )
    diagnostics = _review_evidence_diagnostics(
        wave_text,
        root=root,
        wave_md=wave_md,
        required_run_kind="initial_delivery",
    )
    diagnostics.extend(_wave_review_policy_diagnostics(root))
    diagnostics.extend(
        lifecycle_gate_support._review_policy_receipt_diagnostics(root, wave_md, wave_text)
    )
    if has_reprepare_marker(wave_text):
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "review_policy_reprepare_required",
                "This wave must be re-Prepared before delivery review or close.",
                recovery_tools=["wf_prepare_wave"],
                recovery_usage=f"wf_prepare_wave(wave_id={wave_id!r}, mode='ready')",
            )
        )
    diagnostics.extend(
        _approval_evidence_diagnostics(
            wave_text,
            ["operator-signoff", *required_lanes, *required_council],
            root=root,
            wave_md=wave_md,
        )
    )
    if not lint_result.get("passed"):
        diagnostics.extend(
            lifecycle_gate_support._diagnostic("docs_lint_error", error, recovery_tools=["wf_validate_docs"])
            for error in lint_result.get("errors", [])
        )
    diagnostics.extend(lifecycle_gate_support._docs_lint_warning_diagnostics(lint_result))
    operator_current = authority.operator_signoff_present()
    if not operator_current:
        remedy = (
            "Record wf_review_event(event='approval', signoff_key='operator-signoff', "
            "approval_phase='delivery', mode='create')."
            if authority.typed
            else f"Add `operator-signoff: approved` to `{review_evidence.REVIEW_EVIDENCE_SECTION}` in wave.md."
        )
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "missing_operator_signoff",
                "Operator review approval is required. " + remedy,
                recovery_tools=["wf_review_event", "wf_review_wave"],
                recovery_usage=f"wf_review_wave(wave_id={wave_id!r})",
            )
        )
    lane_results = [
        {
            "lane": lane,
            "recorded_signoff": authority.signoff_current(
                lane, approval_phase="delivery"
            ),
        }
        for lane in required_lanes
    ]
    missing_lanes = [
        row["lane"] for row in lane_results if not row["recorded_signoff"]
    ]
    if missing_lanes:
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "missing_required_lane",
                "Required delivery lanes without a current approval: "
                + ", ".join(missing_lanes),
                recovery_tools=["wf_review_event", "wf_review_wave"],
                recovery_usage=f"wf_review_wave(wave_id={wave_id!r})",
            )
        )
    council_results = [
        {
            "signoff_key": key,
            "recorded_signoff": authority.signoff_current(
                key,
                approval_phase=(
                    "readiness"
                    if key == "wave-council-readiness"
                    else "delivery"
                ),
            ),
        }
        for key in required_council
    ]
    missing_council = [
        row["signoff_key"]
        for row in council_results
        if not row["recorded_signoff"]
    ]
    if missing_council:
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "missing_wave_council_signoff",
                "Required delivery Council approval missing: "
                + ", ".join(missing_council),
                recovery_tools=["wf_review_event", "wf_review_wave"],
                recovery_usage=f"wf_review_wave(wave_id={wave_id!r})",
            )
        )
    blocking = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.get("code") in SHARED_DELIVERY_DIAGNOSTIC_CODES
    ]
    return {
        "diagnostics": diagnostics,
        "blocking_diagnostics": blocking,
        "required_lanes": required_lanes,
        "lane_results": lane_results,
        "operator_current": operator_current,
        "required_council_signoffs": required_council,
        "council_results": council_results,
        "max_severity": authority.max_severity(),
        "authority": authority,
    }


def _framework_test_receipt_status(root: Path) -> dict[str, Any]:
    """Verify the existing ``test-cache.json`` receipt without running anything.

    ``run_tests.py`` writes the receipt only after a SUCCESSFUL run of the WHOLE
    suite, with an ``inputs_hash`` covering every file under
    ``.wavefoundry/framework/`` except ``VERSION``, ``MANIFEST``, the cache
    itself, ``test-run.lock``, and the ``index`` / ``__pycache__`` /
    ``.pytest_cache`` directories, so it self-invalidates the moment any
    framework file changes.  A missing, red, stale, or unreadable receipt is reported as NOT
    PROVEN rather than assumed green.

    Scope has TWO halves and both matter (delivery reverification found the
    first wording asserted one and negated the other).  The hash covers
    ``.wavefoundry/framework/`` only, so a documentation edit never makes a
    standing receipt stale -- but the receipt is written only on a whole-suite
    pass, so a failure triggered by content under ``docs/`` prevents a NEW
    receipt from being written.  The consequence: when the framework tree also
    changed, the standing receipt is stale and close is blocked; in a
    documentation-only wave a current green receipt persists and close is not
    blocked despite a red suite.  A green receipt attests the framework code,
    not the tree -- neither a whole-repository guarantee nor a whole-repository
    exemption.

    Where ``run_tests.py`` is absent this is a documented NO-OP that neither
    blocks nor claims proof: ``build_pack.py`` excludes the runner, the tests,
    and the receipt from the distribution under the standing policy that seeds
    must not instruct target repositories to run framework tests, so a
    pack-vendored target can never write the receipt and would otherwise be
    hard-blocked at close forever.
    """
    runner = root / lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL
    if not runner.is_file():
        return {"state": "not_applicable", "scope": "framework",
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` is absent (the distribution "
                           "excludes it), so the framework test receipt is not checked here.")}
    # Delivery review REL-DEL-2: `is_file()` follows symlinks, and the runner
    # derives its framework directory and its receipt path from its own RESOLVED
    # location.  A symlinked runner would therefore hash a foreign repository's
    # tree and read a foreign receipt -- a false proof, which is the one direction
    # a gate must never fail in.
    try:
        resolved_runner = runner.resolve()
        resolved_root = root.resolve()
        contained = resolved_runner.is_relative_to(resolved_root)
    except OSError as exc:
        return {"state": "unreadable", "scope": "framework",
                "detail": f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` could not be resolved: {exc}"}
    if not contained:
        return {"state": "unreadable", "scope": "framework",
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` resolves outside this repository "
                           f"({resolved_runner}); it would attest a different framework tree, "
                           "so no proof is claimed.")}
    module = lifecycle_gate_support._load_framework_test_runner(runner)
    if module is None or not hasattr(module, "_hash_inputs") or not hasattr(module, "_read_cache"):
        return {"state": "unreadable", "scope": "framework",
                "detail": f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` could not be loaded to verify the receipt."}
    # Delivery review REL-DEL-1: the borrowed call CONTRACT can drift too (an
    # older or newer runner whose `_hash_inputs` takes an argument), so both
    # calls degrade to "not proven" rather than raising out of the tool handler.
    try:
        current_hash = module._hash_inputs()
        cached = module._read_cache()
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - any failure here is "not proven"
        return {"state": "unreadable", "scope": "framework",
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` could not verify the receipt "
                           f"({type(exc).__name__}: {exc}).")}
    if not isinstance(cached, dict):
        return {"state": "missing", "scope": "framework",
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RECEIPT_REL}` is absent or unreadable; no "
                           "successful framework test run has been recorded.")}
    if cached.get("result") != "ok":
        return {"state": "not_ok", "scope": "framework", "ran_at": cached.get("ran_at"),
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RECEIPT_REL}` records "
                           f"result={cached.get('result')!r}, not 'ok'.")}
    if cached.get("inputs_hash") != current_hash:
        return {"state": "stale", "scope": "framework", "ran_at": cached.get("ran_at"),
                "test_count": cached.get("test_count"),
                "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RECEIPT_REL}` was written for a different "
                           "framework tree (a file under `.wavefoundry/framework/` changed "
                           "after that run), so it does not attest the current code.")}
    return {"state": "proven", "scope": "framework", "ran_at": cached.get("ran_at"),
            "test_count": cached.get("test_count"),
            "detail": (f"`{lifecycle_gate_support._FRAMEWORK_TEST_RECEIPT_REL}` is green for the current framework "
                       "tree. It attests the framework code, not the tree: the hash covers "
                       "`.wavefoundry/framework/` only, and the receipt is written only on a "
                       "whole-suite pass.")}


def _framework_test_receipt_diagnostic(status: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    if status.get("state") in {"not_applicable", "proven"}:
        return None
    return lifecycle_gate_support._diagnostic(
        "framework_test_receipt_not_proven",
        (f"Wave close blocked: the framework test receipt is not proven ({status.get('state')}). "
         f"{status.get('detail')} Close verifies the EXISTING receipt and never runs a suite; "
         "record a fresh one with `python3 .wavefoundry/framework/scripts/run_tests.py`, "
         "and run it LAST, because any edit under `.wavefoundry/framework/` invalidates it. "
         "Scope note: the hash covers `.wavefoundry/framework/` only, so a documentation edit "
         "never makes a receipt stale, but the receipt is written only on a whole-suite pass, "
         "so a docs-triggered failure prevents a new one. A green receipt attests the "
         "framework code, not the tree."),
        recovery_tools=["wf_validate_docs", "wf_current_wave"],
        recovery_usage="wf_current_wave()",
    )


def shared_delivery_gate(ctx: GateContext) -> GateResult:
    shared = _evaluate_shared_delivery_state(
        ctx.root, ctx.wave_md, ctx.wave_text, ctx.lint_result,
        lifecycle_phase=ctx.phase,
    )
    return GateResult(shared["diagnostics"], {
        key: value for key, value in shared.items() if key != "diagnostics"
    })


def gardener_gate(ctx: GateContext, *, garden_passed: bool = True) -> GateResult:
    if garden_passed:
        return GateResult()
    return GateResult([lifecycle_gate_support._diagnostic(
        "docs_gardener_failed", f"docs_gardener failed during {ctx.phase}.",
        recovery_tools=["wf_garden_docs", "wf_validate_docs"],
        recovery_usage="wf_garden_docs(mode='run')",
    )])


def close_checkbox_gate(ctx: GateContext) -> GateResult:
    diagnostics: list[GateDiagnostic] = []
    silent_all = lifecycle_gate_support._collect_silent_unchecked_items_for_close(ctx.wave_md, ctx.wave_text)
    # 1uu9z follow-up: an unreadable admitted document is a different failure
    # than an unchecked item and gets its own diagnostic. Folding it into the
    # unchecked-items count produced a false count and an unactionable
    # instruction ("mark it `[x]` or `[~]`") for a file that will not decode,
    # under a code every sibling site does not use.
    doc_findings = [i for i in silent_all if i["item_type"] == "change document"]
    unreadable_docs = [i for i in doc_findings if i["item_id"] == "unreadable"]
    missing_docs = [i for i in doc_findings if i["item_id"] == "missing"]
    silent_unchecked = [i for i in silent_all if i["item_type"] != "change document"]
    for item in missing_docs:
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "change_doc_missing",
                (
                    f"Wave close blocked: admitted change '{item['change_id']}' has no "
                    f"document on disk ({item['item_text']}). The close hard gate cannot "
                    "verify ACs and tasks it cannot see; restore the document, or remove "
                    "the change via wf_remove_change, before close."
                ),
                recovery_tools=["wf_remove_change", "wf_current_wave"],
                recovery_usage=f"wf_remove_change(change_id='{item['change_id']}')",
            )
        )
    for item in unreadable_docs:
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "change_doc_unreadable",
                (
                    f"Wave close blocked: admitted change '{item['change_id']}' could not "
                    f"be read ({item['item_text']}). The close hard gate cannot be "
                    "verified over a document that cannot be read; repair or restore "
                    "the file before close."
                ),
                recovery_tools=["wf_get_change", "wf_current_wave"],
                recovery_usage=f"wf_get_change(change_id='{item['change_id']}')",
            )
        )
    if silent_unchecked:
        # Build a structured, operator-readable message naming up to 10 items inline; counts
        # beyond that summarized. The diagnostic carries the full list in its data for tools.
        sample_lines: list[str] = []
        for item in silent_unchecked[:10]:
            tag = f"[{item['item_id']}]" if item["item_id"] else "[task]"
            sample_lines.append(f"  - {item['change_id']} {tag} {item['item_type']}: {item['item_text']}")
        more = f"\n  ...and {len(silent_unchecked) - 10} more" if len(silent_unchecked) > 10 else ""
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "silent_unchecked_items_at_close",
                (
                    f"Wave close blocked: {len(silent_unchecked)} unchecked AC or task item(s) "
                    "across admitted changes must be marked `[x]` (completed) or `[~]` (intentionally deferred) before close. "
                    "Silent `[ ]` items are blocking findings per the close-time hard gate. "
                    f"See seed `170-plan-feature.prompt.md` for the `[~]` convention.\n{chr(10).join(sample_lines)}{more}"
                ),
                recovery_tools=["wf_current_wave", "wf_validate_docs"],
                recovery_usage="wf_current_wave()",
            )
        )
    return GateResult(diagnostics)


def framework_receipt_gate(ctx: GateContext) -> GateResult:
    receipt = _framework_test_receipt_status(ctx.root)
    diagnostic = _framework_test_receipt_diagnostic(receipt)
    return GateResult([diagnostic] if diagnostic is not None else [],
                      {"framework_test_receipt": receipt})


def required_sensors_gate(ctx: GateContext, *, blocked: bool = False) -> GateResult:
    policy, errors = lifecycle_gate_support._read_phase_gates(ctx.root)
    diagnostics = []
    configured = []
    names = policy.get(ctx.phase, {}).get("required_sensors", [])
    if errors:
        diagnostics.extend(lifecycle_gate_support._diagnostic(
            "phase_sensor_invalid", f"docs/workflow-config.json: {error}",
            recovery_tools=["wf_validate_docs"],
        ) for error in errors)
        configured.extend({"phase": ctx.phase, "gate": name,
                           "source": f"phase_gates.{ctx.phase}.required_sensors",
                           "outcome": "invalid", "duration_ms": None} for name in names)
        return GateResult(diagnostics, {"configured_gates": configured})
    sensors = {sensor["name"]: sensor for sensor in lifecycle_gate_support._read_project_sensors(ctx.root)}
    # Wave 1yd98: the mode predicate is retained under its own name so the
    # single non-execution branch can select its message on the reason.  Read-only
    # takes precedence over blocked when both hold: a read-only call never
    # executes regardless, so naming the blockers there would mislead.
    mutating_mode = (ctx.phase == "prepare" and ctx.mode in ("ready", "create")) or (ctx.phase == "close" and ctx.mode == "create")
    mutating = mutating_mode and not blocked
    timeout = lifecycle_gate_support.subprocess_ops_timeout_seconds(ctx.root, "sensor", default=120)
    for name in names:
        row = {"phase": ctx.phase, "gate": name,
               "source": f"phase_gates.{ctx.phase}.required_sensors",
               "outcome": "would_run", "duration_ms": None}
        sensor = sensors.get(name)
        if sensor is None or not isinstance(sensor.get("command"), list):
            row["outcome"] = "invalid"
            diagnostics.append(lifecycle_gate_support._diagnostic(
                "phase_sensor_invalid", f"docs/workflow-config.json phase_gates.{ctx.phase}.required_sensors: {name!r} requires a list-form sensors command",
            ))
        elif not mutating:
            if not mutating_mode:
                diagnostics.append(lifecycle_gate_support._diagnostic(
                    "phase_sensor_not_executed", f"Required {ctx.phase} sensor {name!r} was not executed in read-only mode.", advisory=True,
                ))
            else:
                diagnostics.append(lifecycle_gate_support._diagnostic(
                    "phase_sensor_not_executed", f"Required {ctx.phase} sensor {name!r} was not executed because this {ctx.phase} carries blocking diagnostics.", advisory=True,
                ))
        else:
            result = sensor_runner.run_sensor(ctx.root, sensor, timeout_seconds=timeout)
            row.update(outcome="passed" if result["passed"] else "failed", duration_ms=result["duration_ms"])
            if not result["passed"]:
                diagnostic = lifecycle_gate_support._diagnostic(
                    "phase_sensor_failed", f"Required {ctx.phase} sensor {name!r} failed: {result['output_summary']}",
                    recovery_tools=["wf_run_sensors"],
                )
                diagnostic.update(phase=ctx.phase, sensor=name, exit_code=result["exit_code"],
                                  output_summary=result["output_summary"], duration_ms=result["duration_ms"])
                diagnostics.append(diagnostic)
        assert row["outcome"] in CONFIGURED_GATE_OUTCOMES
        configured.append(row)
    return GateResult(diagnostics, {"configured_gates": configured})


CLOSE_SHARED_GATES = (shared_delivery_gate, gardener_gate)
CLOSE_HARD_GATES = (close_checkbox_gate, framework_receipt_gate, required_sensors_gate)


def review_prelude_gate(ctx: GateContext, *, review_phase: str = "implementation",
                        requested_wave_id: str | None = None) -> GateResult:
    wave_id = requested_wave_id or ctx.wave_md.parent.name
    authority = resolve_review_authority(ctx.root, ctx.wave_md, wave_text=ctx.wave_text)
    review_evidence_diagnostics = _review_evidence_diagnostics(
        ctx.wave_text,
        root=ctx.root,
        wave_md=ctx.wave_md,
        required_run_kind="readiness" if review_phase == "prepare" else "initial_delivery",
    )
    review_evidence_diagnostics.extend(_wave_review_policy_diagnostics(ctx.root))
    review_evidence_diagnostics.extend(
        lifecycle_gate_support._review_policy_receipt_diagnostics(ctx.root, ctx.wave_md, ctx.wave_text)
    )
    if has_reprepare_marker(ctx.wave_text):
        review_evidence_diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "review_policy_reprepare_required",
                "This wave must be re-Prepared before review.",
                recovery_tools=["wf_prepare_wave"],
                recovery_usage=f"wf_prepare_wave(wave_id={wave_id!r}, mode='ready')",
            )
        )
    return GateResult(review_evidence_diagnostics, {"authority": authority})


def lint_gate(ctx: GateContext, *, review_phase: str = "prepare") -> GateResult:
    if review_phase != "prepare":
        return GateResult()
    diagnostics = []
    if not ctx.lint_result["passed"]:
        diagnostics.extend(lifecycle_gate_support._diagnostic(
            "docs_lint_error", error, recovery_tools=["wf_validate_docs"]
        ) for error in ctx.lint_result["errors"])
    diagnostics.extend(lifecycle_gate_support._docs_lint_warning_diagnostics(ctx.lint_result))
    return GateResult(diagnostics)


def review_lanes_gate(ctx: GateContext, *, review_phase: str = "prepare",
                      authority=None, required_lanes=()) -> GateResult:
    if review_phase != "prepare":
        return GateResult()
    if authority is None:
        authority = resolve_review_authority(ctx.root, ctx.wave_md, wave_text=ctx.wave_text)
    diagnostics = []
    lane_results = [{"lane": lane, "recorded_signoff": authority.signoff_current(lane, section="prepare", approval_phase="readiness")} for lane in required_lanes]
    missing = [entry["lane"] for entry in lane_results if not entry["recorded_signoff"]]
    if missing:
        # Wave 1to78 delivery repair (DF2, message-only): remediation
        # text branches on the resolved authority (predicate unchanged).
        # On a declared wave the fix is a typed approval event per lane;
        # legacy waves keep the exact prose-section instruction. Tests
        # assert the typed wording on a declared fixture and the legacy
        # wording on prose fixtures.
        if authority.typed:
            _prepare_lane_message = (
                f"Prepare-phase review lanes without a current typed approval: {', '.join(missing)}. "
                "Record a typed approval event per lane via wf_review_event(event='approval', "
                "signoff_key=<lane name above>, mode='create') before running wf_implement_wave."
            )
        else:
            _prepare_lane_message = (
                f"Prepare-phase review lanes without recorded signoff in `{review_evidence.PREPARE_REVIEW_EVIDENCE_MARKER}`: {', '.join(missing)}. "
                f"Record each lane signoff in the `{review_evidence.PREPARE_REVIEW_EVIDENCE_MARKER}` section of wave.md before running wf_implement_wave."
            )
        diagnostics.append(lifecycle_gate_support._diagnostic(
            "missing_required_lane",
            _prepare_lane_message,
            recovery_tools=["wf_current_wave"],
            recovery_usage="wf_current_wave()",
        ))
    return GateResult(diagnostics, {"lane_results": lane_results, "missing": missing})


REVIEW_GATES = (review_prelude_gate, lint_gate, review_lanes_gate, shared_delivery_gate)


def wave_policy_gate(ctx: GateContext) -> GateResult:
    diagnostics = _wave_review_policy_diagnostics(ctx.root)
    _policy, errors = lifecycle_gate_support._read_phase_gates(ctx.root)
    diagnostics.extend(lifecycle_gate_support._diagnostic(
        "phase_sensor_invalid", f"docs/workflow-config.json: {error}",
        recovery_tools=["wf_validate_docs"],
    ) for error in errors)
    return GateResult(diagnostics)


def evidence_gate(ctx: GateContext) -> GateResult:
    return GateResult(_review_evidence_diagnostics(
        ctx.wave_text, root=ctx.root, wave_md=ctx.wave_md,
    ))


def change_location_gate(ctx: GateContext, *, admitted_change: str) -> GateResult:
    location = lifecycle_gate_support._change_location_state(ctx.root, ctx.wave_md, admitted_change)
    diagnostics = []
    change_path = None
    needs_relocation = False
    skip = False
    if location["staged_exists"] and location["wave_exists"]:
        diagnostics.append(lifecycle_gate_support._diagnostic(
            "duplicate_change_doc_locations",
            f"Admitted change '{admitted_change}' exists in both {lifecycle_gate_support._repo_rel(ctx.root, location['staged_path'])} and {lifecycle_gate_support._repo_rel(ctx.root, location['wave_path'])}.",
            recovery_tools=["wf_get_change"],
            recovery_usage=f"wf_get_change(change_id={admitted_change!r})",
        ))
        skip = True
    elif location["wave_exists"]:
        change_path = location["wave_path"]
    elif location["staged_exists"]:
        needs_relocation = True
        if ctx.mode in ("create", "ready"):
            change_path = location["wave_path"]
        else:
            diagnostics.append(lifecycle_gate_support._diagnostic(
                "change_doc_not_relocated",
                f"Admitted change '{admitted_change}' is still staged at {lifecycle_gate_support._repo_rel(ctx.root, location['staged_path'])}; prepare must relocate it to {lifecycle_gate_support._repo_rel(ctx.root, location['wave_path'])}.",
                recovery_tools=["wf_prepare_wave"],
                recovery_usage=f"wf_prepare_wave(wave_id={ctx.wave_md.parent.name!r}, mode='create')",
            ))
            skip = True
    else:
        diagnostics.append(lifecycle_gate_support._diagnostic(
            "change_not_found",
            f"Admitted change '{admitted_change}' was not found in {lifecycle_gate_support._repo_rel(ctx.root, location['staged_path'])} or {lifecycle_gate_support._repo_rel(ctx.root, location['wave_path'])}.",
            recovery_tools=["wf_get_change", "wf_list_plans"],
            recovery_usage=f"wf_get_change(change_id={admitted_change!r})",
        ))
        skip = True
    return GateResult(diagnostics, {"location": location, "change_path": change_path,
                                   "needs_relocation": needs_relocation, "skip": skip})


def change_sections_gate(ctx: GateContext, *, admitted_change: str,
                         change_text: str) -> GateResult:
    diagnostics = []
    missing_headers = lifecycle_gate_support._missing_required_change_sections(change_text)
    if missing_headers:
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "change_doc_missing_sections",
                f"Admitted change '{admitted_change}' is missing sections: {', '.join(missing_headers)}.",
                recovery_tools=["wf_get_change"],
                recovery_usage=f"wf_get_change(change_id={admitted_change!r})",
            )
        )
    # AC priority advisory (non-blocking): warn if every AC row still has unpopulated placeholder text
    _AC_PLACEHOLDER = "required / important / nice-to-have / not-this-scope"
    if "## AC Priority" in change_text:
        ac_section_start = change_text.find("## AC Priority")
        ac_section = change_text[ac_section_start:]
        ac_rows = [line for line in ac_section.splitlines() if line.strip().startswith("| AC-")]
        if ac_rows and all(_AC_PLACEHOLDER in row for row in ac_rows):
            diagnostics.append(
                lifecycle_gate_support._diagnostic(
                    "ac_priority_unpopulated",
                    f"Change '{admitted_change}' AC priority table still contains only placeholder text. Fill in priority values (required / important / nice-to-have / not-this-scope) for each AC row before closing the wave.",
                    recovery_tools=["wf_get_change"],
                    recovery_usage=f"wf_get_change(change_id={admitted_change!r})",
                    advisory=True,
                )
            )
    return GateResult(diagnostics)


PREPARE_PREFLIGHT_GATES = (wave_policy_gate, evidence_gate, change_location_gate, change_sections_gate, gardener_gate, lint_gate)


def policy_errors_gate(ctx: GateContext, *, policy_state_errors=(),
                       requested_wave_id: str | None = None) -> GateResult:
    wave_id = requested_wave_id or ctx.wave_md.parent.name
    return GateResult([lifecycle_gate_support._diagnostic(
        "review_policy_receipt_stale", error,
        recovery_tools=["wf_prepare_wave"],
        recovery_usage=f"wf_prepare_wave(wave_id={wave_id!r}, mode='ready')",
    ) for error in policy_state_errors])


def policy_advisory_gate(ctx: GateContext, *, policy_state=None) -> GateResult:
    if ctx.mode == "dry_run" and policy_state is not None:
        return GateResult(lifecycle_gate_support._review_policy_receipt_diagnostics(
            ctx.root, ctx.wave_md, ctx.wave_text, advisory=True
        ))
    return GateResult()


PREPARE_POLICY_GATES = (policy_errors_gate, policy_advisory_gate)


def council_signoff_gate(ctx: GateContext) -> GateResult:
    diagnostics = []
    _prepare_authority = resolve_review_authority(ctx.root, ctx.wave_md, wave_text=ctx.wave_text)
    required_council_signoffs = lifecycle_gate_support._required_wave_council_signoffs(ctx.root, "prepare", wave_text=ctx.wave_text, wave_md=ctx.wave_md)
    if (
        _prepare_authority.typed
        and not required_council_signoffs
        and lifecycle_gate_support._read_workflow_config(ctx.root).get("wave_review") is None
    ):
        required_council_signoffs = ["wave-council-readiness"]
    if required_council_signoffs:
        # Wave 1to78: council-signoff currency is review-evidence content —
        # typed-exclusive on declared waves, prose on legacy waves.
        missing_council = [
            signoff_key
            for signoff_key in required_council_signoffs
            if not _prepare_authority.signoff_current(
                signoff_key, approval_phase="readiness"
            )
        ]
        if missing_council:
            # Wave 1to78 delivery repair (DF2, message-only): remediation text
            # branches on the resolved authority; the gate predicate is
            # unchanged. Declared waves need typed approval events; legacy
            # waves keep the exact prose-line instruction.
            if _prepare_authority.typed:
                _council_remedy = (
                    "Record a typed approval event per missing key via "
                    "wf_review_event(event='approval', signoff_key=<missing key above>, "
                    f"mode='create'); the approval projects into `{review_evidence.REVIEW_EVIDENCE_SECTION}`. "
                    "Do this before the wave can become active."
                )
            else:
                _council_remedy = f"Record the signoff line(s) in `{review_evidence.REVIEW_EVIDENCE_SECTION}` before the wave can become active."
            diagnostics.append(
                lifecycle_gate_support._diagnostic(
                    "missing_wave_council_signoff",
                    (
                        "Required Wave Council signoff missing for prepare: "
                        f"{', '.join(missing_council)}. {_council_remedy}"
                    ),
                    recovery_tools=["wf_current_wave"],
                    recovery_usage="wf_current_wave()",
                )
            )
    return GateResult(diagnostics, {"authority": _prepare_authority,
                                   "required_council_signoffs": required_council_signoffs})


def single_open_gate(ctx: GateContext, *, other_active=None,
                     requested_wave_id: str | None = None) -> GateResult:
    wave_id = requested_wave_id or ctx.wave_md.parent.name
    diagnostics = []
    guard_data: dict[str, Any] = {}
    if ctx.mode == "create" and other_active is not None:
        guard_data = {
            "active_wave_id": other_active["wave_id"],
            "active_wave_path": lifecycle_gate_support._repo_rel(ctx.root, Path(other_active["path"])),
        }
        diagnostics.append(
            lifecycle_gate_support._diagnostic(
                "another_wave_active",
                f"Wave {other_active['wave_id']!r} is already OPEN (active/implementing). Pause it first, "
                f"or run wf_prepare_wave(wave_id={wave_id!r}, mode='ready') to ready {wave_id!r} without opening it.",
                recovery_tools=["wf_prepare_wave", "wf_pause_wave", "wf_current_wave"],
                recovery_usage=f"wf_prepare_wave(wave_id={wave_id!r}, mode='ready')",
            )
        )
    return GateResult(diagnostics, guard_data)


PREPARE_ACTIVATION_GATES = (council_signoff_gate, single_open_gate)


def readiness_gate(ctx: GateContext) -> GateResult:
    return GateResult(_review_evidence_diagnostics(
        ctx.wave_text, root=ctx.root, wave_md=ctx.wave_md,
        required_run_kind="readiness",
    ))


PREPARE_READINESS_GATES = (readiness_gate, required_sensors_gate)
