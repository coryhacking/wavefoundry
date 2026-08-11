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
from review_policy import (
    REVIEW_POLICY_OBLIGATION_ANCHORS,
    REVIEW_POLICY_SURFACE_MARKER_BEGIN,
    RETIRED_LIFECYCLE_TOKENS,
    UPGRADE_POLICY_MARKER_BEGIN,
    normalize_wave_review_policy,
    review_policy_carriers,
    serialization_point_paths,
    SCAFFOLD_DOCS,
)


def check_scaffold_declares_nothing(root: Path, only: set[Path] | None = None) -> list[str]:
    """A document meant to be COPIED must declare no review targets.

    Field report from a 1.15.5 upgrade: a target repository's
    `plan-template.md` carried an unfenced example under the
    `**Review targets (repo-relative paths):**` marker, so the scaffold itself
    declared `path/to/file.swift` and `docs/specs/`. Every plan created from it
    was born in declared mode, silently losing two required review lanes and
    gaining one from a path its author never chose.

    Wavefoundry itself was never affected, and that is exactly the problem the
    rule exists to solve: this repository is clean only because a test in ITS
    OWN suite pins the property. A target repository does not run that suite.
    What it gets is prose instruction in seed 160 telling the upgrade agent to
    fence its example — instruction the downstream repository received and
    followed, and still shipped a declaring template. Prose is not a gate.

    Extraction is DELEGATED to `serialization_point_paths`, never
    re-implemented. A second extractor would drift from the evaluator and pass
    a template the evaluator reads as declaring, recreating the same silent gap
    one layer up. The check therefore consumes parser OUTPUT only and never
    scans raw text: real scaffolds legitimately MENTION example paths in prose,
    and a text scan would fail them.

    Scope is the scaffold set alone. The upgrade can safely repair a scaffold,
    because every declaration in one is by definition an example; it cannot
    safely rewrite authored content, and a closed wave's history is not
    rewritable at all. Blocking anything the upgrade cannot repair would strand
    the repository at the docs gate, so nothing outside the set is examined.
    """

    failures: list[str] = []
    for rel in SCAFFOLD_DOCS:
        path = root / rel
        if not path.is_file():
            continue
        if only is not None and path not in only:
            continue
        try:
            declared = serialization_point_paths(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if declared:
            named = ", ".join(f"`{target}`" for target in declared)
            # No "ERROR: " prefix here: `cli._emit` adds one, and every sibling
            # validator in this module returns a bare message. Self-prefixing
            # renders as `ERROR: ERROR: …` to the operator.
            failures.append(
                f"{rel}: scaffold declares review targets ({named}). "
                "A template is copied, so its declarations become every new "
                "change doc's declarations, silently replacing the lanes its "
                "author would otherwise get. Put the example inside a fenced "
                "block — fenced regions declare nothing."
            )
    return failures


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
    if "wave_review" in data:
        _normalized_review, review_errors = normalize_wave_review_policy(
            data.get("wave_review")
        )
        policy_failures.extend(
            f"docs/workflow-config.json: {error}" for error in review_errors
        )

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


def check_review_policy_carriers(root: Path) -> list[str]:
    """Validate the existing carrier family through its production registry."""

    failures: list[str] = []
    policy_surface_active = any(
        REVIEW_POLICY_SURFACE_MARKER_BEGIN in path.read_text(encoding="utf-8")
        for path in (
            root / "docs/prompts/prepare-wave.prompt.md",
            root / "docs/prompts/review-wave.prompt.md",
            root / "docs/prompts/close-wave.prompt.md",
        )
        if path.is_file()
    )
    carriers = (
        review_policy_carriers()
        if policy_surface_active
        else review_policy_carriers("lifecycle_reconciler")
    )
    for carrier in carriers:
        path = root / carrier.destination
        paths = (
            sorted(item for item in path.rglob("*.md") if item.is_file())
            if path.is_dir()
            else [path] if path.is_file() else []
        )
        if not paths:
            continue
        try:
            text = "\n".join(item.read_text(encoding="utf-8") for item in paths)
        except (OSError, UnicodeError) as exc:
            failures.append(f"{carrier.destination}: review-policy carrier unreadable ({exc})")
            continue
        lowered = text.lower()
        if carrier.owner == "lifecycle_reconciler":
            matches = [token for token in RETIRED_LIFECYCLE_TOKENS if token in lowered]
            if matches:
                failures.append(
                    f"{carrier.destination}: retired review-lifecycle prose remains: {matches[0]}"
                )
        for obligation in carrier.obligations:
            anchors = REVIEW_POLICY_OBLIGATION_ANCHORS.get(obligation, ())
            if not anchors or not any(anchor in lowered for anchor in anchors):
                failures.append(
                    f"{carrier.destination}: registered review-policy obligation "
                    f"is missing: {obligation}"
                )
        if (
            carrier.destination == "docs/prompts/upgrade-wavefoundry.prompt.md"
            and (root / "docs/workflow-config.json").is_file()
        ):
            data, error = load_json(root / "docs/workflow-config.json")
            explicit_policy = bool(
                error is None
                and isinstance(data, dict)
                and isinstance(data.get("wave_review"), dict)
                and "delivery_mode" in data["wave_review"]
            )
            if explicit_policy and UPGRADE_POLICY_MARKER_BEGIN not in text:
                failures.append(
                    f"{carrier.destination}: missing registered review-policy/bridge recovery region"
                )
    return list(dict.fromkeys(failures))


def check_review_policy_carrier_parity(
    root: Path, only: set[Path] | None = None
) -> list[str]:
    """1v1c5: a rendered review-policy region must equal its block source.

    The expected region is composed by the RENDERER'S OWN helper
    (``_upsert_review_policy_region``), never a second implementation of the
    region shape: ``1us4q``'s guard died of a parallel reimplementation, and
    this check exists because nothing else compares content (the carrier check
    above tests marker presence and obligation anchors; the renderer test
    counts markers). Dispositions are deliberate:

    - missing file: skipped (presence stays the existing checks' business);
    - file exists with NEITHER marker: skipped (an unadopted carrier; base
      lint fixtures legitimately hold this state);
    - a single or malformed marker pair: FAILURE (the reconciler
      warns-and-skips there; a gate must not);
    - a well-formed region differing from the block: FAILURE whichever side
      drifted (block edited without re-render, or a hand-edit inside the
      region).
    """

    from render_agent_surfaces import (
        _contained_review_carrier_path,
        _upsert_review_policy_region,
    )
    from review_policy import (
        REVIEW_POLICY_CARRIER_REGISTRY,
        REVIEW_POLICY_SURFACE_BLOCKS,
        REVIEW_POLICY_SURFACE_MARKER_END,
    )

    only_resolved = (
        {path.resolve() for path in only} if only is not None else None
    )
    failures: list[str] = []
    for carrier in REVIEW_POLICY_CARRIER_REGISTRY:
        block = REVIEW_POLICY_SURFACE_BLOCKS.get(carrier.destination)
        if carrier.owner != "renderer" or block is None:
            continue
        path = _contained_review_carrier_path(root, carrier.destination)
        if not path.is_file():
            continue
        if only_resolved is not None and path.resolve() not in only_resolved:
            continue
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                text = handle.read()
        except (OSError, UnicodeError) as exc:
            failures.append(
                f"{carrier.destination}: review-policy carrier unreadable ({exc})"
            )
            continue
        has_begin = REVIEW_POLICY_SURFACE_MARKER_BEGIN in text
        has_end = REVIEW_POLICY_SURFACE_MARKER_END in text
        if not has_begin and not has_end:
            continue
        updated = _upsert_review_policy_region(text, block)
        if updated is None:
            failures.append(
                f"{carrier.destination}: review-policy markers are malformed "
                "(unbalanced or duplicated); repair the markers, then run "
                "reconcile_review_policy_surfaces to re-render the region"
            )
        elif updated != text:
            failures.append(
                f"{carrier.destination}: rendered review-policy region differs "
                "from its registered block source; run "
                "reconcile_review_policy_surfaces to re-render it"
            )
    # The registry legitimately holds more than one renderer row per
    # destination; one destination reports once.
    return list(dict.fromkeys(failures))


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
