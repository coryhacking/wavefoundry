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
    RETIRED_ROLE_NAMES,
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
    1p3dk / 1p3dm (Solaris field feedback 2026-06-04) converts the prefix
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


def check_workflow_config_legacy_aliases(root: Path) -> list[str]:
    """Emit a docs-lint warning when an alias-tuple in `WORKFLOW_REQUIRED_KEYS`
    is satisfied by a legacy spelling while the canonical (first-element)
    spelling is absent.

    Wave 1p3dk follow-up (Solaris field feedback 2026-06-05): the existing
    `check_workflow_config` validator passes silently when only the legacy
    key is present, since the alias-tuple was introduced as back-compat
    affordance. That means a config still on `wave_council_policy` gets a
    confident `docs-lint: ok` with no signal that the canonical name is
    `wave_review`. This warning closes the surfacing gap without forcing the
    rename — operators get a discoverable signal at lint time, the framework
    runtime continues to accept both, and the eventual convergence work
    (canonical-names manifest) remains a separate larger change.

    Wave 1p3iv (1p3j7): warning text now includes the removal version when
    `canonical-names.json` declares a `removed_in` value for the legacy
    key. Operators see the convergence deadline at the gate they trust.
    """
    path = root / "docs/workflow-config.json"
    if not path.exists():
        return []
    data, error = load_json(path)
    if error or data is None:
        return []
    warnings: list[str] = []
    for req in WORKFLOW_REQUIRED_KEYS:
        if not isinstance(req, tuple):
            continue
        canonical, *legacy_aliases = req
        if canonical in data:
            continue
        used_legacy = [k for k in legacy_aliases if k in data]
        for legacy_key in used_legacy:
            removed_in = _config_key_removed_in_safe(root, legacy_key)
            tail = (
                f" (will be removed in {removed_in})"
                if removed_in else " (the framework accepts both for now)"
            )
            warnings.append(
                f"docs/workflow-config.json: legacy key `{legacy_key}` is "
                f"deprecated; rename to canonical `{canonical}`{tail}"
            )
    return warnings


def _config_key_removed_in_safe(root: Path, legacy_key: str):
    """Look up the removed_in for a legacy config key, returning None on any
    error so the lint check stays operational under partial-rollout."""
    try:
        from . import canonical_names
        return canonical_names.config_key_removed_in(root, legacy_key)
    except Exception:  # pragma: no cover — defensive
        return None


def _current_framework_version(root: Path):
    """Read `.wavefoundry/framework/VERSION` and return the semver prefix
    (strips `+build` suffix). Returns None on missing/malformed file."""
    version_file = root / ".wavefoundry/framework/VERSION"
    if not version_file.exists():
        return None
    try:
        raw = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    # Drop +build / -prerelease suffix; keep MAJOR.MINOR.PATCH only.
    return raw.split("+", 1)[0].split("-", 1)[0]


def _semver_parse(version: str):
    """Parse `MAJOR.MINOR.PATCH` into a tuple of ints. Returns None on parse
    failure (caller should treat as 'uncertain — don't escalate')."""
    if not version:
        return None
    parts = version.split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def _current_version_is_at_or_past(root: Path, removed_in: str) -> bool:
    """True iff the on-disk framework version is at or past `removed_in`.
    Returns False (don't escalate) on any uncertainty — a missing VERSION
    file or unparseable semver shouldn't break the gate."""
    current = _semver_parse(_current_framework_version(root) or "")
    target = _semver_parse(removed_in)
    if current is None or target is None:
        return False
    return current >= target


def check_workflow_config_removed_keys(root: Path) -> list[str]:
    """Emit a docs-lint ERROR when a legacy config key in `workflow-config.json`
    is past its `removed_in` version per the canonical-names manifest.

    Wave 1p3iv (1p3j7): pairs with `check_workflow_config_legacy_aliases`.
    Below the removal version, the legacy spelling produces a warning
    (informational). At or past the removal version, it produces an error
    that fails docs-lint — the back-compat window is bounded and ends.

    Returns the empty list when:
    - `workflow-config.json` is absent or malformed
    - No legacy keys are present in the config
    - The current framework version is below `removed_in` for every legacy
      key present
    - The framework VERSION file is missing or unparseable (degraded mode —
      don't escalate when uncertain)
    """
    path = root / "docs/workflow-config.json"
    if not path.exists():
        return []
    data, error = load_json(path)
    if error or data is None:
        return []
    errors: list[str] = []
    for req in WORKFLOW_REQUIRED_KEYS:
        if not isinstance(req, tuple):
            continue
        canonical, *legacy_aliases = req
        used_legacy = [k for k in legacy_aliases if k in data]
        for legacy_key in used_legacy:
            removed_in = _config_key_removed_in_safe(root, legacy_key)
            if not removed_in:
                continue
            if _current_version_is_at_or_past(root, removed_in):
                errors.append(
                    f"docs/workflow-config.json: legacy key `{legacy_key}` "
                    f"was removed in {removed_in}; rename to canonical "
                    f"`{canonical}`"
                )
    return errors


_re = __import__("re")
_RETIRED_ROLE_PATTERNS = {
    name: _re.compile(r"(?<![\w-])" + _re.escape(name) + r"(?![\w-])", _re.IGNORECASE)
    for name in RETIRED_ROLE_NAMES
}
_MARKER_BEGIN_RE = _re.compile(r"<!--\s*waveframework:[\w:-]+\s+begin\b")
_MARKER_END_RE = _re.compile(r"<!--\s*end\s*-->")
_DEPRECATED_ROLE_SCAN_TARGETS = (
    "AGENTS.md",
    "CLAUDE.md",
    "docs/prompts",
    "docs/agents",
    "docs/contributing",
    "docs/references",
)
_DEPRECATED_ROLE_EXCLUDE_PREFIXES = (
    "docs/agents/journals/",
    "docs/agents/personas/journals/",
)


def _scan_file_for_retired_roles(path: Path, root: Path) -> list[str]:
    """Scan a single file for retired-role token references.

    Skips line ranges between `<!-- waveframework:* begin -->` and `<!-- end -->`
    markers since the renderer rewrites those regions on each platform-surface
    render. Token boundaries are kebab-aware: `council-moderator` matches a
    standalone token but NOT a substring of `wave-council-moderator`.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        rel = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        rel = str(path)
    warnings: list[str] = []
    inside_marker = False
    for line_no, line in enumerate(text.splitlines(), 1):
        if not inside_marker and _MARKER_BEGIN_RE.search(line):
            inside_marker = True
            continue
        if inside_marker:
            if _MARKER_END_RE.search(line):
                inside_marker = False
            continue
        for retired, canonical in RETIRED_ROLE_NAMES.items():
            if _RETIRED_ROLE_PATTERNS[retired].search(line):
                warnings.append(
                    f"{rel}:{line_no}: references retired role "
                    f"`{retired}` — canonical replacement is `{canonical}`"
                )
    return warnings


def check_deprecated_role_references(root: Path) -> list[str]:
    """Wave 1p3dk follow-up (Solaris field feedback 2026-06-05): scan
    hand-authored project docs for references to retired framework role
    slugs. Emit a WARNING per match naming the canonical replacement.

    Solaris reported that after the `council-moderator` → `wave-council`
    rename shipped in wave 1p337, every hand-authored reference survived the
    upgrade silently — render scripts only touch generated marker regions.
    This check closes the surfacing gap: a consumer's `docs-lint` run after
    a pack adoption now lists every stale role reference with the canonical
    replacement, without forcing a rename or blocking the gate.

    Scope: hand-authored, currency-tracking docs (AGENTS.md, CLAUDE.md,
    docs/prompts/, docs/agents/ excluding journals/, docs/contributing/,
    docs/references/). Out of scope: docs/waves/** (historical), journals/
    (historical signals), CHANGELOG.md (records the rename itself),
    .wavefoundry/framework/** (vendored — edits don't persist), and any
    text inside `<!-- waveframework:* begin --> ... <!-- end -->` marker
    regions (auto-regenerated by the renderer).
    """
    warnings: list[str] = []
    for target in _DEPRECATED_ROLE_SCAN_TARGETS:
        full = root / target
        if full.is_file():
            warnings.extend(_scan_file_for_retired_roles(full, root))
        elif full.is_dir():
            for path in sorted(full.rglob("*.md")):
                rel = str(path.relative_to(root)).replace("\\", "/")
                if any(rel.startswith(ex) for ex in _DEPRECATED_ROLE_EXCLUDE_PREFIXES):
                    continue
                warnings.extend(_scan_file_for_retired_roles(path, root))
    return warnings


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
