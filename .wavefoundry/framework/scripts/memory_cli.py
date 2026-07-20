#!/usr/bin/env python3
"""Terminal fallback for historical memory backfill and focused validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import server_impl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backfill", "validate"))
    parser.add_argument("--root", default=".")
    parser.add_argument("--mode", default="create", choices=("dry_run", "create"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--entry-path", default="manual")
    parser.add_argument("--memory-id", default="")
    parser.add_argument(
        "--verdict", choices=("promote", "retain", "reject", "rewrite"), default=""
    )
    parser.add_argument("--action-delta", default="")
    parser.add_argument("--rationale", default="")
    parser.add_argument("--canonical-overlap", default="none")
    parser.add_argument("--evidence-verified", action="store_true")
    parser.add_argument("--current-target-verified", action="store_true")
    parser.add_argument("--rewrite-kind", default="")
    parser.add_argument("--rewrite-title", default="")
    parser.add_argument("--rewrite-summary", default="")
    parser.add_argument("--rewrite-evidence", action="append", default=[])
    parser.add_argument("--rewrite-target", action="append", default=[])
    parser.add_argument("--rewrite-confidence", type=float, default=0.8)
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if args.action == "backfill":
        response = server_impl.wave_memory_backfill_response(
            root,
            mode=args.mode,
            limit=args.limit,
            entry_path=args.entry_path,
        )
    else:
        response = server_impl.wave_memory_validate_response(
            root,
            args.memory_id,
            args.verdict,
            args.action_delta,
            args.rationale,
            args.evidence_verified,
            args.current_target_verified,
            args.canonical_overlap,
            rewrite_kind=args.rewrite_kind,
            rewrite_title=args.rewrite_title,
            rewrite_summary=args.rewrite_summary,
            rewrite_evidence=args.rewrite_evidence,
            rewrite_targets=args.rewrite_target,
            rewrite_confidence=args.rewrite_confidence,
        )
    print(json.dumps(response, indent=2, sort_keys=True))
    if response.get("status") == "error":
        return 1
    state = response.get("data", {}).get("state")
    return 4 if state == "awaiting_validation" else 0


if __name__ == "__main__":
    raise SystemExit(main())
