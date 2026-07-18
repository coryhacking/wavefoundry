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
- Separate and never summed: persisted in its own disposable sidecar, surfaced
  under its own label with a mandatory causal caveat, NEVER added to the measured
  `estimated_tokens_saved` total.
- Telemetry-only: a disposable, rebuildable JSON sidecar; a credit failure is
  swallowed and never perturbs the advisory surface or any other behavior.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Optional

sys.dont_write_bytecode = True

# Attribution factors, bounded WELL below 1.0 (the structural anti-inflation
# guarantee vs a count x constant gauge). A merely-surfaced advisory is
# discounted harder than an explicitly-cited one because surface is not use.
ATTRIBUTION_BASE_SURFACED = 0.5
ATTRIBUTION_BASE_CITED = 0.75
# A record that surfaced without a direct target/context match is a weak signal.
WEAK_MATCH_CONFIDENCE = 0.25

CAVEAT = (
    "estimated: a surfaced (or cited) advisory does not prove a re-exploration "
    "was avoided; this is grounded in the measured cost of the original "
    "exploration, scaled by a bounded semantic-match attribution, and is NEVER "
    "summed into the measured Context Efficiency token total."
)

_SIDECAR_REL = Path(".wavefoundry") / "index" / "exploration-avoided.json"


def _sidecar_path(root: Path) -> Path:
    return root / _SIDECAR_REL


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
        add = int(cost * attribution_factor(item.get("match_confidence", 0.0), cited=cited))
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


def _read_sidecar(root: Path) -> dict[str, Any]:
    try:
        data = json.loads(_sidecar_path(root).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"waves": {}}
    except (OSError, ValueError):
        return {"waves": {}}


def _write_sidecar(root: Path, data: dict[str, Any]) -> bool:
    path = _sidecar_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, sort_keys=True)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return True
    except OSError:
        return False


def read_wave(root: Path, wave_id: str) -> dict[str, Any]:
    """The current estimate for a wave (zeros when absent). Read-only."""
    entry = _read_sidecar(root).get("waves", {}).get(str(wave_id))
    out = {"estimated_exploration_avoided": 0, "surfaced_events": 0,
           "cited_events": 0, "credited_records": 0}
    if isinstance(entry, dict):
        for key in out:
            try:
                out[key] = int(entry.get(key, 0))
            except (TypeError, ValueError):
                pass
    return out


def credit_surface(
    root: Path, wave_id: str, surfaced: Iterable[dict[str, Any]], *, cited: bool = False
) -> Optional[dict[str, Any]]:
    """Accumulate credit for an advisory-surface event — FAIL-ISOLATED.

    Returns the wave's updated totals, or ``None`` on any failure or when there
    is nothing to credit (no wave id, no positive-cost record). NEVER raises: a
    telemetry failure must never perturb the advisory surface (AC-6 invariance).
    """
    try:
        wave_id = str(wave_id or "").strip()
        if not wave_id:
            return None
        delta = estimate_credit(surfaced, cited=cited)
        if delta["credit"] <= 0:
            return None
        data = _read_sidecar(root)
        waves = data.setdefault("waves", {})
        entry = waves.get(wave_id) if isinstance(waves.get(wave_id), dict) else {}
        merged = {
            "estimated_exploration_avoided":
                int(entry.get("estimated_exploration_avoided", 0)) + delta["credit"],
            "surfaced_events": int(entry.get("surfaced_events", 0)) + delta["surfaced_events"],
            "cited_events": int(entry.get("cited_events", 0)) + delta["cited_events"],
            "credited_records": int(entry.get("credited_records", 0)) + delta["credited_records"],
        }
        waves[wave_id] = merged
        if not _write_sidecar(root, data):
            return None
        return merged
    except Exception:
        return None
