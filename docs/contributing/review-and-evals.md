# Review and Evaluations

Owner: Engineering
Status: active
Last verified: 2026-07-16

## Review Lane Summary

| Lane | When Required | Gating |
|------|--------------|--------|
| `code-reviewer` | Non-trivial implementation changes | Yes — blocking findings return to implementation |
| `architecture-reviewer` | Cross-boundary or integration-contract changes | Yes |
| `qa-reviewer` | Bug fixes (always); acceptance criteria requiring coverage | Yes |
| `security-reviewer` | Trust boundary, guard mechanism, or allowed-roots changes | Yes |
| `docs-contract-reviewer` | `docs/specs/*.md` behavioral contract changes | Yes at wave closure |
| `performance-reviewer` | Indexing, search, or MCP response path changes | Advisory |
| `release-reviewer` | Packaging, VERSION, or distribution format changes | Yes |
| `wave-council-readiness` | Every wave before implementation (`wave_review.enabled`) | Yes |
| `wave-council-delivery` | Every wave after implementation and before closure (`wave_review.enabled`) | Yes |

All review lanes follow the **Retrieval Posture (All Lanes)** in `docs/contributing/agent-team-workflow.md` — MCP retrieval tools first, and how-many/blast-radius claims backed by `code_references`/`code_callhierarchy`, never a sampled grep.

## Review Protocol Ownership

Seed `209-agent-harness-core.prompt.md` is the only full executable-review-evidence protocol and checklist. Other sources own routing and lane-specific additions; they do not fork the shared protocol.

| Canonical owner | Carrier / rendered target | Init owner | Upgrade / refresh owner | Verification fixture |
|-----------------|---------------------------|------------|-------------------------|----------------------|
| Seed 209 | Shared protocol and Evidence Record schema | Framework seed pack | Framework seed pack | `ReviewEvidenceStateMachineTests` |
| Seed 007 | Framework review-system overview | Framework seed pack | Seeds 150 / 160 | `ReviewProtocolCarrierRegistryTests` |
| Seed 211 | `docs/agents/guru.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 212 | `docs/agents/performance-reviewer.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 213 | `docs/agents/security-reviewer.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 214 | `docs/agents/architecture-reviewer.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 215 | `docs/agents/specialists/wave-council.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 216 | `docs/agents/specialists/reality-checker.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 217 | `docs/agents/specialists/senior-engineering-challenger.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 221 | `docs/agents/code-reviewer.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 225 | `docs/agents/specialists/red-team.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 236 | `docs/agents/specialists/archetype-council.md`; `docs/prompts/archetype-council.prompt.md` | Seeds 050 / 100 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 237 | `docs/prompts/council-review.prompt.md` | Seed 100 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 239 | `docs/agents/qa-reviewer.md` | Seeds 050 / 100 + public renderer | Seeds 150 / 160 + public renderer | `PublicSetupReviewProtocolIntegrationTests`; `PublicUpgradeReviewProtocolIntegrationTests` |
| Seed 100 | `docs/prompts/review-wave.prompt.md`; `docs/prompts/agents/review-wave.prompt.md`; `docs/prompts/create-wave.prompt.md` | Seed 100 + public renderer | Seeds 150 / 160 + public renderer | `PublicSetupReviewProtocolIntegrationTests`; `PublicUpgradeReviewProtocolIntegrationTests` |
| Seeds 050 + 209 | Existing/enabled `docs/agents/docs-contract-reviewer.md`; `docs/agents/release-reviewer.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Seed 209 | `docs/contributing/review-and-evals.md` | Public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| Registered canonical role | Existing/enabled `.claude/agents/<role>.md`; `.codex/skills/agent-role-<role>/SKILL.md`; canonical Guru wrappers `.claude/agents/guru.md` and `.codex/skills/auto-guru/SKILL.md` | Seed 050 + public renderer | Seeds 150 / 160 + public renderer | `ReviewProtocolCarrierRegistryTests` |
| `review_evidence.py` + `wave_record_review_evidence` | Fixed sibling `docs/waves/<wave>/events.jsonl` authority plus bounded count/hash proof in `docs/waves/review-evidence-adoptions.json`; generated Markdown current-head projection in `wave.md` | Seed 100 / `wave_create_wave`; framework MCP server | Direct-ledger validation; typed append on installed/upgraded servers; no consumer-history migration; retained-prefix mutation/refusal without invoking Git | `ReviewEvidenceStateMachineTests`; `WaveLifecycleMutationTests`; `WaveCreateScaffoldAlignmentTests`; build-pack/setup/upgrade distribution fixtures |

Fresh setup, full upgrade, direct `wf render-surfaces`, and self-host refresh converge on that renderer operation. Missing required canonical carriers are materialized from their installed seeds (or a bounded bootstrap pointer for multi-output owners); Guru, conditional repo-local reviewers, and arbitrary native wrappers remain existing/enabled-only. Newly created canonical Guru wrappers are reconciled after materialization in the same render pass. Malformed markers fail safe rather than authorizing whole-file replacement.

The machine contract is fail-closed. `wave.md` declares `review-evidence-source: events.jsonl`; the fixed sibling ledger—not the generated Markdown table—is the append-only authority. The typed `wave_record_review_evidence` tool serializes its event transaction under the project-global lock and refreshes the concise current-head projection on each write. A one-candidate run may reuse its finding evidence as universe proof, and an empty lightweight run needs only one run row, retaining reviewer `verification_context` without a separate dedup row. A synthesis links only to earlier `claim_kind: finding` evidence for the same finding. Approval records use `claim_id: approval:<signoff-key>` and bind the exact authority actor: `operator`, `wave-council`, or the named specialist lane; specialist and council approvals must be fresh and independent. Approval chronology is affected-lane scoped through `approval_recheck_lanes`; unrelated later synthesis does not stale another lane, while council remains scoped to full/council changes and operator approval remains final-wave scoped. Independence means the reviewer did not implement the repair and formed its own current-tree/test assessment before relying on prior findings or verdicts. Mandatory project orientation may disclose status or history, but it is context rather than evidence and does not by itself disqualify a fresh review. Lane reassessment is exact-lane, fresh, independent, and single-use. Universal census records include `residual_uncertainty_status` (`none | bounded | unresolved`) and `index_freshness` (`current | stale | unknown`). Operator waivers include scope, reason, and risk. When cycle-2 reverification completes after cycle 1, the typed writer derives the mandatory convergence checkpoint in that same identified bundle and atomic authority replacement; callers do not append a separate checkpoint event. Its `frozen_boundary` is the set of wave-current synthesis heads after the reverification, and later runs declare deviations or reopened findings explicitly.

The adoption ledger is a local monotonicity sensor, not an undeletable trust anchor. For each adopted wave it stores only the canonical-prefix `record_count` and domain-separated SHA-256. With adoption state retained, lifecycle validation rejects a missing/downgraded source declaration, missing event ledger, proof-ahead state, changed adopted prefix, or unadopted suffix without calling Git. Retained adoption also keeps that exact ledger excluded from semantic indexing when its declaration is missing or malformed, so an integrity failure cannot expose raw/superseded event history; unadopted lifecycle-shaped note files remain eligible. If both adoption state and the source declaration are deleted, no repository-local state remains that can distinguish prior adoption from a legacy wave; protect adoption state through ordinary repository access control, source control, or backup rather than recursively duplicating it.

## Readiness Checklist (Prepare Wave)

Before implementation begins, the wave-coordinator confirms:
- [ ] All admitted changes have consolidated change docs at `docs/waves/<wave-id>/`
- [ ] Required review lanes identified for each admitted change
- [ ] AC priority recorded on each change doc (`## AC priority`)
- [ ] product-owner acknowledgment recorded for product-impacting waves
- [ ] `qa-reviewer` confirmed for any bug fix (per `review_policies.require_qa_reviewer_for_bug_fixes`)
- [ ] `wave-council-readiness` signoff recorded in `## Review Evidence` when `wave_review.enabled`

## Wave Closure

**Closure requires all of the following:**

1. All changes marked `complete` or `deferred` with explicit rationale
2. All required review lanes from readiness are reconciled in `## Review checkpoints` (including deferred with rationale when applicable)
3. `wave-council-readiness` and `wave-council-delivery` signoffs are present in `## Review Evidence` when `wave_review.enabled`
4. Docs-contract review: recorded as performed (findings in `## Review checkpoints`) or `not applicable` with rationale, when any `docs/specs/*.md` changed during the wave
5. Journal distillation complete: any important implementation/review lessons added to relevant role or persona journals
6. Durable memory promoted to `docs/references/project-context-memory.md` (and other canonical docs when applicable)
7. `docs/agents/session-handoff.md` cleared or refreshed to reflect post-closure state
8. Chronology reconciled: `Status: completed`, `Completed at:` date, all change statuses finalized

**Closure is blocked until all eight items above are explicitly recorded in the wave record.**

**Secrets gate (enforced by `wave_close`):** Before calling `wave_close`, check `docs/scan-findings.json`. Any `pending` or `suspected-secret` entry **hard-blocks** close — run the security reviewer (`seed-213`) to classify each as `confirmed-secret` or `false-positive`. `confirmed-secret` entries do **not** block close (wave 1p5pz — classification is the acknowledgment); instead every close returns a non-blocking standing reminder (`confirmed_secrets` + `secrets_reminder` in the response `data`) that the agent presents to the operator. If the file is absent or has no unresolved entries, the gate passes automatically.

## Wave Council

The framework ships `wave_review.enabled: true` by default so the council surface is available without operator action. When `required_for_all_waves: true` (operator opt-in for enforcement), Wavefoundry requires a universal two-phase council pass for every wave:

- `wave-council-readiness` before implementation
- `wave-council-delivery` before closure

Wave Council runs a red-team adversarial primer (Phase 1) before fixed seats (Phase 2), then synthesizes. The full protocol — depth tiers, seat responsibilities, output shape — is in `docs/agents/specialists/wave-council.md`.

Fixed Phase 2 seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, plus one rotating domain seat from wave evidence.

The `wave-council` owns the protocol and verdict. The `wave-coordinator` routes lanes and enforces the gate.

Record machine-readable council signoffs in `## Review Evidence`. Record the narrative synthesis in `## Review checkpoints`.

**Readiness recording contract:** the structured `prepare-council` verdict line's `seats:` field names the seats actually run, each at most once (a rotating pick that is also a fixed seat appears once, identified by `rotating-seat:`), and every rostered seat other than the `red-team` primer and the `wave-council` moderator must have recorded evidence — a finding or an explicit no-findings note — in `## Prepare Review Evidence`, `## Review Evidence`, or a `## Review Checkpoints` entry other than the verdict line itself. docs-lint checks this roster⇄evidence consistency on open waves. Seat verification must be code-grounded: claims checked against the tree, not only against plan prose (see `docs/prompts/council-review.prompt.md`).

## Code Review Requirements

When `code-reviewer` is required:
- Check branch completeness and re-entrant safety for any per-key mutable state the change touches
- Verify dominant patterns from `docs/repo-profile.json` `code_patterns` are followed (when patterns exist)
- Verify `.wavefoundry/framework/scripts/tests/` coverage for any new script behavior
- All blocking findings must be fixed before the wave proceeds to close

## QA Review Requirements

When `qa-reviewer` is required:
- Confirm each required AC row in `## AC priority` has verification evidence (automated test, manual matrix, or documented exception)
- Multi-step verification for any stateful behavior (state across repeated calls or routine steps)
- AC scope gap check: surface important/nice-to-have items not in admitted scope after confirming required ACs

## Independent-Reference Verification

When a change modifies any implementation — a feature, an API or tool-surface change, a config-driven change, a bug fix, or a deterministic mechanism — reviewers apply seed 209's independent-reference rule: verify the changed behavior against a reference that does not share the implementation's assumptions. Eligible references include a specification, the acceptance criteria read independently of the implementer's interpretation, the consumer/caller contract, the original defect reproduction, a materially independent implementation, an authoritative schema/model, a prior-version contract, or a metamorphic invariant. Record the reference, exact promised property, and common-mode limitations; reject invalid generated inputs and compare only the public contract surface. A second helper or agent brief derived from the implementation hypothesis is not an independent reference.

For deterministic transformations, parsers, serializers, migrations, normalizers, compatibility adapters, and fallbacks the sharpest reference is a differential or a specification-derived/metamorphic invariant, spent as one highest-risk, reproducible probe. For example, a hand-written fallback parser can be compared with a grammar-backed parser over valid generated declarations, with the assertion limited to initializer ownership identity. Named regressions remain useful for diagnosed failures; the differential probe adds an assumption-independent reference for the broader property. Agreement does not prove either parser universally correct, so specification-derived identifier and token-boundary invariants still guard plausible shared defects.

Reference independence improves evidence quality; it does not confer reviewer independence. Implementer-authored probes remain `independent: false` and cannot restore a withdrawn approval. Tests that assert this paragraph or its generated carrier is present prove framework propagation only—not that a reviewer followed it on a particular wave. When no credible reference exists or the faithful probe would exceed current authorization, record that limitation and use the closest safe evidence rather than inventing a reference or starting open-ended fuzzing.

## Docs-Contract Review

At wave closure: if any `docs/specs/*.md` behavioral contract changed during the wave, record a docs-contract review with findings in `## Review checkpoints`. If no specs changed, record `Docs-contract review: not applicable` with a one-line rationale.

<!-- waveframework:executable-review-evidence begin — generated by render_agent_surfaces.py; preserve project-authored content outside this region -->
## Executable review evidence

Follow the canonical **Executable Review Evidence Protocol** in
`.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` for material
approval claims and blocking findings. Exercise the public or registered
path when one exists; keep state/interleaving probes within the protocol's
finite risk-selected budget; record expected versus observed evidence and
honest limitations; and never broaden task authority to run destructive,
external, credential-bearing, or cost-bearing probes.

Do not hand-author canonical JSONL when the lifecycle coordinator exposes
the typed review-evidence authoring surface. Reviewers supply the
load-bearing judgment facts to that coordinator; the authoring surface
derives only bookkeeping, appends the fixed sibling
`docs/waves/<wave>/events.jsonl` authority, and rebuilds the compact
Markdown current-state projection in `wave.md`. A role without lifecycle
mutation authority returns those facts to its coordinator instead of
writing wave state.

After validation, apply the ordered four-way actionability gate:
`do_now`, `maybe_later`, `dont_do_later`, or `not_issue`. Complete bounded
`do_now`/`maybe_later` work before closure, create no backlog for rejected
states, and use focused repair replay unless a load-bearing boundary change
objectively requires a full council.
<!-- waveframework:executable-review-evidence end -->
