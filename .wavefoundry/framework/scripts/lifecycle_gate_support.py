"""Pure lifecycle policy and diagnostic support; never imports the server."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import (
    Any,
    Iterable,
    Mapping,
    Optional,
    Sequence,
)
import record_paths
from gardener_metadata import ambiguous_excluded_headings, canonical_review_policy_body
from review_policy import (
    REVIEW_POLICY_EVALUATOR_VERSION,
    REVIEW_POLICY_SCHEMA_VERSION,
    build_policy_receipt,
    receipt_semantic_fields,
    current_policy_receipt,
    delivery_council_required,
    extract_full_council_triggers,
    extract_requested_review_lanes,
    has_reprepare_marker,
    normalize_wave_review_policy,
    normalize_phase_gates,
    policy_input_digest,
    select_required_review_lanes,
)
from review_evidence import (
    current_synthesis_heads,
    parse_review_evidence_source,
    read_review_event_ledger,
    required_review_status_keys,
    resolve_review_authority,
    validate_review_evidence_records,
)
import review_evidence


def _read_workflow_config(root: Path) -> dict:
    cfg = root / "docs" / "workflow-config.json"
    if cfg.is_file():
        try:
            return json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _read_project_required_review_lanes(root: Path) -> list[str]:
    """Return project-declared required review lanes from workflow-config.json."""
    cfg = _read_workflow_config(root)
    raw = cfg.get("required_review_lanes", [])
    if not isinstance(raw, list):
        return []
    return [str(lane).strip() for lane in raw if isinstance(lane, str) and str(lane).strip()]


def _read_wave_council_policy(root: Path) -> dict[str, Any]:
    """Return normalized Wave Council policy from workflow-config.json.

    Reads the canonical ``wave_review`` key. (Wave 1p5b4: the legacy
    ``wave_council_policy`` reader-fallback was removed along with the canonical-names
    rename mechanism — the one-shot upgrade convergence rewrites legacy configs to
    canonical, so the runtime only ever sees ``wave_review``.)
    """
    cfg = _read_workflow_config(root)
    raw = cfg.get("wave_review")
    if raw is None:
        # Undeclared legacy/minimal fixtures keep the pre-policy compatibility
        # path. Canonical project lint requires the key on real installations.
        return {}
    normalized, policy_errors = normalize_wave_review_policy(raw)
    if normalized is None:
        # Fail closed: lifecycle callers retain the strongest council gates
        # and surface the configuration defect through their normal policy
        # diagnostics instead of interpreting malformed policy as disabled.
        return {
            "enabled": True,
            "delivery_mode": "universal",
            "invalid": True,
            "errors": list(policy_errors),
            "phases": {
                "prepare": {
                    "signoff_key": "wave-council-readiness",
                    "moderator_role": "wave-council",
                },
                "review": {
                    "signoff_key": "wave-council-delivery",
                    "moderator_role": "wave-council",
                },
            },
        }
    if not normalized["enabled"]:
        return {
            "enabled": False,
            "delivery_mode": "disabled",
            "evidence_section": str(raw.get("evidence_section", review_evidence.REVIEW_EVIDENCE_SECTION)).strip() or review_evidence.REVIEW_EVIDENCE_SECTION,
            "transition_policy": str(raw.get("transition_policy", "")).strip(),
            "phases": {},
        }

    phases_raw = normalized.get("phases", {})
    if not isinstance(phases_raw, dict):
        phases_raw = {}

    phase_defaults = {
        "prepare": "wave-council-readiness",
        "review": "wave-council-delivery",
    }
    phases: dict[str, dict[str, str]] = {}
    for phase, default_key in phase_defaults.items():
        phase_raw = phases_raw.get(phase, {})
        if not isinstance(phase_raw, dict):
            phase_raw = {}
        signoff_key = str(phase_raw.get("signoff_key", default_key)).strip()
        moderator_role = str(phase_raw.get("moderator_role", "wave-council")).strip()
        if signoff_key:
            phases[phase] = {
                "signoff_key": signoff_key,
                "moderator_role": moderator_role or "wave-council",
            }

    return {
        "enabled": True,
        "delivery_mode": normalized["delivery_mode"],
        "evidence_section": str(raw.get("evidence_section", review_evidence.REVIEW_EVIDENCE_SECTION)).strip() or review_evidence.REVIEW_EVIDENCE_SECTION,
        "transition_policy": str(raw.get("transition_policy", "")).strip(),
        "phases": phases,
    }


def _required_wave_council_signoffs(
    root: Path,
    lifecycle_phase: str,
    wave_text: Optional[str] = None,
    wave_md: Optional[Path] = None,
) -> list[str]:
    """Council signoff keys required at ``lifecycle_phase``.

    Wave 1to78: the transition-policy branch probes signoff PRESENCE, which is
    review-evidence content, so it resolves through the review authority
    facade — typed records on declared waves, prose on legacy waves. Callers
    pass ``wave_md`` (the wave identity) so the facade can reach the typed
    ledger; text-only callers keep the legacy prose probe via the facade's
    text-only resolution (a declared wave without a path fails closed).
    """
    policy = _read_wave_council_policy(root)
    if not policy or not policy.get("enabled"):
        return []
    phase_map = {
        "prepare": ["prepare"],
        "review": ["review"],
        "close": ["prepare", "review"],
    }
    required: list[str] = []
    for phase in phase_map.get(lifecycle_phase, []):
        signoff_key = policy.get("phases", {}).get(phase, {}).get("signoff_key")
        if signoff_key and signoff_key not in required:
            required.append(signoff_key)
    if policy.get("delivery_mode") == "targeted" and lifecycle_phase in {"review", "close"}:
        records: tuple[Mapping[str, Any], ...] = ()
        if wave_md is not None:
            records, _errors = read_review_event_ledger(wave_md)
        receipt = current_policy_receipt(records)
        if receipt is not None:
            council_required = receipt.get("delivery_council_required") is True
        else:
            # Compatibility-only fallback for legacy prose waves that have no
            # typed receipt authority.
            heads = current_synthesis_heads(records).values()
            council_required = delivery_council_required(
                "targeted",
                delivered_boundary_triggers=extract_full_council_triggers(
                    (wave_text or "",)
                ),
                current_heads=heads,
            )
        if not council_required:
            review_key = policy.get("phases", {}).get("review", {}).get("signoff_key")
            required = [key for key in required if key != review_key]
    if not required:
        return required

    transition_policy = str(policy.get("transition_policy", "")).strip().lower()
    if transition_policy != "applies-from-next-prepare" or lifecycle_phase == "prepare" or not (wave_text or wave_md):
        return required

    prepare_key = policy.get("phases", {}).get("prepare", {}).get("signoff_key")
    review_key = policy.get("phases", {}).get("review", {}).get("signoff_key")
    authority = resolve_review_authority(root, wave_md, wave_text=wave_text)
    prepare_signoff_recorded = bool(
        prepare_key
        and authority.signoff_recorded(
            prepare_key, approval_phase="readiness"
        )
    )
    has_review_signoff = bool(
        review_key
        and authority.signoff_current(
            review_key, approval_phase="delivery"
        )
    )

    if lifecycle_phase == "review":
        return required
    if lifecycle_phase == "close":
        # A present-but-stale readiness approval remains required and therefore
        # blocks through the normal currency diagnostic.
        if prepare_signoff_recorded:
            return required
        # The carve-out exists for waves that were in flight BEFORE the policy
        # applied, and absence of an approval is a poor proxy for that: a
        # readiness approval refused as stale is also absent, so keying on
        # absence would make refusing the approval WEAKEN the close gate below
        # what the silent accept required.  Key on never-prepared-under-policy
        # instead.  The ledger-health conjunct is not optional --
        # `resolve_review_authority` empties `records` on any ledger error, so a
        # receipt check alone reads a corrupt ledger as "never prepared" and
        # fails open inside a fail-closed design.
        never_prepared_under_policy = (
            current_policy_receipt(authority.records) is None
            and not authority.ledger_errors
        )
        if not never_prepared_under_policy:
            return required
        # Both exits below drop the readiness key, so the carve-out must gate
        # both.  The `has_review_signoff` exit is not a corner case: it is the
        # normal end-state of a wave whose readiness approval was refused and
        # which then completed delivery review.
        if has_review_signoff and review_key:
            return [review_key]
        return [key for key in required if key != prepare_key]
    return required


_CHANGE_ID_PATTERN = re.compile(r"^Change ID:\s+`([^`]+)`", re.MULTILINE)


_CLOSE_GATE_CHECKBOX_LINE_RE = re.compile(r"^\s*-\s+\[(?P<mark>[ xX~])\]\s+(?P<text>.+?)\s*$", re.MULTILINE)


_CLOSE_GATE_AC_ID_RE = re.compile(r"(AC-[\w\-]+)")


def _extract_close_gate_section(text: str, heading: str) -> str:
    """Extract H2 section content by heading name (without `## ` prefix)."""
    pattern = re.compile(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    return match.group(1) if match else ""


def _close_gate_parse_ac_priority(priority_section: str) -> dict[str, str]:
    """Return `AC-id -> priority` map from a markdown AC priority table (normalized lowercase)."""
    result: dict[str, str] = {}
    for raw in priority_section.splitlines():
        line = raw.strip()
        if not line.startswith("|") or line.count("|") < 2:
            continue
        # Skip the markdown separator row.
        if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        id_match = _CLOSE_GATE_AC_ID_RE.search(cells[0])
        if not id_match:
            continue
        result[id_match.group(1)] = cells[1].lower().replace(" ", "-")
    return result


def _collect_silent_unchecked_items_for_close(wave_md: Path, wave_text: str) -> list[dict[str, str]]:
    """Walk admitted change docs; return silent ``[ ]`` items that block close.

    Wave 1p31b (1p32k): the close-time hard gate. Every AC and task must be ``[x]`` or
    ``[~]`` at close. AC items at ``not-this-scope`` priority are exempt. Returns a list of
    ``{'change_id', 'item_type' ('AC' or 'task'), 'item_id', 'item_text'}`` dicts.
    """
    findings: list[dict[str, str]] = []
    for change_id in _CHANGE_ID_PATTERN.findall(wave_text):
        change_path = wave_md.parent / f"{change_id}.md"
        if not change_path.exists():
            # 1v0lx: absent is not "nothing to check". The gate cannot verify
            # ACs and tasks it cannot see, so a ghost blocks close exactly as
            # an unreadable document does, under its own item id (the recovery
            # differs: restore or wf_remove_change, not repair).
            findings.append({
                "change_id": change_id,
                "item_type": "change document",
                "item_id": "missing",
                "item_text": (
                    f"no file at {wave_md.parent.name}/{change_path.name}; "
                    "restore the document or remove the change via wf_remove_change"
                ),
            })
            continue
        try:
            change_text = change_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            # BOTH causes block. An earlier revision kept the legacy silent skip
            # for I/O failures and surfaced only decode failures, which left the
            # close hard gate fail-open for a permission-denied admitted
            # document -- the same hole, reachable by `chmod 000`. The stated
            # reason (close cannot verify an admitted document it cannot read)
            # does not distinguish the two, so neither does this.
            findings.append({
                    "change_id": change_id,
                    "item_type": "change document",
                    # Non-empty so the renderer tags it `[unreadable]` rather
                    # than `[task]`, which told the operator to mark an
                    # unreadable file `[x]` or `[~]`.
                    "item_id": "unreadable",
                    "item_text": (
                        f"could not read {change_path.name}: "
                        + _read_error_detail(exc)
                    ),
                })
            continue

        ac_section = _extract_close_gate_section(change_text, "Acceptance Criteria")
        priority_section = _extract_close_gate_section(change_text, "AC Priority")
        priorities = _close_gate_parse_ac_priority(priority_section)

        # Walk AC items — silent `[ ]` at non-exempt priority blocks close.
        for match in _CLOSE_GATE_CHECKBOX_LINE_RE.finditer(ac_section):
            if match.group("mark") != " ":
                continue
            text_part = match.group("text").strip()
            id_match = _CLOSE_GATE_AC_ID_RE.search(text_part)
            ac_id = id_match.group(1) if id_match else "<unidentified>"
            priority = priorities.get(ac_id, "unknown")
            if priority == "not-this-scope":
                continue
            findings.append({
                "change_id": change_id,
                "item_type": "AC",
                "item_id": ac_id,
                "item_text": text_part[:120],
            })

        # Walk task items — every silent `[ ]` blocks close (no priority exemption for tasks).
        task_section = _extract_close_gate_section(change_text, "Tasks")
        for match in _CLOSE_GATE_CHECKBOX_LINE_RE.finditer(task_section):
            if match.group("mark") != " ":
                continue
            text_part = match.group("text").strip()
            findings.append({
                "change_id": change_id,
                "item_type": "task",
                "item_id": "",
                "item_text": text_part[:120],
            })
    return findings


def _read_wave_record_text(wave_md: Path) -> tuple[Optional[str], Optional[str]]:
    """Sole raw-read boundary for wave records (wave 1v0lw).

    Returns ``(text, None)`` on success or ``(None, read_error)`` on failure,
    where ``read_error`` is the operator-safe cause from ``_read_error_detail``
    (exception type plus detail, never an absolute path).  Every ``wave.md``
    read in this module must route through here; the residue census test keys
    on the resolved read target, so a new raw read cannot land unreviewed.
    """
    try:
        return wave_md.read_text(encoding="utf-8"), None
    except (OSError, UnicodeError) as exc:
        return None, _read_error_detail(exc)


def _diagnostic(
    code: str,
    message: str,
    *,
    recovery_tools: list[str] | None = None,
    recovery_usage: str = "",
    advisory: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if recovery_tools:
        payload["recovery_tools"] = recovery_tools
    if recovery_usage:
        payload["recovery_usage"] = recovery_usage
    if advisory is True:
        payload["advisory"] = True
    return payload


def _extract_change_ids_from_wave_text(text: str) -> list[str]:
    return _CHANGE_ID_PATTERN.findall(text)


def _wave_change_doc_path(root: Path, wave_md: Path, change_id: str) -> Path:
    return wave_md.parent / f"{change_id}.md"


def _plan_change_doc_path(root: Path, change_id: str) -> Path:
    return record_paths.load_record_roots(root).plans / f"{change_id}.md"


def _read_error_detail(exc: BaseException) -> str:
    """Operator-safe one-line cause for a failed document read.

    An OSError's ``str`` embeds the absolute filesystem path
    ("[Errno 13] Permission denied: '/…'"), which re-leaks the path the
    surrounding message just rendered repo-relative.  ``strerror`` carries the
    cause alone; decode errors have no path in their ``str`` and stay verbatim.
    """
    if isinstance(exc, OSError) and exc.strerror:
        return f"{type(exc).__name__}: {exc.strerror}"
    return f"{type(exc).__name__}: {exc}"


def _repo_rel(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path.resolve(strict=False).relative_to(root.resolve())
    return str(relative).replace("\\", "/")


def _change_location_state(root: Path, wave_md: Path, change_id: str) -> dict[str, Any]:
    staged = _plan_change_doc_path(root, change_id)
    wave_path = _wave_change_doc_path(root, wave_md, change_id)
    return {
        "staged_path": staged,
        "wave_path": wave_path,
        "staged_exists": staged.exists(),
        "wave_exists": wave_path.exists(),
    }


def _missing_required_change_sections(change_text: str) -> list[str]:
    required_headers = [
        "## Rationale",
        "## Requirements",
        "## Scope",
        "## Acceptance Criteria",
        "## Tasks",
        "## AC Priority",
    ]
    return [hdr for hdr in required_headers if hdr not in change_text]


def _extract_required_review_lanes(wave_text: str) -> list[str]:
    lanes: list[str] = []
    in_participants = False
    for raw in wave_text.splitlines():
        line = raw.strip()
        if line.startswith("## Participants"):
            in_participants = True
            continue
        if in_participants and line.startswith("## "):
            break
        if not in_participants:
            continue
        bullet_match = re.match(
            r"^-\s*Required review lanes\s*:\s*(?P<lanes>.+?)\s*$",
            line,
            re.IGNORECASE,
        )
        if bullet_match:
            for lane in bullet_match.group("lanes").split(","):
                normalized = lane.strip().strip("`").strip()
                if normalized and normalized.lower() not in {"none", "—", "-"}:
                    lanes.append(normalized)
            continue
        if not line.startswith("|") or line.startswith("|------"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        role, lane = cells[0], cells[1]
        if role.lower() == "role":
            continue
        if "review" not in lane.lower():
            continue
        lanes.append(role)
    # preserve order, dedupe
    out: list[str] = []
    for lane in lanes:
        if lane not in out:
            out.append(lane)
    return out


def receipt_supersession_attribution(
    state: Mapping[str, Any],
    change_ids: Sequence[str],
    *,
    labels: tuple[str, str] = ("current receipt", "pending receipt"),
) -> str:
    """Name what moved, and only what the persisted data actually supports.

    A bare diagnostic code reproduces the confusion this exists to remove: the
    operator sees approvals lapse and cannot tell which input moved.  Per-change
    attribution is deliberately NOT claimed -- the per-change digests are
    computed into a local and discarded, and the receipt validator enforces a
    closed field set -- so this reports the change ids that were digested and
    stops there rather than implying it knows which one changed.
    """

    pending = state.get("receipt") or {}
    current = current_policy_receipt(state.get("records") or []) or {}
    pending_fields = receipt_semantic_fields(pending) if pending else {}
    current_fields = receipt_semantic_fields(current) if current else {}
    differing = sorted(
        key
        for key in set(pending_fields) | set(current_fields)
        if pending_fields.get(key) != current_fields.get(key)
    )
    parts = [
        f"{labels[0]} {current.get('receipt_id') or 'none'}",
        f"{labels[1]} {pending.get('receipt_id') or 'none'}",
        (
            "differing receipt_semantic_fields: " + ", ".join(differing)
            if differing
            else "no differing receipt_semantic_fields"
        ),
        (
            "digested change ids: " + ", ".join(change_ids)
            if change_ids
            else "digested change ids: none"
        ),
    ]
    return (
        " (" + "; ".join(parts) + "). "
        "Which specific document changed is not attributable from persisted data."
    )


class PolicyInputError(str):
    """A policy-selection error that remembers WHY it could not be computed.

    Callers that only report errors keep treating these as plain strings.  The
    readiness-approval staleness check needs more: it degrades to a warning for
    an environmental failure but must REFUSE for an authoring defect, and the
    two arrive on the same `errors` channel.  Discriminating on message prose
    would break the first time a message is reworded, so the cause travels with
    the error instead.
    """

    __slots__ = ("cause",)

    def __new__(cls, cause: str, message: str) -> "PolicyInputError":
        item = super().__new__(cls, message)
        item.cause = cause
        return item


POLICY_INPUT_DEGRADABLE_CAUSES = frozenset({"read"})


def policy_input_error_cause(error: str) -> str:
    """Cause for one policy-selection error; `unknown` for untagged legacy strings."""

    return getattr(error, "cause", "unknown")


def _prepare_policy_state(
    root: Path,
    wave_md: Path,
    wave_text: str,
    change_ids: list[str],
    council_brief: Mapping[str, Any],
    *,
    change_text_overrides: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    config = _read_workflow_config(root)
    policy, policy_errors = normalize_wave_review_policy(config.get("wave_review"))
    _phase_policy, phase_errors = normalize_phase_gates(config)
    if policy_errors or phase_errors or policy is None:
        return None, tuple(PolicyInputError("config", e) for e in (*policy_errors, *phase_errors))
    requested = extract_requested_review_lanes(wave_text)
    project_lanes = tuple(_read_project_required_review_lanes(root))
    change_inputs: list[tuple[str, str, bytes]] = []
    change_texts: list[str] = []
    errors: list[PolicyInputError] = []
    for change_id in change_ids:
        path = _wave_change_doc_path(root, wave_md, change_id)
        try:
            override = (change_text_overrides or {}).get(change_id)
            if override is None:
                body = path.read_bytes()
                text = body.decode("utf-8")
            else:
                text = override
                body = text.encode("utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(PolicyInputError(
                "read",
                f"cannot read admitted change `{change_id}` for policy selection: {_read_error_detail(exc)}",
            ))
            continue
        kind = change_id.split("-", 1)[0].rsplit("-", 1)[-1]
        # Loud, not silent, and not fatal. The exclusion normalizers degrade by
        # returning the text unchanged, which is right for a pure helper whose
        # callers have no handler -- but a silent degrade means the churn comes
        # back with no explanation. Report the ambiguity here instead, where the
        # existing (None, errors) channel already reaches the operator.
        for problem in ambiguous_excluded_headings(text):
            errors.append(PolicyInputError(
                "ambiguous_headings", f"admitted change `{change_id}`: {problem}"
            ))
        change_inputs.append((change_id, kind, body))
        change_texts.append(text)
    if errors:
        return None, tuple(errors)
    required_lanes, reasons = select_required_review_lanes(
        requested_lanes=requested,
        project_lanes=project_lanes,
        change_texts=change_texts,
    )
    digest = policy_input_digest(
        wave_review=policy,
        project_lanes=project_lanes,
        review_policies=config.get("review_policies", {}),
        changes=change_inputs,
        requested_lanes=requested,
        phase_gates=config.get("phase_gates"),
        sensors=config.get("sensors", []),
    )
    records, ledger_errors = read_review_event_ledger(wave_md)
    if ledger_errors:
        return None, tuple(PolicyInputError("ledger", e) for e in ledger_errors)
    record_errors = validate_review_evidence_records(records)
    if record_errors:
        return None, tuple(PolicyInputError("record", e) for e in record_errors)
    heads = current_synthesis_heads(records).values()
    mode = str(policy["delivery_mode"])
    # One canonical representation feeds every receipt-semantic reader. Lane
    # scoring already canonicalizes internally; these two did not, so a mandated
    # Progress Log row could carry a trigger word (for example "windows"), flip
    # `delivery_council_required`, and supersede the receipt while
    # `policy_input_digest` stayed byte-identical, leaving no diagnostic able to
    # explain why the approvals lapsed.
    canonical_change_texts = [
        canonical_review_policy_body(text.encode("utf-8")).decode("utf-8", "replace")
        for text in change_texts
    ]
    delivery_council = delivery_council_required(
        mode,
        delivered_boundary_triggers=extract_full_council_triggers(canonical_change_texts),
        current_heads=heads,
    )
    # Receipt seat selection is bound to admitted change bytes, never to the
    # mutable wave projection (which later contains actor/lane vocabulary and
    # must not change its own policy input).
    stable_rotating, _stable_reason = _select_prepare_council_rotating_seat(
        "\n".join(canonical_change_texts)
    )
    seats = ["red-team", *([stable_rotating] if stable_rotating else [])]
    semantic = {
        "schema_version": REVIEW_POLICY_SCHEMA_VERSION,
        "evaluator_version": REVIEW_POLICY_EVALUATOR_VERSION,
        "policy_input_digest": digest,
        "delivery_mode": mode,
        "primer_depth": "standard",
        "council_seats": seats,
        "requested_lanes": list(requested),
        "required_lanes": list(required_lanes),
        "delivery_council_required": delivery_council,
    }
    receipt, append_required = build_policy_receipt(
        semantic, current_policy_receipt(records)
    )
    return {
        "policy": policy,
        "requested_lanes": list(requested),
        "required_lanes": list(required_lanes),
        "reasons": {key: list(value) for key, value in reasons.items()},
        "delivery_council_required": delivery_council,
        "policy_input_digest": digest,
        "receipt": receipt,
        "receipt_append_required": append_required,
        "records": records,
    }, ()


def _review_policy_receipt_diagnostics(
    root: Path, wave_md: Path, wave_text: str, *, advisory: bool = False
) -> list[dict[str, Any]]:
    """Recompute receipt inputs; downstream lifecycle gates never reselect."""

    if not _wave_uses_external_review_evidence(root, wave_md):
        return []
    existing_records, existing_errors = read_review_event_ledger(wave_md)
    if not existing_errors and current_policy_receipt(existing_records) is None and not has_reprepare_marker(wave_text):
        # Pre-policy in-flight waves remain on their historical authority
        # until Upgrade marks them for deterministic re-Prepare.
        return []
    change_ids = _extract_change_ids_from_wave_text(wave_text)
    brief = _build_prepare_council_brief(
        wave_md.parent.name, wave_text, change_ids
    )
    state, errors = _prepare_policy_state(
        root, wave_md, wave_text, change_ids, brief
    )
    diagnostics = [
        _diagnostic(
            "review_policy_receipt_stale",
            error,
            recovery_tools=["wf_prepare_wave"],
            recovery_usage=f"wf_prepare_wave(wave_id={wave_md.parent.name!r}, mode='ready')",
        )
        for error in errors
    ]
    if state is None:
        return diagnostics
    persisted = tuple(_extract_required_review_lanes(wave_text))
    selected = tuple(state["required_lanes"])
    if persisted != selected:
        diagnostics.append(
            _diagnostic(
                "review_policy_receipt_stale",
                "Persisted Required review lanes no longer match the current policy inputs; re-Prepare.",
                recovery_tools=["wf_prepare_wave"],
                recovery_usage=f"wf_prepare_wave(wave_id={wave_md.parent.name!r}, mode='ready')",
                advisory=advisory,
            )
        )
    if state["receipt_append_required"]:
        # Only this site can build the full attribution payload: the error loop
        # above has `state is None` (no current receipt, no pending receipt, no
        # semantic fields) and the roster-drift site may have no distinct
        # pending receipt id.  Demanding the same payload at all three would
        # force an implementer to invent placeholder values.
        diagnostics.append(
            _diagnostic(
                "review_policy_receipt_stale",
                "The current review-policy receipt does not match the wave/config/change inputs; re-Prepare."
                + receipt_supersession_attribution(state, change_ids),
                recovery_tools=["wf_prepare_wave"],
                recovery_usage=f"wf_prepare_wave(wave_id={wave_md.parent.name!r}, mode='ready')",
                advisory=advisory,
            )
        )
    return diagnostics


def _docs_lint_warning_diagnostics(lint_result: Mapping[str, Any] | dict[str, Any],
                                   *, recovery_tools: list[str] | None = None) -> list[dict[str, Any]]:
    """Wave 1wuju (1wujs): render docs-lint ``WARNING:`` lines as ``docs_lint_warning``
    diagnostics carrying ``advisory: true`` (the non-blocking flag the prepare contract
    defines) at EVERY lifecycle gate caller of ``run_validate``, not only at
    ``wf_validate_docs``. A sensor registered advisory would otherwise be visible in one
    tool and invisible at Prepare, Review, Close, and audit, which is the hidden class a
    non-blocking polarity must not create."""
    return [
        _diagnostic("docs_lint_warning", warning,
                    recovery_tools=recovery_tools or ["wf_validate_docs"], advisory=True)
        for warning in (lint_result.get("warnings") or [])
    ]


def _select_prepare_council_rotating_seat(wave_text: str) -> tuple[str | None, str]:
    """Select the rotating Wave Council seat for the prepare-phase review.

    Heuristic (first match wins; documented explicitly per 12sp5 AC-2):
    1. docs-contract-reviewer  — wave objective/watchpoints reference seeds, prompts, docs, or templates
    2. security-reviewer       — wave objective/watchpoints reference auth, security, trust, vulnerability,
                                  permission, credential, or secret
    3. architecture-reviewer   — wave objective/watchpoints reference architecture, boundary, structural,
                                  refactor, or layering
    4. code-reviewer           — wave objective/watchpoints reference server_impl, MCP, api, endpoint,
                                  or tool surface
    5. (no rotating seat)      — no clear domain signal; red-team only
    """
    probe = wave_text.casefold()
    if any(kw in probe for kw in ("seed", "prompt", "template", "doc authoring", "seed prompt")):
        return "docs-contract-reviewer", "Wave references seed/prompt authoring or documentation changes"
    if any(kw in probe for kw in ("auth", "security", "trust boundary", "vulnerability", "credential", "permission", "secret")):
        return "security-reviewer", "Wave references authentication, security, or trust boundary changes"
    if any(kw in probe for kw in ("architecture", "boundary", "structural", "refactor", "layering")):
        return "architecture-reviewer", "Wave references architectural or structural changes"
    if any(kw in probe for kw in ("server_impl", "mcp tool", "mcp surface", "api endpoint", "tool registration")):
        return "code-reviewer", "Wave references MCP tool or API surface changes"
    return None, "No clear domain signal; red-team fixed seat only"


def _prepare_council_instructions(rotating_seat: str | None) -> str:
    """Council instructions for one rotating seat.

    Keyed on the seat so every producer renders the same text for the same
    roster; the receipt binding rebuilds this rather than inheriting a string
    built from superseded wave text.
    """

    return (
        "Run each council seat in isolation against the admitted change docs and wave record. "
        "Verification must be code-grounded: verify each plan's load-bearing claims against the "
        "actual tree, not against the plan's own prose — cited file:line sites and symbols must "
        "resolve, 'X already does Y' claims must hold in the code, and 'no other caller/site' "
        "censuses must be complete. Do not approve a plan whose claims were checked only against "
        "its own text. When a seat writes a finding that cites code, cite a resolvable anchor — a "
        "function, class, method, constant, test name, or distinguishing expression — rather than "
        "a bare file:line, because a symbol anchor resolves to today's text while a line anchor "
        "drifts hardest when a sibling wave edits the target concurrently. A line number is still "
        "correct for a module-level constant block, data file, specific line in a generated "
        "artifact, prose in a hand-authored markdown document, or deliberately historical "
        "citation; name that case inline so a reviewer can tell a deliberate line anchor from a "
        "lapsed one. Have wave-council synthesize findings. "
        "Record the verdict in ## Review Checkpoints with a structured 'prepare-council' line "
        "whose seats: field lists the seats actually run, each at most once, with per-seat "
        "evidence (or an explicit no-findings note) recorded in the wave record "
        f"(e.g. `{_prepare_council_verdict_template(rotating_seat)}`) "
        "before calling wf_prepare_wave(mode='create')."
    )


def _prepare_council_verdict_template(rotating_seat: str | None) -> str:
    rotating_part = rotating_seat or "none"
    seat_list = ["red-team", "architecture-reviewer", "security-reviewer", "qa-reviewer", "reality-checker"]
    # De-dup: the rotating pick can itself be a fixed seat (security-reviewer and
    # architecture-reviewer are both in the fixed list). The roster lists distinct seats;
    # a seat serving as both fixed and rotating is identified by the separate
    # `rotating-seat:` field, so dropping the duplicate token loses no information.
    if rotating_seat and rotating_seat not in seat_list:
        seat_list.append(rotating_seat)
    seats = ", ".join(seat_list)
    return (
        "- **Prepare-phase Wave Council [prepare-council] — <date>: PASS** "
        "(moderator: wave-council; primer-depth: standard; "
        f"seats: <replace with the seats actually run, each at most once, e.g. {seats}>; "
        f"rotating-seat: {rotating_part}; "
        "strongest-challenge: <summary>; strongest-alternative: <summary>)"
    )


def _build_prepare_council_brief(wave_id: str, wave_text: str, change_ids: list[str]) -> dict[str, Any]:
    """Build the council review brief returned by wf_prepare_wave when no verdict is recorded."""
    rotating_seat, rotating_seat_reason = _select_prepare_council_rotating_seat(wave_text)
    seats = ["red-team (fixed)"]
    if rotating_seat:
        seats.append(f"{rotating_seat} (rotating)")
    return {
        "wave_id": wave_id,
        "change_count": len(change_ids),
        "fixed_seat": "red-team",
        "rotating_seat": rotating_seat,
        "rotating_seat_reason": rotating_seat_reason,
        "council_seats": seats,
        "instructions": _prepare_council_instructions(rotating_seat),
        "verdict_format": _prepare_council_verdict_template(rotating_seat),
    }


def _wave_uses_external_review_evidence(root: Path, wave_md: Path) -> bool:
    """True for the new contract; unmarked pre-protocol waves remain prose-only legacy."""

    # Wave 1v0lw: seam-routed; an unreadable record stays classified as
    # legacy (the historical OSError behavior, now covering decode too) --
    # callers gate on their own record read before any authority decision.
    text, _read_error = _read_wave_record_text(wave_md)
    if text is None:
        return False
    source, source_errors = parse_review_evidence_source(text)
    legacy_inline_marker = re.search(r"(?mi)^review-evidence-protocol\s*:", text) is not None
    return source is not None or bool(source_errors) or legacy_inline_marker


def _review_status_signoff_keys(
    root: Path,
    wave_text: str,
    records: Iterable[Mapping[str, Any]] = (),
) -> tuple[str, ...]:
    """Return the canonical keys represented by the bounded status projection."""

    return required_review_status_keys(root, wave_text, records)


_FRAMEWORK_TEST_RUNNER_REL = ".wavefoundry/framework/scripts/run_tests.py"


_FRAMEWORK_TEST_RECEIPT_REL = ".wavefoundry/framework/test-cache.json"


_RUN_TESTS_IMPORT_ENV = "WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"


def _load_framework_test_runner(runner_path: Path) -> Any:
    """Load the target repository's ``run_tests.py`` for its hash computation only.

    The hash is REUSED rather than reimplemented so the gate and the writer
    cannot drift.  The module is loaded from the target root's own path (never
    imported by name) and is not registered in ``sys.modules``.

    ``run_tests.py`` mutates FIVE pieces of interpreter state at import, and all
    five are undone here.  Delivery review found the inventory short twice: first
    at two (ARCH-DEL-1 / CODE-DEL-2 added ``sys.path`` and the tool-venv
    activation), then at four, when reverification demonstrated that
    ``sys.modules`` is an unrestored fifth channel whose safety rested only on
    ``server_impl`` happening to import the same two scripts-directory modules
    the runner does.  One added module-scope import in a future runner would
    leak a foreign module permanently, surviving deletion of the foreign
    repository.  The five: ``sys.dont_write_bytecode``, the dashboard-browser
    suppression variable, a ``sys.path`` insert of the runner's own scripts
    directory, ``venv_bootstrap.activate_tool_venv()`` (which prepends the tool
    venv's ``site-packages``), and every module the borrow registers.

    This matters because the MCP server may be launched from one repository
    against a different ``--root``: leaving a foreign ``scripts/`` directory
    ahead of the server's own on ``sys.path``, or a foreign module in
    ``sys.modules``, would make later imports resolve against code the server
    does not own.

    ``activate_tool_venv`` also calls ``sys.exit(2)`` on a venv/interpreter
    mismatch. ``SystemExit`` is a ``BaseException``, so it is caught explicitly
    (ARCH-DEL-2 / CODE-DEL-1 / REL-DEL-1): a runner that cannot be loaded is
    "not proven", never a terminated tool call.  The catch is deliberately
    ``(Exception, SystemExit)`` rather than bare ``BaseException``: reverification
    showed the broader form swallows a ``KeyboardInterrupt`` delivered on the
    server's main thread during the borrow, costing the operator a Ctrl-C and
    mislabelling it as a load failure, while catching nothing the wave needs.
    """
    saved_bytecode = sys.dont_write_bytecode
    saved_path = list(sys.path)
    saved_modules = set(sys.modules)
    saved_env_present = _RUN_TESTS_IMPORT_ENV in os.environ
    saved_env = os.environ.get(_RUN_TESTS_IMPORT_ENV)
    try:
        spec = importlib.util.spec_from_file_location(
            "wavefoundry_close_gate_run_tests", runner_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (Exception, SystemExit):  # noqa: BLE001 - a runner that cannot be loaded is "not proven"
        return None
    finally:
        sys.dont_write_bytecode = saved_bytecode
        sys.path[:] = saved_path
        for name in [name for name in sys.modules if name not in saved_modules]:
            sys.modules.pop(name, None)
        if saved_env_present:
            os.environ[_RUN_TESTS_IMPORT_ENV] = saved_env or ""
        else:
            os.environ.pop(_RUN_TESTS_IMPORT_ENV, None)


SUBPROCESS_OPS_TIMEOUT_DEFAULT = 180.0


def subprocess_ops_timeout_seconds(root: Path, op: str, *, default: float = SUBPROCESS_OPS_TIMEOUT_DEFAULT) -> float:
    """Timeout (seconds) for a bounded short-op subprocess (``gardener`` or
    ``surface_render`` or ``sensor``). Reads ``docs/workflow-config.json``
    ``subprocess_ops.<op>_timeout_seconds``; any error / missing key /
    non-positive / non-finite / boolean value falls back to the generous default
    and never raises."""
    try:
        cfg = _read_workflow_config(root)
        val = (cfg.get("subprocess_ops") or {}).get(f"{op}_timeout_seconds")
        if isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0 and math.isfinite(val):
            return float(val)
    except Exception:
        pass
    return default


def _read_project_sensors(root: Path) -> list[dict]:
    """Return registered sensor definitions from workflow-config.json."""
    cfg = _read_workflow_config(root)
    raw = cfg.get("sensors", [])
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        command = item.get("command")
        if not name or not command:
            continue
        out.append({
            "name": name,
            "command": command if isinstance(command, list) else str(command),
            "dimension": str(item.get("dimension", "maintainability")),
            "description": str(item.get("description", "")),
        })
    return out


def _read_phase_gates(root: Path) -> tuple[dict[str, Any], tuple[str, ...]]:
    return normalize_phase_gates(_read_workflow_config(root))
