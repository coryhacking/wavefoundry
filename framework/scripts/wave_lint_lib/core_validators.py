from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .constants import (
    ADDITIONAL_REQUIRED_DOCS,
    MANIFEST_REQUIRED_KEYS,
    PROMPT_SURFACE_ALIASES,
    PROMPT_SURFACE_FILES,
    WORKFLOW_REQUIRED_KEYS,
)
from .helpers import load_json


def _check_lifecycle_id_policy(data: dict) -> list[str]:
    failures: list[str] = []
    policy = data.get("lifecycle_id_policy")
    if policy is None:
        return failures
    if not isinstance(policy, dict):
        return ["docs/workflow-config.json: `lifecycle_id_policy` must be an object"]
    epoch_raw = policy.get("epoch_utc")
    if epoch_raw is not None:
        if not isinstance(epoch_raw, str) or not epoch_raw.strip():
            failures.append("docs/workflow-config.json: lifecycle_id_policy.epoch_utc must be a non-empty UTC ISO-8601 string")
        else:
            text = epoch_raw.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                failures.append("docs/workflow-config.json: lifecycle_id_policy.epoch_utc must be a valid UTC ISO-8601 timestamp")
            else:
                if dt.tzinfo is None:
                    failures.append("docs/workflow-config.json: lifecycle_id_policy.epoch_utc must include a timezone (use `Z` for UTC)")
    hour_offset = policy.get("hour_offset", 0)
    if isinstance(hour_offset, bool) or not isinstance(hour_offset, int):
        failures.append("docs/workflow-config.json: lifecycle_id_policy.hour_offset must be a non-negative integer")
    elif hour_offset < 0:
        failures.append("docs/workflow-config.json: lifecycle_id_policy.hour_offset must be non-negative")
    width = policy.get("prefix_width")
    if width is not None and width != 5:
        failures.append("docs/workflow-config.json: lifecycle_id_policy.prefix_width must be 5 when set")
    return failures


def check_pycache(root: Path) -> list[str]:
    failures: list[str] = []
    scripts_root = root / ".wavefoundry" / "framework" / "scripts"
    if not scripts_root.exists():
        return failures
    for path in scripts_root.rglob("__pycache__"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        failures.append(f"python bytecode cache should not be checked in: {rel}")
    return failures


def check_required_files(root: Path) -> list[str]:
    failures: list[str] = []
    init_or_upgrade_started = any(
        (root / candidate).exists()
        for candidate in (
            "docs/prompts/install-wavefoundry.md",
            "docs/prompts/upgrade-wavefoundry.md",
            "docs/prompts/prompt-surface-manifest.json",
            "docs/waves",
            "docs/agents/journals",
            "docs/agents/personas",
        )
    )
    for relative in (*PROMPT_SURFACE_FILES, *ADDITIONAL_REQUIRED_DOCS):
        path = root / relative
        if not path.exists():
            failures.append(f"{relative}: missing required Wavefoundry file")
    if init_or_upgrade_started:
        for required in (
            "docs/prompts/install-wavefoundry.md",
            "docs/prompts/upgrade-wavefoundry.md",
        ):
            if not (root / required).exists():
                failures.append(f"{required}: missing required Wavefoundry file")
    return failures


def check_workflow_config(root: Path) -> list[str]:
    path = root / "docs/workflow-config.json"
    if not path.exists():
        return []
    data, error = load_json(path)
    if error:
        return [f"docs/workflow-config.json: unreadable or invalid JSON ({error})"]
    assert data is not None
    policy_failures = _check_lifecycle_id_policy(data)
    if any(key in data for key in WORKFLOW_REQUIRED_KEYS):
        failures: list[str] = []
        for key in WORKFLOW_REQUIRED_KEYS:
            if key not in data:
                failures.append(f"docs/workflow-config.json: missing `{key}` section")
        return policy_failures + failures

    legacy_compatible_keys = {
        "lifecycle_mode",
        "top_level_modules",
        "spec_package_roots",
        "agent_platform_generation",
        "agent_invocation_policy",
    }
    if legacy_compatible_keys.intersection(data.keys()):
        return policy_failures

    failures = []
    for key in WORKFLOW_REQUIRED_KEYS:
        if key not in data:
            failures.append(f"docs/workflow-config.json: missing `{key}` section")
    return policy_failures + failures


def check_prompt_surface_manifest(root: Path) -> list[str]:
    path = root / "docs/prompts/prompt-surface-manifest.json"
    if not path.exists():
        return []
    data, error = load_json(path)
    if error:
        return [f"docs/prompts/prompt-surface-manifest.json: unreadable or invalid JSON ({error})"]
    assert data is not None
    failures: list[str] = []
    for key in MANIFEST_REQUIRED_KEYS:
        if key not in data:
            failures.append(f"docs/prompts/prompt-surface-manifest.json: missing `{key}`")
    return failures
