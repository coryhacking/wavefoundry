# Extract Lifecycle Gate Checks Into Named Units

Change ID: `1y044-ref extract-lifecycle-gate-units`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-14
Wave: `1y0h0 typed-phase-gates`

## Rationale

**Brief.** Goal: turn the prepare, review, and close checks into an ordered list of named, independently tested gate units per phase, with no behavior change, so the companion change can add config-declared gates at a seam instead of inside orchestrator bodies. Audience: framework maintainers. Approach: a flat sibling module with a small context type and phase lists; checks extracted one to one. Constraints: diagnostics identical on the existing corpus; evidence read only through the `review_evidence` facade; hot-reload safe. Success: the lifecycle test corpus passes unchanged against gates driven from the lists.

Verification found the checks partly factored already. The orchestrators `wf_prepare_wave_response` (`server_impl.py:17765` as of 2026-09-17), `wf_review_wave_response` (18524), and `wf_close_wave_response` (19659) run several hundred lines of inline sequencing each, but the load-bearing checks live in named helpers: `_evaluate_shared_delivery_state` (18375), `_review_evidence_diagnostics` (16737), `_wave_review_policy_diagnostics` (3342), and the framework test receipt pair `_framework_test_receipt_status` and `_framework_test_receipt_diagnostic` (19553 and 19641). `events.jsonl` is already the only signoff authority through `read_review_event_ledger` (`review_evidence.py:4080`). The RFC's claim that gating is interleaved is therefore overstated, which makes this a modest extraction rather than the large slice the kickoff estimates.

Re-verified 2026-09-17 against four intervening commits: `review_policy.py` is byte-identical across all four (`git diff` empty), and none of the eight functions named above changed body — only line-shifted by one insertion block earlier in the file. Separately confirmed no vocabulary collision: the new `setup_readiness.py` module (from `1y3og setup-local-reconciliation`) introduces its own `ready` / `action_required` / `indeterminate` status concept for environment and index readiness, entirely distinct from wave-lifecycle prepare/review/close readiness and its own config surface. The two never share a config key or a status enum.

## Requirements

1. A new module `.wavefoundry/framework/scripts/lifecycle_gates.py` defines `GateContext` (repository root, wave record path and parsed fields, admitted change docs, mode, the review-event ledger already read once, and the workflow config already read once), `GateDiagnostic` (code, severity, message, structured detail), and a `Gate` callable signature `check(ctx) -> list[GateDiagnostic]`.
2. Three ordered tuples, `PREPARE_GATES`, `REVIEW_GATES`, and `CLOSE_GATES`, list the default gate units for each phase. The orchestrators build one `GateContext`, run the phase tuple in order, and merge the diagnostics exactly where the inline checks ran before. Ordering and short-circuit behavior match today's control flow.
3. The existing checks are extracted one to one into gate units, including at minimum: review-evidence diagnostics, review-policy diagnostics, shared delivery state, AC and task checkbox completeness at close, the single-OPEN activation guard, the framework test receipt at close, and the docs validation and gardening results the phases consume. Each unit gets a unit test using a fixture `GateContext`.
4. Gate units obtain signoff evidence only from the `GateContext` ledger populated through `read_review_event_ledger`. A test asserts that `lifecycle_gates.py` never opens `events.jsonl` directly and never applies a regular expression to `wave.md` text for approval state.
5. No diagnostic code, message, ordering, or `next_tools` hint changes: the existing prepare, review, and close test corpus passes unchanged, and dry-run outputs on the current repository are identical before and after.
6. `lifecycle_gates` is added to the module purge list at the top of `server_impl.py`, and the reload test asserts a modified gate module is picked up by `wf_reload_mcp`.
7. No discovery, plugin loading, or configuration reading is introduced by this change; the phase tuples are static data. The companion change `1y0bd-enh config-declared-phase-gates` appends units driven from configuration.
8. The golden tool-surface fixture is unchanged.

## Scope

**Problem statement:** Gate checks are named helpers called from long orchestrator bodies, so adding a check means editing the orchestrator and there is no single place that states what a phase requires.

**In scope:**

- The gate module, context, diagnostic type, and phase tuples.
- One-to-one extraction of the existing checks and their unit tests.
- The facade-only evidence test and the reload purge entry.

**Out of scope:**

- Any new gate, any config-driven gate, and any change to which lanes or signoffs a phase requires.
- Extracting the orchestrators' non-check sequencing (mode validation, wave lookup, garden and lint invocation) out of `server_impl.py`.
- The upgrade-time hook system in `upgrade_extensions.py`.

## Acceptance Criteria

- [ ] AC-1: The prepare, review, and close test corpus passes with no test edited, and dry-run responses for `wf_prepare_wave`, `wf_review_wave`, and `wf_close_wave` on the fixture repositories are byte-identical to a pre-change capture.
- [ ] AC-2: Every unit in the three phase tuples has a unit test that exercises at least one passing and one failing `GateContext`.
- [ ] AC-3: The facade-only test passes on the completed module and fails when a direct `events.jsonl` open or a `wave.md` approval regex is introduced.
- [ ] AC-4: The reload test picks up a modified `lifecycle_gates.py` after `wf_reload_mcp`.
- [ ] AC-5: The golden tool-surface fixture is unchanged.
- [ ] AC-6: A test scans every gate unit's source (or instruments a full-suite run) and fails if any `GateContext` field is read by fewer than two gate units across `PREPARE_GATES ∪ REVIEW_GATES ∪ CLOSE_GATES`, so the "no grab-bag fields" rule below is enforced rather than aspirational.
- [ ] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Capture pre-change dry-run responses for the three phases on the fixture repositories.
- [ ] Write `lifecycle_gates.py` with `GateContext`, `GateDiagnostic`, and empty phase tuples.
- [ ] Extract the close gates first (receipt, checkbox completeness, delivery state), then review, then prepare, running the corpus after each phase.
- [ ] Write unit tests per gate unit.
- [ ] Write the facade-only evidence test.
- [ ] Add the purge-list entry and extend the reload test.
- [ ] Compare post-change dry-run captures to the pre-change captures.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ------------ | ------------ | ----- |
| capture        | qa          | —            | pre-change dry-run baselines |
| module         | implementer | —            | types and empty tuples |
| extract-close  | implementer | module, capture | smallest phase first |
| extract-review | implementer | extract-close | |
| extract-prepare| implementer | extract-review | |
| guards         | qa          | extract-prepare | facade test, reload test, capture comparison |


## Serialization Points

- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/layering-rules.md` gains the rule that lifecycle gate units consume review evidence only through the `review_evidence` facade and read configuration only through the context. `docs/architecture/current-state.md` lists the module. No decision record: the change moves code without changing policy.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The change is defined by having no behavior change |
| AC-2 | required  | Independent testability is the point of the extraction |
| AC-3 | required  | Preserves the ledger as sole evidence authority |
| AC-4 | required  | A stale gate module after reload would enforce old policy silently |
| AC-5 | required  | No public schema change |
| AC-6 | required  | Makes the context's own stated discipline self-enforcing instead of a documented intention |
| AC-7 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-14 | Change planned and admitted to `1y0h0 typed-phase-gates` | this document |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-14 | Flat sibling module with static phase tuples, no discovery | Matches how every other extracted subsystem is loaded and purged today; keeps the refactor free of policy or security decisions | (a) RFC `GatePipeline` with convention auto-discovery: couples a refactor to a trust decision. (b) Leave checks in place and only add a config hook: smaller, but the companion change would then add a second gate mechanism beside the inline one |
| 2026-09-14 | Extract close first, then review, then prepare | Close has the fewest and most self-contained checks, so the pattern is proven on the smallest surface | Prepare first: it is the largest and would front-load risk |
| 2026-09-14 | One `GateContext` reads the ledger and config once per invocation | Removes repeated file reads across checks and gives the companion change a single place to attach configured requirements | Each gate reads what it needs: simpler units, repeated I/O, harder to keep consistent |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A check's short-circuit behavior is subtly changed by list ordering | Pre and post dry-run captures compared byte for byte, plus the unchanged corpus |
| Orchestrators still hold sequencing that later needs to move | Accepted; this change owns the checks only, and the sequencing extraction is a separate decision |
| The context grows into a grab bag | The context carries only inputs that at least two gate units consume; anything else stays local to the unit. Archetype Council (Feynman, 2026-09-17): this rule is now a mechanically-enforced test (AC-6), not only a stated intention that erodes once the author moves on |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
