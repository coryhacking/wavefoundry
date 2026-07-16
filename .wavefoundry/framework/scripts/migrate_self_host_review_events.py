#!/usr/bin/env python3
"""One-time pre-release self-host migration from inline review JSONL.

This command is intentionally not called by setup, install, upgrade, or the
runtime server.  It migrates only the adopted waves in the explicitly targeted
Wavefoundry source repository, writes a resumable census manifest, and always
migrates the named in-flight wave last.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from review_evidence import (
    ADOPTION_LEDGER_REL,
    PROTOCOL_VERSION,
    REVIEW_EVIDENCE_SOURCE,
    REVIEW_EVIDENCE_SOURCE_DECLARATION,
    canonical_review_events_bytes,
    render_review_evidence_projection,
    review_event_path,
    review_event_prefix_proof,
    review_event_write_lock,
    validate_adopted_protocol_state,
    validate_external_review_evidence,
    validate_review_evidence,
)


MANIFEST_REL = Path("docs/waves/review-evidence-migration.json")


def _atomic_bytes(path: Path, payload: bytes, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{label}.tmp")
    try:
        temp.write_bytes(payload)
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def _atomic_json(path: Path, value: Any, label: str) -> None:
    _atomic_bytes(
        path,
        (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        label,
    )


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _find_wave(root: Path, wave_key: str) -> Path:
    wave_md = root / "docs" / "waves" / wave_key / "wave.md"
    if not wave_md.is_file():
        raise ValueError(f"adopted wave `{wave_key}` has no wave.md")
    return wave_md


def _externalize_wave_text(text: str, records: tuple[dict[str, Any], ...]) -> str:
    marker = re.compile(r"(?m)^review-evidence-protocol:\s*`?1`?\s*$\n?")
    if len(marker.findall(text)) != 1:
        raise ValueError("legacy wave must contain exactly one protocol marker")
    external = marker.sub(REVIEW_EVIDENCE_SOURCE_DECLARATION + "\n", text, count=1)
    return render_review_evidence_projection(external, records)


def migrate_self_host_review_events(
    root: Path, *, in_flight_wave: str
) -> dict[str, Any]:
    """Migrate exactly the retained adopted-wave census, resumably."""

    root = root.resolve()
    adoption_path = root / ADOPTION_LEDGER_REL
    manifest_path = root / MANIFEST_REL
    with review_event_write_lock(root):
        adoption = _load_json(adoption_path)
        if adoption.get("protocol_version") != PROTOCOL_VERSION or not isinstance(
            adoption.get("waves"), dict
        ):
            raise ValueError("review evidence adoption ledger has an unsupported shape/version")
        adopted_keys = sorted(adoption["waves"])
        if in_flight_wave not in adopted_keys:
            raise ValueError("the named in-flight wave is not present in the adopted census")
        ordered = [key for key in adopted_keys if key != in_flight_wave] + [in_flight_wave]

        if manifest_path.exists():
            manifest = _load_json(manifest_path)
            if manifest.get("adopted_wave_keys") != ordered:
                raise ValueError("migration census changed after the manifest was created")
        else:
            entries: dict[str, Any] = {}
            for key in ordered:
                state = adoption["waves"][key]
                records = state.get("records") if isinstance(state, dict) else None
                if not isinstance(records, list):
                    raise ValueError(f"adopted wave `{key}` is not in the legacy inline shape")
                proof = review_event_prefix_proof(records)
                entries[key] = {
                    "source_record_count": proof["record_count"],
                    "source_prefix_sha256": proof["prefix_sha256"],
                    "migration_state": "pending",
                    "target_record_count": None,
                    "target_prefix_sha256": None,
                }
            manifest = {
                "schema": 1,
                "in_flight_wave_last": in_flight_wave,
                "adopted_wave_keys": ordered,
                "waves": entries,
            }
            _atomic_json(manifest_path, manifest, "migration-census")

        for key in ordered:
            entry = manifest["waves"][key]
            wave_md = _find_wave(root, key)
            state = adoption["waves"][key]
            if entry.get("migration_state") == "complete":
                result = validate_external_review_evidence(wave_md)
                if result.errors or validate_adopted_protocol_state(root, key, wave_md):
                    raise ValueError(f"completed migration proof for `{key}` no longer validates")
                continue

            if isinstance(state, dict) and isinstance(state.get("records"), list):
                current_text = wave_md.read_text(encoding="utf-8")
                if REVIEW_EVIDENCE_SOURCE_DECLARATION in current_text:
                    resumed = validate_external_review_evidence(wave_md)
                    if resumed.errors:
                        raise ValueError(
                            f"partially externalized wave `{key}` is invalid: "
                            + "; ".join(resumed.errors)
                        )
                    records = tuple(dict(row) for row in resumed.records)
                else:
                    legacy = validate_review_evidence(current_text)
                    if legacy.errors:
                        raise ValueError(f"legacy wave `{key}` is invalid: {'; '.join(legacy.errors)}")
                    records = tuple(dict(row) for row in legacy.records)
                if list(records) != state["records"]:
                    raise ValueError(f"legacy wave `{key}` does not equal its adopted record history")
                proof = review_event_prefix_proof(records)
                if (
                    proof["record_count"] != entry["source_record_count"]
                    or proof["prefix_sha256"] != entry["source_prefix_sha256"]
                ):
                    raise ValueError(f"legacy source proof changed for `{key}`")
                if REVIEW_EVIDENCE_SOURCE_DECLARATION not in current_text:
                    _atomic_bytes(
                        review_event_path(wave_md),
                        canonical_review_events_bytes(records),
                        "migration-events",
                    )
                    _atomic_bytes(
                        wave_md,
                        _externalize_wave_text(current_text, records).encode("utf-8"),
                        "migration-wave",
                    )
            else:
                # Resume after the authority/proof commit but before manifest update.
                result = validate_external_review_evidence(wave_md)
                if result.errors:
                    raise ValueError(f"partially migrated wave `{key}` is invalid")
                records = tuple(result.records)
                proof = review_event_prefix_proof(records)
                if (
                    proof["record_count"] != entry["source_record_count"]
                    or proof["prefix_sha256"] != entry["source_prefix_sha256"]
                ):
                    raise ValueError(f"partially migrated target proof changed for `{key}`")

            proof = review_event_prefix_proof(records)
            adoption["waves"][key] = {
                "version": PROTOCOL_VERSION,
                "source": REVIEW_EVIDENCE_SOURCE,
                **proof,
            }
            _atomic_json(adoption_path, adoption, "migration-adoption")
            retained_errors = validate_adopted_protocol_state(root, key, wave_md)
            reread = validate_external_review_evidence(wave_md)
            if reread.errors or retained_errors or tuple(reread.records) != records:
                raise ValueError(f"external reread failed for `{key}`")
            entry.update(
                migration_state="complete",
                target_record_count=proof["record_count"],
                target_prefix_sha256=proof["prefix_sha256"],
            )
            _atomic_json(manifest_path, manifest, "migration-progress")

        return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--in-flight-wave", required=True)
    args = parser.parse_args(argv)
    migrate_self_host_review_events(
        Path(args.root), in_flight_wave=args.in_flight_wave
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
