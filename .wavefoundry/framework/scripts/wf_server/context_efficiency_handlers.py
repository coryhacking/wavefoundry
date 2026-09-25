"""Context-efficiency projection and response ownership."""
from __future__ import annotations

import json
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Iterable, Mapping, TYPE_CHECKING

import context_efficiency
import index_source_guard
import record_paths
from lifecycle_gate_support import _read_wave_record_text
from review_evidence import ProjectPublicationUnavailable

if TYPE_CHECKING:
    from wf_server.server_impl import ImplHandler

_CE_PROJECTION_MIN_QUIET_SECONDS = 90.0


_CE_PROJECTION_DEFAULT_QUIET_SECONDS = 120.0


_CE_PROJECTION_MAX_QUIET_SECONDS = 600.0


_CE_PROJECTION_POLL_SECONDS = 15.0


def _read_ce_projection_config(root: Path) -> dict[str, Any]:
    quiet = _CE_PROJECTION_DEFAULT_QUIET_SECONDS
    try:
        cfg = json.loads((root / "docs" / "workflow-config.json").read_text(encoding="utf-8"))
        raw = (((cfg.get("context_efficiency") or {}).get("projection") or {})
               .get("quiet_period_seconds"))
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            quiet = float(raw)
    except Exception:  # noqa: BLE001
        pass
    quiet = min(
        _CE_PROJECTION_MAX_QUIET_SECONDS,
        max(_CE_PROJECTION_MIN_QUIET_SECONDS, quiet),
    )
    return {"enabled": True, "interval_seconds": _CE_PROJECTION_POLL_SECONDS,
            "quiet_period_seconds": quiet}


def _pending_ce_generations(root: Path) -> tuple[dict[str, int], str | None]:
    state = context_efficiency.pending_wave_ids(root)
    if not state.get("ok"):
        return {}, str(state.get("error") or state.get("status") or "unavailable")
    generations: dict[str, int] = {}
    for wave_id in state.get("pending", []):
        snapshot = context_efficiency.read_wave_snapshot(root, str(wave_id))
        generations[str(wave_id)] = int(snapshot.get("generation", 0))
    return generations, None


def _maybe_project_context_efficiency(
    root: Path,
    observed: dict[str, tuple[int, float]],
    *,
    now: float | None = None,
) -> dict[str, Any]:
    """Trailing-edge automatic CE projection; never records a tool cost."""
    from wf_server import server_impl
    checked_at = time.time() if now is None else float(now)
    cfg = server_impl._read_ce_projection_config(root)
    pending, error = _pending_ce_generations(root)
    if error:
        return {"last_checked_at": checked_at, "reason": "authority_unavailable",
                "error": error, "triggered": False, "pending_count": 0}
    for wave_id in list(observed):
        if wave_id not in pending:
            observed.pop(wave_id, None)
    eligible: list[str] = []
    for wave_id, generation in pending.items():
        previous = observed.get(wave_id)
        if previous is None or previous[0] != generation:
            observed[wave_id] = (generation, checked_at)
            continue
        if checked_at - previous[1] >= float(cfg["quiet_period_seconds"]):
            eligible.append(wave_id)
    if not eligible:
        return {"last_checked_at": checked_at, "reason": "quiet_period_pending"
                if pending else "nothing_pending", "triggered": False,
                "pending_count": len(pending)}
    projected: list[str] = []
    failure: dict[str, Any] | None = None
    result = project_pending_context_efficiency_root(
        root, automatic=True, wave_ids=eligible
    )
    projected = list(result.get("projected", []))
    for wave_id in projected:
        observed.pop(wave_id, None)
    if not result.get("ok"):
        failure = {
            "wave_id": result.get("failed_wave"),
            **dict(result.get("detail") or {}),
        }
    return {
        "last_checked_at": checked_at,
        "reason": "projected" if projected and failure is None else
                  (str(failure.get("reason") or "projection_failed") if failure else "projection_failed"),
        "triggered": bool(projected),
        "projected": projected,
        "pending_count": len(pending),
        **({"failure": failure} if failure else {}),
    }


def _project_context_efficiency_wave(
    root: Path,
    wave_id: str,
    *,
    handler: "ImplHandler | None" = None,
    automatic: bool = False,
) -> dict[str, Any]:
    """Publish one durable CE generation without recording or flushing telemetry.

    ``automatic`` callers are fail-fast on publication-lock contention and never
    seal, compact, or change process focus. Lifecycle/reload callers retain the
    historical hard-boundary behavior through ``automatic=False``.
    """
    from wf_server import server_impl
    wave_md = server_impl._find_wave_md(root, wave_id)
    if wave_md is None:
        return {"persistence": "failed", "projection": "wave_not_found"}
    canonical_wave = wave_md.parent.name
    try:
        with (index_source_guard.index_source_guard(root, wait=False) if automatic else nullcontext()), \
                server_impl.project_state_publication_lock(root, wait=not automatic):
            # Status, floor, and the durable generation are one publication
            # decision.  Read all three only after acquiring the shared lock;
            # otherwise a concurrent close can be overwritten with sealed=0.
            current, current_read_error = _read_wave_record_text(wave_md)
            if current is None:
                # Wave 1v0lw: same failed shape the broad handler below
                # produced, with the sanitized cause.
                return {
                    "persistence": "failed",
                    "projection": "pending",
                    "error": current_read_error,
                    "wave_id": canonical_wave,
                }
            status_match = server_impl._STATUS_PATTERN.search(current)
            sealed = bool(status_match and status_match.group(1) == "closed")
            if automatic and sealed:
                return {
                    "persistence": "durable",
                    "projection": "pending",
                    "reason": "closed_wave_requires_hard_boundary",
                    "wave_id": canonical_wave,
                }
            floor = context_efficiency.parse_checkpoint_block(current)
            context_efficiency.reconcile_checkpoint_authority(
                root,
                canonical_wave,
                floor or context_efficiency.empty_checkpoint(canonical_wave),
                sealed=sealed,
            )
            snapshot = context_efficiency.read_wave_snapshot(root, canonical_wave)
            if automatic and not snapshot.get("pending"):
                return {
                    "persistence": "durable",
                    "projection": "published",
                    "sealed": sealed,
                    "compacted": False,
                    "changed": False,
                    "already_current": True,
                }
            published = dict(snapshot)
            published["pending"] = False
            updated = context_efficiency.replace_checkpoint_block(current, published)
            exploration = server_impl._load_script("exploration_avoided")
            updated = exploration.replace_checkpoint_block(
                updated, root, canonical_wave
            )
            if updated != current:
                server_impl._atomic_replace_text(
                    wave_md, updated, "context-efficiency-projection"
                )
            marked = context_efficiency.mark_checkpoint_published(
                root,
                canonical_wave,
                published,
                expected_generation=int(snapshot.get("generation", 0)),
                seal=sealed,
            )
            compacted = (
                context_efficiency.compact_published_wave(
                    root,
                    canonical_wave,
                    expected_generation=int(snapshot.get("generation", 0)),
                )
                if marked and sealed
                else not sealed
            )
            focus_clear_error = ""
            if marked and sealed and compacted and handler is not None:
                if server_impl._focus_clear_write_needed(handler):
                    applied, clear_error = server_impl._attempt_focus_state(
                        handler, action="clear"
                    )
                    if not applied:
                        focus_clear_error = clear_error
        return {
            "persistence": "durable",
            "projection": "published" if marked and compacted else "pending",
            "sealed": sealed,
            "compacted": bool(marked and sealed and compacted),
            "changed": updated != current,
            **(
                {"focus_clear_error": focus_clear_error}
                if focus_clear_error
                else {}
            ),
        }
    except index_source_guard.RuntimeLockBusy as exc:
        return {
            "persistence": "durable", "projection": "pending",
            "reason": "index_source_busy", "error": str(exc),
            "wave_id": canonical_wave,
        }
    except index_source_guard.RuntimeLockError as exc:
        return {
            "persistence": "durable", "projection": "pending",
            "reason": "index_source_unavailable", "error": str(exc),
            "wave_id": canonical_wave,
        }
    except ProjectPublicationUnavailable as exc:
        return {
            "persistence": "durable",
            "projection": "pending",
            "reason": "publication_lock_busy",
            "error": str(exc),
            "wave_id": canonical_wave,
        }
    except Exception as exc:
        return {
            "persistence": "failed",
            "projection": "pending",
            "error": f"{type(exc).__name__}: {exc}",
            "wave_id": canonical_wave,
        }


def _flush_context_efficiency(
    handler: "ImplHandler",
    wave_id: str,
    *,
    transfer_general: bool = False,
) -> tuple[dict[str, Any], context_efficiency.FlushResult | None]:
    """Persist one process buffer and project its durable wave checkpoint."""
    from wf_server import server_impl
    root = handler.root
    canonical_wave = wave_id
    try:
        wave_md = server_impl._find_wave_md(root, wave_id)
        if wave_md is None:
            return (
                {"persistence": "failed", "projection": "wave_not_found"},
                None,
            )
        canonical_wave = wave_md.parent.name
        floor = server_impl._wave_checkpoint_floor(root, canonical_wave)
        initial_markdown, initial_read_error = _read_wave_record_text(wave_md)
        if initial_markdown is None:
            # Wave 1v0lw: same failed shape the broad handler below produced,
            # with the sanitized cause.
            return (
                {
                    "persistence": "failed",
                    "projection": "pending",
                    "error": initial_read_error,
                    "wave_id": canonical_wave,
                },
                None,
            )
        status_match = server_impl._STATUS_PATTERN.search(initial_markdown)
        sealed = bool(status_match and status_match.group(1) == "closed")
        context_efficiency.reconcile_checkpoint_authority(
            root, canonical_wave, floor, sealed=sealed
        )
        # Wave 1t3ek (1t3el): boundary adoption stamps the stage the wave is
        # actually in — plan while planned/paused (create/prepare boundaries),
        # implement while OPEN, review once the ledger holds a delivery run.
        wave_status = status_match.group(1) if status_match else ""
        if wave_status in ("active", "implementing"):
            transfer_stage = context_efficiency._derive_open_wave_stage(wave_md.parent)
        else:
            transfer_stage = "plan"
        flushed = handler.telemetry.flush(
            root,
            transfer_general_to=canonical_wave if transfer_general else None,
            transfer_stage=transfer_stage,
            checkpoint_floors=None,
        )
        if not flushed.success:
            return (
                {
                    "persistence": "failed",
                    "projection": "pending",
                    "error": flushed.error,
                },
                flushed,
            )
        projection = _project_context_efficiency_wave(
            root, canonical_wave, handler=handler, automatic=False
        )
        return (
            {
                **projection,
                "credited_invocations": sorted(
                    f"{wave}:{invocation_id}"
                    for wave, invocation_id in flushed.credited_keys
                ),
                "duplicate_invocations": sorted(
                    f"{wave}:{invocation_id}"
                    for wave, invocation_id in flushed.duplicate_keys
                ),
            },
            flushed,
        )
    except Exception as exc:
        return (
            {
                "persistence": "failed",
                "projection": "pending",
                "error": f"{type(exc).__name__}: {exc}",
                "wave_id": canonical_wave,
            },
            None,
        )


def project_pending_context_efficiency(
    handler: "ImplHandler",
) -> dict[str, Any]:
    """Project every pending durable wave generation before reload/upgrade."""

    return project_pending_context_efficiency_root(
        handler.root, handler=handler, automatic=False
    )


def project_pending_context_efficiency_root(
    root: Path,
    *,
    handler: "ImplHandler | None" = None,
    automatic: bool = False,
    wave_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Project pending generations from a root-bound, accounting-neutral path.

    ``wave_ids`` limits an automatic trailing-edge pass to generations that
    have already satisfied its quiet period. Hard boundaries omit it and
    retain the all-pending barrier.
    """

    pending_state = context_efficiency.pending_wave_ids(root)
    if not pending_state.get("ok"):
        return {
            "ok": False,
            "projected": [],
            "failed_wave": None,
            "detail": {
                "persistence": "failed",
                "projection": "unavailable",
                "error": pending_state.get("error"),
                "authority_status": pending_state.get("status"),
            },
        }
    pending = list(pending_state.get("pending", []))
    if wave_ids is not None:
        selected = {str(wave_id) for wave_id in wave_ids}
        pending = [wave_id for wave_id in pending if wave_id in selected]
    projected: list[str] = []
    skipped_unknown: list[dict[str, Any]] = []
    automatic_failures: list[dict[str, Any]] = []
    for wave_id in pending:
        result = _project_context_efficiency_wave(
            root, wave_id, handler=handler, automatic=automatic
        )
        if result.get("projection") == "wave_not_found":
            # Hardening (1t59p, operator-approved): a phantom or misattributed
            # wave key must never brick reload/upgrade. Leave its rows pending,
            # surface it explicitly, and keep projecting the real waves.
            skipped_unknown.append({"wave_id": wave_id, "detail": result})
            continue
        if result.get("projection") != "published":
            if automatic:
                automatic_failures.append({"wave_id": wave_id, "detail": result})
                continue
            return {
                "ok": False,
                "projected": projected,
                "failed_wave": wave_id,
                "detail": result,
            }
        projected.append(wave_id)
    out: dict[str, Any] = {"ok": not automatic_failures, "projected": projected}
    if skipped_unknown:
        out["skipped_unknown_waves"] = skipped_unknown
    if automatic_failures:
        out["failed_wave"] = automatic_failures[0]["wave_id"]
        out["detail"] = automatic_failures[0]["detail"]
        out["automatic_failures"] = automatic_failures
    return out


def _context_efficiency_state(
    handler: "ImplHandler", wave_ids: Iterable[str]
) -> dict[str, Any]:
    """Read-only durable + current-process overlay; never creates the store."""
    from wf_server import server_impl
    canonical_waves = sorted({wave for wave in wave_ids if wave})
    health = context_efficiency.read_store_health(handler.root)
    if health["status"] == "failed":
        durable = {
            wave_id: server_impl._wave_checkpoint_floor(handler.root, wave_id)
            for wave_id in canonical_waves
        }
        durable_general = {
            "calls": 0,
            "request_debit": 0,
            "response_debit": 0,
            "source_credit": 0,
            "estimated_tokens_saved": 0,
        }
        durable_source = "published_checkpoint_floor"
        durable_general_available = False
    else:
        durable = {
            wave_id: context_efficiency.read_wave_snapshot(
                handler.root, wave_id
            )
            for wave_id in canonical_waves
        }
        durable_general = context_efficiency.read_general_totals(handler.root)
        durable_source = (
            "sidecar"
            if health["status"] in {"healthy", "accounting_gap"}
            else "empty_store"
        )
        durable_general_available = True
    producer_id: str | None = None
    try:
        buffered = handler.telemetry.buffered_snapshot()
        producer_id = buffered.pop("producer_id", None)
    except Exception:
        buffered = {
            "focus": None,
            "retrieval": {},
            "workflow_credit_intents": [],
            "general_note": context_efficiency.GENERAL_ASSOCIATION_NOTE,
            "available": False,
            "persistence": "failed",
        }
    if health["status"] in {"healthy", "accounting_gap"}:
        durable_general = context_efficiency.read_general_totals(
            handler.root, producer_id
        )
    return {
        "durable_waves": durable,
        "current_process": buffered,
        "durable_general": durable_general,
        "durable_source": durable_source,
        "durable_general_available": durable_general_available,
        "persistence_health": health,
        "visibility": (
            "SQLite is the live write-through authority. Process focus and "
            "producer-scoped general attribution remain isolated; wave.md is "
            "the last published checkpoint. Accounting gaps suppress a "
            "positive headline."
        ),
    }


def wf_context_efficiency_eval_response(
    root: Path,
    wave_id: str,
    phase_id: str,
    *,
    mode: str,
    report_path: str = "",
    applicability: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Register or attach one phase-scoped paired evaluation."""
    from wf_server import server_impl
    mode_s = str(mode or "").strip().lower()
    try:
        if mode_s == "scaffold":
            # Wave 1t72b (1t72a): write a pair-artifact skeleton whose shape is
            # derived from the scorer's own canonical constants — no parallel
            # schema. Placeholders (negative tokens, empty ids, incomplete
            # arms) FAIL score_pairs until genuinely filled, so a scaffold can
            # never accidentally qualify.
            applicability = context_efficiency.registered_applicability(
                root, wave_id, phase_id
            )
            if applicability is None:
                raise ValueError(
                    "no applicability registered for this (wave, phase) — run "
                    "mode='register' first, then mode='scaffold'"
                )
            candidate = Path(report_path)
            if not candidate.is_absolute():
                candidate = root / candidate
            resolved_root = root.resolve(strict=True)
            target = candidate.resolve()
            if not target.is_relative_to(resolved_root):
                raise ValueError("report_path must be a contained path")
            if target.exists():
                raise ValueError("report_path already exists; refusing to overwrite")
            scorer = server_impl._load_script("score_context_efficiency_pairs")
            placeholder_arm = {}
            for key in scorer.ARM_KEYS:
                if key == "quality":
                    placeholder_arm[key] = {k: -1 for k in scorer.QUALITY_KEYS}
                elif key == "completed":
                    placeholder_arm[key] = False
                elif key == "usage_source":
                    placeholder_arm[key] = "provider_reported"
                elif key == "quality_scored_blind":
                    placeholder_arm[key] = True
                else:
                    placeholder_arm[key] = -1
            skeleton = {
                "schema_version": 1,
                "evaluation_id": "",
                "supersedes_evaluation_id": None,
                "applicability": applicability,
                "pairs": [
                    {
                        key: (
                            "" if key == "pair_id"
                            else 0 if key == "assisted_direct_net"
                            else dict(placeholder_arm)
                        )
                        for key in scorer.PAIR_KEYS
                    }
                    for _ in range(scorer.MIN_QUALIFYING_PAIRS)
                ],
            }
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(skeleton, indent=1) + "\n", encoding="utf-8"
            )
            result = {
                "scaffolded": True,
                "path": str(target.relative_to(resolved_root)),
                "pairs": scorer.MIN_QUALIFYING_PAIRS,
                "protocol": "docs/references/context-efficiency-paired-evaluation.md",
            }
        elif mode_s == "register":
            result = context_efficiency.attach_evaluation(
                root,
                wave_id,
                phase_id,
                mode=mode_s,
                applicability=applicability,
            )
        elif mode_s in {"attach", "replace"}:
            candidate = Path(report_path)
            if not candidate.is_absolute():
                candidate = root / candidate
            resolved_root = root.resolve(strict=True)
            report_file = candidate.resolve(strict=True)
            if (
                not report_file.is_relative_to(resolved_root)
                or not report_file.is_file()
            ):
                raise ValueError("report_path must be a contained file")
            payload = json.loads(report_file.read_text(encoding="utf-8"))
            scorer = server_impl._load_script("score_context_efficiency_pairs")
            report = scorer.score_pairs(payload)
            result = context_efficiency.attach_evaluation(
                root,
                wave_id,
                phase_id,
                mode=mode_s,
                report=report,
            )
            result["scorer"] = {
                "qualifying_pairs": int(report["qualifying_pairs"]),
                "quality_gate_passed": bool(report["quality_gate_passed"]),
                "matched_pair_residual": int(report["matched_pair_residual"]),
            }
        elif mode_s == "revoke":
            result = context_efficiency.attach_evaluation(
                root, wave_id, phase_id, mode=mode_s
            )
        else:
            raise ValueError(
                "mode must be register, scaffold, attach, replace, or revoke"
            )
        return server_impl._response(
            "ok",
            result,
            next_tools=["wf_current_wave"],
            usage=(
                "wf_context_efficiency_eval("
                f"wave_id={wave_id!r}, phase_id={phase_id!r}, mode={mode_s!r})"
            ),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return server_impl._response(
            "error",
            {
                "failed": True,
                "stage": "context_efficiency_evaluation",
                "error": f"{type(exc).__name__}: {exc}",
            },
            diagnostics=[
                {
                    "code": "context_efficiency_evaluation_invalid",
                    "message": str(exc),
                }
            ],
            usage=(
                "Register applicability first, generate a skeleton with "
                "mode='scaffold', fill it per "
                "docs/references/context-efficiency-paired-evaluation.md, then "
                "attach the contained pair artifact."
            ),
        )


def _state_sources_review_evidence(root: Path, result: Mapping[str, Any]) -> list[str]:
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("status") != "ok":
        return []
    # Wave 1t59p (1t6ow): the read-only list event conveys whole-ledger state
    # on every response (summary, chain heads, and approval currency derive
    # from every record, not just the filtered rows), so it credits the live
    # ledger file it read on the caller's behalf. The canonical source-proof
    # machinery keeps this once-only per (wave, phase, source, version).
    if data.get("event") == "list":
        value = data.get("events_path")
        return [value] if isinstance(value, str) and value else []
    if data.get("mode") != "create" or data.get("replayed"):
        return []
    paths = []
    for field in ("events_path", "path"):
        value = data.get(field)
        if isinstance(value, str) and value:
            paths.append(value)
    return paths


def _state_sources_memory_validate(root: Path, result: Mapping[str, Any]) -> list[str]:
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("status") != "ok":
        return []
    record = data.get("record")
    path = record.get("path") if isinstance(record, Mapping) else None
    return [str(path)] if path else []


def _state_sources_memory_propose(root: Path, result: Mapping[str, Any]) -> list[str]:
    """Best-effort: resolve the change docs the drafted records derive from."""
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("status") != "ok" or not data.get("written"):
        return []
    change_ids: set[str] = set()
    for item in data.get("written") or []:
        source = item.get("source_event") if isinstance(item, Mapping) else None
        if isinstance(source, str) and source.startswith("decision-log:"):
            parts = source.split(":", 2)
            if len(parts) >= 2 and parts[1]:
                change_ids.add(parts[1])
    paths: list[str] = []
    # Finding `commit-provenance-nested-wave-dir`: the shared discovery walk
    # (flat or nested) locates the wave folders; the change-id prefix glob is
    # kept, now applied inside each discovered folder.
    wave_dirs = record_paths.discover_wave_dirs(root)
    try:
        for change_id in sorted(change_ids):
            for wave_dir in wave_dirs:
                matches = sorted(wave_dir.glob(f"{change_id}*.md"))
                if matches:
                    paths.append(str(matches[0].relative_to(root)))
                    break
    except OSError:
        pass
    return paths


def _state_sources_get_change(root: Path, result: Mapping[str, Any]) -> list[str]:
    """Credit only change docs whose content the response conveys.

    Bulk rows cap content at 300 lines and carry a structural ``truncated``
    field; a truncated row conveys an excerpt, not the document, so it earns
    no whole-file credit. Listing digests (wf_current_wave, wf_list_waves,
    wf_list_plans, wf_map, memory_search, memory_brief) are deliberately
    absent from the extractor table for the same reason: their responses
    reference documents without conveying them, so deterministic whole-file
    credit would scale with corpus size rather than information delivered.
    Counterfactual read-avoidance for digests belongs to paired evaluations
    (wf_context_efficiency_eval), never the measured ledger.
    """
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("status") != "ok":
        return []
    paths: list[str] = []
    change = data.get("change")
    if isinstance(change, Mapping) and change.get("path") and change.get("content"):
        paths.append(str(change["path"]))
    for row in data.get("changes") or []:
        if (
            isinstance(row, Mapping)
            and row.get("path")
            and row.get("content")
            and not row.get("truncated")
        ):
            paths.append(str(row["path"]))
    return paths


def _state_sources_live_waves(root: Path, result: Mapping[str, Any]) -> list[str]:
    """Credit the LIVE working set a wave listing enumerates — never history.

    Whole-corpus credit was rejected (operator direction, 2026-07-20): a
    listing sweeps every wave record to answer a one-line question, so credit
    would scale with repository age. The bounded middle ground credits only
    rows the response marks non-closed — the waves an operator acting on this
    listing would actually open — so credit tracks work in flight, not the
    archive tail.
    """
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("status") != "ok":
        return []
    paths: list[str] = []
    for row in data.get("waves") or []:
        if (
            isinstance(row, Mapping)
            and row.get("path")
            and str(row.get("status") or "") not in ("closed", "")
        ):
            paths.append(str(row["path"]))
    return paths


def _state_sources_list_plans(root: Path, result: Mapping[str, Any]) -> list[str]:
    """Plan docs under docs/plans/ are pending work by construction — the
    listing enumerates the live backlog, bounded by work in flight."""
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("status") != "ok":
        return []
    return [
        str(row["path"])
        for row in data.get("plans") or []
        if isinstance(row, Mapping) and row.get("path")
    ]


def _state_sources_memory_views(*rows_keys: str):
    """Memory views credit the record files they surface (operator direction,
    2026-07-20): each surfaced row names a real record file an agent without
    the tool would have opened, and the response cap bounds the set."""
    def extract(root: Path, result: Mapping[str, Any]) -> list[str]:
        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        if result.get("status") != "ok":
            return []
        paths: list[str] = []
        for key in rows_keys:
            for row in data.get(key) or []:
                if isinstance(row, Mapping) and row.get("path"):
                    paths.append(str(row["path"]))
        return paths
    return extract


def _state_sources_map(root: Path, result: Mapping[str, Any]) -> list[str]:
    """wf_map resolves exactly one address; credit the one resolved document."""
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("status") != "ok":
        return []
    path = data.get("path")
    if isinstance(path, str) and path and data.get("file_exists"):
        return [path]
    return []


_STATE_SOURCE_EXTRACTORS: dict[str, Any] = {
    "wf_review_event": _state_sources_review_evidence,
    "memory_validate": _state_sources_memory_validate,
    "memory_propose": _state_sources_memory_propose,
    "wf_get_change": _state_sources_get_change,
    "wf_current_wave": _state_sources_live_waves,
    "wf_list_waves": _state_sources_live_waves,
    "wf_list_plans": _state_sources_list_plans,
    "wf_map": _state_sources_map,
    "memory_search": _state_sources_memory_views("records"),
    "memory_brief": _state_sources_memory_views("advisories", "community_scoped"),
}
