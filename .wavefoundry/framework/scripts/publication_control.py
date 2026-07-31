"""Typed publication registry and upgrade checkpoint guard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


UPGRADE_CHECKPOINT_REL = Path(".wavefoundry/upgrade-in-progress.json")


@dataclass(frozen=True)
class PublicationWriter:
    tool_name: str
    producer: str
    contention_policy: str
    memory_recovery: bool = False
    surface: str = "tool"


PUBLICATION_WRITER_REGISTRY = (
    PublicationWriter("wf_create_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_add_change", "lifecycle", "fail_fast"),
    PublicationWriter("wf_remove_change", "lifecycle", "fail_fast"),
    PublicationWriter("wf_prepare_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_pause_wave", "lifecycle", "fail_fast"),
    PublicationWriter("wf_close_wave", "lifecycle", "fail_fast"),
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
    PublicationWriter("memory_backfill", "memory_recovery", "checkpoint_only", True),
    PublicationWriter("memory_validate", "memory_recovery", "checkpoint_only", True),
    PublicationWriter("wf_scan_secrets", "security_findings", "fail_fast"),
    PublicationWriter("wf_garden_docs", "docs_garden", "fail_fast"),
    PublicationWriter("wf_sync_surfaces", "surface_renderer", "fail_fast"),
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
        value = json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    # Presence is authoritative. Valid JSON of the wrong shape is corruption,
    # not evidence that no upgrade is running.
    return value if isinstance(value, dict) else {}


def publication_checkpoint_reason(
    root: Path,
    producer: str,
    *,
    memory_recovery: bool = False,
) -> str | None:
    """Guard a concrete writer boundary, including non-MCP/background writers."""

    checkpoint = read_upgrade_checkpoint(root)
    if checkpoint is None:
        return None
    phase = str(
        checkpoint.get("current_phase")
        or checkpoint.get("failed_phase")
        or checkpoint.get("phase")
        or "corrupt_checkpoint"
    )
    if phase == "awaiting_memory_validation" and memory_recovery:
        return None
    return (
        f"upgrade_in_progress: publication by {producer} is blocked while "
        f"Upgrade is at {phase}; retry or resume Upgrade to a terminal state"
    )


def publication_block_reason(root: Path, tool_name: str) -> str | None:
    """Return an actionable fail-fast reason while Upgrade is non-terminal."""

    writer = _BY_TOOL.get(tool_name)
    if writer is None:
        return None
    return publication_checkpoint_reason(
        root,
        tool_name,
        memory_recovery=(
            writer.memory_recovery
            and tool_name in {"memory_backfill", "memory_validate"}
        ),
    )


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
