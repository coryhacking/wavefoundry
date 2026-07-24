# Attribute review-evidence telemetry to its explicit wave

Change ID: `1tbt6-bug review-evidence-explicit-wave-telemetry-attribution`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-23
Wave: `1tbt7 review-evidence-telemetry-attribution`

## Rationale

`wf_review_evidence` accepts an explicit `wave_id`, but its generic
context-efficiency instrumentation records against the process's ambient focus.
If an operator creates or prepares another wave before finishing review work,
review-evidence debits, source credits, and derived-artifact credits can land on
the unrelated wave. The savings are not lost, but both waves' stage accounting
becomes misleading.

## Requirements

1. Successful or target-resolved `wf_review_evidence` calls must attribute
   telemetry to the canonical explicit wave rather than an unrelated ambient
   focus.
2. The explicit target's stage must use existing lifecycle semantics: planned
   or readied work is `plan`; an open wave is `implement` until its canonical
   ledger contains a delivery run and `review` afterward.
3. Per-call targeting must not mutate process focus. Work that follows the
   review-evidence call must continue to attribute to the previously focused
   wave.
4. Sealed-wave protection remains authoritative: a call targeting a closed,
   sealed wave must demote to the general bucket rather than changing frozen
   history.
5. Existing replay neutrality, source-proof credit, derived-artifact credit,
   event identities, and accounting-gap behavior remain unchanged.
6. When the target wave-stage already has a durable minted phase, targeted and
   ambient calls must share that phase identity so source-credit deduplication
   cannot split across bare-stage and numbered-phase keys. The bare stage
   remains the stable fallback only when no phase exists for that wave-stage.
7. A paused target must explicitly use the `plan` stage, with the behavior
   documented and regression-tested rather than inherited only from an unknown
   status fallback.

## Scope

**Problem statement:** `wf_review_evidence` telemetry follows ambient focus even
though the tool has an explicit, resolvable wave target.

**In scope:**

- A narrowly registered explicit-attribution extractor for
  `wf_review_evidence`.
- An optional per-call focus override in the internal retrieval-cost recording
  path; no process-global focus mutation.
- Stage derivation from the target wave using the existing canonical
  plan/implement/review rules.
- Regression coverage for cross-wave focus, stage selection, credit placement,
  focus preservation, and sealed-wave demotion.
- Context-efficiency reference documentation.

**Out of scope:**

- Automatic rewriting of historical telemetry, including the two already
  misattributed `1tamx` calls.
- Changing attribution for unrelated tools merely because they accept a field
  named `wave_id`.
- Changing credit formulas, list replay neutrality, or lifecycle focus
  transitions.

## Acceptance Criteria

- [x] AC-1: With process focus on Wave B, a target-resolved
  `wf_review_evidence(wave_id=Wave A)` records its debit and any source/artifact
  credit against Wave A, not Wave B.
- [x] AC-2: Target-stage derivation records planned/readied Wave A work as
  `plan`, pre-delivery open work as `implement`, and post-delivery open work as
  `review`.
- [x] AC-3: The ambient focus is byte-for-byte unchanged after the targeted
  call, and the next ordinary instrumented call still attributes to Wave B.
- [x] AC-4: A targeted call against a sealed Wave A leaves its frozen snapshot
  unchanged and records through the existing general-bucket protection.
- [x] AC-5: Existing repeat-list neutrality, source-proof, artifact-credit, and
  replay tests remain green; full framework tests and docs validation pass.
- [x] AC-6: With an existing target `stage-N` phase, one ambient and one
  cross-wave targeted non-replay operation returning the same unchanged source
  both record under `stage-N` and produce only one source-credit row for that
  source version.
- [x] AC-7: A paused explicit target records in `plan`, and the reference
  contract states that mapping.

## Tasks

- [x] Add a target-wave attribution resolver registered only for
  `wf_review_evidence`.
- [x] Thread an optional per-call attribution focus through
  `record_tool_cost`/`record_retrieval` without calling `set_focus`.
- [x] Add cross-wave, stage, sealed-wave, focus-preservation, and credit
  regression tests.
- [x] Update the context-efficiency reference and run verification.
- [x] Reuse the latest durable target wave-stage phase for cross-wave calls and
  pin phase-scoped source-credit deduplication.
- [x] Make paused-target `plan` attribution explicit in code, tests, and the
  reference contract.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| attribution core | implementer | — | Per-call override only |
| wrapper integration | implementer | attribution core | `wf_review_evidence` only |
| verification | qa-reviewer | wrapper integration | Cross-wave and sealed cases |


## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py` and
  `.wavefoundry/framework/scripts/server_impl.py` must agree on the override
  shape before tests are finalized.
- The framework edit gate must be open for implementation and closed after
  verification.

## Affected Architecture Docs

- `docs/references/context-efficiency.md` — document explicit target precedence
  for `wf_review_evidence`.
- Architecture child docs are N/A: this corrects attribution inside the
  existing telemetry boundary without adding a new component or control path.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Corrects the observed cross-wave defect |
| AC-2 | required | Prevents moving the defect to the wrong stage |
| AC-3 | required | Avoids corrupting unrelated subsequent work |
| AC-4 | required | Preserves frozen-history safety |
| AC-5 | required | Protects established accounting contracts |
| AC-6 | required | Removes a bounded but avoidable duplicate-credit key |
| AC-7 | important | Makes canonical paused-wave behavior stable and discoverable |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-23 | Planned from a live cross-wave attribution failure. | Two `wf_review_evidence` calls targeting `1tamx` appeared under `1tbt5` plan telemetry after `1tbt5` became process focus. |
| 2026-07-23 | Implemented an optional per-call `Focus` override and a resolver registered only for `wf_review_evidence`; matching ambient target/stage retains the current phase identity. | Focused integration regression records the explicit target through `plan`, `implement`, and `review`, then proves the next ordinary call remains on ambient focus. |
| 2026-07-23 | Preserved sealed-history protection and existing replay/source/artifact accounting. | The public-wrapper regression seals and compacts the target, replays a targeted call, and asserts the frozen snapshot is unchanged while the call lands in general; existing credit/replay tests remain green. |
| 2026-07-23 | Verification complete. | Focused modules: 119/119; full framework suite: 6,172/6,172 across 59 files; `wf_validate_docs`: clean; `git diff --check`: clean. |
| 2026-07-23 | Live post-reload attribution verified through the registered MCP path. | After `wf_reload_mcp` reported 82 tools and `impl_matches_disk: true`, `wf_review_evidence(event='list', wave_id='1tbt5')` increased `1tbt5` plan telemetry from 11 to 12 calls and its source-credit count from 5 to 6 instead of landing on the sole OPEN wave `1tbt7`. |
| 2026-07-23 | Gapfill: used `rg --files` only to discover the dedicated `test_server_context_efficiency.py` filename after an MCP exact-search query against the wrong test file returned no cost-wrapper hits. | All behavior discovery, source inspection, and change validation used `code_outline`, `code_read`, `code_definition`, `code_references`, and `docs_search`; shell was limited to test execution, diff checks, and that filename discovery. |
| 2026-07-23 | Delivery review returned two follow-ups and the operator directed both into this wave: parallel targeted/ambient phase keys could duplicate a source credit, and paused targets mapped to `plan` only through the generic fallback. | Findings `targeted-review-evidence-parallel-phase-key` and `paused-review-evidence-target-stage-undocumented` are recorded in the canonical review ledger. |
| 2026-07-23 | Repaired both follow-ups. Targeted calls now reuse the newest durable phase for the resolved target wave-stage, with a read-only/no-store fallback; paused targets have an explicit `plan` branch and contract entry. | Focused suites: 54/54 and 67/67; full framework suite: 6,174/6,174 across 59 files; docs-lint and `git diff --check` clean. Repair-start evidence is recorded for both findings; the blocking code-reviewer lane remains for independent reverification. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-23 | Use a per-call override; do not call `set_focus`. | Correct attribution without stealing the agent's current working context. | Temporarily switch and restore focus: rejected because exceptions and concurrency make restoration fragile. |
| 2026-07-23 | Register only `wf_review_evidence`. | The defect is proven on this explicit target and broad inference from argument names is unsafe. | Override every `wave_id` tool: rejected as unreviewed scope. |
| 2026-07-23 | Do not rewrite history automatically. | Closed-wave history is sealed and existing totals remain conserved. | Move old rows automatically: rejected without a separate operator-approved correction. |
| 2026-07-23 | Reuse the newest durable phase for the resolved target wave-stage. | It unifies ambient and targeted source-dedup keys without collapsing credits across genuine phase transitions. | Deduplicate by wave-stage forever: rejected because a new phase intentionally permits recredit. |
| 2026-07-23 | Treat paused targets explicitly as `plan`. | Paused work is outside active implementation/review and should remain pre-activation accounting, but the contract must say so. | Leave the catch-all undocumented: rejected as drift-prone. |


## Risks


| Risk | Mitigation |
| --- | --- |
| Override recredits a source in an unintended phase | Reuse existing target-stage and phase conventions; pin source placement and replay behavior |
| Closed history accepts new events | Preserve `_commit_event` sealed-wave demotion and add a regression |
| Ambient focus changes accidentally | Never call `set_focus`; assert focus and the next call's attribution |
| Broad wrapper behavior regresses | Explicit extractor map entry and existing full-suite coverage |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
