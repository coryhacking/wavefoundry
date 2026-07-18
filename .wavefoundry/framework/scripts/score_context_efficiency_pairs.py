#!/usr/bin/env python3
"""Score bounded, quality-gated context-efficiency paired evaluations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

QUALITY_KEYS = ("correctness", "completeness", "evidence", "maintainability")
APPLICABILITY_KEYS = (
    "wave_id",
    "phase_id",
    "stage",
    "task_spec_digest",
    "repository_snapshot_digest",
    "model_id",
    "model_version",
    "tool_configuration_digest",
)
MIN_QUALIFYING_PAIRS = 5


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _validate_quality(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(QUALITY_KEYS):
        raise ValueError(f"{label} must contain the four quality dimensions")
    quality: dict[str, int] = {}
    for key in QUALITY_KEYS:
        score = value[key]
        if type(score) is not int or not 0 <= score <= 4:
            raise ValueError(f"{label}.{key} must be an integer from 0 to 4")
        quality[key] = score
    return quality


def _validate_arm(value: Any, label: str) -> dict[str, Any]:
    required = {
        "input_tokens",
        "output_tokens",
        "tool_calls",
        "completed",
        "usage_source",
        "quality_scored_blind",
        "quality",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError(f"{label} has non-canonical fields")
    if type(value["completed"]) is not bool:
        raise ValueError(f"{label}.completed must be a boolean")
    if value["usage_source"] != "provider_reported":
        raise ValueError(f"{label}.usage_source must be provider_reported")
    if value["quality_scored_blind"] is not True:
        raise ValueError(f"{label}.quality_scored_blind must be true")
    return {
        "input_tokens": _nonnegative_int(value["input_tokens"], f"{label}.input_tokens"),
        "output_tokens": _nonnegative_int(value["output_tokens"], f"{label}.output_tokens"),
        "tool_calls": _nonnegative_int(value["tool_calls"], f"{label}.tool_calls"),
        "completed": value["completed"],
        "usage_source": "provider_reported",
        "quality_scored_blind": True,
        "quality": _validate_quality(value["quality"], f"{label}.quality"),
    }


def score_pairs(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and conservatively score one paired-evaluation artifact."""

    allowed = {
        "schema_version",
        "evaluation_id",
        "supersedes_evaluation_id",
        "applicability",
        "pairs",
    }
    if not isinstance(payload, Mapping) or not set(payload).issubset(allowed):
        raise ValueError("evaluation artifact has non-canonical fields")
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    evaluation_id = payload.get("evaluation_id")
    if not isinstance(evaluation_id, str) or not evaluation_id:
        raise ValueError("evaluation_id is required")
    supersedes = payload.get("supersedes_evaluation_id")
    if supersedes is not None and (
        not isinstance(supersedes, str) or not supersedes
    ):
        raise ValueError("supersedes_evaluation_id must be null or a non-empty string")
    applicability = payload.get("applicability")
    if not isinstance(applicability, Mapping) or set(applicability) != set(
        APPLICABILITY_KEYS
    ):
        raise ValueError("applicability key is incomplete")
    if any(
        not isinstance(applicability[key], str) or not applicability[key]
        for key in APPLICABILITY_KEYS
    ):
        raise ValueError("applicability values must be non-empty strings")
    pairs = payload.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("pairs must be a non-empty array")

    pair_ids: set[str] = set()
    qualifying: list[dict[str, Any]] = []
    all_deltas: list[dict[str, Any]] = []
    for index, raw in enumerate(pairs):
        if not isinstance(raw, Mapping) or set(raw) != {
            "pair_id",
            "baseline",
            "assisted",
            "assisted_direct_net",
        }:
            raise ValueError(f"pairs[{index}] has non-canonical fields")
        pair_id = raw.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id or pair_id in pair_ids:
            raise ValueError("pair_id values must be unique non-empty strings")
        pair_ids.add(pair_id)
        baseline = _validate_arm(raw["baseline"], f"pairs[{index}].baseline")
        assisted = _validate_arm(raw["assisted"], f"pairs[{index}].assisted")
        direct_net = raw["assisted_direct_net"]
        if type(direct_net) is not int:
            raise ValueError("assisted_direct_net must be an integer")
        quality_ok = all(
            assisted["quality"][key] >= baseline["quality"][key]
            for key in QUALITY_KEYS
        )
        total_delta = (
            baseline["input_tokens"]
            + baseline["output_tokens"]
            - assisted["input_tokens"]
            - assisted["output_tokens"]
        )
        residual = max(0, total_delta - direct_net)
        row = {
            "pair_id": pair_id,
            "quality_qualified": bool(
                baseline["completed"] and assisted["completed"] and quality_ok
            ),
            "input_delta": baseline["input_tokens"] - assisted["input_tokens"],
            "output_delta": baseline["output_tokens"] - assisted["output_tokens"],
            "tool_call_delta": baseline["tool_calls"] - assisted["tool_calls"],
            "total_delta": total_delta,
            "assisted_direct_net": direct_net,
            "residual": residual,
        }
        all_deltas.append(row)
        if row["quality_qualified"]:
            qualifying.append(row)
    matched = (
        min(row["residual"] for row in qualifying)
        if len(qualifying) >= MIN_QUALIFYING_PAIRS
        else 0
    )
    return {
        "schema_version": 1,
        "evaluation_id": evaluation_id,
        "supersedes_evaluation_id": payload.get("supersedes_evaluation_id"),
        "applicability": dict(applicability),
        "qualifying_pairs": len(qualifying),
        "required_qualifying_pairs": MIN_QUALIFYING_PAIRS,
        "quality_gate_passed": len(qualifying) >= MIN_QUALIFYING_PAIRS,
        "matched_pair_residual": int(matched),
        "pairs": all_deltas,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    print(json.dumps(score_pairs(payload), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
