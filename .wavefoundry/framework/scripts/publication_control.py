"""Typed publication registry and upgrade checkpoint guard."""

from __future__ import annotations

import json
import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_READ_ONLY_PREVIEW = contextvars.ContextVar("publication_read_only_preview", default=False)


def read_only_preview_active() -> bool:
    """Whether this call is a no-publication upgrade preview (not a sandbox)."""
    return _READ_ONLY_PREVIEW.get()


@contextmanager
def read_only_preview():
    token = _READ_ONLY_PREVIEW.set(True)
    try:
        yield
    finally:
        _READ_ONLY_PREVIEW.reset(token)


UPGRADE_CHECKPOINT_REL = Path(".wavefoundry/upgrade-in-progress.json")


@dataclass(frozen=True)
class PublicationWriter:
    tool_name: str
    producer: str
    contention_policy: str
    surface: str = "tool"


PUBLICATION_WRITER_REGISTRY = (
    PublicationWriter("wf_create_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_add_change", "lifecycle", "fail_fast"),
    PublicationWriter("wf_remove_change", "lifecycle", "fail_fast"),
    PublicationWriter("wf_prepare_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_pause_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_close_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_close_change", "lifecycle", "fail_fast"),
    PublicationWriter("wf_reopen_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_implement_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_set_handoff", "lifecycle", "fail_fast"),
    PublicationWriter("wf_open_gate", "lifecycle", "fail_fast"),
    PublicationWriter("wf_close_gate", "lifecycle", "fail_fast"),
    PublicationWriter("wf_new_feature", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_bug", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_enhancement", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_refactor", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_change", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_documentation", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_tech_debt", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_task", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_maintenance", "change_doc", "fail_fast"),
    PublicationWriter("wf_new_operations", "change_doc", "fail_fast"),
    PublicationWriter("wf_review_event", "review_event", "fail_fast"),
    PublicationWriter("wf_review_wave", "review_boundary", "fail_fast"),
    PublicationWriter("wf_context_efficiency_eval", "context_efficiency", "fail_fast"),
    PublicationWriter("memory_add", "memory", "fail_fast"),
    PublicationWriter("memory_propose", "memory", "fail_fast"),
    PublicationWriter("memory_reconcile", "memory", "fail_fast"),
    PublicationWriter("memory_consolidate", "memory", "fail_fast"),
    PublicationWriter("memory_purge", "memory", "fail_fast"),
    PublicationWriter("memory_backfill", "memory", "checkpoint_only"),
    PublicationWriter("memory_validate", "memory", "checkpoint_only"),
    PublicationWriter("wf_scan_secrets", "security_findings", "fail_fast"),
    PublicationWriter("wf_garden_docs", "docs_garden", "fail_fast"),
    PublicationWriter("wf_sync_surfaces", "surface_renderer", "fail_fast"),
    PublicationWriter("wf_techdocs_baseline", "techdocs_baseline", "fail_fast"),
    PublicationWriter("index_build", "index", "fail_fast"),
    PublicationWriter("index_optimize", "index", "fail_fast"),
    PublicationWriter(
        "retrieval_context_telemetry", "context_efficiency", "fail_fast",
        surface="native",
    ),
    PublicationWriter(
        "background_index_refresh", "index", "fail_fast", surface="native"
    ),
)

_BY_TOOL = {
    writer.tool_name: writer
    for writer in PUBLICATION_WRITER_REGISTRY
    if writer.surface == "tool"
}
_BY_NATIVE_PRODUCER = {
    writer.tool_name: writer
    for writer in PUBLICATION_WRITER_REGISTRY
    if writer.surface == "native"
}


def read_upgrade_checkpoint(root: Path) -> dict[str, Any] | None:
    path = root / UPGRADE_CHECKPOINT_REL
    try:
        from contained_files import read_contained_bytes
        value = json.loads(read_contained_bytes(root, path, max_bytes=256 * 1024, follow_links=False))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RecursionError, MemoryError):
        return {}
    # Presence is authoritative. Valid JSON of the wrong shape is corruption,
    # not evidence that no upgrade is running.
    return value if isinstance(value, dict) else {}


def preview_checkpoint_compatible(root: Path, installed_version: str) -> bool:
    """Bounded advisory shape/identity check, never recovery or pack authority."""
    from upgrade_protocol import SUPPORTED_RUNNER_PROTOCOLS
    import storage_identity

    checkpoint = read_upgrade_checkpoint(root)
    if not checkpoint or not isinstance(installed_version, str) or not installed_version:
        return False
    target = checkpoint.get("to_version")
    origin = checkpoint.get("from_version")
    if (not isinstance(target, str) or not target or
            (origin is not None and not isinstance(origin, str)) or
            installed_version not in {target, origin}):
        return False
    if checkpoint.get("entry_path", "upgrade") not in ("upgrade", "setup"):
        return False
    for key in ("runner_protocol", "pack_protocol"):
        protocol = checkpoint.get(key)
        if protocol is not None and (type(protocol) is not int or protocol not in SUPPORTED_RUNNER_PROTOCOLS):
            return False
    phase = checkpoint.get("current_phase") or checkpoint.get("failed_phase") or checkpoint.get("phase")
    # The existing resume reader accepts pre-protocol-2 memory checkpoints
    # without current_phase. Do not require newer producer fields there.
    if phase is None and isinstance(checkpoint.get("memory_backfill_run_id"), str) and checkpoint["memory_backfill_run_id"]:
        phase = "awaiting_memory_validation"
    if not isinstance(phase, str) or not phase.strip():
        return False
    # Setup has a top-level identity; upgrades may carry their identity in the
    # index handoff. Check supplied locators without demanding them of old runs.
    records = [checkpoint]
    if "index_guard_handoff" in checkpoint:
        handoff = checkpoint["index_guard_handoff"]
        if not isinstance(handoff, dict):
            return False
        records.append(handoff)
    try:
        observed = root.stat()
        live = {"device": observed.st_dev, "inode": observed.st_ino}
        for record in records:
            if "root" in record and not storage_identity.same_path(record["root"], root):
                return False
            if "root_identity" in record and not storage_identity.compare_identity(record["root_identity"], live)["matches"]:
                return False
    except (OSError, ValueError, TypeError, RuntimeError):
        return False
    return True


def publication_checkpoint_reason(
    root: Path,
    producer: str,
) -> str | None:
    """Guard a concrete writer boundary, including non-MCP/background writers."""

    if read_only_preview_active():
        return "upgrade_in_progress: read-only upgrade preview refuses publication"
    checkpoint = read_upgrade_checkpoint(root)
    if checkpoint is None:
        return None
    phase = str(
        checkpoint.get("current_phase")
        or checkpoint.get("failed_phase")
        or checkpoint.get("phase")
        or "corrupt_checkpoint"
    )
    return (
        f"upgrade_in_progress: publication by {producer} is blocked while "
        f"Upgrade is at {phase}; " + _checkpoint_recovery_tail(checkpoint, root)
    )


def _checkpoint_recovery_tail(checkpoint: dict[str, Any], root: Path | None = None) -> str:
    """Use the established checkpoint continuation without memory authority."""
    if checkpoint.get("entry_path") == "setup":
        action = checkpoint.get("action_required") or {}
        continuation = action.get("command") if isinstance(action, dict) else None
        return ("resume the recorded wf setup continuation: " + continuation if continuation
                else "rerun ordinary wf setup to finish installed-checkout reconciliation; retain the checkpoint and index")
    from sqlite_storage_migration import legacy_memory_pause, resume_guidance
    action = checkpoint.get("action_required")
    foreign = (isinstance(action, dict) and action.get("kind") in {"storage_migration", "index_guard_handoff"}
               or checkpoint.get("current_phase") == "storage_restart_required"
               or isinstance(checkpoint.get("index_guard_handoff"), dict) and not checkpoint["index_guard_handoff"].get("hosts_stopped_confirmed"))
    if foreign:
        recorded = action if isinstance(action, dict) else checkpoint.get("restart_action")
        command = recorded.get("command") if isinstance(recorded, dict) else None
        return "follow the retained storage/index-guard continuation after stopping its recorded hosts" + (": " + command if isinstance(command, str) else "")
    if legacy_memory_pause(checkpoint) or checkpoint.get("failed_phase") == "index_update":
        return "continue with wf_upgrade(phase='update_index'), then wf_upgrade(phase='cleanup'); confirm with index_health"
    guidance = resume_guidance(root, checkpoint) if root is not None else None
    return "retry or resume Upgrade to a terminal state" + (". " + guidance["guidance"] if guidance else "")


def publication_block_reason(root: Path, tool_name: str) -> str | None:
    """All registered writers fail closed under a retained upgrade checkpoint."""
    if _BY_TOOL.get(tool_name) is None:
        return None
    return publication_checkpoint_reason(root, tool_name)


def native_publication_block_reason(root: Path, producer: str) -> str | None:
    """Guard a registered non-tool/background publication boundary."""

    writer = _BY_NATIVE_PRODUCER.get(producer)
    if writer is None:
        raise ValueError(f"unregistered native publication producer: {producer}")
    return publication_checkpoint_reason(root, producer)


def registered_publication_tool_names() -> tuple[str, ...]:
    return tuple(
        writer.tool_name
        for writer in PUBLICATION_WRITER_REGISTRY
        if writer.surface == "tool"
    )


def registered_native_publication_producers() -> tuple[str, ...]:
    return tuple(_BY_NATIVE_PRODUCER)


__all__ = [
    "PUBLICATION_WRITER_REGISTRY", "PublicationWriter",
    "UPGRADE_CHECKPOINT_REL", "publication_block_reason",
    "publication_checkpoint_reason", "read_upgrade_checkpoint",
    "native_publication_block_reason", "registered_native_publication_producers",
    "registered_publication_tool_names",
]
