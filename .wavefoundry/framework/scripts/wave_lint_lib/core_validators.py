from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .constants import (
    ADDITIONAL_REQUIRED_DOCS,
    FORBIDDEN_ROOT_WRAPPERS_RELOCATED,
    FORBIDDEN_ROOT_WRAPPERS_RETIRED,
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
    # prefix_width 5 is the MINIMUM display width: scheme v2 never wraps, so IDs
    # may widen to 6 chars at the ~40-year overflow horizon. The config value
    # stays pinned at 5 (it names the standard width, not a hard cap).
    width = policy.get("prefix_width")
    if width is not None and width != 5:
        failures.append(
            "docs/workflow-config.json: lifecycle_id_policy.prefix_width must be 5 when set "
            "(minimum display width; IDs may widen to 6 chars at the scheme-v2 overflow horizon)"
        )
    # v2 keys — mirror lifecycle_id.load_lifecycle_policy's strict rules so
    # docs-lint catches a hand-edited malformed v2 block before a mint does.
    scheme = policy.get("scheme_version")
    if scheme is not None and scheme not in ("v1", "v2"):
        failures.append("docs/workflow-config.json: lifecycle_id_policy.scheme_version must be 'v1' or 'v2' when set")
    offset = policy.get("offset")
    if scheme == "v2":
        if isinstance(offset, bool) or not isinstance(offset, int):
            failures.append("docs/workflow-config.json: lifecycle_id_policy.offset must be an integer when scheme_version is 'v2'")
        elif offset < 36 ** 3:
            failures.append("docs/workflow-config.json: lifecycle_id_policy.offset must be >= 36^3 (46656) when scheme_version is 'v2'")
        if not (isinstance(epoch_raw, str) and epoch_raw.strip()):
            failures.append("docs/workflow-config.json: lifecycle_id_policy.epoch_utc is required when scheme_version is 'v2'")
        node_bits = policy.get("node_bits")
        if node_bits not in (None, 0):
            failures.append(
                "docs/workflow-config.json: lifecycle_id_policy.node_bits is reserved and must be 0 when set "
                "(unset = full 12-bit hash entropy)"
            )
        project_seed = policy.get("project_seed")
        if project_seed is not None and (not isinstance(project_seed, str) or not project_seed.strip()):
            failures.append("docs/workflow-config.json: lifecycle_id_policy.project_seed must be a non-empty string when set")
    return failures


# Wave 1p35d (1p35n / 1p35p enterprise-deployment hardening): directories
# `docs-lint` excludes from "checked in" classification. Named, frozen, single
# source of truth so the exclusion list is discoverable.
#
# Membership rationale: each entry is a transient cache or build artifact that
# is already excluded by `.gitignore` by ecosystem convention. Duplicating that
# exclusion in lint produced a recurring blocker for the MCP server flow (which
# generates pycache on every Python import) and would produce the same blocker
# for every Python tool that writes a cache dir (pytest, mypy, ruff, tox,
# coverage).
#
# Operator-visible documentation lives at
# `.wavefoundry/framework/docs/lint-exclusions.md` — keep that doc and this constant
# in sync.
LINT_EXCLUDED_TRANSIENT_DIRS: frozenset[str] = frozenset({
    "__pycache__",      # Python bytecode cache
    ".pytest_cache",    # pytest run cache
    ".mypy_cache",      # mypy type-check cache
    ".ruff_cache",      # ruff lint cache
    ".tox",             # tox virtualenv cache
    ".coverage",        # coverage.py data file (technically a file, listed for parity)
})


def check_pycache(root: Path) -> list[str]:
    """Always returns an empty list.

    `__pycache__` is in `LINT_EXCLUDED_TRANSIENT_DIRS`: lint defers to `.gitignore`
    as the source of truth for "should not be checked in" for this pattern. The
    function is retained as a stable callable so callers and tests don't need to
    change shape if the exclusion list ever expands and we want per-pattern checks
    again.
    """
    return []


def check_forbidden_root_wrappers(root: Path) -> list[str]:
    """Flag legacy binary wrapper files that must not exist at the repository root."""
    failures: list[str] = []
    for name in FORBIDDEN_ROOT_WRAPPERS_RETIRED:
        if (root / name).exists():
            failures.append(
                f"{name}: retired root wrapper must be removed (no replacement)"
            )
    for name in FORBIDDEN_ROOT_WRAPPERS_RELOCATED:
        if (root / name).exists():
            failures.append(
                f"{name}: root wrapper must be removed — use .wavefoundry/bin/{name} instead"
            )
    return failures


_SEED_PREFIX_RE = __import__("re").compile(r"^(\d{3})-")


def check_seed_prefix_uniqueness(root: Path) -> list[str]:
    """Fail when two framework seeds share a numeric prefix.

    The seed prefix convention treats `NNN-` as a unique key referenced from
    seed prose, consumer code, and operator docs. When two seeds ship under
    the same prefix, references like ``seed-NNN`` resolve ambiguously. Wave
    1p3dk / 1p3dm (field feedback 2026-06-04) converts the prefix
    from a soft convention to an enforced unique key.
    """
    failures: list[str] = []
    seeds_dir = root / ".wavefoundry" / "framework" / "seeds"
    if not seeds_dir.is_dir():
        return failures
    by_prefix: dict[str, list[str]] = {}
    for path in sorted(seeds_dir.glob("*.md")):
        match = _SEED_PREFIX_RE.match(path.name)
        if not match:
            continue
        by_prefix.setdefault(match.group(1), []).append(path.name)
    for prefix, names in by_prefix.items():
        if len(names) > 1:
            joined = " and ".join(f"`{n}`" for n in names)
            failures.append(
                f"seed prefix collision: `{prefix}-` shared by {joined}"
            )
    return failures


def check_required_files(root: Path) -> list[str]:
    failures: list[str] = []
    init_or_upgrade_started = any(
        (root / candidate).exists()
        for candidate in (
            "docs/prompts/install-wavefoundry.prompt.md",
            "docs/prompts/upgrade-wavefoundry.prompt.md",
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
            "docs/prompts/install-wavefoundry.prompt.md",
            "docs/prompts/upgrade-wavefoundry.prompt.md",
        ):
            if not (root / required).exists():
                failures.append(f"{required}: missing required Wavefoundry file")
    return failures


_PROMPT_EXTENSION_EXEMPT = frozenset({"index.md", "README.md"})


def check_prompt_file_extensions(root: Path) -> list[str]:
    """Flag plain .md files under docs/prompts/ that should use the .prompt.md extension.

    Exempt by filename (at any depth): index.md, README.md — these are navigation/catalog
    docs, not runnable prompts. All other .md files under docs/prompts/ must use .prompt.md.
    Only fires when docs/prompts/ exists — skips repos that haven't seeded the prompt surface.
    """
    prompts_dir = root / "docs" / "prompts"
    if not prompts_dir.exists():
        return []
    failures: list[str] = []
    for path in prompts_dir.rglob("*.md"):
        if path.name in _PROMPT_EXTENSION_EXEMPT:
            continue
        if not path.name.endswith(".prompt.md"):
            rel = path.relative_to(root).as_posix()
            failures.append(
                f"{rel}: runnable prompt file must use .prompt.md extension"
                f" (rename to {path.stem}.prompt.md)"
            )
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

    # Wave 1p337 (1p336): `WORKFLOW_REQUIRED_KEYS` entries are either strings (single
    # canonical key) or tuples (alias groups where any one key satisfies the requirement).
    # Tuple form is the back-compat affordance for seed-prose renames.
    def _requirement_satisfied(req) -> bool:
        if isinstance(req, tuple):
            return any(k in data for k in req)
        return req in data

    def _requirement_label(req) -> str:
        if isinstance(req, tuple):
            primary, *legacy = req
            if legacy:
                legacy_str = " or legacy " + " / ".join(f"`{k}`" for k in legacy)
                return f"`{primary}`{legacy_str}"
            return f"`{primary}`"
        return f"`{req}`"

    if any(_requirement_satisfied(req) for req in WORKFLOW_REQUIRED_KEYS):
        failures: list[str] = []
        for req in WORKFLOW_REQUIRED_KEYS:
            if not _requirement_satisfied(req):
                failures.append(f"docs/workflow-config.json: missing {_requirement_label(req)} section")
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
    for req in WORKFLOW_REQUIRED_KEYS:
        if not _requirement_satisfied(req):
            failures.append(f"docs/workflow-config.json: missing {_requirement_label(req)} section")
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
