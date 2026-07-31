# Review Workflow Ergonomics

Change ID: `1ttp6-enh review-workflow-ergonomics`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-29
Wave: `1tvbs review-workflow-ergonomics`

## Rationale

The review controls now enforce approval currency, repair chronology, independent lane
clearance, evidence integrity, and convergence correctly. Using those controls still requires
too much protocol archaeology. During waves `1tsyx` and `1tuoc`, reviewers repeatedly had to
inspect large ledger listings, infer the next valid actor and event shape, and learn required
fields from rejected write attempts. That made a sound process look confused and made review
duration depend too heavily on familiarity with the ledger implementation.

This is the third wave pursuing review-lifecycle simplification. It succeeds only if the ordinary
workflow has fewer calls and rejected retries without adding another public mode, state authority,
or mandatory transition. The existing `wf_review_wave` entry point will provide one concise,
state-derived workflow snapshot; `wf_review_event(event="list")` remains the unchanged forensic
history surface. The change does not weaken gates, merge independent reviewer roles, or make review
evidence inferentially true.

## Requirements

1. Make the existing `wf_review_wave` response the single guided review-status **entry point**. It
   runs its existing full validation once and returns a bounded set of current legal actions plus
   one deterministic `recommended_next_action`. A successful `wf_review_event` write returns the
   same bounded projection for the post-commit ledger state as an additive continuation payload;
   it is not an inspection mode, does not run validation, and is absent on dry-run or failed writes.
   Finding
   actions are ordered by first-seen finding order and then action kind; approval actions follow the
   existing required-signoff order. When several reviewer lanes may legally clear in any order, the
   recommendation must not imply that the other legal lane operations became invalid.
2. Define a discriminated, phase-scoped action union in `review_evidence.py` with separate
   `repair_start`, `reverification`, and `approval` shapes. Every action contains `action_kind`,
   `actor_role`, `phase`, `state_args`, `required_caller_inputs`, `legal_alternatives`, and
   `reinspect_after_success`. `state_args` contains only mechanically derived fields:
   `repair_start`/`reverification` may carry event, run kind, cycle, finding, source/current lane
   sets, and affected approvals; `approval` may carry event, signoff key, and approval phase.
   `required_caller_inputs` names the still-required context, judgment, evidence, integrity,
   freshness, and independence fields. `reinspect_after_success` names the successful write
   response as the normal continuation source and `wf_review_wave` as stale/failure recovery; it
   must not prescribe a second full-validation call after every accepted write. These are
   schema-completable templates, not executable requests until the caller supplies and attests
   those inputs; no placeholder string is executable.
3. Distinguish operator-owned decisions, implementer-owned repair starts, blocking-lane
   reverifications, and council approval refreshes. A tool must not suggest that one actor can
   perform another actor's independence-bearing step.
4. Preserve `wf_review_event(event="list")`, including its parameters and response shape, as the
   forensic/history surface. Do not add a compact list mode. Initial inspection and stale/failed
   recovery route to `wf_review_wave`; an accepted write continues from its own additive
   post-commit action payload instead of requiring either a list call or another full review call.
5. Make `review_evidence.py` the named vocabulary owner. Export canonical field registries for the
   action union and caller-required judgment/evidence/integrity inputs; `wf_review_wave`, event
   diagnostics, seed 209, and tests must consume or verify against those registries. The fresh-build
   MCP registration must expose the existing top-level `approval_phase` and `integrity_checks`
   parameters, while `required_caller_inputs` exposes their nested requiredness without changing
   the writer's compatible `dict` input contract. State the reconnect limitation for attached
   clients whose tool schema was cached before reload.
6. Route chain-sequence and field-shape write rejections to phase-correct `wf_review_wave` recovery.
   Preserve specialized recovery for missing/stale readiness receipts, invalid ledgers, path/storage
   failures, and other failures for which review actions cannot be trusted. An invalid/unreadable
   authority emits no derived actions. Diagnostics must not contain stale or hand-assembled retry
   calls.
7. Update the review guidance to repair by bounded root-cause family: look for adjacent variants
   sharing the same mechanism and admitted scope, fix them in the same repair pass, and then run
   one class-level reverification. Unrelated or low-value observations retain the existing
   `maybe_later`, `dont_do_later`, and `not_issue` dispositions.
8. Before product edits, freeze canonical starting ledger bytes and an executable baseline driver
   for the single-lane, multi-lane, multi-cycle, stale-approval, and operator-signoff shapes from
   `1tsyx`/`1tuoc`. The current driver uses public `wf_review_wave`, forensic list inspection, and
   public writes. The candidate starts from identical bytes and differs only by consuming the
   initial `wf_review_wave.next_actions` and each accepted write's post-commit continuation after
   supplying fixed explicit caller-owned inputs. Record the
   normalized call trace, accepted transition sequence, invalid-diagnostic matrix, final canonical
   ledger bytes, current heads, approval currency, convergence state, close dry-run result, and
   `run_validate` invocation count partitioned into the guided review-navigation interval and the
   unchanged final close dry-run.
9. Preserve existing event records, append-only ledger semantics, approval chronology,
   convergence behavior, and close-gate outcomes byte-compatibly except for additive
   `wf_review_wave` and successful-create `wf_review_event` response fields plus diagnostic fields.
10. Introduce no new MCP tool, event type, list mode, production sensor, or mandatory lifecycle
    transition. The canonical multi-lane and multi-cycle fixtures must require fewer
    inspection/recovery calls than the current flow while retaining equal or stronger invalid-state
    detection.
11. Cap current action templates at `REVIEW_ACTION_CAP = 50`. The response must report
    `total_current_actions`, `returned_current_actions`, `omitted_current_actions`, and `truncated`;
    truncation emits a named diagnostic pointing to the unchanged forensic list route. The top-level
    recommendation is selected from returned actions only, and the response must never claim it
    contains every current action when truncated.
12. Introduce one structured authority projection in `review_evidence.py` that owns current finding
    facts, structured approval-affect relationships, approval currency, and legal action derivation.
    Preserve `review_status_rows` and the list response as exact legacy presentations consuming the
    same structured facts; do not parse `why` prose or reimplement `_finding_affects_signoff`.

## Scope

**Problem statement:** Review state is mechanically decidable, but the current operator surface
exposes enough raw protocol detail that callers still reconstruct the next legal transition by
trial and error.

**In scope:**

- Additive `next_actions` data on the existing `wf_review_wave` response, derived from its resolved
  `ReviewAuthority.records` and the existing current-head/approval-currency functions.
- The same derived projection on successful `wf_review_event` create responses as a post-commit
  continuation only; dry-run, error, and list responses retain their existing shapes.
- Unchanged `wf_review_event(event="list")` behavior as the forensic/history route.
- Review-event validation diagnostics and registered tool schema/description alignment.
- Seed 209 and corresponding tool/reference documentation for the guided repair flow.
- Hermetic replay tests for multi-finding, multi-lane, and stale-approval review states.
- A deterministic evaluation fixture in the existing test suite that counts inspection calls,
  rejected writes, mandatory transitions, and preserved invalid-state detection.

**Trust boundaries touched:**

- The registered MCP schema and response contract presented to agent clients.
- The append-only review ledger versus its derived current-chain and approval-currency views.
- Actor ownership boundaries between implementer, reviewer lanes, council, and operator.

**Expected files in scope:**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/review-and-evals.md`

**Out of scope:**

- Weakening or removing readiness, delivery, independence, chronology, integrity, or operator
  signoff gates.
- Automatically attesting evidence, freshness, independence, or reviewer judgment.
- Allowing one actor to clear multiple independent reviewer lanes in one event.
- Redesigning the policy/receipt/evaluator architecture delivered by wave `1tuoc`.
- A general dashboard redesign or a new interactive review UI.
- Automatically fixing every nearby observation regardless of scope or value.
- A new MCP tool, `wf_review_event` event/list mode, production telemetry sensor, or required
  lifecycle transition.
- Changes to summarized rendered reviewer carriers: seed 209 remains the sole full protocol owner,
  and carrier summaries remain unchanged.

## Acceptance Criteria

- [x] AC-1: One initial `wf_review_wave` call over each canonical nonterminal fixture returns the
  discriminated current action templates, legal alternatives, one deterministic recommendation,
  phase, counts, and exact truncation state; each accepted write returns the same projection for its
  post-commit state, and alternative legal lane orders remain accepted.
- [x] AC-2: `wf_review_wave` returns at most 50 current actions in stable order, reports total,
  returned, omitted, and truncated counts, and emits a named forensic-route diagnostic on overflow.
  The complete `wf_review_event(event="list")` contract remains byte/shape compatible.
- [x] AC-3: After the fixture supplies every named caller-owned input, executing the initial
  recommendation and then each successful write's continuation reaches the expected terminal state
  for single-lane, multi-lane, multi-cycle, stale-approval, and operator-signoff fixtures with zero
  exploratory rejected writes and exactly one full-validation call during review navigation before
  the separately measured close dry-run.
- [x] AC-4: Implementer, reviewer-lane, council, and operator steps are assigned only to their
  permitted actors; mutation tests prove that actor substitution and same-context reverification
  still fail closed.
- [x] AC-5: Exported field/action registries in `review_evidence.py` are the vocabulary authority;
  the action response, diagnostics, seed/spec prose, and fresh-build MCP top-level schema are pinned
  to them without copied parallel field sets.
- [x] AC-6: Chain-sequence and field-shape rejections route to phase-correct `wf_review_wave` and
  yield a schema-completable retry; invalid authority emits no action, and readiness-receipt,
  path/storage, and other specialized failures keep their existing recovery.
- [x] AC-7: Review guidance explicitly requires a bounded adjacent-variant census for the repaired
  root-cause family and preserves honest non-action dispositions for unrelated or low-value items.
- [x] AC-8: Existing ledger compatibility, complete list-tool contract, gate polarity,
  lane-by-lane independence, approval chronology, convergence, and close behavior pass unchanged;
  additive `wf_review_wave`, successful-create `wf_review_event`, and diagnostic response fields are
  the only intentional contract delta. Dry-run, error, and list responses remain unchanged.
- [x] AC-9: Existing-suite evaluation fixtures report baseline and candidate inspection calls,
  rejected writes, full-lint calls, mandatory transitions, and invalid-state detections from
  identical canonical bytes. Multi-lane and multi-cycle candidates each use at least one fewer
  inspection/recovery call, produce zero exploratory rejected writes, use exactly one full-lint
  call during review navigation through the initial `wf_review_wave`, add no mandatory transition,
  and finish with identical canonical ledger bytes, heads, approval currency,
  convergence, and close outcome. Actor swap, same-context reverification, stale lane set, wrong
  cycle, missing repair start, wrong approval phase, and malformed integrity payload remain red with
  zero append. The final public close dry-run remains full-corpus: candidate and baseline each use
  exactly two total full validations (one initial review plus one final close) and no accepted event
  write runs one. Known-bad mutations prove the oracle can fail.
- [x] AC-10: Exact pre/post censuses of registered MCP tool names/top-level schemas, review event and
  run-kind enums, list parameters, lifecycle transition/gate registry, configured production
  sensors, and accepted event/run-kind/actor sequences prove the change adds no tool, event/list
  mode, sensor, gate, or transition; one known-bad addition to each census fails its test.
- [x] AC-11: A valid direct `wf_review_event` write without a preceding `wf_review_wave` call still
  succeeds, proving guided inspection is not a mandatory transition, token, or cursor.
- [x] AC-12: `review_status_rows` and the forensic list keep their existing public shape while both
  they and `wf_review_wave.next_actions` consume the same structured authority projection; source
  pins reject prose parsing or parallel approval-affect logic.

## Tasks

- [x] Define canonical structured authority facts plus the discriminated action union and field
  registries in `review_evidence.py`.
- [x] Add bounded `next_actions` to `wf_review_wave` by consuming `ReviewAuthority.records`, without
  duplicating chain derivation or changing `wf_review_event(event="list")`.
- [x] Attach the same post-commit projection to successful `wf_review_event` create responses so
  accepted transitions continue without another list or full-validation call.
- [x] Generate diagnostics and schema-completable recovery action templates from the same action
  model, retaining explicit `required_caller_inputs` for every caller-owned attestation.
- [x] Reconcile the registered schema, docstring, tool specification, and seed 209 vocabulary.
- [x] Freeze the pre-change baseline driver/bytes and add candidate, equivalence, call-count,
  invalid-mutation, cap-boundary, and direct-write controls to existing tests; add no sensor.
- [x] Run mutation checks proving the guided path does not bypass existing gates.
- [x] Reconcile the affected canonical seed, self-hosted reference, and fresh-build tool descriptions; no platform-rendered surface changed. Run focused plus canonical verification.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Action-model design | implementer | — | Reuse current synthesis; no parallel state machine. |
| Tool and diagnostic integration | implementer | Action-model design | Extend `wf_review_wave` and successful event-write continuations; keep the list tool unchanged. |
| Prompt/schema reconciliation | docs-contract-reviewer | Action-model design | One vocabulary across generated surfaces. |
| Replay and usability evaluation | qa-reviewer | Tool and diagnostic integration | Existing-suite fixture only; include known-bad and actor-substitution controls. |
| Independent delivery review | code-reviewer | All implementation workstreams | Review gate preservation before ergonomics gains. |


## Serialization Points

- The typed action model and its response vocabulary must settle before tool, diagnostic, seed,
  and test edits proceed in parallel.
- Changes to `server_impl.py`, `review_evidence.py`, and seed 209 require normal repository edit-gate
  serialization.
- The existing-suite evaluation baseline must be frozen before candidate behavior is measured.

## Affected Architecture Docs

Update `docs/specs/mcp-tool-surface.md` for additive `wf_review_wave` response/schema changes and
`docs/contributing/review-and-evals.md` for the ownership boundary: seed 209 owns the full human
protocol; `review_evidence.py` owns state/vocabulary; `wf_review_wave` owns derived guided
presentation; `wf_review_event` owns typed writes and forensic listing. No testing-architecture
change, rendered-carrier change, new sensor, or ADR is expected.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The concise state-derived action view is the central outcome. |
| AC-2 | required | Compactness is necessary to remove the ledger-archaeology failure mode. |
| AC-3 | required | The guided path must be executable, not descriptive. |
| AC-4 | required | Ergonomics cannot weaken independence or actor boundaries. |
| AC-5 | required | Schema/document drift caused a real rejected-call detour in `1tuoc`. |
| AC-6 | required | Recovery must converge through one current-state route. |
| AC-7 | important | Root-cause batching reduces repeated repair cycles without forcing scope creep. |
| AC-8 | required | Existing review enforcement and archives are compatibility boundaries. |
| AC-9 | required | The claimed simplification is not real without a fair executable baseline and equivalent outcome. |
| AC-10 | required | A third simplification wave must not add another public workflow surface. |
| AC-11 | required | Guided inspection must remain optional rather than becoming a hidden lifecycle step. |
| AC-12 | required | One structured authority projection prevents the new presentation from becoming a second model. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-29 | Created as the focused ergonomics follow-on to wave `1tuoc`; intentionally excludes review-policy redesign and gate relaxation. | Operator direction after final `1tuoc` review; observed schema-discovery and ledger-navigation detours. |
| 2026-07-29 | Thought: freeze the current public-path baseline before product edits, then implement the canonical structured projection and integrate it at the two permitted presentation points. | Implementation activated only after final code, architecture, QA, docs-contract, and Wave Council readiness approvals; next action is baseline/source census with no behavior mutation. |
| 2026-07-29 | Froze the pre-change two-lane public workflow before changing product behavior. | Fixed wave-id canonical starting ledger SHA-256 `a3fa2311d0c993c22c1e950797c3b4a1ec40c1ac6d125126b33bfa560dad2fcc`; executable baseline passes and records one `wf_review_wave`, four forensic list inspections, three accepted writes, one navigation validation, zero rejected writes. The candidate reaches byte-identical ledger authority and identical projected heads/status rows with no list calls and the same three accepted writes. |
| 2026-07-29 | Thought: implement the action vocabulary and structured authority projection in `review_evidence.py` first; server integration will only consume that projection and must leave list/dry-run/error response shapes untouched. | Baseline is frozen and passing; the next scoped mutation is the canonical model, not a presentation-layer reimplementation. |
| 2026-07-29 | Implemented the single guided authority projection and integrated it into initial review plus successful post-commit writes. | `review_evidence.py` owns discriminated repair/reverification/approval actions, exact counts, stable ordering, legacy presentation, and the 50-action cap. `wf_review_wave` runs the one navigation validation; accepted writes run none and carry the next projection. Dry-run, error, partial, and list shapes remain without a continuation. |
| 2026-07-29 | Proved the simplification over identical canonical authority through two repair cycles. | Fixed starting SHA-256 `a3fa2311d0c993c22c1e950797c3b4a1ec40c1ac6d125126b33bfa560dad2fcc`; baseline trace uses one review, seven forensic inspections, and six accepted writes; candidate uses one review, zero forensic inspections, and the same six writes. Both produce byte-identical ledger bytes, heads, status rows, convergence checkpoint, and close signature. Each uses exactly two full validations total: initial review plus final close. |
| 2026-07-29 | Reconciled guidance and completed verification. | Seed 209 and public references route normal work through `wf_review_wave` plus successful-write continuations, retain bounded same-root-cause review, and document stale-client reconnect. Docs-lint clean; `git diff --check` clean; canonical suite 6,454/6,454 across 61 files OK. |
| 2026-07-29 | Independent delivery review requested changes; affected AC/task claims were reopened immediately. | Six typed blocking findings recorded: prerequisite-blind approval actions, an accepted zero-lane nonterminal loop, quadratic alternatives bypassing the response cap, missing post-build recovery metadata, phase-wrong recovery, and mutation-proven gaps in the five-shape evaluation oracle. Code, QA, and architecture lanes requested changes; docs-contract passed contingent on the architecture repair. |
| 2026-07-29 | Repaired all six delivery-review findings and restored the affected AC/task evidence. | Approval templates now require the named phase run and disappear when the policy receipt is stale; accepted zero-lane heads route through an originating reviewer to a terminal reverification; the cap bounds alternatives as well as top-level actions; both builder and post-build rejections carry phase-authoritative guided recovery; successful continuations use the same authority-derived phase. Public-path fixtures now cover single-lane, multi-lane, zero-lane, multi-cycle, stale-approval, and operator-signoff shapes, plus a product-seam actor mutation that demonstrably fails the oracle. Focused review/evidence and server-tool tests are green; independent lane reverification follows the final canonical run. |
| 2026-07-29 | Completed independent cycle-1 reverification and final canonical verification. | Architecture, code, and QA independently cleared all six typed findings. QA's adjacent-variant pass drove one final correction: the projection resolves the repair actor through linked executable evidence and selects a distinct reviewer for malformed-but-accepted zero-lane history. Four public zero-lane variants terminate; the two-process publication-lock regression passes. Re-Prepare then exposed and pinned the adjacent valid-specialist-readiness-on-OPEN-wave case without restoring invalid caller-phase trust. Final canonical suite 6,466/6,466 across 61 files OK; docs-lint and `git diff --check` clean. |
| 2026-07-29 | Completed cycle-2 repair bookkeeping and independent reverification for specialist readiness routing. | The live re-Prepare flow exposed that a valid specialist `approval_phase="readiness"` must remain authoritative even after the wave is OPEN. The bounded repair preserves that case while council/operator mismatches, invalid specialist phases, and finding continuations still derive recovery from canonical authority. Because the code repair preceded its typed `repair_start`, the chronology deviation is disclosed in the ledger rather than hidden; a fresh code reviewer independently re-executed the valid and invalid phase matrix plus the two-process publication-lock control. The cycle-2 head is terminal with no unresolved lane. |
| 2026-07-29 | Implemented the five cycle-3 final-review repairs under pre-recorded repair starts. | Repair actors are excluded from their own blocking lanes; stale lane templates cannot restore a cleared lane; guided repair cycles follow wave-global completed/incomplete chronology; exported registries now own action state, caller input, judgment, and evidence field vocabularies and are pinned to seed/spec/tool guidance; and the frozen evaluation now covers deterministic single-lane/stale-approval/operator equivalence plus all seven named invalid transitions with zero append. The focused review-evidence and public server-tool suites pass 178/178; independent lane reverification remains required before restoring delivery approval. |
| 2026-07-29 | Completed independent cycle-3 code, QA, and docs-contract reverification. | Code mutation-proved the repair-actor, global-cycle, and stale-lane guards; QA re-executed eight public repair/evaluation tests and cleared all four assigned findings; docs-contract mutation-proved the exported registry and public-surface pins. Each owning lane was recorded separately from current list state, and all five cycle-3 chains are terminal with no unresolved required lanes. Focused verification remains 178/178, docs-lint is clean, and delivery approvals remain separate from repair completion. |
| 2026-07-29 | Refreshed every specialist delivery approval after a distinct architecture pass. | The architecture reviewer confirmed single ownership in `review_evidence.py`, ledger-derived rather than persisted cycle authority, transaction-bound monotonic lane clearing, 43/43 historical typed-ledger compatibility, and no new tool/event/gate/sensor surface. Code, QA, docs-contract, and architecture approvals now post-date the cycle-3 repairs; readiness/delivery council and operator decisions remain separate. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-29 | Improve the existing review tools instead of introducing a new review protocol or UI. | The state machine is sound; the problem is presenting its next legal transition clearly. | New orchestration tool or dashboard workflow — rejected as unnecessary surface area. |
| 2026-07-29 | Measure successful guided transitions and rejected writes, not elapsed time. | Timing is machine- and reviewer-dependent; transition counts directly measure protocol friction. | Wall-clock budget — rejected as noisy and flake-prone. |
| 2026-07-29 | Make `wf_review_wave` the single guided status surface and leave `wf_review_event(event="list")` unchanged as forensic history. | `wf_review_wave` already resolves `ReviewAuthority` and owns the operator-facing review evaluation; adding another list mode would create public surface area without removing a step. | Remove records from the default list — rejected as breaking. Add a compact list mode — rejected as another mode in the third simplification wave. |
| 2026-07-29 | Recommend one deterministic lane operation without redefining the valid transition set. | Current lane clearing deliberately permits any unresolved lane to act next; ergonomics may choose a stable presentation order but must not narrow protocol semantics. | Claim a single uniquely valid operation — rejected as false. Batch-clear lanes — rejected because it weakens independent actor ownership. |
| 2026-07-29 | Prove ergonomics with existing-suite fixtures, not a production usability sensor. | Call counts and rejected transitions are deterministic test properties; production instrumentation would add runtime and documentation surface without improving the workflow. | Ship a sensor and testing-architecture contract — rejected as unnecessary machinery. |
| 2026-07-29 | Emit discriminated schema-completable templates, never purported executable calls with invented evidence. | Repair and approval events have different mechanical fields, while judgment, evidence, integrity, context, freshness, and independence remain caller-owned. | One universal copy-ready call — rejected as structurally false. Placeholder evidence — rejected as fabricated attestation. |
| 2026-07-29 | Build both legacy presentation and guided actions from one structured authority projection. | `review_status_rows` is currently presentation-shaped and cannot safely be reparsed for affected approvals; duplicating `_finding_affects_signoff` would recreate the drift this wave is meant to remove. | Parse `why` strings — rejected as unstable. Recompute affected approvals in `server_impl.py` — rejected as a second authority. |
| 2026-07-29 | Run full validation once at the guided entry point and continue from successful event-write responses. | `wf_review_wave` is intentionally one of six full-corpus lifecycle gates; calling it after every transition would make the simplified path slower. A post-commit continuation is already inside the typed write operation, uses the same canonical projection, and adds no inspection mode or authority. | Cache or weaken full validation — rejected as a gate regression. Re-run `wf_review_wave` after every write — rejected as extra cost. Add a compact list mode — rejected as new surface. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A schema-completable action template may expose fields a client schema has cached without recognizing. | Pin fresh-client registration and state reconnect/restart requirements explicitly; retain explicit `required_caller_inputs` and keep the action object structured as well as human-readable. |
| Simplification could accidentally infer reviewer judgment or merge lanes. | Derive only mechanical state and required operation fields; retain caller-authored evidence and one-lane-per-event enforcement. |
| Adding another summary could create a second state authority. | Build `wf_review_wave.next_actions` solely from `ReviewAuthority.records` and the existing current-chain/approval-currency synthesis; source-pin against parallel derivation. |
| Adjacent-variant guidance could recreate unbounded review scope. | Require the same root cause, admitted scope, and bounded repair surface; otherwise use an explicit non-action disposition. |
| A deterministic recommendation could be mistaken for a new serialization rule. | Label it as recommended, test alternative legal lane orders, and leave validation semantics unchanged. |
| A capped response could conceal live work while claiming completeness. | Return exact total/returned/omitted/truncated fields, stable ordering, and a named forensic-list diagnostic. |
| A call-count result could win by handicapping the baseline. | Freeze identical starting bytes, the current public baseline driver, accepted transitions, final ledger/state, invalid matrix, and lint-call count before product edits. |
| A successful-write continuation could become a second inspection surface. | Emit it only after a committed write, from the same structured projection; keep it absent from dry-run, error, and list responses, and route initial/stale/failed inspection to `wf_review_wave`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
