# Anonymized Council Synthesis and Seat-Agreement Score

Change ID: `12yli-enh anonymized-council-synthesis-and-agreement-score`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-05-28
Wave: 12xr1 graph-index-extraction-and-visualization

## Rationale

Wave Council's stated default stance is that "apparent agreement can hide correlated error" (`215-council-moderator.prompt.md`). The strongest mechanism for breaking correlation — running seats on diverse model families — is out of scope right now (operator constraint: no multi-model support). That leaves the council exposed to two single-model weaknesses that we *can* address cheaply:

1. **Authority-anchoring during synthesis.** The council-moderator currently compares seat outputs labeled by seat role. A finding from `architecture-reviewer` carries implicit weight over the same finding from the rotating fifth seat, regardless of merit. karpathy's `llm-council` anonymizes peer outputs before judgment to reduce "playing favorites." On a single model this is an **anchoring-reduction hypothesis, not measured decorrelation** — it reduces label-anchoring within one synthesis call but does not decorrelate the underlying generator. We adopt it because it is low-cost (zero additional model calls, reuses the one place outputs are already compared) and reversible, not because it is proven; the change must be framed accordingly and not over-claim.

2. **Disagreement is unmeasured.** The challenge-round trigger fires "when seats materially disagree," but "materially" is a moderator judgment call with no recorded signal. A lightweight aggregate **agreement/severity score** makes the trigger measurable and gives the operator a fast triage signal in `## Review checkpoints`.

This change reconciles the transferable parts of karpathy's council pattern (anonymization, an aggregate quality signal) with our existing adversarial-primer + specialist-lane structure, without regressing toward his consensus/ranking model.

## Requirements

1. The council-moderator must perform its **first synthesis pass on anonymized seat findings** — seat/role identity stripped (e.g. "Seat 1/2/3…") — and re-attach seat identity only after findings have been weighed on merit.
2. The same anonymization must apply to any inputs presented during a challenge round.
3. The red-team Phase 1 primer remains explicitly attributed (it is shared by design); anonymization applies only to the Phase 2 fixed-seat and rotating-seat outputs being compared.
4. The moderator output shape must include a **seat-agreement/severity aggregate**: a deterministic summary of (a) how aligned the seats were and (b) the maximum finding severity across seats.
5. The aggregate computation must be specified well enough to be reproducible: named inputs (per-seat verdicts, per-finding severities), the levels it can take, and how it maps to the challenge-round trigger.
6. The existing challenge-round trigger language must reference the aggregate measure rather than relying solely on unqualified moderator judgment.
7. All existing council invariants must be explicitly preserved: seat isolation before synthesis, mandatory red-team primer sharing, and non-waiver of blocking required specialist lanes.
8. **Two-tier identity handling (non-waiver guard).** Anonymization must apply only to the convergence/agreement assessment. Any finding that carries blocking authority from a required specialist lane must retain explicit lane attribution through synthesis and must never be merit-weighted below its blocking status on the basis of anonymization. The seed wording must make this split explicit so the non-waiver guarantee is structurally intact, not merely asserted.

## Scope

**Problem statement:** Single-model Wave Council is vulnerable to authority-anchoring during synthesis and has no recorded signal for seat disagreement. Both are addressable in the moderator/synthesis layer without model diversity.

**In scope:**

- `215-council-moderator.prompt.md` — anonymized first-pass synthesis, aggregate score in output shape, challenge-round trigger language, preserved-invariants note
- `007-review-system-overview.md` — document anonymized synthesis and the aggregate score in the shared review model
- `230-council-review.prompt.md` — reflect anonymized synthesis + aggregate in the standalone council protocol/synthesis section
- Regeneration of rendered surfaces that derive from these seeds (`docs/agents/council-moderator.md`, `docs/prompts/council-review.prompt.md`)

**Out of scope:**

- Multi-model / cross-vendor seat assignment (explicitly deferred by operator)
- A separate anonymized peer-ranking round (Stage-2-style) — low value on a single model; shelved
- Making the aggregate score a **machine-readable, gated** signoff (it lives in the narrative `## Review checkpoints` for now; enforcement/validator changes would be a separate change)
- Any change to `## Review Evidence` machine-readable signoff parsing in `server_impl.py` / `docs_lint.py`

## Acceptance Criteria

- [x] AC-1: `215-council-moderator.prompt.md` Council Protocol documents an anonymized first synthesis pass (identity stripped, re-attached only after merit weighting) and the `Do Not` section forbids attributing seat authority before merit weighting.
- [x] AC-2: `215`, `230`, and `007` describe the seat-agreement/severity aggregate in the moderator output shape, using consistent wording across all three.
- [x] AC-3: The aggregate's computation is specified — named inputs (per-seat verdicts, per-finding severities), its discrete levels, and the mapping to the challenge-round trigger.
- [x] AC-4: The challenge-round trigger language in `215` (and `230`) references the aggregate measure rather than unqualified "materially disagree."
- [x] AC-5: Seat isolation, red-team primer sharing, and non-waiver of blocking lanes are explicitly preserved and unchanged in the edited seeds.
- [x] AC-6: Rendered surfaces (`docs/agents/council-moderator.md`, `docs/prompts/council-review.prompt.md`) are regenerated/consistent with the seeds and docs-lint passes. (Note: these are self-hosted surfaces with no mechanical re-render; synced by hand — see Progress Log.)
- [x] AC-7: The edited seeds explicitly state that anonymization applies only to convergence/agreement assessment and that blocking required-lane findings retain lane attribution and blocking authority through synthesis (two-tier handling per Requirement 8); the wording is concrete enough that a reviewer can confirm a blocking finding cannot be merit-weighted below blocking via anonymization.

## Tasks

- [x] Open the `seed_edit_allowed` gate (`wave_gate_open(gate="seed_edit_allowed")`; CLI fallback `.wavefoundry/bin/wave-gate open seed_edit_allowed`)
- [x] Edit `215-council-moderator.prompt.md`: anonymized first-pass synthesis, aggregate in Output Shape, challenge-round trigger, preserved-invariants note
- [x] Edit `007-review-system-overview.md`: document anonymized synthesis + aggregate score
- [x] Edit `230-council-review.prompt.md`: reflect both in the standalone council synthesis section
- [x] Regenerate rendered agent/prompt surfaces and confirm `docs/agents/council-moderator.md` + `docs/prompts/council-review.prompt.md` match the seeds (synced by hand — no mechanical renderer covers these surfaces)
- [x] Run framework tests (`python3 .wavefoundry/framework/scripts/run_tests.py`) and docs-lint; fix failures
- [x] Close the `seed_edit_allowed` gate

## Agent Execution Graph


| Workstream             | Owner       | Depends On | Notes                                                        |
| ---------------------- | ----------- | ---------- | ------------------------------------------------------------ |
| seed-edits             | Engineering | —          | `215`, `007`, `230` — single author to keep wording aligned  |
| surface-regeneration   | Engineering | seed-edits | Render + verify `council-moderator.md`, `council-review.prompt.md` |
| verification           | Engineering | surface-regeneration | Framework tests + docs-lint                         |


## Serialization Points

- All three seed edits share the same vocabulary for the aggregate score and anonymization; author them together (or define the wording first) to avoid drift.
- Surface regeneration must run after all seed edits land, not per-file.

## Affected Architecture Docs

`N/A` — the change is confined to review-protocol seed prompts and their rendered surfaces. It introduces no module boundary, data/control-path, integration-contract, or test/release-seam change in implementation code. The `docs/architecture/` set documents the chunking/indexing/search pipeline, which this change does not touch.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Core of the anonymization improvement |
| AC-2 | required   | Core of the aggregate-score improvement |
| AC-3 | required   | Without a specified computation the aggregate is not reproducible |
| AC-4 | important  | Connects the aggregate to existing behavior |
| AC-5 | required   | Guards against regressing council guarantees |
| AC-6 | required   | Seeds are source of truth; rendered surfaces must not drift |
| AC-7 | required   | Resolves the council's strongest challenge: anonymization must not dilute blocking lanes |


## Progress Log


| Date       | Update                  | Evidence |
| ---------- | ----------------------- | -------- |
| 2026-05-28 | Change doc authored     | this file |
| 2026-05-28 | Prepare-wave council readiness pass (full tier) run; verdict PASS with conditions; added Req 8 + AC-7 (non-waiver guard), reframed Rationale, recorded rollout decision | `wave.md` ## Review Checkpoints |
| 2026-05-28 | Implemented: edited seeds 215, 007, 230 under `seed_edit_allowed`; manually synced self-hosted surfaces `docs/agents/council-moderator.md` + `docs/prompts/council-review.prompt.md` (no mechanical re-render covers them — `render_*` scripts handle hooks/MCP/bin/guru only); 1718 framework tests pass; docs-lint ok; gate closed | `run_tests.py` (OK, 1718), `docs-lint: ok` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-28 | Adopt anonymized synthesis + aggregate score on the single model | Highest value/cost within the no-multi-model constraint; reuses the one place outputs are already compared | (1) Cross-model decorrelation — rejected: operator constraint, no multi-model support now. (2) Separate anonymized peer-ranking round — rejected: a model grading anonymized copies of its own reasoning is self-consistency, not decorrelation; adds latency/cost for marginal benefit. (3) Selected: anonymize the existing synthesis/challenge comparison + add an aggregate agreement/severity signal. |
| 2026-05-28 | Keep the aggregate score in narrative `## Review checkpoints`, not a gated machine-readable signoff | Simplest solution first; avoids touching `## Review Evidence` parsing in `server_impl.py`/`docs_lint.py` | Make it a machine-readable gated field — deferred to a separate change if enforcement is wanted |
| 2026-05-28 | Adopt two-tier identity handling: anonymize for convergence assessment only, preserve lane attribution for blocking authority | Council strongest challenge — blanket anonymization could let a blocking required-lane finding be merit-weighted below blocking, regressing the non-waiver guarantee | Blanket anonymization of all seat outputs — rejected: violates non-waiver |
| 2026-05-28 | Change the default council protocol rather than gating behind an opt-in `wave_council_policy` flag | The goal is to improve the default council everywhere; rollout safety is covered by the two-tier non-waiver guard + reversibility (narrative-only); an opt-in flag adds config surface against the "simplest solution first" principle | Opt-in policy flag (rotating-seat alternative) — recorded; revisit only if a target repo needs to defer the behavior |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Anonymization wording is interpreted as hiding the red-team primer too | Requirement 3 explicitly scopes anonymization to Phase 2 seat outputs; primer stays attributed |
| Anonymization dilutes a blocking required-lane finding (council's strongest challenge) | Requirement 8 + AC-7: two-tier handling preserves lane attribution and blocking authority; anonymization limited to convergence assessment |
| Over-claiming decorrelation benefit on a single model | Rationale reframed as an anchoring-reduction hypothesis; benefit is low-cost/reversible, not proven |
| Aggregate score is too vague to be reproducible | AC-3 forces a specified computation (inputs, levels, trigger mapping) |
| Seed edits affect all target repos | `seed_edit_allowed` gate + this change warrants its own council pass before closure |
| Rendered surfaces drift from seeds | AC-6 + surface-regeneration workstream; docs-lint in verification |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
