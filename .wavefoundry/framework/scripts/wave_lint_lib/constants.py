from __future__ import annotations

import re

METADATA_PATTERNS = {
    "Owner": re.compile(r"^Owner:\s+.+$", re.MULTILINE),
    "Status": re.compile(r"^Status:\s+.+$", re.MULTILINE),
    "Last verified": re.compile(r"^Last verified:\s+\d{4}-\d{2}-\d{2}$", re.MULTILINE),
}

PROMPT_SURFACE_FILES = (
    "docs/prompts/index.md",
    "docs/prompts/plan-feature.md",
    "docs/prompts/implement-feature.md",
    "docs/prompts/finalize-feature.md",
    "docs/prompts/agent-routing-concurrency.md",
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

WORKFLOW_REQUIRED_KEYS = (
    "wave_execution",
    "agent_memory",
    "project_persona_generation",
    "prompt_generation",
    "factor_review_policy",
    "persona_review_policy",
)

MANIFEST_REQUIRED_KEYS = (
    "schema_version",
    "seed_framework_source",
    "framework_revision",
)

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
    "## Recent Captures",
    "## Distillation",
    "## Promotion Evidence",
    "## Retirement And Supersession",
    "## Governance",
)

PERSONA_REQUIRED_SECTIONS = (
    "## Scope",
    "## Operating Identity",
    "## Salience Triggers",
    "## Planning Duties",
    "## Review Triggers",
    "## Escalation Conditions",
    "## Associated Journal",
)

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

TERMINAL_CHANGE_STATUSES = ("complete", "completed", "deferred", "moved", "superseded")
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
LIFECYCLE_PREFIX_PATTERN = r"(?:[0-9a-hjkmnp-tv-z]{5}|00000)"

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
