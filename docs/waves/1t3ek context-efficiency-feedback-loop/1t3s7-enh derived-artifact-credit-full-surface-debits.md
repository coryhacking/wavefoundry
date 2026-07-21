# Derived-Artifact Credit and Full-Surface Debits

Change ID: `1t3s7-enh derived-artifact-credit-full-surface-debits`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

Operator observation (2026-07-20, during wave 1t3ek's delivery review): the review phase
made dozens of real tool calls — `wf_review_evidence` eight times, the `memory_*`
curation pass, `wf_validate_docs`, gates — and the Context Efficiency table noted none
of them, because only the five lifecycle tools and the 18 retrieval tools are
instrumented. Those tools do work the agent would otherwise perform manually, and the
operator asked whether they should take credit to offset their debits.

The subsystem's founding constraint blocks the naive answer: no causal counterfactual
claims without a quality-equivalent paired evaluation ("what the agent would have done
manually" is exactly the estimate the design refuses). But there is a measurable,
non-counterfactual version. Several tools DERIVE AND PERSIST textual artifacts far
larger than the caller's input: `wf_review_evidence` turns supplied judgment/evidence
fields into canonical serialized ledger records (derived IDs, identity digests, cycle
linkage, synthesis rows) plus rebuilt wave.md projection tables; `memory_propose`
drafts complete records from Decision Logs; the wave/change scaffold generators emit
whole documents from a slug. Before the typed surface existed, agents emitted that text
as output tokens — hand-authored canonical JSONL is precisely what `wf_review_evidence`
replaced. Crediting the persisted artifact's size is a deterministic byte count of a
real artifact, the same shape as the existing credits: `content_source_credit` measures
avoided reading, `workflow_prompt_credit` measures avoided instruction loading, and
derived-artifact credit measures avoided writing.

Tools that derive nothing textual (`wf_validate_docs`, `wf_garden_docs`, gates,
`wf_audit`) get debit-only instrumentation: their value is verification and state
management, and claiming context savings for them would be the counterfactual the
design forbids. Their debits are real context costs that today silently vanish.

## Requirements

1. **New credit type `derived_artifact_credit`** in the closed ledger equation and the
   per-stage metric keys: the UTF-8/4 size of textual artifacts a tool PERSISTED that
   the caller did not supply, computed as persisted-artifact bytes minus the
   caller-supplied request bytes already debited (floored at zero per artifact). Same
   estimator, same conservative framing; the reference doc documents it as avoided
   writing, never as avoided agent effort.
2. **Instrumented artifact-deriving tools** (initial set): `wf_review_evidence`
   (appended canonical records + projection delta), `memory_propose` (drafted record
   files), `memory_add`/`memory_validate` rewrite path (persisted record minus supplied
   fields), `wf_create_wave` and the `wf_new_*` scaffolds (generated document bodies;
   note these already carry workflow proxies — the artifact credit must not
   double-count the prompt credit).
3. **Debit-only instrumentation for the remaining first-party surface**: every
   non-instrumented `wf_`/`memory_`/`index_` tool records request/response debits as
   telemetry events (stage from focus or open-wave attribution as usual), so phase
   costs stop vanishing. Retrieval and lifecycle tools are unchanged.
4. **No counterfactual claims**: no credit for verification-only or state-flip tools;
   the reference doc's "not a causal claim" framing extends to the new credit type
   explicitly.
5. Credits deduplicate per (wave, phase, artifact identity) analogous to source-credit
   once-only keys: an idempotent replay of the same event derives zero new credit.
6. The 1sx2f signed-display invariant and the sealed/compaction machinery carry the new
   metric key through the established additive path — including the schema_ready
   fast-path column check (per the recorded 1t3ek gotcha) and stage-metric key set
   updates in `_STAGE_KEYS` with checkpoint-state validation.

## Scope

**Problem statement:** Most of the first-party tool surface is invisible to Context
Efficiency: artifact-deriving tools get no credit for the text they persist on the
agent's behalf, and non-instrumented tools' real debits vanish, so busy phases (review
especially) report near-zero activity.

**In scope:**

- The `derived_artifact_credit` metric key end-to-end (ledger, stage totals,
  checkpoint state, rendered table remains the two-column projection with the new
  credit folded into estimated savings)
- Instrumentation at the artifact-deriving tools listed in Requirement 2
- Debit-only events for the remaining first-party tools
- Double-count guards (workflow prompt credit vs artifact credit; replay dedup)
- Reference doc update; hermetic tests per credit path plus a replay test

**Out of scope:**

- Any paired-evaluation machinery change (saved model output / avoided loops stay
  gated behind paired evals)
- Counterfactual credit for verification or state-flip tools
- Historical backfill of previously unmeasured calls

## Acceptance Criteria

- [x] AC-1: A `wf_review_evidence` create call credits the size of the derived
      persisted artifact minus the caller-supplied request, verified by hermetic test
      with a known-size fixture.
- [x] AC-2: An idempotent replay of the same event derives zero additional credit,
      verified by test.
- [x] AC-3: A previously uninstrumented tool (e.g. `wf_validate_docs`) records
      request/response debits with correct stage attribution and zero credit, verified
      by test.
- [x] AC-4: Scaffold-generating tools credit the generated document body without
      double-counting their workflow prompt credit, verified by test.
- [x] AC-5: The new metric key flows through checkpoint publish, seal, and compaction
      with the signed-display invariant intact, and the store migration passes the
      stripped-current-store regression pattern, verified by tests.
- [x] AC-6: `docs/references/context-efficiency.md` documents derived-artifact credit
      as avoided writing with the explicit non-counterfactual framing; docs-lint
      passes.
- [x] AC-7: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [x] Add the metric key through `_STAGE_KEYS`, checkpoint state validation, snapshot
      assembly, and the savings equation (schema_ready check included)
- [x] Implement artifact-size capture at the Requirement 2 tools with per-artifact
      identity for replay dedup
- [x] Add debit-only event recording for the remaining first-party surface
- [x] Add the double-count guard for scaffold tools
- [x] Hermetic tests for AC-1 through AC-5
- [x] Update `docs/references/context-efficiency.md`
- [x] Run full framework test suite

## Requirements

1. [Numbered behavioral requirement — specific enough for an implementer to act on unambiguously]
2. …

## Scope

**Problem statement:** [What is broken, missing, or improving?]

**In scope:**

- …

**Out of scope:**

- …

## Acceptance Criteria

- [x] AC-1: [Testable outcome — verifiable by QA, automated test, or manual check]
- [x] AC-2: …

## Tasks

- [ ] [Concrete implementation step]
- [ ] …

## Agent Execution Graph


| Workstream       | Owner       | Depends On | Notes |
| ---------------- | ----------- | ---------- | ----- |
| artifact-credit  | Engineering | —          | `context_efficiency.py` metric plumbing first, then per-tool instrumentation |


## Serialization Points

- Late-admitted into wave `1t3ek` AFTER its delivery review (operator direction
  2026-07-20): implemented on top of the wave's landed changes, followed by a fresh
  delivery cycle and a superseding council approval. Same-file serialization satisfied
  by strict ordering.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (the closed-ledger equation and credit
taxonomy). `N/A` for the architecture hub docs: a new metric within the existing
accounting flow.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The operator-directed outcome: artifact-deriving tools take measurable credit for avoided writing |
| AC-2 | required  | Replay dedup protects the accounting signal from idempotent-retry inflation |
| AC-3 | required  | Full-surface debits are the honesty half; vanishing costs overstate net savings |
| AC-4 | required  | Double-counting between credit types would corrupt the closed ledger |
| AC-5 | required  | The checkpoint/seal/migration pipeline is where the last additive change broke; the regression pattern is mandatory |
| AC-6 | required  | The non-counterfactual framing is the design's load-bearing honesty constraint |
| AC-7 | required  | Suite-green is the delivery gate for all framework script changes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-20 | Operator static review (two P1s against this change's wrapper): (1) credit floored once on the artifact aggregate instead of per artifact as this doc requires — repaired: extractors return per-artifact token lists, wrapper sums per-artifact floors, boundary-case regression test added; (2) artifact tools without an operation digest got uuid4 event ids so identical replays re-credited — repaired: stable sha256(tool+request+response) identity, replay/different-outcome regression test added. Typed chains cycle 4 | `ev-artifact-credit-floors-aggregate-not-per-artifac*`, `ev-artifact-replay-uuid-event-ids-recredit*`; `test_artifact_credit_floors_per_artifact_not_aggregate`, `test_artifact_replay_without_operation_digest_dedupes` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Instrumentation is a generic post-registration wrapping pass over the FastMCP registry (`_wrap_first_party_tool_costs`), not per-tool call-site edits: uninstrumented first-party tools get a debit recorder, artifact extractors are a small named map, lifecycle/retrieval tools are exempt by name, and every failure path is observational (the tool result is never altered). | ~40 uninstrumented tools; per-tool edits would be error-prone and drift-prone; the registry-wrapping pattern is already established by the hot-reload machinery. | Per-tool instrumentation calls (rejected: bulk churn); FastMCP middleware (rejected: version-dependent API surface) |
| 2026-07-20 | `wf_create_wave` keeps only its lifecycle workflow proxy this pass; its generated wave.md/journal bodies are not artifact-credited yet. The `wf_new_*` scaffolds (no proxy) carry the artifact credit. | Avoids credit/proxy double-instrumentation complexity on the one tool that has both shapes; the scaffold family covers the dominant generated-document volume. | Credit both with an intersection guard (deferred: measurable but not worth the complexity in this pass) |
| 2026-07-20 | The stage metric key-set change required the one-time re-render of all 9 published checkpoint blocks (the 1t3ld cleanup pattern) because the checkpoint validator enforces an exact key set; executed via the canonical normalizer/renderer, docs-lint clean. | Old published states would fail docs-lint corpus-wide otherwise. | Validator tolerance for missing keys (rejected: weakens the exact-shape contract) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Artifact credit drifts into counterfactual overclaim as more tools are added | Requirement 4's bright line (persisted textual artifacts only, verification tools debit-only) plus the reference doc's explicit framing |
| Double-counting between workflow prompt credit and artifact credit on scaffold tools | Explicit guard + AC-4 |
| New metric key breaks sealed-floor compaction or the fast-path migration | AC-5 reuses the stripped-current-store regression pattern recorded from the 1t3ek schema_ready finding |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
