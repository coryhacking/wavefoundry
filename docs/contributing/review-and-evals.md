# Review and Evaluations

Owner: Engineering
Status: active
Last verified: 2026-08-03

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
| Seed 209 + `review_evidence.py` + `wf_review_wave` + `wf_review_event` | Seed 209 owns the human protocol and bounded same-root-cause review rule. `review_evidence.py` owns typed state, vocabulary, and the one structured authority/action projection. `wf_review_wave` is the sole guided inspection entry point and full-validation owner. `wf_review_event` owns typed writes, the post-commit continuation, and the forensic `list` presentation. The fixed sibling `events.jsonl` remains the sole machine authority; generated Markdown is presentation only. | Seed 100 / `wf_create_wave`; framework MCP server | Direct-ledger validation (missing/noncanonical/schema/relationship failures reject without Git); typed append; Prepare-owned policy receipt in the same ledger; protocol-2 upgrade reprojects only non-closed waves; successful writes derive continuation without rerunning validation | `ReviewEvidenceStateMachineTests`; `GuidedReviewAuthorityProjectionTests`; `ReviewEvidenceListEventTests`; `WaveLifecycleMutationTests`; `WaveCreateScaffoldAlignmentTests`; build-pack/setup/upgrade distribution fixtures; rollback-boundary negative control; live-surface deletion census |

Fresh setup, full upgrade, direct `wf render-surfaces`, and self-host refresh converge on that renderer operation. Missing required canonical carriers are materialized from their installed seeds (or a bounded bootstrap pointer for multi-output owners); Guru, conditional repo-local reviewers, and arbitrary native wrappers remain existing/enabled-only. Newly created canonical Guru wrappers are reconciled after materialization in the same render pass. Malformed markers fail safe rather than authorizing whole-file replacement.

The machine contract is fail-closed. `wave.md` declares `review-evidence-source: events.jsonl`; the fixed sibling ledger—not the generated Markdown table—is the append-only authority. Start guided work with one phase-correct `wf_review_wave`; it runs the existing full validation and returns state-derived actions without supplying reviewer judgments. The typed `wf_review_event` tool serializes its event transaction under the project-global lock, refreshes the concise current-head projection, and on successful create returns the next post-commit actions without another validation or list call. Use `event="list"` for forensic history, filters, truncation recovery, or disputed state. A one-candidate run may reuse its finding evidence as universe proof, and an empty lightweight run needs only one run row, retaining reviewer `verification_context` without a separate dedup row. A synthesis links only to earlier `claim_kind: finding` evidence for the same finding. Approval records use `claim_id: approval:<signoff-key>` and bind the exact authority actor: `operator`, `wave-council`, or the named specialist lane; specialist and council approvals must be fresh and independent. Approval chronology is affected-lane scoped through `approval_recheck_lanes`; unrelated later synthesis does not stale another lane, while readiness findings stale readiness approval until terminal, delivery findings stale their declared delivery lanes, and operator approval remains final-wave scoped. Independence means the reviewer did not implement the repair and formed its own current-tree/test assessment before relying on prior findings or verdicts. Mandatory project orientation may disclose status or history, but it is context rather than evidence and does not by itself disqualify a fresh review. Lane reassessment is exact-lane, fresh, independent, and single-use. Universal census records include `residual_uncertainty_status` (`none | bounded | unresolved`) and `index_freshness` (`current | stale | unknown`). Operator waivers include scope, reason, and risk.

Independence is split between what the validator enforces and what stays declared (seed 209, "Enforced versus declared independence"). Enforced, chain-aware and matched by exact finding and cycle: a `reverification` sharing its resolving `repair_start`'s `context_id` while declaring `fresh_context=true` is rejected at append with `reverification_context_not_fresh` (a self-contradiction, decidable with no trust assumption); a `reverification` carrying the same `actor` as that `repair_start` from a different context is rejected with `reverification_actor_not_distinct` (forward protocol policy — not proof of shared caller identity). When both match, only the same-context contradiction is returned. Rejected attempts append nothing, so the prior synthesis head stays authoritative. The close gate additionally audits an open or reopened wave's current/latest chains for the same defects appended by older code (`review_evidence_independence_invalid`); recovery is a next-cycle `repair_start` plus a distinct-role, distinct-context reverification, and sealed/closed archives are never retroactively invalidated. Declared, honor-system: the truth of `fresh_context` and `independent`, and actor identity itself — the validator sees strings, not callers, and no waiver bypasses the enforced checks.

A repair cycle is an aggregate of actionable findings, not one physical run. Each finding has exactly one same-cycle repair start; a readiness-born finding may open it directly after cycle-0 readiness, while a delivery-born finding requires `initial_delivery`. Historical batch runs and compact per-finding runs are both valid. Fresh independent reviewers may append ordered same-cycle reverification progress as they clear their own required lanes. A finding becomes terminal only when its current same-cycle head has no required lanes and is either completed by reverification, truthfully reclassified to `not_issue` / `dont_do_later` with `not_required` repair state, or distinctly operator-waived with valid waiver metadata; waiver is never relabeled as completion or independent verification. Continue the fix/review loop in the phase where the finding was raised; do not carry a repaired readiness finding into delivery merely to obtain a predecessor record. Use repeated same-cycle reverifications for lane progress and a later aggregate cycle only for a later repair pass. The next cycle remains blocked until every started finding is terminal, and a completed cycle cannot be extended retroactively. When the final outstanding cycle-2 reverification makes both cycles aggregate-complete, the typed writer derives the mandatory convergence checkpoint in that same identified bundle and atomic authority replacement; callers do not append a separate checkpoint event. Its `frozen_boundary` is the set of wave-current synthesis heads after that final transition, and later runs declare deviations or reopened findings explicitly.

The events-only contract carries no receipt ledger, checkpoint record, or hash chain, deliberately: a checksum stored in or beside the same local log cannot prove that its own tail was not deleted, so restoring a complete older but internally valid ledger is not locally detectable. Lifecycle validation rejects a downgraded source declaration that is still present, a missing event ledger on a declared wave, noncanonical bytes, and schema or relationship failures without calling Git; a surviving non-empty ledger without a readable declared (or legacy inline-marker) `wave.md` is a detected state, failed by the docs-lint orphan-ledger check (wave 1to78), covering both declaration-line removal and `wave.md` deletion or rename; the undetected boundary narrows to whole-ledger rollback, empty-ledger declaration removal, and co-deletion of ledger plus declaration (an undeclared wave without a surviving non-empty ledger reads as prose-only legacy), and Git or backups remain the appropriate optional history authority when rollback investigation matters. Semantic indexing excludes every canonical wave-folder `events.jsonl` by its fixed role alone, so an integrity failure cannot expose raw event history; lifecycle-shaped note files outside that fixed role remain eligible. Protect wave records and ledgers through ordinary repository access control, source control, or backup rather than duplicating ledger state.

## Readiness Checklist (Prepare Wave)

Before implementation begins, the wave-coordinator confirms:
- [ ] All admitted changes have consolidated change docs at `docs/waves/<wave-id>/`
- [ ] Required review lanes identified for each admitted change
- [ ] AC priority recorded on each change doc (`## AC priority`)
- [ ] product-owner acknowledgment recorded for product-impacting waves
- [ ] `qa-reviewer` confirmed for any bug fix (per `review_policies.require_qa_reviewer_for_bug_fixes`)
- [ ] `wave-council-readiness` signoff recorded when `wave_review.enabled` (on declared waves this is a typed approval event in `events.jsonl`, projected into `## Review Evidence`; a prose signoff line satisfies the gate only on legacy waves)
- [ ] Every blocking readiness finding has a terminal current head before that signoff; repair and
      independent reverification happen during readiness, before implementation

## Wave Closure

**Closure requires all of the following:**

1. All changes marked `complete` or `deferred` with explicit rationale
2. All required review lanes from readiness are reconciled in `## Review checkpoints` (including deferred with rationale when applicable)
3. `wave-council-readiness` is present when review is enabled, and `wave-council-delivery` is present when the persisted Prepare receipt says the configured delivery mode requires it (typed, phase-scoped approval events on declared waves; prose lines count only on legacy waves)
4. Docs-contract review: recorded as performed (findings in `## Review checkpoints`) or `not applicable` with rationale, when any `docs/specs/*.md` changed during the wave
5. Journal distillation complete: any important implementation/review lessons added to relevant role or persona journals
6. Durable memory promoted to `docs/references/project-context-memory.md` (and other canonical docs when applicable)
7. `docs/agents/session-handoff.md` cleared or refreshed to reflect post-closure state
8. Chronology reconciled: `Status: completed`, `Completed at:` date, all change statuses finalized

**Closure is blocked until all eight items above are explicitly recorded in the wave record.**

**Secrets gate (enforced by `wf_close_wave`):** Before calling `wf_close_wave`, check `docs/scan-findings.json`. Any `pending` or `suspected-secret` entry **hard-blocks** close — run the security reviewer (`seed-213`) to classify each as `confirmed-secret` or `false-positive`. `confirmed-secret` entries do **not** block close (wave 1p5pz — classification is the acknowledgment); instead every close returns a non-blocking standing reminder (`confirmed_secrets` + `secrets_reminder` in the response `data`) that the agent presents to the operator. If the file is absent or has no unresolved entries, the gate passes automatically.

## Wave Council

The framework ships `wave_review.enabled: true` and `delivery_mode: targeted` by default. Readiness Council is required whenever review is enabled. Delivery Council follows the explicit mode: `universal` requires it for every wave, `targeted` requires it only when the Prepare receipt or current boundary triggers select it (including upgrade/release, permission/trust-boundary, and cross-platform work), and `disabled` is valid only with `enabled: false`.

- `wave-council-readiness` before implementation
- `wave-council-delivery` before closure when the selected delivery mode requires it

Wave Council runs a red-team adversarial primer (Phase 1) before fixed seats (Phase 2), then synthesizes. The full protocol — depth tiers, seat responsibilities, output shape — is in `docs/agents/specialists/wave-council.md`.

Fixed Phase 2 seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, plus one rotating domain seat from wave evidence.

The `wave-council` owns the protocol and verdict. The `wave-coordinator` routes lanes and enforces the gate.

Record machine-readable council signoffs as typed approval events through `wf_review_event` on declared waves (they project into `## Review Evidence`); only legacy prose waves record the signoff line in `## Review Evidence` directly. Record the narrative synthesis in `## Review checkpoints`.

Prepare is the sole policy authority. It derives the ordered specialist roster from requested lanes, project policy, and admitted change bytes; appends an idempotent, parent-bound `review_policy_receipt`; reprojects status rows; and clears `review-policy-reprepare-required`. Readiness approvals bind the current receipt and use `approval_phase: readiness`; Review/Close consume the persisted roster and receipt without independently selecting lanes. A changed policy input or upgrade marker blocks Implement, Review, and Close until Prepare runs again. Delivery approvals use `approval_phase: delivery`; historical approvals without the field retain their documented compatibility mapping.

Review and Close consume one shared delivery evaluator for ledger validity, receipt/marker currency, docs lint, required lanes, Council selection, approval evidence, and operator state. Close then adds only its registered closure delta (garden, unresolved change/checkbox, repair-independence, memory, secrets, gates, and transition checks), preventing the two lifecycle paths from silently drifting.

**Readiness recording contract:** on declared waves, the typed `wave-council-readiness` approval is the machine authority. A structured `prepare-council` checkpoint may still summarize the seats actually run, but it is narrative and cannot change a lifecycle result; when present, docs-lint may warn if its roster lacks corresponding evidence. Legacy waves retain the structured verdict compatibility gate. Seat verification follows the all-phase code-grounded verification tenet (canonical definition: seed `209-agent-harness-core.prompt.md`, "Code-Grounded Verification"; review-phase contract: `docs/prompts/council-review.prompt.md`).

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

<!-- wavefoundry:review-policy:begin -->
## Review-policy evidence baseline

The review policy requires phase-scoped integrity evidence. After repair,
check the same root cause and adjacent repair class before focused repair
reverification.
<!-- wavefoundry:review-policy:end -->

<!-- wave:executable-review-evidence begin — generated by render_agent_surfaces.py; preserve project-authored content outside this region -->
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

Under the current review policy, after validation apply the ordered
four-way actionability gate:
`do_now`, `maybe_later`, `dont_do_later`, or `not_issue`. Complete bounded
`do_now`/`maybe_later` work before closure, create no backlog for rejected
states, and use focused repair replay unless a load-bearing boundary change
objectively requires a full council.

Repair/reverification independence is enforced chain-aware at the typed
authoring surface: a reverification sharing its `repair_start`'s context
while declaring `fresh_context=true` is rejected as a contradiction
(`reverification_context_not_fresh`), and a same-actor reverification is
rejected as protocol policy (`reverification_actor_not_distinct`); both
append nothing. The close gate audits open and reopened waves' current
chains (`review_evidence_independence_invalid`); closed archives are never
retroactively invalidated. Actor equality is protocol policy, not caller
authentication — the truth of `fresh_context`, `independent`, and actor
identity itself remains a declaration the validator cannot verify.
<!-- wave:executable-review-evidence end -->
