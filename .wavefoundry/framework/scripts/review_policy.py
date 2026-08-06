"""Review-policy normalization, selection, receipts, and carrier authority.

This module is deliberately stdlib-only.  Lifecycle handlers, docs lint,
upgrade, rendering, and tests consume the same vocabulary rather than keeping
parallel mode, trigger, or carrier lists.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from gardener_metadata import canonical_review_policy_body


DELIVERY_MODES = ("disabled", "targeted", "universal")
FRESH_INSTALL_DELIVERY_MODE = "targeted"
TARGETED_DEFAULT_COUNCIL_REDUCTION_MIN = 0.20
TARGETED_DEFAULT_LANE_REDUCTION_MIN = 0.15
REVIEW_POLICY_SCHEMA_VERSION = 1
REVIEW_POLICY_EVALUATOR_VERSION = 4
REVIEW_POLICY_RECEIPT_RECORD_TYPE = "review_policy_receipt"
REVIEW_POLICY_REPREPARE_MARKER = "review-policy-reprepare-required"
GENESIS_RECEIPT_PARENT = "genesis"

REVIEW_LANE_ORDER = (
    "code-reviewer",
    "qa-reviewer",
    "architecture-reviewer",
    "docs-contract-reviewer",
    "release-reviewer",
    "performance-reviewer",
    "security-reviewer",
)

RISK_TRIGGER_LANES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("code-reviewer", (".py", ".js", ".ts", ".go", ".rs", "src/", "framework/scripts/")),
    ("qa-reviewer", ("tests/",)),
    ("architecture-reviewer", ("docs/architecture", "docs/architecture.md")),
    ("docs-contract-reviewer", ("framework/seeds/", "docs/prompts/", "docs/specs/")),
    ("release-reviewer", ("upgrade_wavefoundry.py", "build_pack.py")),
)

# Whole-document tokens used ONLY for a change doc that declares no repo-relative
# targets in `## Serialization Points`. This is the migration bridge: an
# un-migrated plan keeps exactly the coverage it had, including the known false
# positives of prose scoring, until its author declares real targets and earns
# the precise roster above. It deliberately OMITS `security-reviewer` and
# `performance-reviewer`, whose retirement to request-only is a recorded decision
# that applies to declared and undeclared documents alike.
LEGACY_WHOLE_DOCUMENT_TRIGGER_LANES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("code-reviewer", ("-feat ", "-enh ", "-refactor ", ".py", ".js", ".ts", ".go", ".rs", "src/", "framework/scripts/")),
    ("qa-reviewer", ("-bug ", "tests/", "regression", "test harness", "fixture path")),
    ("architecture-reviewer", ("docs/architecture", "protocol boundary", "ownership change", "state machine", "public abi")),
    ("docs-contract-reviewer", ("framework/seeds/", "docs/prompts/", "docs/specs/", "public contract")),
    ("release-reviewer", ("upgrade_wavefoundry.py", "build_pack.py", "release artifact", "distribution boundary")),
)

FULL_COUNCIL_TRIGGER_FIELDS = (
    "contract_or_required_ac_semantics_changed",
    "release_or_upgrade_changed",
    "trust_boundary_changed",
    "permission_boundary_changed",
    "architecture_or_ownership_changed",
    "cross_component_protocol_or_state_changed",
    "failure_or_readiness_semantics_changed",
    "cross_platform_changed",
)
FULL_COUNCIL_TRIGGER_TOKENS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("contract_or_required_ac_semantics_changed", ("required ac semantics", "public contract", "contract semantics")),
    ("release_or_upgrade_changed", ("upgrade boundary", "release boundary", "release artifact", "distribution boundary")),
    ("trust_boundary_changed", ("trust boundary", "security boundary", "privilege boundary")),
    ("permission_boundary_changed", ("permission boundary", "permission model", "access control boundary")),
    ("architecture_or_ownership_changed", ("architecture ownership", "ownership change", "architecture boundary")),
    ("cross_component_protocol_or_state_changed", ("cross-component protocol", "cross component protocol", "shared state protocol")),
    ("failure_or_readiness_semantics_changed", ("failure semantics", "readiness semantics", "fail-open", "fail-closed")),
    ("cross_platform_changed", ("cross-platform", "cross platform", "windows", "macos", "linux")),
)

RETIRED_LIFECYCLE_TOKENS = (
    "pre-implementation-review",
    "pre-implementation review gate",
    "pre-implementation gate reconciliation",
    "## pre-implementation gate",
    "continues with implementation-time and final review passes",
    "collect required review outputs for all admitted changes",
    "all review gates satisfied?",
    "reviewer and persona lanes with no shared dependencies run concurrently",
    "runs parallel reviewer lanes (those with no shared dependencies) concurrently",
    "reviewer loop",
    "fix and re-run reviewer",
    "blocking findings return the wave to implementation (level 2 loop)",
    "reviewers participate during implementation",
    "implement and review in one pass",
    "requires a structured `prepare-council` verdict line",
    "not sufficient for the lifecycle gate",
    "lifecycle gate only accepts that structured verdict",
    "`wf_prepare_wave` signals this step with `status: \"ready_for_council_review\"`",
    "verify that the prior prepare-council verdict was structured and machine-readable",
    "the recorded verdict must be a structured `prepare-council` line",
    "recorded verdict must be written back into `## review checkpoints` as a structured `prepare-council` line",
)

UPGRADE_POLICY_MARKER_BEGIN = "<!-- wavefoundry:review-policy-upgrade:begin -->"
UPGRADE_POLICY_MARKER_END = "<!-- wavefoundry:review-policy-upgrade:end -->"
UPGRADE_POLICY_BLOCK = f"""{UPGRADE_POLICY_MARKER_BEGIN}
## Versioned review-policy and bridge recovery

Upgrade maps legacy review enablement to the current default: enabled projects become
`enabled=true, delivery_mode=targeted`; disabled projects become
`enabled=false, delivery_mode=disabled`. The structured upgrade result reports the
selected delivery mode. Every non-closed declared wave is marked for re-Prepare when
the migration changes the policy (a no-op migration marks nothing); closed wave
Markdown and ledgers remain immutable. After the upgrade reload—or a
restart when `runner_stale` or cutover requires one—check from a fresh turn. If the
catalog remains stale, reconnect MCP, then restart as the final fallback. Once current,
use `wf_list_waves` for compact wave metrics and `memory_brief` for the active-memory
budget and any consolidation candidates. If `memory_brief` reports
`curation_required=true` or returns consolidation candidates, recommend the public
**Review memories** shortcut (alias **Memory review**); Upgrade never auto-curates or
purges memory.

Every upgrade also reconciles shortcut discovery merge-safely: ensure the canonical
**Review memories** entry exists in `AGENTS.md` and `docs/prompts/index.md`, and ensure
`docs/prompts/prompt-surface-manifest.json` contains exactly the canonical shortcut
`Review memories` for `docs/prompts/memory-review.prompt.md` (the alias stays in the
human-readable surfaces). Preserve project-authored additions and prose outside the
framework-owned regions; never replace an entire discovery surface to add this entry. While
`.wavefoundry/upgrade-in-progress.json` exists, lifecycle, review-evidence,
context-efficiency, memory, docs, and index publication is blocked except the named
memory-recovery phase.

Feature packs carry integer `upgrade_protocol_version` and
`minimum_runner_protocol`. `upgrade_protocol_invalid` means the pack is missing,
malformed, import-incomplete, or incompatible and is refused before extraction.
`bridge_release_required` means the installed protocol-1 runner must not extract the
feature. Use the same single matching `wavefoundry-<version>.zip` release package.
The agent stops the dashboard, disconnects/stops every Wavefoundry MCP server for
the repository, and leaves the current host session idle; it then runs the exact
`command_argv` through its ordinary non-MCP shell. No operator-entered terminal
command is required. The package records that confirmation, verifies both embedded
archives, swaps only
`.wavefoundry/framework/`, and immediately executes the hash-bound feature hop.
Fully restart every attached host and follow the package's structured recovery result;
retry or resume any retained failed phase until the checkpoint reaches terminal cleanup.
An already-loaded protocol-1 MCP wrapper predates the current response cap and cannot
be changed by the incoming pack. Its compact bridge JSON is emitted last; if the host
rejects or truncates that one legacy response, the agent uses its ordinary shell to
detect and execute the single installed package after Wavefoundry services stop. The
operator still does not copy or type a terminal command.
{UPGRADE_POLICY_MARKER_END}"""

REVIEW_POLICY_SURFACE_MARKER_BEGIN = "<!-- wavefoundry:review-policy:begin -->"
REVIEW_POLICY_SURFACE_MARKER_END = "<!-- wavefoundry:review-policy:end -->"
REVIEW_POLICY_SURFACE_BLOCKS = {
    "docs/prompts/prepare-wave.prompt.md": """## Review-policy readiness

Prepare Wave is the single readiness authority. It evaluates the configured
`wave_review.delivery_mode`, records the review-policy receipt, and requires a
re-Prepare whenever policy inputs change before implementation.""",
    "docs/prompts/review-wave.prompt.md": """## Review-policy delivery

Review Wave consumes the shared delivery evaluator selected by the current
review-policy receipt. After a repair, search the same root cause and adjacent
repair class before focused reverification; broaden review only when a
load-bearing boundary changed.""",
    "docs/prompts/close-wave.prompt.md": """## Review-policy closure

Close Wave consumes the same shared delivery evaluator and current
`wave_review.delivery_mode`; it performs closure-only delta checks and does not
recompute a parallel review policy.""",
    "docs/prompts/implement-wave.prompt.md": """## Review-policy implementation

Prepare Wave is the single readiness authority. Implementation consumes the
current shared delivery evaluator and never recreates a separate readiness
review gate.""",
    "docs/prompts/agents/review-wave.prompt.md": """## Review-policy repair guidance

Use the shared delivery evaluator. After a repair, check the same root cause
and adjacent repair class before focused reverification; broaden review only
when a load-bearing boundary changed.""",
    "docs/prompts/council-review.prompt.md": """## Review-policy council phases

Council approval is phase-scoped: the readiness council and delivery council
record independent current approval_phase evidence.""",
    "docs/references/project-overview.md": """## Review-policy baseline

Wave delivery follows the configured review policy and its current
`delivery_mode`.""",
    "docs/contributing/build-and-verification.md": """## Review-policy release baseline

Release verification consumes the current review policy and preserves the
documented protocol bridge boundary.""",
    "docs/contributing/review-and-evals.md": """## Review-policy evidence baseline

The review policy requires phase-scoped integrity evidence. After repair,
check the same root cause and adjacent repair class before focused repair
reverification.""",
    "docs/contributing/feature-wave-lifecycle-overview.md": """## Review-policy lifecycle baseline

The review policy records phase-scoped approval_phase evidence separately for
readiness and delivery.""",
    "docs/specs/mcp-tool-surface.md": """## Review-policy tool baseline

Typed review tools preserve the current policy receipt, phase-scoped
approval_phase evidence, and evidence-integrity checks.""",
    "docs/references/dashboard-adapter-model.md": """## Review-policy dashboard baseline

Dashboard review state projects the current review-policy receipt rather than
deriving a parallel policy.""",
}

# Production docs lint consumes these anchors for every registered carrier.
# Each obligation is a semantic one-of set, not a byte-exact copy of prose.
REVIEW_POLICY_OBLIGATION_ANCHORS: dict[str, tuple[str, ...]] = {
    "policy": ("delivery_mode", "review policy", "review-policy"),
    "receipt": ("policy receipt", "review-policy receipt"),
    "reprepare": ("re-prepare", "reprepare"),
    "shared_evaluator": ("shared delivery evaluator", "review wave"),
    "repair_census": ("same root cause", "repair class", "focused repair"),
    "closure_only": ("closure-only", "closure only"),
    "policy_migration": ("delivery_mode", "review-policy"),
    "single_prepare": ("prepare wave", "prepare is the single"),
    "phase_currency": ("approval_phase", "readiness council", "delivery council"),
    "bridge": ("bridge",),
    "integrity": ("integrity",),
    "phase": ("approval_phase", "phase-scoped", "readiness council"),
    "dashboard_policy": ("policy receipt", "review-policy"),
    "executable_review": ("wave:executable-review-evidence",),
}

@dataclass(frozen=True)
class ReviewPolicyCarrier:
    source: str
    destination: str
    owner: str
    obligations: tuple[str, ...]
    conditional_existing: bool = False
    create_if_missing: bool = True


REVIEW_POLICY_CARRIER_REGISTRY = (
    ReviewPolicyCarrier("lifecycle:prepare-wave.prompt.md", "docs/prompts/prepare-wave.prompt.md", "renderer", ("policy", "receipt", "reprepare")),
    ReviewPolicyCarrier("lifecycle:review-wave.prompt.md", "docs/prompts/review-wave.prompt.md", "renderer", ("policy", "shared_evaluator", "repair_census")),
    ReviewPolicyCarrier("lifecycle:close-wave.prompt.md", "docs/prompts/close-wave.prompt.md", "renderer", ("policy", "shared_evaluator", "closure_only")),
    ReviewPolicyCarrier("seed:160", "docs/prompts/upgrade-wavefoundry.prompt.md", "lifecycle_reconciler", ("policy_migration", "reprepare", "bridge")),
    ReviewPolicyCarrier("baseline:implement", "docs/prompts/implement-wave.prompt.md", "lifecycle_reconciler", ("single_prepare", "shared_evaluator")),
    ReviewPolicyCarrier("baseline:review", "docs/prompts/review-wave.prompt.md", "lifecycle_reconciler", ("shared_evaluator", "repair_census")),
    ReviewPolicyCarrier("baseline:agent-review", "docs/prompts/agents/review-wave.prompt.md", "lifecycle_reconciler", ("shared_evaluator", "repair_census")),
    ReviewPolicyCarrier("baseline:council", "docs/prompts/council-review.prompt.md", "lifecycle_reconciler", ("phase_currency",)),
    ReviewPolicyCarrier("baseline:prepare", "docs/prompts/prepare-wave.prompt.md", "lifecycle_reconciler", ("single_prepare", "receipt")),
    # Portable policy prose is framework-owned only inside marker-bounded
    # regions. The companion direct_docs rows below remain the file-wide
    # validation authority for project-authored content.
    ReviewPolicyCarrier("policy-baseline:implement", "docs/prompts/implement-wave.prompt.md", "renderer", ()),
    ReviewPolicyCarrier("policy-baseline:agent-review", "docs/prompts/agents/review-wave.prompt.md", "renderer", ()),
    ReviewPolicyCarrier("policy-baseline:council", "docs/prompts/council-review.prompt.md", "renderer", ()),
    ReviewPolicyCarrier("docs/references/project-overview.md", "docs/references/project-overview.md", "direct_docs", ("policy",), True, False),
    ReviewPolicyCarrier("policy-baseline:project-overview", "docs/references/project-overview.md", "renderer", (), True, False),
    ReviewPolicyCarrier("docs/contributing/build-and-verification.md", "docs/contributing/build-and-verification.md", "direct_docs", ("policy", "bridge"), True, False),
    ReviewPolicyCarrier("policy-baseline:build-and-verification", "docs/contributing/build-and-verification.md", "renderer", (), True, False),
    ReviewPolicyCarrier("docs/contributing/review-and-evals.md", "docs/contributing/review-and-evals.md", "direct_docs", ("policy", "integrity", "phase", "repair_census"), True, False),
    ReviewPolicyCarrier("policy-baseline:review-and-evals", "docs/contributing/review-and-evals.md", "renderer", (), True, False),
    ReviewPolicyCarrier("docs/contributing/feature-wave-lifecycle-overview.md", "docs/contributing/feature-wave-lifecycle-overview.md", "direct_docs", ("policy", "phase"), True, False),
    ReviewPolicyCarrier("policy-baseline:feature-wave-lifecycle", "docs/contributing/feature-wave-lifecycle-overview.md", "renderer", (), True, False),
    ReviewPolicyCarrier("docs/specs/mcp-tool-surface.md", "docs/specs/mcp-tool-surface.md", "direct_docs", ("receipt", "integrity", "phase"), True, False),
    ReviewPolicyCarrier("policy-baseline:mcp-tool-surface", "docs/specs/mcp-tool-surface.md", "renderer", (), True, False),
    ReviewPolicyCarrier("docs/agents", "docs/agents", "direct_docs", ("policy", "repair_census"), True, False),
    ReviewPolicyCarrier("docs/references/dashboard-adapter-model.md", "docs/references/dashboard-adapter-model.md", "direct_docs", ("dashboard_policy",), True, False),
    ReviewPolicyCarrier("policy-baseline:dashboard-adapter", "docs/references/dashboard-adapter-model.md", "renderer", (), True, False),
    ReviewPolicyCarrier("211-guru.prompt.md", "docs/agents/guru.md", "renderer", ("executable_review",), False, False),
    ReviewPolicyCarrier("239-qa-reviewer.prompt.md", "docs/agents/qa-reviewer.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("214-architecture-reviewer.prompt.md", "docs/agents/architecture-reviewer.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("212-performance-reviewer.prompt.md", "docs/agents/performance-reviewer.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("221-code-reviewer.prompt.md", "docs/agents/code-reviewer.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("213-security-reviewer.prompt.md", "docs/agents/security-reviewer.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("050-agent-entry-surface-bootstrap.prompt.md", "docs/agents/docs-contract-reviewer.md", "renderer", ("executable_review",), True, False),
    ReviewPolicyCarrier("050-agent-entry-surface-bootstrap.prompt.md", "docs/agents/release-reviewer.md", "renderer", ("executable_review",), True, False),
    ReviewPolicyCarrier("225-red-team.prompt.md", "docs/agents/specialists/red-team.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("216-reality-checker.prompt.md", "docs/agents/specialists/reality-checker.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("215-wave-council.prompt.md", "docs/agents/specialists/wave-council.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("236-archetype-council.prompt.md", "docs/agents/specialists/archetype-council.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("217-senior-engineering-challenger.prompt.md", "docs/agents/specialists/senior-engineering-challenger.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("236-archetype-council.prompt.md", "docs/prompts/archetype-council.prompt.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("237-council-review.prompt.md", "docs/prompts/council-review.prompt.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("100-project-prompt-surface-bootstrap.prompt.md", "docs/prompts/review-wave.prompt.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("100-project-prompt-surface-bootstrap.prompt.md", "docs/prompts/agents/review-wave.prompt.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("100-project-prompt-surface-bootstrap.prompt.md", "docs/prompts/create-wave.prompt.md", "renderer", ("executable_review",)),
    ReviewPolicyCarrier("209-agent-harness-core.prompt.md", "docs/contributing/review-and-evals.md", "renderer", ("executable_review",)),
)

# Compatibility exports are derived views, never parallel authorities.
LIFECYCLE_RECONCILER_CARRIERS = tuple(
    dict.fromkeys(
        carrier.destination
        for carrier in REVIEW_POLICY_CARRIER_REGISTRY
        if carrier.owner == "lifecycle_reconciler"
    )
)


def review_policy_carriers(owner: str | None = None) -> tuple[ReviewPolicyCarrier, ...]:
    if owner is None:
        return REVIEW_POLICY_CARRIER_REGISTRY
    return tuple(
        carrier for carrier in REVIEW_POLICY_CARRIER_REGISTRY
        if carrier.owner == owner
    )


def normalize_wave_review_policy(
    value: object,
    *,
    allow_legacy_missing_mode: bool = False,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    """Validate the exact enablement/mode truth table."""

    if not isinstance(value, dict):
        return None, ("wave_review must be an object",)
    enabled = value.get("enabled")
    if not isinstance(enabled, bool):
        return None, ("wave_review.enabled must be boolean",)
    mode = value.get("delivery_mode")
    if mode is None and allow_legacy_missing_mode:
        mode = FRESH_INSTALL_DELIVERY_MODE if enabled else "disabled"
    errors: list[str] = []
    if mode not in DELIVERY_MODES:
        errors.append(
            "wave_review.delivery_mode must be disabled, targeted, or universal"
        )
    elif (not enabled and mode != "disabled") or (enabled and mode == "disabled"):
        errors.append(
            "wave_review.enabled and delivery_mode violate the policy truth table"
        )
    if errors:
        return None, tuple(errors)
    normalized = dict(value)
    normalized["enabled"] = enabled
    normalized["delivery_mode"] = mode
    return normalized, ()


def migrate_wave_review_policy(value: object) -> dict[str, Any]:
    """Map a legacy boolean policy to its enforcement-preserving explicit mode."""

    if value is None:
        return {"enabled": True, "delivery_mode": FRESH_INSTALL_DELIVERY_MODE}

    normalized, errors = normalize_wave_review_policy(
        value, allow_legacy_missing_mode=True
    )
    if errors or normalized is None:
        raise ValueError("; ".join(errors))
    return normalized


def targeted_default_adoption_allowed(
    *,
    council_reduction: float,
    specialist_lane_reduction: float,
    omitted_required_lanes: int,
    explicit_operator_decision: bool = False,
) -> bool:
    """Return whether measured evidence permits a targeted install default.

    This is intentionally separate from per-wave policy evaluation.  It is a
    release/adoption gate: safety (zero omissions) is mandatory unless the
    operator explicitly records a product-policy decision, and both measured
    materiality thresholds must otherwise pass.
    """

    if explicit_operator_decision:
        return True
    return (
        omitted_required_lanes == 0
        and council_reduction >= TARGETED_DEFAULT_COUNCIL_REDUCTION_MIN
        and specialist_lane_reduction >= TARGETED_DEFAULT_LANE_REDUCTION_MIN
    )


def extract_requested_review_lanes(wave_text: str) -> tuple[str, ...]:
    match = re.search(
        r"(?mi)^-\s*Requested review lanes\s*:\s*(?P<value>[^\n]*)$",
        wave_text,
    )
    if match is None:
        return ()
    value = match.group("value").strip()
    if not value or value.lower() in {"none", "—", "-"}:
        return ()
    return tuple(
        dict.fromkeys(
            item.strip().strip("`")
            for item in value.split(",")
            if item.strip().strip("`")
        )
    )


_SERIALIZATION_POINTS_HEADING_RE = re.compile(
    r"(?mi)^##[ \t]+Serialization Points\s*$"
)
# Any repo-relative path, not a fixed prefix allowlist. An earlier form accepted
# only `.wavefoundry/`, `docs/`, `src/` and `tests/`, which silently returned NO
# paths — and therefore no automatic lanes and no diagnostic — for any target
# repository laid out as `lib/`, `pkg/`, `cmd/`, `internal/` or `app/`. Wavefoundry
# must work against any configured target repo, so the shape is the contract: one
# or more `segment/` parts followed by a final segment. Bare root-level files stay
# out deliberately; requiring a separator is what keeps ordinary Serialization
# Points prose from being read as a declared target.
# The final segment may be empty so an explicit directory declaration keeps its
# trailing separator; `_is_declared_target` relies on that separator to accept
# `docs/architecture/` while still rejecting slashed prose like `runner/test`.
_REPO_PATH_RE = re.compile(
    r"(?<![\w./-])(?P<path>(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]*)"
)


def serialization_point_paths(change_text: str) -> tuple[str, ...]:
    """Return explicit repo-relative targets from the one declared section."""

    match = _SERIALIZATION_POINTS_HEADING_RE.search(change_text)
    if match is None:
        return ()
    tail = change_text[match.end():]
    next_heading = re.search(r"(?m)^##[ \t]+", tail)
    body = tail[:next_heading.start()] if next_heading else tail
    return tuple(
        dict.fromkeys(
            candidate
            for candidate in (
                m.group("path").lower() for m in _REPO_PATH_RE.finditer(body)
            )
            if _is_declared_target(candidate)
        )
    )


def _is_declared_target(candidate: str) -> bool:
    """Reject slashed English prose that is not a file or directory reference.

    Serialization Points is written for humans as well as the evaluator, and
    real plans say things like "the runner/test corpus" or "stop
    dashboard/index activity". Accepting those as declared targets is not just
    noise: a document misclassified as DECLARED loses the undeclared-document
    fallback and can end up with no required lanes at all. A declared target
    therefore has to look like one — an extension on its final segment, or an
    explicit trailing separator.
    """

    if candidate.endswith("/"):
        return True
    return "." in candidate.rsplit("/", 1)[-1]


def _path_token_matches(token: str, path: str) -> bool:
    """Match extensions and path fragments at path boundaries, never substrings.

    A directory-shaped token matches at a segment boundary, and a bare token
    matches the path itself, its trailing segment, OR any directory prefix it
    names. That last case is load-bearing: without it a token like
    ``docs/architecture`` could only ever match the literal bare string, so
    `docs/architecture/current-state.md` selected NOTHING and the
    architecture lane became unreachable from any real declared target.
    """

    if token.startswith("."):
        return path.endswith(token)
    if token.endswith("/"):
        return path.startswith(token) or ("/" + token) in path
    return (
        path == token
        or path.endswith("/" + token)
        or path.startswith(token + "/")
        or ("/" + token + "/") in path
    )


def select_required_review_lanes(
    *,
    requested_lanes: Iterable[str],
    project_lanes: Iterable[str],
    change_texts: Iterable[str],
) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    """Derive an ordered risk-selected delivery roster and its reasons."""

    # Per-document, because the declared-target contract is per-document: a doc
    # that declares paths is scored on them, and a doc that declares none FAILS
    # OPEN to whole-text scoring rather than to an empty roster.
    #
    # Without this, path-only scoring is retroactive. Measured over the corpus at
    # delivery: 775 change docs lost lanes and NONE gained any, and five of the
    # six non-closed change docs collapsed to zero required lanes, because every
    # plan authored before this contract describes its targets in prose. A change
    # that removes all required review from every existing readied wave is a far
    # worse failure than the over-recruitment it set out to fix, so an undeclared
    # document keeps exactly the coverage it had.
    undeclared: list[str] = []
    paths: list[str] = []
    for text in change_texts:
        text_s = str(text)
        found = serialization_point_paths(text_s)
        if found:
            paths.extend(found)
        else:
            undeclared.append(text_s.lower())
    # Adoption is a property of the WAVE, not of each document. As soon as any
    # admitted change declares real targets, the wave has adopted the contract
    # and prose scoring stays off for all of its documents — otherwise one
    # un-migrated sibling would resurrect exactly the false positives this
    # change exists to remove. The fallback is for a wave that declares nothing
    # anywhere, which is every wave planned before this contract shipped.
    if paths:
        undeclared = []
    reasons: dict[str, list[str]] = {}
    selected: list[str] = []

    def add(lane: str, reason: str) -> None:
        if lane not in selected:
            selected.append(lane)
        reasons.setdefault(lane, []).append(reason)

    for lane in requested_lanes:
        add(str(lane), "requested by operator/project wave input")
    for lane in project_lanes:
        add(str(lane), "required by project policy")
    undeclared_corpus = "\n".join(undeclared)
    legacy_tokens = dict(LEGACY_WHOLE_DOCUMENT_TRIGGER_LANES)
    for lane, tokens in RISK_TRIGGER_LANES:
        matched = tuple(
            token for token in tokens
            if any(_path_token_matches(token, path) for path in paths)
        )
        if matched:
            add(lane, "risk trigger: " + ", ".join(matched[:4]))
        if not undeclared_corpus:
            continue
        legacy = tuple(
            token for token in legacy_tokens.get(lane, ())
            if token in undeclared_corpus
        )
        if legacy and not matched:
            # Named distinctly so the fallback is visible in the receipt rather
            # than passing as a declared-target match.
            add(
                lane,
                "risk trigger (undeclared targets, whole-document fallback): "
                + ", ".join(legacy[:4]),
            )
    ordered = tuple(
        [lane for lane in REVIEW_LANE_ORDER if lane in selected]
        + [lane for lane in selected if lane not in REVIEW_LANE_ORDER]
    )
    return ordered, {lane: tuple(reasons[lane]) for lane in ordered}


def policy_input_digest(
    *,
    wave_review: Mapping[str, Any],
    project_lanes: Iterable[str],
    review_policies: object,
    changes: Iterable[tuple[str, str, bytes]],
    requested_lanes: Iterable[str],
) -> str:
    payload = {
        "schema_version": REVIEW_POLICY_SCHEMA_VERSION,
        "evaluator_version": REVIEW_POLICY_EVALUATOR_VERSION,
        "wave_review": dict(wave_review),
        "project_required_review_lanes": list(project_lanes),
        "review_policies": review_policies,
        "changes": [
            {
                "change_id": change_id,
                "kind": kind,
                "sha256": hashlib.sha256(canonical_review_policy_body(body)).hexdigest(),
            }
            for change_id, kind, body in changes
        ],
        "requested_lanes": list(requested_lanes),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def delivery_council_required(
    delivery_mode: str,
    *,
    delivered_boundary_triggers: Iterable[str] = (),
    current_heads: Iterable[Mapping[str, Any]] = (),
) -> bool:
    if delivery_mode == "universal":
        return True
    if delivery_mode == "disabled":
        return False
    if delivery_mode != "targeted":
        raise ValueError("unknown delivery mode")
    if any(str(trigger) in FULL_COUNCIL_TRIGGER_FIELDS for trigger in delivered_boundary_triggers):
        return True
    return any(
        any(head.get(field) is True for field in FULL_COUNCIL_TRIGGER_FIELDS)
        for head in current_heads
    )


def extract_full_council_triggers(texts: Iterable[str]) -> tuple[str, ...]:
    """Map admitted/delivered prose to the canonical full-Council fields."""

    corpus = "\n".join(str(text).lower() for text in texts)
    selected: list[str] = []
    for field, tokens in FULL_COUNCIL_TRIGGER_TOKENS:
        explicit = bool(
            re.search(rf"(?mi)\b{re.escape(field)}\b\s*[:=]\s*true\b", corpus)
        )
        if explicit or any(token in corpus for token in tokens):
            selected.append(field)
    return tuple(selected)


def receipt_semantic_fields(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: receipt[key]
        for key in (
            "schema_version",
            "evaluator_version",
            "policy_input_digest",
            "delivery_mode",
            "primer_depth",
            "council_seats",
            "requested_lanes",
            "required_lanes",
            "delivery_council_required",
        )
    }


def derive_receipt_id(
    semantic_fields: Mapping[str, Any], parent_receipt_id: str
) -> str:
    payload = {
        "parent_receipt_id": parent_receipt_id,
        "semantic": dict(semantic_fields),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return f"review-policy-{digest}"


def current_policy_receipt(
    records: Iterable[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    current: Mapping[str, Any] | None = None
    for record in records:
        if record.get("record_type") == REVIEW_POLICY_RECEIPT_RECORD_TYPE:
            current = record
    return current


def build_policy_receipt(
    semantic_fields: Mapping[str, Any],
    current: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, bool]:
    """Return (new receipt or current receipt, append_required)."""

    if current is not None and receipt_semantic_fields(current) == dict(semantic_fields):
        return dict(current), False
    parent = (
        str(current["receipt_id"])
        if current is not None
        else GENESIS_RECEIPT_PARENT
    )
    receipt: dict[str, Any] = {
        "record_type": REVIEW_POLICY_RECEIPT_RECORD_TYPE,
        "receipt_id": derive_receipt_id(semantic_fields, parent),
        **dict(semantic_fields),
    }
    if current is not None:
        receipt["supersedes_receipt_id"] = parent
    return receipt, True


def validate_policy_receipt(record: Mapping[str, Any]) -> tuple[str, ...]:
    required = {
        "record_type", "receipt_id", "schema_version", "evaluator_version",
        "policy_input_digest", "delivery_mode", "primer_depth", "council_seats",
        "requested_lanes", "required_lanes", "delivery_council_required",
    }
    optional = {"supersedes_receipt_id"}
    errors: list[str] = []
    keys = set(record)
    if required - keys:
        errors.append("review_policy_receipt missing fields: " + ", ".join(sorted(required - keys)))
    if keys - required - optional:
        errors.append("review_policy_receipt has unsupported fields: " + ", ".join(sorted(keys - required - optional)))
    if record.get("delivery_mode") not in DELIVERY_MODES:
        errors.append("review_policy_receipt delivery_mode is invalid")
    for field in ("council_seats", "requested_lanes", "required_lanes"):
        value = record.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            errors.append(f"review_policy_receipt {field} must be a string list")
    if not isinstance(record.get("delivery_council_required"), bool):
        errors.append("review_policy_receipt delivery_council_required must be boolean")
    for field in ("receipt_id", "policy_input_digest", "primer_depth"):
        if not isinstance(record.get(field), str) or not str(record.get(field)).strip():
            errors.append(f"review_policy_receipt {field} must be a non-empty string")
    for field in ("schema_version", "evaluator_version"):
        if not isinstance(record.get(field), int) or isinstance(record.get(field), bool):
            errors.append(f"review_policy_receipt {field} must be an integer")
    return tuple(errors)


def has_reprepare_marker(wave_text: str) -> bool:
    return bool(
        re.search(
            rf"(?mi)^review-policy-reprepare-required:\s*true\s*$",
            wave_text,
        )
    )


def set_reprepare_marker(wave_text: str, required: bool) -> str:
    line = f"{REVIEW_POLICY_REPREPARE_MARKER}: {'true' if required else 'false'}"
    pattern = re.compile(
        rf"(?mi)^{re.escape(REVIEW_POLICY_REPREPARE_MARKER)}:\s*(?:true|false)\s*$"
    )
    if pattern.search(wave_text):
        return pattern.sub(line, wave_text, count=1)
    header_end = wave_text.find("\n## ")
    if header_end < 0:
        return wave_text.rstrip() + "\n" + line + "\n"
    return wave_text[:header_end].rstrip() + "\n" + line + wave_text[header_end:]


def contained_relative_path(root: Path, relative: str) -> Path:
    """Resolve a registry destination without permitting symlink escape."""

    root_real = root.resolve(strict=True)
    target = root / relative
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"review-policy carrier may not traverse symlink: {relative}")
    resolved = target.resolve(strict=False)
    if not resolved.is_relative_to(root_real):
        raise ValueError(f"review-policy carrier escapes root: {relative}")
    return target


__all__ = [
    "DELIVERY_MODES", "FRESH_INSTALL_DELIVERY_MODE",
    "FULL_COUNCIL_TRIGGER_FIELDS", "FULL_COUNCIL_TRIGGER_TOKENS",
    "GENESIS_RECEIPT_PARENT",
    "LIFECYCLE_RECONCILER_CARRIERS", "RETIRED_LIFECYCLE_TOKENS",
    "REVIEW_LANE_ORDER", "REVIEW_POLICY_CARRIER_REGISTRY",
    "REVIEW_POLICY_EVALUATOR_VERSION", "REVIEW_POLICY_RECEIPT_RECORD_TYPE",
    "REVIEW_POLICY_REPREPARE_MARKER", "REVIEW_POLICY_SCHEMA_VERSION",
    "UPGRADE_POLICY_BLOCK", "UPGRADE_POLICY_MARKER_BEGIN",
    "UPGRADE_POLICY_MARKER_END",
    "TARGETED_DEFAULT_COUNCIL_REDUCTION_MIN",
    "TARGETED_DEFAULT_LANE_REDUCTION_MIN",
    "ReviewPolicyCarrier", "build_policy_receipt", "contained_relative_path",
    "current_policy_receipt", "delivery_council_required", "derive_receipt_id",
    "extract_full_council_triggers",
    "review_policy_carriers",
    "extract_requested_review_lanes", "has_reprepare_marker",
    "migrate_wave_review_policy", "normalize_wave_review_policy",
    "policy_input_digest", "receipt_semantic_fields", "select_required_review_lanes",
    "set_reprepare_marker", "targeted_default_adoption_allowed",
    "validate_policy_receipt",
]
