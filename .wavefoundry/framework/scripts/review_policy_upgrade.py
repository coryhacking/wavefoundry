"""Upgrade-time review-policy migration and in-flight wave reprojection."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import review_evidence
from review_policy import migrate_wave_review_policy, set_reprepare_marker
from review_policy_reconcile import CarrierEdit, apply_reconciliation, plan_reconciliation


@dataclass(frozen=True)
class WaveMigration:
    path: Path
    before: bytes
    marked: bytes
    projected: bytes


@dataclass(frozen=True)
class ReviewPolicyUpgradePlan:
    config_path: Path
    config_before: bytes | None
    config_after: bytes
    carriers: tuple[CarrierEdit, ...]
    waves: tuple[WaveMigration, ...]


def _atomic_replace(path: Path, body: bytes) -> None:
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _status(text: str) -> str:
    match = re.search(r"(?mi)^Status:\s*([^\n]+)$", text)
    return match.group(1).strip().lower() if match else ""


def plan_review_policy_upgrade(root: Path) -> ReviewPolicyUpgradePlan:
    """Read and validate the complete migration set before the first write."""

    config_path = root / "docs" / "workflow-config.json"
    try:
        config_before = config_path.read_bytes() if config_path.exists() else None
        config = (
            json.loads(config_before.decode("utf-8"))
            if config_before is not None
            else {}
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot preflight workflow config: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("cannot preflight workflow config: root must be an object")
    try:
        config["wave_review"] = migrate_wave_review_policy(config.get("wave_review"))
    except ValueError as exc:
        raise ValueError(f"cannot migrate wave_review policy: {exc}") from exc
    config_after = (json.dumps(config, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    carriers = plan_reconciliation(root)
    waves: list[WaveMigration] = []
    errors: list[str] = []
    waves_root = root / "docs" / "waves"
    for wave_md in sorted(waves_root.glob("*/wave.md")) if waves_root.is_dir() else ():
        try:
            before = wave_md.read_bytes()
            text = before.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{wave_md}: unreadable wave: {exc}")
            continue
        if _status(text) == "closed" or review_evidence.REVIEW_EVIDENCE_SOURCE_DECLARATION not in text:
            continue
        records, ledger_errors = review_evidence.read_review_event_ledger(wave_md)
        if ledger_errors:
            errors.extend(f"{wave_md}: {error}" for error in ledger_errors)
            continue
        try:
            marked_text = set_reprepare_marker(text, True)
            projected_text = review_evidence.render_review_evidence_projection(marked_text, records)
            keys = review_evidence.required_review_status_keys(
                root, projected_text, records, config_override=config
            )
            projected_text = review_evidence.render_review_status_projection(
                projected_text, records, keys
            )
        except ValueError as exc:
            errors.append(f"{wave_md}: cannot reproject: {exc}")
            continue
        waves.append(
            WaveMigration(
                wave_md,
                before,
                marked_text.encode("utf-8"),
                projected_text.encode("utf-8"),
            )
        )
    if errors:
        raise ValueError("review-policy upgrade preflight failed: " + "; ".join(errors))
    return ReviewPolicyUpgradePlan(
        config_path, config_before, config_after, carriers, tuple(waves)
    )


def apply_review_policy_upgrade(
    root: Path,
    plan: ReviewPolicyUpgradePlan,
    *,
    checkpoint: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    """Apply a preflighted plan in the required config/carrier/wave order."""

    report = checkpoint or (lambda _phase, _path: None)
    live_config = plan.config_path.read_bytes() if plan.config_path.exists() else None
    if live_config != plan.config_before:
        raise ValueError("workflow config changed after preflight; retry Upgrade")
    if plan.config_after != plan.config_before:
        plan.config_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_replace(plan.config_path, plan.config_after)
    report("review_policy_config", str(plan.config_path.relative_to(root)))

    changed_carriers = apply_reconciliation(root, plan.carriers)
    for relative in changed_carriers:
        report("review_policy_carrier", relative)

    migrated_waves: list[str] = []
    for migration in plan.waves:
        if migration.path.read_bytes() != migration.before:
            raise ValueError(f"{migration.path}: wave changed after preflight; retry Upgrade")
        _atomic_replace(migration.path, migration.marked)
        relative = migration.path.relative_to(root).as_posix()
        report("review_policy_marker", relative)
        _atomic_replace(migration.path, migration.projected)
        report("review_policy_projection", relative)
        migrated_waves.append(relative)
    return {
        "delivery_mode": json.loads(plan.config_after)["wave_review"]["delivery_mode"],
        "carriers_reconciled": list(changed_carriers),
        "waves_marked_for_reprepare": migrated_waves,
    }


__all__ = [
    "ReviewPolicyUpgradePlan", "WaveMigration", "apply_review_policy_upgrade",
    "plan_review_policy_upgrade",
]
