#!/usr/bin/env python3
"""Estimated exploration-avoided: a SEPARATE, grounded, labeled wave metric.

Wave 1svuk. The 1stwj `## Context Efficiency` telemetry measures per-call
retrieval token savings honestly (returned bytes vs whole-file bytes of cited
sources). It deliberately EXCLUDES the memory layer's biggest real value: a
surfaced memory advisory that prevents a costly re-exploration. That value is a
counterfactual and cannot be folded into the measured number without rebuilding
an inflatable gauge. This module keeps it visible as a SEPARATE, explicitly
labeled ESTIMATE that is honest because it is grounded in a MEASURED quantity:
the real cost of the exploration that produced the surfaced record (its
`source_exploration_cost`, stamped at record creation), discounted by a bounded
attribution factor and credited ONLY on an actual advisory-surface event.

Invariants:
- Grounded, never a constant: the unit is the record's measured source cost.
- Event-triggered: credited only when an advisory is actually surfaced, never by
  a record's existence, so it cannot inflate with corpus size.
- Bounded attribution: credit = source_cost x ATTRIBUTION_BASE x match_confidence,
  ATTRIBUTION_BASE well below 1.0; a merely-surfaced advisory is discounted
  harder than an explicitly-cited one because surface is not proof of use.
- Phase-scoped idempotence: the same advisory, origin, and target context is
  counted once in a receiving phase, while a later phase may earn new credit.
- Origin-bounded: all memories produced by one source wave share one receiving-
  phase budget, preventing record multiplication from multiplying the estimate.
- Separate and never summed: persisted in the context-efficiency SQLite
  authority and projected under its own label, NEVER added to the measured
  `estimated_tokens_saved` total.
- Telemetry-only: a credit failure is swallowed and never perturbs the advisory
  surface or any other behavior.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Optional

import context_efficiency

sys.dont_write_bytecode = True

# Attribution factors, bounded WELL below 1.0 (the structural anti-inflation
# guarantee vs a count x constant gauge). A merely-surfaced advisory is
# discounted harder than an explicitly-cited one because surface is not use.
ATTRIBUTION_BASE_SURFACED = 0.5
ATTRIBUTION_BASE_CITED = 0.75
CAVEAT = (
    "estimated: a surfaced (or cited) advisory does not prove a re-exploration "
    "was avoided; this is grounded in the measured cost of the original "
    "exploration, scaled by a bounded exact-match attribution, and is NEVER "
    "summed into the measured Context Efficiency token total."
)

MARKER_BEGIN = "<!-- wave:exploration-avoided begin -->"
MARKER_END = "<!-- wave:exploration-avoided end -->"


def attribution_factor(match_confidence: float, *, cited: bool = False) -> float:
    """The bounded factor: base (surfaced|cited) x clamped match confidence."""
    base = ATTRIBUTION_BASE_CITED if cited else ATTRIBUTION_BASE_SURFACED
    conf = min(1.0, max(0.0, float(match_confidence)))
    return base * conf


def estimate_credit(
    surfaced: Iterable[dict[str, Any]], *, cited: bool = False
) -> dict[str, Any]:
    """Compute the credit for a set of surfaced records — PURE, no I/O.

    Each ``surfaced`` item is ``{source_exploration_cost, match_confidence}``.
    Only records carrying a POSITIVE measured source cost contribute (a record
    with no measured cost grounds nothing). Returns
    ``{credit, surfaced_events, cited_events, credited_records}``.
    """
    credit = 0
    credited = 0
    for item in surfaced:
        try:
            cost = int(item.get("source_exploration_cost"))
        except (TypeError, ValueError):
            continue
        if cost <= 0:
            continue
        confidence = float(item.get("match_confidence", 0.0))
        if confidence != 1.0:
            continue
        add = int(cost * attribution_factor(confidence, cited=cited))
        if add <= 0:
            continue
        credit += add
        credited += 1
    return {
        "credit": credit,
        "surfaced_events": 0 if cited else credited,
        "cited_events": credited if cited else 0,
        "credited_records": credited,
    }


def _event_key(
    wave_id: str,
    stage: str,
    phase_id: str,
    origin_id: str,
    memory_id: str,
    context_key: str,
    cited: bool,
) -> str:
    core = json.dumps(
        [wave_id, stage, phase_id, origin_id, memory_id, context_key, bool(cited)],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(core.encode("utf-8")).hexdigest()


def current_phase(root: Path, wave_id: str) -> tuple[str, str]:
    """Return the newest durable receiving phase, with a stable empty-store fallback."""
    conn = context_efficiency._open_read_store(root)
    if conn is None:
        return "implement", "implement-0"
    try:
        row = conn.execute(
            "SELECT stage,phase_id FROM phase_state WHERE wave_id=? "
            "ORDER BY ordinal DESC LIMIT 1",
            (str(wave_id),),
        ).fetchone()
        if row:
            return str(row[0]), str(row[1])
    except sqlite3.Error:
        pass
    finally:
        conn.close()
    return "implement", "implement-0"


def read_wave(root: Path, wave_id: str) -> dict[str, Any]:
    """The current SQLite-backed estimate for a wave (zeros when absent)."""
    out = {"estimated_exploration_avoided": 0, "surfaced_events": 0,
           "cited_events": 0, "credited_records": 0}
    conn = context_efficiency._open_read_store(root)
    if conn is None:
        return out
    try:
        if not context_efficiency._table_exists(conn, "exploration_credit_event"):
            return out
        row = conn.execute(
            "SELECT COALESCE(SUM(credit),0),"
            "COALESCE(SUM(CASE WHEN cited=0 THEN 1 ELSE 0 END),0),"
            "COALESCE(SUM(CASE WHEN cited=1 THEN 1 ELSE 0 END),0),"
            "COUNT(DISTINCT CASE WHEN credit>0 THEN memory_id END) "
            "FROM exploration_credit_event WHERE wave_id=?",
            (str(wave_id),),
        ).fetchone()
        if row:
            out = {
                "estimated_exploration_avoided": int(row[0]),
                "surfaced_events": int(row[1]),
                "cited_events": int(row[2]),
                "credited_records": int(row[3]),
            }
    except sqlite3.Error:
        pass
    finally:
        conn.close()
    return out


def credit_surface(
    root: Path,
    wave_id: str,
    surfaced: Iterable[dict[str, Any]],
    *,
    cited: bool = False,
    stage: str = "",
    phase_id: str = "",
    context_key: str = "",
) -> Optional[dict[str, Any]]:
    """Transactionally credit advisory events once per receiving phase/context.

    Returns the wave's updated totals, or ``None`` on any failure or when there
    is nothing to credit (no wave id, no positive-cost record). NEVER raises: a
    telemetry failure must never perturb the advisory surface (AC-6 invariance).
    """
    try:
        wave_id = str(wave_id or "").strip()
        if not wave_id:
            return None
        items = list(surfaced)
        if not items:
            return None
        if not stage or not phase_id:
            current_stage, current_phase_id = current_phase(root, wave_id)
            stage = stage or current_stage
            phase_id = phase_id or current_phase_id
        context_key = str(context_key or "unspecified")
        conn = context_efficiency._open_write_store(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            inserted = 0
            for index, item in enumerate(items):
                try:
                    cost = int(item.get("source_exploration_cost"))
                    confidence = float(item.get("match_confidence", 0.0))
                except (TypeError, ValueError):
                    continue
                if cost <= 0 or confidence != 1.0:
                    continue
                memory_id = str(item.get("memory_id") or f"anonymous-{index}")
                origin_id = str(item.get("source_origin") or memory_id)
                key = _event_key(
                    wave_id, stage, phase_id, origin_id, memory_id, context_key, cited
                )
                if conn.execute(
                    "SELECT 1 FROM exploration_credit_event WHERE event_key=?", (key,)
                ).fetchone():
                    continue
                already = int(
                    conn.execute(
                        "SELECT COALESCE(SUM(credit),0) FROM exploration_credit_event "
                        "WHERE wave_id=? AND phase_id=? AND origin_id=?",
                        (wave_id, phase_id, origin_id),
                    ).fetchone()[0]
                )
                prior_cost_row = conn.execute(
                    "SELECT MIN(source_cost) FROM exploration_credit_event "
                    "WHERE wave_id=? AND phase_id=? AND origin_id=?",
                    (wave_id, phase_id, origin_id),
                ).fetchone()
                origin_cost = (
                    min(cost, int(prior_cost_row[0]))
                    if prior_cost_row and prior_cost_row[0] is not None
                    else cost
                )
                prior_cited = bool(
                    conn.execute(
                        "SELECT 1 FROM exploration_credit_event WHERE wave_id=? "
                        "AND phase_id=? AND origin_id=? AND cited=1 LIMIT 1",
                        (wave_id, phase_id, origin_id),
                    ).fetchone()
                )
                budget_factor = (
                    ATTRIBUTION_BASE_CITED if cited or prior_cited
                    else ATTRIBUTION_BASE_SURFACED
                )
                budget = int(origin_cost * budget_factor)
                raw = int(origin_cost * attribution_factor(confidence, cited=cited))
                credit = max(0, min(raw, budget - already))
                conn.execute(
                    "INSERT INTO exploration_credit_event("
                    "event_key,wave_id,phase_id,stage,origin_id,memory_id,"
                    "context_key,cited,source_cost,match_confidence,credit,created_at"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        key, wave_id, phase_id, stage, origin_id, memory_id,
                        context_key, int(cited), cost, confidence, credit, time.time(),
                    ),
                )
                inserted += 1
            if not inserted:
                conn.rollback()
                return None
            conn.execute(
                "INSERT INTO wave_state(wave_id,generation,pending,measurement_status)"
                " VALUES(?,1,1,'healthy') ON CONFLICT(wave_id) DO UPDATE SET "
                "generation=wave_state.generation+1,pending=1",
                (wave_id,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return read_wave(root, wave_id)
    except Exception:
        return None


def render_checkpoint_block(root: Path, wave_id: str) -> str:
    """Render the human projection; the SQLite ledger remains authoritative."""
    totals = read_wave(root, wave_id)
    state = json.dumps(totals, sort_keys=True, separators=(",", ":"))
    return "\n".join([
        "## Estimated Exploration Avoided",
        "",
        MARKER_BEGIN,
        "",
        "This is a bounded estimate from exact-match memory advisories. It is not "
        "added to measured Context Efficiency.",
        "",
        "| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |",
        "| ---: | ---: | ---: | ---: |",
        f"| {totals['surfaced_events']} | {totals['cited_events']} | "
        f"{totals['credited_records']} | {totals['estimated_exploration_avoided']} |",
        "",
        CAVEAT,
        "",
        f"<!-- wave:exploration-avoided-state {state} -->",
        MARKER_END,
        "",
    ])


def replace_checkpoint_block(markdown: str, root: Path, wave_id: str) -> str:
    """Replace or append the owned projection block."""
    block = render_checkpoint_block(root, wave_id)
    start = markdown.find(MARKER_BEGIN)
    end = markdown.find(MARKER_END)
    if start >= 0 and end >= start:
        heading = markdown.rfind("## Estimated Exploration Avoided", 0, start)
        replace_start = heading if heading >= 0 else start
        return markdown[:replace_start].rstrip() + "\n\n" + block + markdown[
            end + len(MARKER_END):
        ].lstrip("\n")
    return markdown.rstrip() + "\n\n" + block
