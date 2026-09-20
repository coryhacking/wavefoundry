# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0h1 tool-registry-dispatch`
Title: Tool Registry Dispatch

## Objective

When this wave closes, the MCP server has an enumerable runtime registry of tool specifications and one explicit, ordered middleware chain, with no handler moved and the public tool surface byte-identical to the golden fixture.

## Changes

Change ID: `1y0be-ref tool-registry-and-wrapper-chain`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-19

## Wave Summary

Wave `1y0h1 tool-registry-dispatch` (Tool Registry Dispatch) delivered one change: Declarative Tool Registry And Explicit Wrapper Chain. Notable adjustments during implementation: Declarative Tool Registry And Explicit Wrapper Chain: Readiness drift check at `f4063a85` after `1y0h0` and `1yd97` landed, run as one scoped round under the rule that readiness takes at most one round once the design is settled. Code-reviewer, qa-reviewer and red-team each approved this wave with no blocking finding. Their notes are applied here in one pass: Requirement 3 now states the only chain shape that keeps the `1y0do` permutation test, the `1yd97` provenance test and the lock-order structural test green unchanged, which three lanes each confirmed by scratch-copy mutation; Requirements 2 and 4 name the roster source, the build order and the purge placement; AC-3, AC-4 and AC-5 name their subjects and tests; line anchors are replaced with symbols; Declarative Tool Registry And Explicit Wrapper Chain: Delivery round 1: code-reviewer approved; qa-reviewer blocked on two false sentences in `1ye5y-adr` (`QA-DEL-1`: the wrapper order was already stated in `build-and-verification.md` and pinned by the `1y0do` tests; `QA-DEL-2`: modules loaded through `_load_script` or lazily are re-imported on reload, and what fails is the reload test's public-name lookup). Both corrected in the record. The non-blocking gaps both lanes found were closed in the same pass: tests now pin the runtime drift warning, the registry-build fallback, `tools()` ordering, rebinding by assignment or by a literal `setattr` of `fn`, and the import placement and purge entry, and seven mutants that had survived now each fail a test; an unusable roster now yields an empty registry instead of 89 false defects; `MIDDLEWARE` moved to directly follow the wrappers; the reload probe now guards its scratch path and checks code objects. Two wording imprecisions in this document are recorded here rather than edited, since editing digested text would rotate the receipt: Requirement 3's "every callable that wrapper replaced" means the callable the wrapper installed, the 2026-09-19 Rationale paragraph's claim that a lazily imported module fails the reload test holds only for a lazy import outside re-registration, and the Scope problem statement's "documented only in a comment" and "parity is checked by parsing source" omit the pre-existing `build-and-verification.md` statement and the `1y0do` runtime tests, as `QA-DEL-1` corrected in the decision record; Declarative Tool Registry And Explicit Wrapper Chain: Delivery scoped reverification: qa-reviewer replayed `QA-DEL-1` and `QA-DEL-2` against their original reproductions and both are closed; code-reviewer read the repair diff and confirmed its round-1 approval holds, finding every tool's served wrapper chain and the reload probe byte-identical across HEAD, round 1 and the repair. Delivery converged in the one scoped round. Notes carried, not repaired after approval: the rebinding test does not catch `object.__setattr__` or a `for`-loop target; the late binding of a single `MIDDLEWARE` entry, an empty `TOOL_TIERS` mapping, and a roster without `RUNNER_TOOLS` are not individually pinned.

**Changes delivered:**

- **Declarative Tool Registry And Explicit Wrapper Chain** (`1y0be-ref tool-registry-and-wrapper-chain`) — 6 ACs completed. Key decisions: Flat sibling module, not a `server/` package; Roster check stays warning-only at runtime
## Watchpoints

- Requires `1y0do` closed; AC-1 is defined against the golden fixture.
- The actual wrapper order is cost innermost, lifecycle lock middle, upgrade-publication guard outermost. The RFC and kickoff state it differently; the existing guard-is-outermost test is the authority.
- The runtime roster check stays warning-only by recorded decision; do not reverse it.
- `repo_root`, `subprocess_util`, `venv_bootstrap`, and now (as of `1y3og`, verified 2026-09-17) `setup_readiness` and `runtime_advisory` are outside the reload purge list and stay stale across `wf_reload_mcp`; out of scope here, worth its own small change, and growing.
- This wave does not unblock Waveforge; do not sequence it ahead of `1y0gz` or `1y0h0`.
- Resolved 2026-09-17: `1y0h2` keeps decorated closures in `register_mcp_surface` and delegates late to sibling response modules. No hand-authored tool specifications or second registration source; AST and runtime parity coverage remain.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-DEL-1 | do_now | no | completed | — |
| QA-DEL-2 | do_now | no | completed | — |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- `1y0do tool-surface-snapshot` must close before implementation.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| credit_history_unavailable | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":192,"measurement_status":"credit_history_unavailable","pending":false,"schema_version":1,"stages":{"implement":{"calls":111,"content_source_credit":1576147,"derived_artifact_credit":1147,"direct_net":1326822,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3590,"response_debit":250379,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3497},"plan":{"calls":65,"content_source_credit":1474064,"derived_artifact_credit":3059,"direct_net":1376391,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7187,"response_debit":100418,"source_credit_count":64,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6873},"review":{"calls":15,"content_source_credit":123673,"derived_artifact_credit":519,"direct_net":87559,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6080,"response_debit":32555,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":191,"content_source_credit":3173884,"derived_artifact_credit":4725,"direct_net":2790772,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16857,"response_debit":383352,"source_credit_count":126,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12372},"wave_id":"1y0h1 tool-registry-dispatch"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 6 | 0 | 6 | 3,161,837 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":3161837,"surfaced_events":6} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a 90-site decorator conversion may be avoidable by introspecting FastMCP's own tool table; strongest-alternative: recorded as an open decision for the operator, not applied).
- **Prepare-phase Wave Council [prepare-council] — 2026-09-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: red-team claimed the module purge list Requirement 4 depends on does not exist, refuted by the `sys.modules` eviction block at the top of `server_impl.py`; strongest-alternative: AC-1 restated as an AST-digest test and Requirement 2 gains the `RUNNER_TOOLS` timing invariant, both applied in-session; `1y0h2` composition mismatch recorded as a watchpoint for that wave's own re-ready).
