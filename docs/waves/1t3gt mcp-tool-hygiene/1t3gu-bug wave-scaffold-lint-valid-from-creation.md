# Wave Scaffold Must Be Lint-Valid From Creation

Change ID: `1t3gu-bug wave-scaffold-lint-valid-from-creation`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

Operating principle (operator-stated): every template the framework generates must produce
lint-valid documents when filled out as-is. Operators should never discover validator failures
only after populating a scaffold, forcing rework and hand-patching of generated structure.

The `wave.md` scaffold currently violates this twice, observed directly while creating wave
`1t3gt mcp-tool-hygiene`:

1. **Missing review-status projection block.** `create_wave` in `server_impl.py` hardcodes the
   scaffold body. It seeds the Finding Synthesis owned markers via
   `empty_external_finding_synthesis_section()`, but its `## Review Evidence` section predates
   the review-status projection introduced by wave 1t3dm
   (`render_review_status_projection`), so docs-lint reports "review evidence projection is
   stale; regenerate it from sibling events.jsonl" on every freshly created wave — the error
   appears in `wave_create_wave`'s own lint output at creation time. The workaround was
   hand-inserting the `<!-- wave:review-status begin -->` block.
2. **Watchpoints placeholder fails its own validator.** The `## Journal Watchpoints`
   placeholder text ("Add any coordination notes, sequencing constraints, or guard
   requirements here.") contains none of the `WAVE_WATCHPOINT_MARKERS` tokens
   (`watchpoint`, `follow-up`, `block`, `retry`, `defer`, `move`) required by
   `wave_validators.py` once any admitted change is non-terminal — so the scaffold fails lint
   as soon as the first change is admitted, even before an operator has touched the section.

The root cause of defect 1 is structural: the scaffold hardcodes projection-owned markup
instead of generating it through the same renderer the validator checks against, so any future
projection change will silently reintroduce this drift class.

## Requirements

1. A wave created by `wave_create_wave(mode='create')` must pass docs-lint with zero errors
   immediately, with no manual edits.
2. A freshly created wave must continue to pass docs-lint after a change doc is admitted via
   `wave_add_change` while that change is in a non-terminal status (the state every new wave
   passes through).
3. The scaffold's Review Evidence / Finding Synthesis projection content must be **generated
   by the same rendering functions the validator compares against**
   (`render_review_evidence_projection` / `render_review_status_projection` over the empty
   record set), not hardcoded prose — so future projection-format changes cannot reintroduce
   scaffold drift.
4. The `## Journal Watchpoints` placeholder must itself satisfy the
   `WAVE_WATCHPOINT_MARKERS` check (e.g. placeholder guidance phrased with "watchpoint" /
   "follow-up" / "blocking" language), while still reading as clear instruction to the
   operator.
5. Waves already created and hand-patched (including `1t3gt`) must not be rewritten by this
   change; the fix applies to newly scaffolded waves only.

## Scope

**Problem statement:** The `wave.md` scaffold emitted by `create_wave` fails docs-lint
immediately (missing review-status projection) and again at first change admission
(placeholder lacks watchpoint markers), forcing manual repair of generated structure on every
new wave.

**In scope:**

- `create_wave` scaffold body in `server_impl.py`
- Generating the projection-owned sections through the canonical renderers instead of
  hardcoding them
- The Journal Watchpoints placeholder text
- Regression test: create a wave in a fixture repo, admit a planned change, assert docs-lint
  is clean at both points
- An audit pass over the other document scaffolds for the same defect class (`wave_new_*`
  change-doc template, journal stub co-created by `create_wave`): audit-and-fix if a scaffold
  can fail lint as generated; audit-and-skip with a note if clean

**Out of scope:**

- Changing what the validators require (the projection and watchpoint checks are correct;
  the scaffold is what lags)
- Rewriting existing wave records already patched by hand

## Acceptance Criteria

- [x] AC-1: `wave_create_wave(mode='create')` produces a wave.md whose creation-time lint
      result is clean (`error_count: 0`), verified by a regression test.
- [x] AC-2: After `wave_add_change(mode='create')` admits a planned change into a freshly
      scaffolded wave, docs-lint remains clean, verified by the same regression test.
- [x] AC-3: The scaffold's projection sections are produced by
      `render_review_evidence_projection`/`render_review_status_projection` (or an equivalent
      single-source call path shared with the validator), with no hardcoded projection markup
      left in `create_wave`.
- [x] AC-4: The audit of the `wave_new_*` change-doc template and the journal stub is recorded
      in this change's Decision Log (fixed, or confirmed clean).
- [x] AC-5: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [x] Rework `create_wave`'s scaffold to render the Finding Synthesis and Review Evidence
      projection sections via the canonical renderers over the empty record set
- [x] Rewrite the Journal Watchpoints placeholder so it contains watchpoint/follow-up/blocking
      guidance language satisfying `WAVE_WATCHPOINT_MARKERS`
- [x] Add regression test covering create → lint-clean → admit change → still lint-clean
- [x] Audit the `wave_new_*` change-doc template and the co-created journal stub for the same
      generated-doc-fails-lint class; fix or record clean in the Decision Log
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream   | Owner       | Depends On | Notes |
| ------------ | ----------- | ---------- | ----- |
| scaffold-fix | Engineering | —          | Single small workstream; touches `create_wave` in `server_impl.py` plus tests |


## Serialization Points

- This change edits `server_impl.py`, which change `1t3gs-ref mcp-tool-prefix-rename` (same
  wave) rewrites broadly. Do not implement the two concurrently — sequence this fix either
  fully before or fully after the `1t3gs` rename pass lands.

## Affected Architecture Docs

N/A — confined to the scaffold text emitted by one function and a placeholder string; no
boundary, flow, or verification-structure change. The validator contract is unchanged.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The operator-stated principle: generated docs must be lint-valid at creation with no manual repair |
| AC-2 | required  | The second observed failure fired at change admission — creation-time cleanliness alone does not cover the state every new wave passes through |
| AC-3 | important | Single-sourcing through the canonical renderer is what prevents recurrence of this drift class; a hardcoded-but-currently-correct scaffold would satisfy AC-1/AC-2 today and drift again later |
| AC-4 | important | The audit closes the defect class across the other generators; recording it keeps "audit" honest (audit-and-skip with a note when clean) |
| AC-5 | required  | Suite-green is the delivery gate for all framework script changes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Audit result: the `wf_new_*` change-doc template and the co-created journal stub are clean — all four change-doc creations this session returned `lint.clean: true` at creation, and the new creation-lint regression test exercises the journal stub through docs-lint `--changed` on the create path. No fix needed (audit-and-skip). | 1t3gu audit task; evidence from this session's own tool responses plus the new tests | Rework those scaffolds too (rejected: nothing to fix) |
| 2026-07-20 | Baking the review-status block into the scaffold surfaced a latent contract interaction: the 1t3dm freshness contract requires the projection to be re-rendered whenever a wave.md edit changes the derived signoff keys (e.g. adding a Participants table or prose signoffs), and one legacy prose-flow test relied on the block being absent. Kept 1t3dm's strict contract; fixed the test to reconcile via `_project_current_review_status` after its text mutations. An empty-ledger staleness tolerance was prototyped and REVERTED: 1t3dm's own tests assert strictness with an empty ledger, and weakening a two-day-old shipped contract inside a hygiene wave is silent scope expansion. | Strictness is the shipped contract (test_docs_lint projection-drift/missing tests, empty-ledger fixture); the projection self-reconciles on every typed write, so only direct-text editors bear the re-render duty | Empty-ledger tolerance in both checkers (rejected: reverses 1t3dm); scaffold without the block (rejected: recreates the original creation-time lint failure) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Rendering projections at scaffold time couples `create_wave` to renderer preconditions (e.g. section must exist before rendering into it) | Regression test exercises the real create path end-to-end, not a mocked renderer |
| `1t3gs` rename pass and this fix both touch `server_impl.py` and could conflict | Explicit serialization point: sequence, don't parallelize |
| Watchpoint placeholder rewrite could accidentally stop reading as placeholder guidance | Keep angle-bracket placeholder convention; only the guidance wording changes |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
