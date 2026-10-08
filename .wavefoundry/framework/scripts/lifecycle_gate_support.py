"""Pure lifecycle policy and diagnostic support; never imports the server."""
from __future__ import annotations

import errno
import importlib.util
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from typing import (
    Any,
    Iterable,
    Mapping,
    Optional,
    Sequence,
)
import contained_files  # the contained read rule's owner (wave 200ey, change 1zyv2)
import path_containment
import record_paths
import vocabulary_profile as _vocab  # record markers are vocabulary (wave 1z8mm)
from gardener_metadata import ambiguous_excluded_headings, canonical_review_policy_body
from review_policy import (
    ProjectLanesConfigError,
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
    policy_input_snapshot,
    project_required_review_lanes,
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
import review_policy  # the pure lane helper is called through the module (wave 1zlu1)
import change_doc_checklist  # shared checklist parser (wave 1zime, 1zimq)


def _read_workflow_config(root: Path) -> dict:
    cfg = root / "docs" / "workflow-config.json"
    if cfg.is_file():
        try:
            return json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _read_project_required_review_lanes(root: Path) -> list[str]:
    """Return project-declared required review lanes from workflow-config.json.

    Wave 1zlu1 (1zlu4): a present, non-list value raises
    ``ProjectLanesConfigError`` instead of reading as no lanes."""
    return project_required_review_lanes(_read_workflow_config(root))


def _project_lanes_for_phase(root: Path, phase: str) -> list[str]:
    """Root-reading wrapper over ``review_policy.project_lanes_for_phase``
    (wave 1zlu1, change 1zlu4): the project lanes required at ``phase``
    (``prepare`` or ``close``).  Raises ``ProjectLanesConfigError`` for a
    non-list ``required_review_lanes``."""
    return review_policy.project_lanes_for_phase(_read_workflow_config(root), phase)


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
                    "signoff_key": review_evidence.COUNCIL_READINESS_SIGNOFF_KEY,
                    "moderator_role": review_evidence.COUNCIL_ACTOR,
                },
                "review": {
                    "signoff_key": review_evidence.COUNCIL_DELIVERY_SIGNOFF_KEY,
                    "moderator_role": review_evidence.COUNCIL_ACTOR,
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
        "prepare": review_evidence.COUNCIL_READINESS_SIGNOFF_KEY,
        "review": review_evidence.COUNCIL_DELIVERY_SIGNOFF_KEY,
    }
    phases: dict[str, dict[str, str]] = {}
    for phase, default_key in phase_defaults.items():
        phase_raw = phases_raw.get(phase, {})
        if not isinstance(phase_raw, dict):
            phase_raw = {}
        signoff_key = str(phase_raw.get("signoff_key", default_key)).strip()
        # Wave 200ey (change 200ew): the default is ``council-chair``; a
        # config naming the earlier ``wave-council`` is read as written.
        moderator_role = str(phase_raw.get("moderator_role", review_evidence.COUNCIL_ACTOR)).strip()
        if signoff_key:
            phases[phase] = {
                "signoff_key": signoff_key,
                "moderator_role": moderator_role or review_evidence.COUNCIL_ACTOR,
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
    # Config values are canonicalized here, at the comparison site (wave
    # 1zyb4): a config naming the earlier council keys requires the same keys
    # as one naming the current keys. The policy object is never rewritten.
    canonical = review_evidence.canonical_signoff_key

    def _phase_key(phase: str) -> str | None:
        key = policy.get("phases", {}).get(phase, {}).get("signoff_key")
        return canonical(key) if key else None

    required: list[str] = []
    for phase in phase_map.get(lifecycle_phase, []):
        signoff_key = _phase_key(phase)
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
            review_key = _phase_key("review")
            required = [key for key in required if key != review_key]
    if not required:
        return required

    transition_policy = str(policy.get("transition_policy", "")).strip().lower()
    if transition_policy != "applies-from-next-prepare" or lifecycle_phase == "prepare" or not (wave_text or wave_md):
        return required

    prepare_key = _phase_key("prepare")
    review_key = _phase_key("review")
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


_CHANGE_ID_PATTERN = re.compile(rf"^{_vocab.MEMBER_ID_LABEL_RE}:\s+`([^`]+)`", re.MULTILINE)


# Wave 1zxo0 (1zxns): the one allow-list for a change id. The prefix and slug
# fragments are literal copies of ``wave_lint_lib.constants``
# ``LIFECYCLE_PREFIX_PATTERN`` and ``SLUG_PATTERN`` (importing them here would
# cycle through ``wave_lint_lib``); a parity test pins them equal. The kind is
# the kind SHAPE ``vocabulary_profile`` enforces for extra kinds, not the live
# kind list, so an archived record written under a profile that later dropped
# an extra kind stays readable while every accepted value stays path-safe: no
# separator, colon, control character, dot, uppercase letter, or leading or
# trailing space, and never a reserved Windows device name.
_CHANGE_ID_PREFIX_FRAGMENT = r"(?:[0-9a-z]{5,6}|00000)"
_CHANGE_ID_SLUG_FRAGMENT = r"[a-z0-9][a-z0-9-]*"
_CHANGE_ID_KIND_SHAPE_FRAGMENT = r"[a-z][a-z0-9]{1,15}"
CHANGE_ID_SHAPE_RE = re.compile(
    rf"{_CHANGE_ID_PREFIX_FRAGMENT}-{_CHANGE_ID_KIND_SHAPE_FRAGMENT} {_CHANGE_ID_SLUG_FRAGMENT}"
)


def is_change_id(value: Any) -> bool:
    """True only for a ``str`` that fully matches ``CHANGE_ID_SHAPE_RE``."""
    return isinstance(value, str) and CHANGE_ID_SHAPE_RE.fullmatch(value) is not None


class ChangeIdRejected(ValueError):
    """A path helper was handed a value that is not a change id (wave 1zxo0).

    The message never carries the value."""


_DRIVE_PREFIX_RE = re.compile(r"^[A-Za-z]:")


def _change_id_reason_class(value: str) -> str:
    """The reason class for a rejected member id: ``control character``,
    ``path character`` or ``shape``. Never the value itself."""
    if any(ord(ch) < 0x20 or 0x7F <= ord(ch) <= 0x9F for ch in value):
        return "control character"
    if any(ch in value for ch in ("/", "\\", ":")) or value.strip() in (".", ".."):
        return "path character"
    return "shape"


def _change_id_shape_error(change_id: Any) -> Optional[dict[str, Any]]:
    """An ``invalid_arguments`` diagnostic when ``change_id`` cannot be a change id.

    Wave 1zv87 (1zv85): lifecycle tools build ``<wave dir>/<change_id>.md``
    from this argument, so an id that is empty, absolute (a drive-letter form
    included), or carries a path separator (``/`` or ``\\``), a ``..``
    component, or a NUL is refused here, with no filesystem access, before any
    path is built.  Wave 1zxo0 (1zxns): moved here from the server and closed
    with the allow-list, so any other value that is not of the form
    ``<prefix>-<kind> <slug>`` is refused too.  The message never echoes the
    value."""
    value = change_id if isinstance(change_id, str) else ""
    reason = ""
    if not value.strip():
        reason = "is empty"
    elif "\x00" in value:
        reason = "contains a NUL character"
    elif value.startswith(("/", "\\")) or _DRIVE_PREFIX_RE.match(value) or os.path.isabs(value):
        reason = "is an absolute path"
    elif "/" in value or "\\" in value:
        reason = "contains a path separator"
    elif value == "..":
        reason = "is a `..` path component"
    elif not is_change_id(value):
        reason = "is not a change id of the form `<prefix>-<kind> <slug>`"
    if not reason:
        return None
    return _diagnostic(
        "invalid_arguments",
        f"change_id {reason}; pass the FULL admitted change id as listed by the wave record.",
        recovery_tools=["wf_current_wave"],
        recovery_usage="wf_current_wave()",
    )


def _member_id_pattern(profile=None) -> "re.Pattern[str]":
    if profile is None:
        return _CHANGE_ID_PATTERN
    return re.compile(rf"^{profile.MEMBER_ID_LABEL_RE}:\s+`([^`]+)`", re.MULTILINE)


def _partition_member_ids(text: str, profile=None) -> tuple[list[str], list[dict[str, Any]]]:
    """Split a record's member-id lines into allow-listed ids and rejections.

    Wave 1zxo0 (1zxns): ``valid`` keeps record order; each rejected entry is
    ``{"line": <1-based line of the member line>, "reason": <class>}`` and never
    carries the rejected value, so no message built from it can echo it.
    ``profile`` parses an archived record (see
    ``_extract_change_ids_from_wave_text``)."""
    valid: list[str] = []
    rejected: list[dict[str, Any]] = []
    for match in _member_id_pattern(profile).finditer(text):
        value = match.group(1)
        if is_change_id(value):
            valid.append(value)
        else:
            rejected.append({
                "line": text.count("\n", 0, match.start()) + 1,
                "reason": _change_id_reason_class(value),
            })
    return valid, rejected


def _change_id_invalid_message(record_rel: str, entry: Mapping[str, Any]) -> str:
    """The ``change_id_invalid`` message: record path, line number and reason
    class only, with the hand-edit recovery (wave 1zxo0)."""
    return (
        f"{record_rel} line {entry['line']} holds a member id that is not a change id "
        f"({entry['reason']}); no path is built from it. Edit that line by hand (no tool "
        "repairs it, and wf_remove_change refuses an invalid id), then run wf_validate_docs."
    )


def _change_id_invalid_diagnostics(
    record_rel: str, rejected: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """One blocking ``change_id_invalid`` diagnostic per rejected member line.
    The one advisory use (bulk ``wf_get_change``) builds its own, so no flag is
    forwarded through here."""
    return [
        _diagnostic(
            "change_id_invalid",
            _change_id_invalid_message(record_rel, entry),
            recovery_tools=["wf_validate_docs"],
            recovery_usage="wf_validate_docs()",
        )
        for entry in rejected
    ]


# Wave 1zxo0 (1zxns): the member-doc read rule. A member change doc is read
# only as a regular file (never a link) directly in its expected folder, inside
# that folder and inside the repository once resolved, through a capped read.
MEMBER_DOC_MAX_BYTES = 8 * 1024 * 1024


class MemberDocRefused(OSError):
    """A member change doc failed the read rule; an ``OSError`` so existing
    ``except OSError`` branches report it as unreadable. The message is a
    cause class only, never a path."""

    def __init__(self, cause: str) -> None:
        super().__init__(errno.EPERM, cause)


def _member_doc_lstat(path: Path) -> Optional[os.stat_result]:
    """``lstat`` of a member doc when it is a regular file, else ``None``: the
    existence probe that feeds a member-doc read, so a link or a directory
    reads as absent rather than being followed."""
    try:
        entry = os.lstat(path)
    except (OSError, ValueError):
        return None
    return entry if stat.S_ISREG(entry.st_mode) else None


# Wave 1zv87 (1zuq7): ``(st_dev, st_ino)`` of every ``*.lock`` file under
# ``<root>/.wavefoundry/``. Since wave 200ey (change 1zyv2) the rule lives in
# ``contained_files.runtime_lock_identities``; this re-export keeps the name for
# the member-doc read below and the server's runtime-lock refusal
# (``server_impl._runtime_lock_identities``).
runtime_lock_identities = contained_files.runtime_lock_identities


def _runtime_lock_identity_match(resolved_root: Path, entry: os.stat_result) -> bool:
    """True when ``entry`` shares ``(st_dev, st_ino)`` with a ``*.lock`` file
    under ``<root>/.wavefoundry/``: a hard link to a runtime lock. The identity
    half of the server's runtime-lock refusal (wave 1zxnz), through the shared
    ``runtime_lock_identities``; no lock file is opened."""
    return (entry.st_dev, entry.st_ino) in runtime_lock_identities(resolved_root)


def _read_member_doc_bytes(folder: Path, path: Path, *, root: Path) -> bytes:
    """Read a member change doc under the member-doc read rule (wave 1zxo0).

    Reads only when ``path.parent`` is ``folder``; ``lstat`` shows a regular
    file (not a link); the resolved path lies in the resolved ``folder`` and in
    the resolved repository ``root`` (so a folder link leaving the repository
    serves nothing, while one inside it still works); the file is not a hard
    link to a runtime lock (the wave 1zxnz rule, so the read cannot release a
    held record lock); and the read through ``contained_files.read_contained``
    (wave 200ey), whose open descriptor must be the file ``lstat`` saw. At most
    ``MEMBER_DOC_MAX_BYTES`` + 1 bytes are read and more than the cap is
    refused; the ``lstat`` size is not trusted. A refusal raises
    ``MemberDocRefused``; a missing file raises the ordinary
    ``FileNotFoundError``. Windows has no ``O_NOFOLLOW`` or ``dir_fd``: the
    checks plus the handle identity comparison stand alone there, and the
    window between a directory check and the open is a documented limit, as in
    ``runtime_lock``.
    """
    folder = Path(folder)
    path = Path(path)
    if path.parent != folder:
        raise MemberDocRefused("not in its expected folder")
    entry = os.lstat(path)
    if not stat.S_ISREG(entry.st_mode):
        raise MemberDocRefused("not a regular file")
    try:
        resolved_folder = folder.resolve(strict=True)
        resolved = path.resolve(strict=True)
        resolved_root = Path(root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise MemberDocRefused("could not be resolved") from exc
    if path_containment.contained_resolved_path(resolved_folder, resolved) is None:
        raise MemberDocRefused("resolves outside its folder")
    if path_containment.contained_resolved_path(resolved_root, resolved) is None:
        raise MemberDocRefused("resolves outside the repository")
    if entry.st_nlink > 1 and _runtime_lock_identity_match(resolved_root, entry):
        raise MemberDocRefused("resolves to a framework runtime lock")
    # Wave 200ey (change 1zyv2): the read itself is the shared contained read
    # (resolved parent walked without following links, non-blocking no-follow
    # open whose identity must match, capped). Its refusal is re-raised with
    # this rule's cause text, which ``wave_lint_lib.helpers._refusal_cause``
    # maps; a test pins every string.
    try:
        data, opened = contained_files.read_contained(
            resolved_root, resolved, max_bytes=MEMBER_DOC_MAX_BYTES
        )
    except contained_files.ContainedFileRefused as exc:
        raise MemberDocRefused(_MEMBER_DOC_CAUSES.get(exc.cause, exc.cause)) from None
    if (opened.st_dev, opened.st_ino) != (entry.st_dev, entry.st_ino):
        raise MemberDocRefused("changed while being opened")
    return data


# The contained read's cause classes as the member-doc rule names them. A cause
# not listed keeps its text (every other primitive cause is already one of this
# rule's strings).
_MEMBER_DOC_CAUSES = {
    contained_files.CAUSE_SIZE: "exceeds the member document size cap",
    contained_files.CAUSE_NOT_UNDER_ROOT: "resolves outside the repository",
    contained_files.CAUSE_LINK_COMPONENT: "changed while being opened",
    contained_files.CAUSE_NOT_DIRECTORY: "changed while being opened",
}


def _read_member_doc_text(folder: Path, path: Path, *, root: Path) -> str:
    """``_read_member_doc_bytes`` decoded as UTF-8 (``UnicodeDecodeError`` on
    bad bytes, as ``read_text`` raised)."""
    return _read_member_doc_bytes(folder, path, root=root).decode("utf-8")


# Wave 1zime (1zimq): the shared any-marker item pattern; the gate counts an
# open item under every list marker, not only `-`.
_CLOSE_GATE_CHECKBOX_LINE_RE = change_doc_checklist.CHECKLIST_ITEM_RE


_CLOSE_GATE_AC_ID_RE = re.compile(r"(AC-[\w\-]+)")


def _extract_close_gate_section(text: str, heading: str) -> str:
    """Extract the first exact ``## <heading>`` section body (heading name
    without the ``## `` prefix), read through the shared parser so fenced code
    neither ends the section nor contributes lines (wave 1zls7, 1zltr)."""
    bodies = change_doc_checklist.section_bodies(text, heading)
    return change_doc_checklist.unfenced_text(bodies[0]) if bodies else ""


def _close_gate_change_ids(wave_text: str) -> list[str]:
    """Admitted change ids for the close checklist gate (wave 1zls7, 1zltr).

    Read through docs-lint's record parser, which strips each line, so an
    indented member id block cannot escape the gate; only ``change``
    records are kept (the parser's legacy ``item`` fallback ids are not change
    documents).  Column-0 ids the lint parser does not accept (a non-lint id
    shape) are kept too, so no id the gate read before is dropped.  Wave 1zxo0
    (1zxns): every id passes the allow-list; a rejected column-0 line is
    reported by ``_collect_silent_unchecked_items_for_close`` as a ``change id``
    finding instead.
    """
    from wave_lint_lib.wave_validators import _parse_work_records

    ids: list[str] = []
    for record in _parse_work_records(wave_text, ""):
        if (record.anchor_type == "change" and is_change_id(record.record_id)
                and record.record_id not in ids):
            ids.append(record.record_id)
    for change_id in _partition_member_ids(wave_text)[0]:
        if change_id not in ids:
            ids.append(change_id)
    return ids


def _close_gate_item_text(match: "re.Match[str]") -> str:
    """Item text for a close finding; an unusual mark is shown (``[-] step``)."""
    text_part = match.group("text").strip()
    mark = match.group("mark")
    if not change_doc_checklist.is_canonical_mark(mark):
        text_part = f"[{mark}] {text_part}"
    return text_part[:120]


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


def _collect_silent_unchecked_items_for_close(
    wave_md: Path, wave_text: str, root: Optional[Path] = None,
) -> list[dict[str, str]]:
    """Walk admitted change docs; return silent open items that block close.

    Wave 1p31b (1p32k): the close-time hard gate. Every AC and task must be ``[x]`` or
    ``[~]`` at close. AC items at ``not-this-scope`` priority are exempt. Returns a list of
    ``{'change_id', 'item_type' ('AC' or 'task'), 'item_id', 'item_text'}`` dicts.
    Wave 1zls7 (1zltr): an item is open unless its mark is ``x``, ``X`` or ``~``
    (an unusual mark such as ``[-]`` is open and shown in ``item_text``), items
    are read through the shared parser (blockquoted items count; fenced
    examples do not), and change ids come from docs-lint's record parser.
    Wave 1zxo0 (1zxns): member docs are read under the member-doc read rule
    inside ``root`` (the lifecycle callers pass it; without it the wave folder
    bounds the read), and a rejected member line is a ``change id`` finding.
    """
    read_root = root if root is not None else wave_md.parent
    findings: list[dict[str, str]] = []
    # Wave 1zxo0 (1zxns): a member line whose id fails the allow-list blocks
    # close as a ``change id`` finding; no path is built from it, the finding
    # carries an empty ``change_id`` (never the value) and the line number only.
    for entry in _partition_member_ids(wave_text)[1]:
        findings.append({
            "change_id": "",
            "item_type": "change id",
            "item_id": entry["reason"],
            "item_text": str(entry["line"]),
        })
    for change_id in _close_gate_change_ids(wave_text):
        change_path = _wave_change_doc_path(read_root, wave_md, change_id)
        if not os.path.lexists(change_path):
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
            change_text = _read_member_doc_text(change_path.parent, change_path, root=read_root)
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

        # Wave 1zime (1zimq): both sections are required by exact heading (a
        # misspelled, suffixed or demoted heading counts as missing; the
        # section may be empty), and EVERY section with the heading is read.
        missing_sections = [
            f"## {heading}"
            for heading in ("Acceptance Criteria", "Tasks")
            if not change_doc_checklist.has_section(change_text, heading)
        ]
        if missing_sections:
            findings.append({
                "change_id": change_id,
                "item_type": "change document",
                "item_id": "missing_sections",
                "item_text": ", ".join(missing_sections),
            })
        priority_section = _extract_close_gate_section(change_text, "AC Priority")
        priorities = _close_gate_parse_ac_priority(priority_section)

        # Walk AC items — silent `[ ]` at non-exempt priority blocks close.  The
        # id comes only from the start of the item: an id cited later in the
        # text never exempts it.
        # A near-miss section (`## Tasks (remaining)`) is counted too: an open
        # item under it is never invisible to the gate.
        for ac_section in change_doc_checklist.section_bodies(
            change_text, "Acceptance Criteria", include_near_miss=True
        ):
            for match in change_doc_checklist.checklist_items(ac_section):
                if not change_doc_checklist.is_open_mark(match.group("mark")):
                    continue
                text_part = match.group("text").strip()
                ac_id = change_doc_checklist.leading_ac_id(text_part) or "<unidentified>"
                priority = priorities.get(ac_id, "unknown")
                if priority == "not-this-scope":
                    continue
                findings.append({
                    "change_id": change_id,
                    "item_type": "AC",
                    "item_id": ac_id,
                    "item_text": _close_gate_item_text(match),
                })

        # Walk task items: every open item blocks close (no priority exemption for tasks).
        for task_section in change_doc_checklist.section_bodies(
            change_text, "Tasks", include_near_miss=True
        ):
            for match in change_doc_checklist.checklist_items(task_section):
                if not change_doc_checklist.is_open_mark(match.group("mark")):
                    continue
                findings.append({
                    "change_id": change_id,
                    "item_type": "task",
                    "item_id": "",
                    "item_text": _close_gate_item_text(match),
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


def _extract_change_ids_from_wave_text(text: str, profile=None) -> list[str]:
    """Member ids listed in a wave record; ``profile`` (an
    ``vocabulary_profile.archive_profile()`` object) parses an archived record
    written under another vocabulary (wave 1z8ts). Wave 1zxo0 (1zxns): only
    allow-listed ids are returned, in record order; see
    ``_partition_member_ids`` for the rejected lines."""
    return _partition_member_ids(text, profile)[0]


def _wave_change_doc_path(root: Path, wave_md: Path, change_id: str) -> Path:
    """``<wave folder>/<id>.md``; raises ``ChangeIdRejected`` before any
    filesystem work for a value that is not a change id (wave 1zxo0)."""
    if not is_change_id(change_id):
        raise ChangeIdRejected("not a change id; no path is built from it")
    return wave_md.parent / f"{change_id}.md"


def _plan_change_doc_path(root: Path, change_id: str) -> Path:
    """``<plans root>/<id>.md``; raises ``ChangeIdRejected`` before any
    filesystem work for a value that is not a change id (wave 1zxo0)."""
    if not is_change_id(change_id):
        raise ChangeIdRejected("not a change id; no path is built from it")
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
    """Where a member doc is. Wave 1zxo0 (1zxns): presence is ``lexists``, so
    a link is present but never followed here; every caller that reads the
    doc does so through ``_read_member_doc_bytes``, which refuses it with the
    readability diagnostic before any move or write."""
    staged = _plan_change_doc_path(root, change_id)
    wave_path = _wave_change_doc_path(root, wave_md, change_id)
    return {
        "staged_path": staged,
        "wave_path": wave_path,
        "staged_exists": os.path.lexists(staged),
        "wave_exists": os.path.lexists(wave_path),
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
    # Wave 1zime (1zimq): the two sections the close gate reads are checked by
    # exact heading line, so a heading close would refuse is refused here
    # first; the other four keep their substring check.
    exact = {"## Acceptance Criteria": "Acceptance Criteria", "## Tasks": "Tasks"}
    return [
        hdr for hdr in required_headers
        if (not change_doc_checklist.has_section(change_text, exact[hdr]) if hdr in exact
            else hdr not in change_text)
    ]


def _noncanonical_checklist_headings(change_text: str) -> list[str]:
    """H2 headings that start with ``## Acceptance Criteria`` or ``## Tasks`` but
    are not exact (wave 1zime repair), such as ``## Tasks (remaining)``."""
    return [
        line
        for heading in ("Acceptance Criteria", "Tasks")
        for line in change_doc_checklist.near_miss_headings(change_text, heading)
    ]


def _noncanonical_checklist_items(change_text: str) -> list[str]:
    """Checklist items in ``## Acceptance Criteria`` or ``## Tasks`` (or a
    near-miss section of either) whose list marker is not the canonical ``-``
    (wave 1zime, 1zimq) or whose mark is not a space, ``x``, ``X`` or ``~``
    (wave 1zls7, 1zltr), as ``marker [m] text``."""
    found: list[str] = []
    for heading in ("Acceptance Criteria", "Tasks"):
        for match in change_doc_checklist.section_items(change_text, heading, include_near_miss=True):
            if (not change_doc_checklist.is_canonical_marker(match.group("marker"))
                    or not change_doc_checklist.is_canonical_mark(match.group("mark"))):
                found.append(f"{match.group('marker')} [{match.group('mark')}] {match.group('text').strip()[:120]}")
    return found


_REQUIRED_DELIVERY_LANES_RE = re.compile(r"^-\s*Required delivery lanes\s*:\s*(?P<lanes>.+?)\s*$", re.IGNORECASE)


def _participants_lines(wave_text: str) -> list[str]:
    """The stripped lines of the wave record's ``## Participants`` section."""
    lines: list[str] = []
    in_participants = False
    for raw in wave_text.splitlines():
        line = raw.strip()
        if line.startswith("## Participants"):
            in_participants = True
            continue
        if in_participants and line.startswith("## "):
            break
        if in_participants:
            lines.append(line)
    return lines


def _roster_values(value: str) -> list[str]:
    lanes: list[str] = []
    for lane in value.split(","):
        normalized = lane.strip().strip("`").strip()
        if normalized and normalized.lower() not in {"none", "—", "-"} and normalized not in lanes:
            lanes.append(normalized)
    return lanes


def _extract_required_delivery_line(wave_text: str) -> Optional[list[str]]:
    """The ``- Required delivery lanes:`` roster (wave 1zlu1, change 1zlu4),
    or ``None`` when the wave record has no such line."""
    for line in _participants_lines(wave_text):
        match = _REQUIRED_DELIVERY_LANES_RE.match(line)
        if match:
            return _roster_values(match.group("lanes"))
    return None


def _extract_required_delivery_lanes(wave_text: str) -> list[str]:
    """The delivery roster (Review and Close): the ``Required delivery
    lanes`` line when present, otherwise the readiness roster."""
    delivery = _extract_required_delivery_line(wave_text)
    return delivery if delivery is not None else _extract_required_review_lanes(wave_text)


def _extract_required_lanes_for_phase(wave_text: str, phase: str) -> list[str]:
    """The wave-record roster for ``phase``: ``prepare`` reads the readiness
    line, ``close`` the delivery roster."""
    return _extract_required_review_lanes(wave_text) if phase == "prepare" else _extract_required_delivery_lanes(wave_text)


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
    """Name only document changes supported by persisted receipt metadata."""

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
    old_inputs = current.get("policy_inputs")
    new_inputs = pending.get("policy_inputs")
    if isinstance(old_inputs, Mapping) and isinstance(new_inputs, Mapping):
        old_changes = {entry["change_id"]: entry for entry in old_inputs["changes"]}
        new_changes = {entry["change_id"]: entry for entry in new_inputs["changes"]}
        changed = sorted(
            change_id for change_id in old_changes.keys() | new_changes.keys()
            if old_changes.get(change_id) != new_changes.get(change_id)
        )
        parts.append("changed change docs: " + (", ".join(changed) or "none"))
        if old_inputs["project_policy_sha256"] != new_inputs["project_policy_sha256"]:
            parts.append("project policy inputs changed")
        return " (" + "; ".join(parts) + "). Which section changed is not attributable from persisted data."
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
    try:
        # The digest keeps receiving the base list (both phases); the two
        # rosters below add each phase's own lanes (wave 1zlu1, 1zlu4).
        project_lanes = tuple(project_required_review_lanes(config))
        readiness_project_lanes = tuple(review_policy.project_lanes_for_phase(config, "prepare"))
        delivery_project_lanes = tuple(review_policy.project_lanes_for_phase(config, "close"))
    except ProjectLanesConfigError as exc:
        return None, (PolicyInputError("config", str(exc)),)
    change_inputs: list[tuple[str, str, bytes]] = []
    change_texts: list[str] = []
    errors: list[PolicyInputError] = []
    for change_id in change_ids:
        path = _wave_change_doc_path(root, wave_md, change_id)
        try:
            override = (change_text_overrides or {}).get(change_id)
            if override is None:
                # Wave 1zxo0 (1zxns): the member-doc read rule.
                body = _read_member_doc_bytes(path.parent, path, root=root)
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
        project_lanes=readiness_project_lanes,
        change_texts=change_texts,
    )
    delivery_lanes, _delivery_reasons = select_required_review_lanes(
        requested_lanes=requested,
        project_lanes=delivery_project_lanes,
        change_texts=change_texts,
    )
    digest, policy_inputs = policy_input_snapshot(
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
        "policy_inputs": policy_inputs,
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
        # Wave 1zlu1 (1zlu4): the delivery roster (Review and Close) and the
        # lanes it adds over readiness; the receipt keeps the readiness roster.
        "delivery_lanes": list(delivery_lanes),
        "delivery_only_lanes": [lane for lane in delivery_lanes if lane not in required_lanes],
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
    # Policy input only (the brief text is not a receipt input); this path is
    # reached only for an external-evidence (typed) wave.
    brief = _build_prepare_council_brief(
        wave_md.parent.name, wave_text, change_ids, typed=True
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
    # Wave 1zlu1 (1zlu4): the delivery roster (the line, or the readiness
    # line when it is absent) is compared with the delivery selection too.
    persisted_delivery = tuple(_extract_required_delivery_lanes(wave_text))
    if persisted_delivery != tuple(state["delivery_lanes"]):
        diagnostics.append(
            _diagnostic(
                "review_policy_receipt_stale",
                "Persisted Required delivery lanes no longer match the current policy inputs; re-Prepare.",
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


def _prepare_council_instructions(rotating_seat: str | None, *, typed: bool = False) -> str:
    """Council instructions for one rotating seat and one review authority.

    Keyed on the pair (seat, authority) so every producer renders the same
    text for the same roster and authority; the receipt binding rebuilds this
    rather than inheriting a string built from superseded wave text.  On a
    declared (typed) wave the authority is the typed ``council-readiness``
    approval, so the brief points there (wave 1zime, 1ziml); legacy waves keep
    the ``## Review Checkpoints`` prose line.
    """

    grounding = (
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
        f"lapsed one. Have {review_evidence.COUNCIL_ACTOR} synthesize findings. "
    )
    if typed:
        return grounding + (
            "This wave's review authority is the typed ledger, so record the outcome there: first "
            "the readiness review run, then each required lane's readiness approval, then the "
            "council verdict as a typed approval, "
            "wf_review_event(event='approval', signoff_key='council-readiness', "
            "approval_phase='readiness', mode='create', ...), whose evidence names the seats "
            "actually run, each at most once, with per-seat evidence or an explicit no-findings "
            f"note (e.g. `{_prepare_council_verdict_template(rotating_seat, typed=True)}`). "
            "A ## Review Checkpoints narrative is optional and is not authority: the gate reads "
            "only the typed approval. Then call wf_prepare_wave(mode='ready'), or mode='create' "
            "to also open the wave."
        )
    return grounding + (
        "Record the verdict in ## Review Checkpoints with a structured 'prepare-council' line "
        "whose seats: field lists the seats actually run, each at most once, with per-seat "
        "evidence (or an explicit no-findings note) recorded in the wave record "
        f"(e.g. `{_prepare_council_verdict_template(rotating_seat)}`) "
        "before calling wf_prepare_wave(mode='create')."
    )


def _prepare_council_verdict_template(rotating_seat: str | None, *, typed: bool = False) -> str:
    rotating_part = rotating_seat or "none"
    seat_list = ["red-team", "architecture-reviewer", "security-reviewer", "qa-reviewer", "reality-checker"]
    # De-dup: the rotating pick can itself be a fixed seat (security-reviewer and
    # architecture-reviewer are both in the fixed list). The roster lists distinct seats;
    # a seat serving as both fixed and rotating is identified by the separate
    # `rotating-seat:` field, so dropping the duplicate token loses no information.
    if rotating_seat and rotating_seat not in seat_list:
        seat_list.append(rotating_seat)
    seats = ", ".join(seat_list)
    if typed:
        # Wave 1zime (1ziml): the typed approval is the record that counts.
        return (
            "wf_review_event(wave_id=<wave id>, event='approval', "
            "signoff_key='council-readiness', approval_phase='readiness', "
            f"actor='{review_evidence.COUNCIL_ACTOR}', context_id=<fresh context id>, mode='create', "
            f"evidence={{'observed': 'Prepare-phase {_vocab.COUNCIL_DISPLAY_NAME} PASS "
            f"(moderator: {review_evidence.COUNCIL_ACTOR}; "
            "primer-depth: standard; "
            f"seats: <replace with the seats actually run, each at most once, e.g. {seats}>; "
            f"rotating-seat: {rotating_part}; "
            "strongest-challenge: <summary>; strongest-alternative: <summary>)', "
            "'artifact_or_test_id': <per-seat evidence reference>}, ...)"
        )
    return (
        "- **Prepare-phase Wave Council [prepare-council] — <date>: PASS** "
        f"(moderator: {review_evidence.COUNCIL_ACTOR}; primer-depth: standard; "
        f"seats: <replace with the seats actually run, each at most once, e.g. {seats}>; "
        f"rotating-seat: {rotating_part}; "
        "strongest-challenge: <summary>; strongest-alternative: <summary>)"
    )


def _build_prepare_council_brief(
    wave_id: str, wave_text: str, change_ids: list[str], *, typed: bool = False
) -> dict[str, Any]:
    """Build the council review brief returned by wf_prepare_wave when no verdict is recorded.

    ``typed`` is the resolved review authority (wave 1zime): the instructions
    and verdict format name the record that counts for it.
    """
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
        "instructions": _prepare_council_instructions(rotating_seat, typed=typed),
        "verdict_format": _prepare_council_verdict_template(rotating_seat, typed=typed),
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
