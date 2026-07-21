# State-File Source Credit for Artifact Tools

Change ID: `1t2zq-enh state-file-source-credit-artifact-tools`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

Operator direction (2026-07-20): fair accounting means the typed tools' deterministic
context savings are counted. Grounded measurement on the live wave showed the gap: a
`wf_review_evidence` approval call cost ~1,480 tokens and credited 337, while the manual
path requires reading the canonical ledger (`events.jsonl`, 7,400 tokens and growing)
and the projection region before a record can be authored safely — the tool performs
those reads on the caller's behalf. That avoided reading is the exact epistemics of
`content_source_credit` on retrieval tools ("contained project files that would
otherwise have had to be read"), so it is claimable deterministically, with no
counterfactual about agent behavior. The remaining gap (schema-learning amortization,
retry loops, ~9k+ first-call) stays correctly gated behind paired evaluations.

## Requirements

1. Artifact-deriving tools credit, through the EXISTING content-source machinery, the
   contained state files they demonstrably read as part of serving the call:
   - `wf_review_evidence` (create, committed, not replayed): the sibling
     `events.jsonl` ledger and the wave record (`wave.md`) whose projections it
     re-renders.
   - `memory_validate`: the candidate record file it validated.
   - `memory_propose` (create, records written): the source change docs its drafts
     derive from (best-effort resolution from the written records' source events);
     unresolvable sources credit nothing.
   - `memory_add` and the `wf_new_*` scaffolds credit no sources (the caller supplies
     the content; nothing is read on their behalf).
2. Credits ride the existing `_source_credits` path in the telemetry commit: opaque
   source identifiers, stat-signature versions, verified classification,
   `content` credit kind — so the once-only `(wave, phase, source, version)` key
   deduplicates repeat credits of an unchanged file within a phase, and a file that
   grew (a new ledger version) legitimately earns a fresh credit.
3. All file access is containment-checked under the repository root; any resolution
   failure credits nothing and never alters the tool result (the wrapper stays
   observational end-to-end).
4. The reference doc extends the derived-artifact section: artifact tools may also
   carry content source credit for the state files they read on the caller's behalf,
   under the same non-counterfactual bright line.

## Scope

**Problem statement:** Artifact tools take credit for avoided writing but not for the
deterministic avoided reading they perform (ledger, projections, validated records),
under-claiming their measured savings by roughly an order of magnitude on evidence
calls.

**In scope:**

- Source-file extractors alongside the existing artifact extractors in the 1t3s7
  wrapper; `record_tool_cost` gains pass-through source credits
- The three tool families in Requirement 1
- Hermetic tests: credit rows land with dedup semantics (same version once, new
  version again); containment and failure paths credit nothing
- Reference doc extension

**Out of scope:**

- Any counterfactual credit (schema learning, retry loops) — paired evaluations remain
  the only route
- Retrieval and lifecycle tools (unchanged instrumentation)

## Acceptance Criteria

- [x] AC-1: A committed `wf_review_evidence` create call adds content source credits
      for the ledger and wave record with verified classification, exactly once per
      file version, verified by hermetic test.
- [x] AC-2: A second identical-version credit attempt in the same phase deduplicates
      to zero; a grown ledger (new version) earns a fresh credit, verified by test.
- [x] AC-3: `memory_validate` credits the validated record file; `memory_add` and
      `wf_new_*` credit no sources, verified by test.
- [x] AC-4: Resolution or containment failure credits nothing and leaves the tool
      result untouched, verified by test.
- [x] AC-5: The reference doc documents state-file source credit under the
      non-counterfactual bright line; docs-lint passes.
- [x] AC-6: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [x] Extend `record_tool_cost` to pass through `_source_credits`
- [x] Add state-file extractors for the Requirement 1 tools using canonical opaque
      ids and stat-signature versions
- [x] Hermetic tests for AC-1 through AC-4
- [x] Extend `docs/references/context-efficiency.md`
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


| Workstream      | Owner       | Depends On | Notes |
| --------------- | ----------- | ---------- | ----- |
| state-credit    | Engineering | —          | Builds directly on the landed 1t3s7 wrapper |


## Serialization Points

- Third late admission into wave `1t3ek` (operator direction), after the superseding
  delivery approval: implemented on the landed 1t3s7 wrapper, followed by another
  delivery-cycle delta and a second superseding council approval.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (credit taxonomy extension). `N/A` for the
architecture hub docs.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The operator-directed outcome: deterministic avoided reading is counted |
| AC-2 | required | The once-only dedup is what keeps the credit honest across repeat calls |
| AC-3 | required | The no-read tools crediting nothing is the bright line in practice |
| AC-4 | required | Observational safety is the wrapper's contract |
| AC-5 | required | The taxonomy doc is the operator-facing contract |
| AC-6 | required | Suite-green is the delivery gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Crediting the post-write ledger version each event could read as self-dealing (every write mints a new creditable version) | It is the honest reading: each event genuinely obviates a fresh read of the grown authoritative ledger; the once-only key bounds it to one credit per version, and the reference doc states the semantics plainly |
| Extractor file resolution drifts outside the repo root | Containment check reuses the 1t3s7 `_artifact_file_tokens` pattern; failures credit nothing |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
