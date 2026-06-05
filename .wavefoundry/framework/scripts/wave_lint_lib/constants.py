from __future__ import annotations

import re

METADATA_PATTERNS = {
    "Owner": re.compile(r"^Owner:\s+.+$", re.MULTILINE),
    "Status": re.compile(r"^Status:\s+.+$", re.MULTILINE),
    "Last verified": re.compile(r"^Last verified:\s+\d{4}-\d{2}-\d{2}$", re.MULTILINE),
}

PROMPT_SURFACE_FILES = (
    "docs/prompts/index.md",
    "docs/prompts/plan-feature.prompt.md",
    "docs/prompts/implement-feature.prompt.md",
    "docs/prompts/finalize-feature.prompt.md",
    "docs/prompts/agent-routing-concurrency.prompt.md",
)

PROMPT_SURFACE_ALIASES: tuple[tuple[str, str], ...] = ()

ADDITIONAL_REQUIRED_DOCS = (
    "docs/README.md",
    "docs/agents/session-handoff.md",
    "docs/workflow-config.json",
    "docs/waves/README.md",
    "docs/agents/journals/README.md",
    "docs/prompts/prompt-surface-manifest.json",
    "docs/references/project-context-memory.md",
    "docs/references/project-overview.md",
    "docs/agents/personas/README.md",
)

WAVE_REQUIRED_PATHS = (
    "docs/waves",
    "docs/agents/journals",
    "docs/prompts/prompt-surface-manifest.json",
    "docs/agents/personas",
)

# Wave 1p337 (1p336): tuple entries express "alias groups" — any one of the listed
# keys satisfies the requirement. String entries express single canonical keys.
# This generalization supports the seed-prose rename `wave_execution` → `wave_implement`
# without breaking consumer configs that still use the legacy key; future renames can
# be added the same way without touching the validator logic.
#
# **Convention (wave 1p3dk):** the **first element** of each tuple is the canonical
# name; subsequent elements are deprecated legacy aliases accepted for back-compat.
# `check_workflow_config_legacy_aliases` in `core_validators.py` emits a docs-lint
# WARNING when a config satisfies an alias-tuple via a legacy spelling so operators
# see a discoverable migration signal at the gate. The framework runtime continues
# to accept both spellings indefinitely; convergence to a single name requires the
# canonical-names manifest (deferred to a follow-on wave).
# Wave 1p3iv (1p3j6): canonical alias data for the renamable required keys
# (`wave_implement`, `wave_review`) is derived from `canonical-names.json` at
# module-load time. Required keys without renames stay as plain strings.
# Required keys WITH renames in the manifest become alias tuples whose first
# element is the canonical name (per the 1p3dk convention) and whose subsequent
# elements are the legacy spellings sorted ascending.
#
# If the manifest is absent or malformed, the loader returns an empty alias map;
# the renamable canonical keys then become plain strings (no aliases known).
# This degrades the legacy-spelling WARNING — but `docs-lint` remains operational.
_REQUIRED_KEYS_WITH_POSSIBLE_ALIASES = ("wave_implement", "wave_review")
_REQUIRED_KEYS_WITHOUT_ALIASES = (
    "agent_memory",
    "project_persona_generation",
    "prompt_generation",
    "factor_review_policy",
    "persona_review_policy",
)


def _build_workflow_required_keys() -> tuple:
    # Local import keeps the module loader self-contained and avoids surprising
    # circular-import behavior at framework cold-start.
    from . import canonical_names

    alias_to_canonical = canonical_names.config_key_alias_to_canonical(
        canonical_names.framework_repo_root()
    )
    canonical_to_aliases = canonical_names.canonical_to_aliases(alias_to_canonical)

    entries: list = []
    for canonical in _REQUIRED_KEYS_WITH_POSSIBLE_ALIASES:
        aliases = canonical_to_aliases.get(canonical, [])
        if aliases:
            entries.append((canonical, *aliases))
        else:
            entries.append(canonical)
    entries.extend(_REQUIRED_KEYS_WITHOUT_ALIASES)
    return tuple(entries)


WORKFLOW_REQUIRED_KEYS = _build_workflow_required_keys()

MANIFEST_REQUIRED_KEYS = (
    "schema_version",
    "seed_framework_source",
    "framework_revision",
)

# Wave 1p3dk follow-up (Solaris field feedback 2026-06-05): when the framework
# renames a role, hand-authored project docs that mirror the role name in prose
# (AGENTS.md, docs/prompts/*.md, etc.) silently retain the old name across an
# upgrade — render scripts only touch generated marker regions. This map
# declares every retired role slug and its canonical replacement.
# `check_deprecated_role_references` emits a docs-lint WARNING when a scanned
# doc still references a retired slug, so operators see the migration signal
# at the gate that they actually trust.
#
# Maintenance contract: every framework-shipped role rename adds an entry
# here. Same shape as `WORKFLOW_REQUIRED_KEYS` alias tuples — declarative
# rather than dynamic upgrade-time detection.
# Wave 1p3iv (1p3j6): retired role mapping is now derived from the canonical
# names manifest (`.wavefoundry/framework/canonical-names.json`). The hardcoded
# dict that lived here is gone — the manifest is the single source of truth.
# The public name `RETIRED_ROLE_NAMES` is preserved so external imports (test
# files, validators) keep working. Manifest absent → empty map → no warnings;
# `docs-lint` stays operational.
def _build_retired_role_names() -> dict[str, str]:
    from . import canonical_names

    return canonical_names.role_alias_to_canonical(
        canonical_names.framework_repo_root()
    )


RETIRED_ROLE_NAMES = _build_retired_role_names()

MANIFEST_REQUIRED_GENERATED_ARTIFACTS = (
    "docs/prompts/prompt-surface-manifest.json",
    "docs/agents/session-handoff.md",
    "docs/waves/",
    "docs/agents/journals/",
    "docs/agents/personas/",
)

INDEX_REQUIRED_REFERENCES = (
    "docs/prompts/prompt-surface-manifest.json",
    "docs/agents/session-handoff.md",
    "docs/waves/",
    "docs/agents/journals/",
)

WAVE_REQUIRED_SECTIONS = (
    "## Wave Summary",
    "## Journal Watchpoints",
)

JOURNAL_REQUIRED_SECTIONS = (
    "## Operating Identity",
    "## Salience Triggers",
    "## Active Signals",
    "## Distillation",
    "## Promotion Evidence",
    "## Retirement And Supersession",
    "## Governance",
)

PERSONA_REQUIRED_SECTIONS = (
    "## Who",
    "## Goals",
    "## Workflows",
    "## Failure modes",
    "## Invocation signals",
    "## Operating identity",
    "## Salience triggers",
    "## Associated journal",
)

# Root wrapper names that must not exist at the repository root.
# RETIRED: no replacement — these have been removed entirely.
FORBIDDEN_ROOT_WRAPPERS_RETIRED = (
    "package-wave-framework",
    "install-wave-framework",
    "upgrade-wave-framework",
)
# RELOCATED: these belong under .wavefoundry/bin/ instead.
FORBIDDEN_ROOT_WRAPPERS_RELOCATED = (
    "docs-lint",
    "docs-gardener",
)
FORBIDDEN_ROOT_WRAPPERS = FORBIDDEN_ROOT_WRAPPERS_RETIRED + FORBIDDEN_ROOT_WRAPPERS_RELOCATED

LEGACY_MARKERS = ("spec-change-lifecycle",)
# All repositories should be Wavefoundry-first. We still flag non-wave legacy markers during
# migration edges, but the framework does not treat the legacy pack path as a supported surface.
HYBRID_LEGACY_MARKERS = ()
FACTOR_REVIEW_MARKERS = ("factor review", "factor-review")
JOURNAL_SIGNAL_MARKERS = ("watchpoint", "follow-up", "escalat", "review")
JOURNAL_SALIENCE_MARKERS = (
    "critical",
    "high",
    "medium",
    "low",
    "operator",
    "compaction",
    "restart",
    "regression",
    "security",
    "release",
    "trust",
)
JOURNAL_GOVERNANCE_MARKERS = (
    "allowed",
    "disallowed",
    "sensitive",
    "secret",
    "credential",
    "review",
    "retire",
    "delete",
    "supersed",
)
JOURNAL_DISALLOWED_PATTERNS = (
    re.compile(r"\b(password|passwd|api[_-]?key|secret|token)\s*[:=]", re.IGNORECASE),
    re.compile(r"\b(raw|full)\s+(chat\s+)?transcript\b", re.IGNORECASE),
    re.compile(r"\bcopy\s+every\s+(message|command|observation|output)\b", re.IGNORECASE),
    re.compile(r"\broutine\s+(success|progress)\s+(update|log|entry)\b", re.IGNORECASE),
)
WAVE_WATCHPOINT_MARKERS = ("watchpoint", "follow-up", "block", "retry", "defer", "move")

TERMINAL_ITEM_STATUSES = ("complete", "completed", "deferred", "moved", "superseded")
PROGRESSABLE_ITEM_STATUSES = ("ready", "active", "review", "complete", "completed")
ALLOWED_ITEM_STATUS_TRANSITIONS = {
    "planned": {"planned", "ready", "active", "blocked", "deferred", "moved", "retry", "superseded", "complete", "completed"},
    "ready": {"ready", "active", "blocked", "review", "complete", "completed", "retry", "moved", "superseded"},
    "active": {"active", "blocked", "review", "complete", "completed", "retry", "moved", "superseded"},
    "blocked": {"blocked", "ready", "active", "retry", "deferred", "moved", "superseded"},
    "review": {"review", "active", "complete", "completed", "retry", "blocked", "moved", "superseded"},
    "complete": {"complete"},
    "completed": {"completed"},
    "deferred": {"deferred", "ready", "active", "superseded"},
    "moved": {"moved"},
    "retry": {"retry", "ready", "active", "blocked", "review", "complete", "completed", "moved", "superseded"},
    "superseded": {"superseded"},
}

TERMINAL_CHANGE_STATUSES = ("complete", "completed", "done", "deferred", "moved", "superseded")
PROGRESSABLE_CHANGE_STATUSES = ("ready", "active", "review", "complete", "completed")
ALLOWED_CHANGE_STATUS_TRANSITIONS = {
    "planned": {"planned", "ready", "active", "blocked", "deferred", "moved", "retry", "superseded", "complete", "completed"},
    "ready": {"ready", "active", "blocked", "review", "complete", "completed", "retry", "moved", "superseded"},
    "active": {"active", "blocked", "review", "complete", "completed", "retry", "moved", "superseded"},
    "blocked": {"blocked", "ready", "active", "retry", "deferred", "moved", "superseded"},
    "review": {"review", "active", "complete", "completed", "retry", "blocked", "moved", "superseded"},
    "complete": {"complete"},
    "completed": {"completed"},
    "deferred": {"deferred", "ready", "active", "superseded"},
    "moved": {"moved"},
    "retry": {"retry", "ready", "active", "blocked", "review", "complete", "completed", "moved", "superseded"},
    "superseded": {"superseded"},
}

AUDIT_DEFAULT_REPORT = "docs/reports/wave-migration-audit.md"

SLUG_PATTERN = r"[a-z0-9][a-z0-9-]*"
LEGACY_SLUG_PATTERN = r"legacy[a-z0-9-]*"
LIFECYCLE_PREFIX_PATTERN = r"(?:[0-9a-z]{5}|00000)"

WAVE_ID_PATTERN = re.compile(rf"^wave-id:\s+`({LIFECYCLE_PREFIX_PATTERN} {SLUG_PATTERN})`$", re.MULTILINE)
CHANGE_KIND_PATTERN = r"(?:bug|feat|enh|change|doc|debt|ref|task|maint|ops)"
CHANGE_ID_PATTERN = re.compile(rf"^Change ID:\s+`({LIFECYCLE_PREFIX_PATTERN}-{CHANGE_KIND_PATTERN} {SLUG_PATTERN})`$", re.MULTILINE)
# CHANGE_ID_PATTERN validates change plan document headers (docs/plans/**/*.md and archived wave plan files).
# It is not used for wave record headers — wave records carry only `wave-id`.
PLAN_WAVE_OVERVIEW_PATTERN = re.compile(rf"^Wave:\s+`({LIFECYCLE_PREFIX_PATTERN} {SLUG_PATTERN})`$", re.MULTILINE)
# PLAN_WAVE_OVERVIEW_PATTERN matches wave-level overview plans that sit under `docs/plans/` and use
# a `Wave:` line (rather than a `Change ID:` line) as their identifier. Such plans use the wave-id
# as the filename (example: `docs/plans/1n3dq github-enterprise-webhooks.md`).
ITEM_ID_PATTERN = re.compile(r"^Item ID:\s+`([a-z0-9][a-z0-9-]*)`$", re.MULTILINE)
ITEM_STATUS_PATTERN = re.compile(r"^Item Status:\s+`([a-z0-9-]+)`$", re.MULTILINE)
PREVIOUS_ITEM_STATUS_PATTERN = re.compile(r"^Previous Item Status:\s+`([a-z0-9-]+)`$", re.MULTILINE)
CHANGE_STATUS_PATTERN = re.compile(r"^Change Status:\s+`([a-z0-9-]+)`$", re.MULTILINE)
PREVIOUS_CHANGE_STATUS_PATTERN = re.compile(r"^Previous Change Status:\s+`([a-z0-9-]+)`$", re.MULTILINE)
DEPENDS_ON_LINE_PATTERN = re.compile(r"^Depends On:\s+(.+)$", re.MULTILINE)
BACKTICK_TOKEN_PATTERN = re.compile(r"`([a-z0-9][a-z0-9-]*)`")
BACKTICK_VALUE_PATTERN = re.compile(r"`([^`]+)`")
JOURNAL_PATH_PATTERN = re.compile(r"docs/agents/journals/[A-Za-z0-9._/-]+\.md")
WAVE_REFERENCE_PATTERN = re.compile(rf"^wave-id:\s+`({LIFECYCLE_PREFIX_PATTERN} {SLUG_PATTERN})`$", re.MULTILINE)
ITEM_REFERENCE_PATTERN = re.compile(r"^Item ID:\s+`([a-z0-9][a-z0-9-]*)`$", re.MULTILINE)
CHANGE_REFERENCE_PATTERN = CHANGE_ID_PATTERN
MARKDOWN_HEADING_PATTERN = re.compile(r"^(## .+)$", re.MULTILINE)
