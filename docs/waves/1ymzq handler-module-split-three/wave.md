# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ymzq handler-module-split-three`
Title: Handler Module Split Three

## Objective

When this wave closes, five more families are out of `server_impl.py` under the `1ymzk` recipe (context-efficiency projection, index build and health, the docs and dashboard and lifecycle-surface wrappers, and upgrade), the upgrade runner's source names `dashboard_handlers` instead of the server for its dashboard reaches with a module-absence fallback for older installs, and path containment has one containment owner with resolving and pure comparison entry points adopted at eleven sites with an explicit allowlist for the rest. Now, because `1ymzk` proves the recipe on the two hardest families and these are the remaining families with clean boundaries; search, lifecycle and the registrar split wait for their own triggers.

## Changes

Change ID: `1ymzl-ref context-efficiency-handler-module`
Change Status: `complete`

Change ID: `1ymzm-ref index-handler-module`
Change Status: `complete`

Change ID: `1ymzn-ref thin-wrapper-handler-modules`
Change Status: `complete`

Change ID: `1ymzo-ref upgrade-handler-module-inversion`
Change Status: `complete`

Change ID: `1ymzp-ref shared-path-containment-primitive`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (the seven new modules: `path_containment.py` and six handler modules, the composition root, the inverted siblings, the containment adoptions, tests), technical-writer (architecture doc lines in `current-state.md`, `domain-map.md`, `layering-rules.md`, `cross-cutting-concerns.md` and `testing-architecture.md`, the standing-baseline references and their lint pin, CHANGELOG)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, security-reviewer

Completed At: 2026-09-22

## Wave Summary

Delivered all five changes and 27 ACs: six handler modules, preserved registration/reload/patch boundaries, upgrade compatibility and shared containment with caller error contracts intact. Closed on 2026-09-22 after all required independent lanes and Council approved. The framework receipt is current at 9,508 tests; docs lint and close passed. R1 passed against R0; R2 is the completed new baseline on stable generation 1914, not a cross-identity comparison. No full index rebuild and no commit were performed.

No deferred ACs or tasks. Key decisions, memory disposition, cleanup/retained exceptions and reproducible evidence are consolidated in **Review Checkpoints → Final delivery reconciliation** below. Canonical architecture/evaluation docs preserve the durable lessons; no new memory promotion was warranted.

**Changes delivered:**

- **Context-Efficiency Handler Module** (`1ymzl-ref context-efficiency-handler-module`) — 5 ACs completed. Key decisions: Second change, after containment.; `_read_ce_projection_config` read through `server_impl` at call time.
- **Index Handler Module** (`1ymzm-ref index-handler-module`) — 6 ACs completed. Key decisions: Move the whole family including members reached by search and lifecycle.; Last in the wave; final receipt becomes the new baseline.
- **Thin-Wrapper Handler Modules** (`1ymzn-ref thin-wrapper-handler-modules`) — 5 ACs completed. Key decisions: Three modules, one change; `wf_audit`, secrets gate, lint substrate and introspection stay.; The child-PID trio (set, register, reap) goes with index.
- **Upgrade Handler Module And Back-Reference Inversion** (`1ymzo-ref upgrade-handler-module-inversion`) — 6 ACs completed. Key decisions: Module-absence fallback chain in the extensions.; Invert the two dashboard reaches; keep the memory seam.
- **Shared Path Containment Primitive** (`1ymzp-ref shared-path-containment-primitive`) — 5 ACs completed. Key decisions: Operator approved the shared pure comparison entry point after an extra-resolution fault changed successful wrapper behavior.; Operator approved staging unused primitive/tests/evaluator membership before new-baseline R0; caller adoption follows R0.
## Watchpoints

- Watchpoint: receipt sequence (operator-approved staged baseline). After readiness, the only permitted pre-R0 source edits are the real unused `path_containment.py`, its focused primitive tests, and any justified evaluator membership/identity test. Derive membership against the remaining eleven planned adoptions and supported retrieval paths; the unchanged indexer helper is not evidence for registration. Prove no production caller imports or adopts the primitive yet and record the bootstrap diff/fingerprint. R0 (`docs/reports/retrieval-quality-1ymzq-before.json`) is a NEW baseline under that evaluator identity, before any caller adoption; it is not a signed comparison to `1ymzk`. Adopt containment, context efficiency, wrappers and upgrade afterward. R1 (`docs/reports/retrieval-quality-1ymzq-mid-comparison.json`) follows `1ymzo` and compares to R0 with identical evaluator and fixture identity. Only then extract index handlers and register their evaluator membership; R2 (`-after.json`) is the new baseline under that second identity boundary. Retain `1ymzk-after` as the historical reference and disclose the bootstrap baseline and final identity boundary (and whether bootstrap registration changed identity). Use a completed, policy-conformant corpus at each measurement; inspect for excluded test paths and stabilize background activity. Do not rebuild merely to obtain a receipt. Wave `1yljp` closed with an explicit operator benchmark waiver and has no after-receipt prerequisite.
- Watchpoint: every family follows the `1ymzk` rules: domain-ownership move criterion, module-level objects classified and re-exported, patch transparency narrowed to staying callers and call-time reads with every moved-to-moved site listed and repointed, plain module-body imports for the purge census, no module-top `server_impl` import and no handler-to-handler import at any scope, a committed inventory before each move, a full-classified-set AST assertion per module, and `FAMILIES` as a tool-to-response map.
- Watchpoint: constants that tests patch or assign on `server_impl` are read at call time by the moved code (`DASHBOARD_START_WAIT_SECONDS`, `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS`, `UPGRADE_SUMMARY_TERMINAL_KEYS`), as are `_read_ce_projection_config` and `project_state_publication_lock`; each is a named exception in its change doc.
- Watchpoint: `1ymzo` depends on `dashboard_handlers` from `1ymzn`; the extension hook needs a module-absence fallback because it runs from the new archive against the installed tree; the memory backfill seam in the upgrade runner is source-text pinned and is not repointed.
- Watchpoint: `wf_audit_response` (decorated at definition time), the secrets close gate, the lint substrate with `_run_post_write_lint` and the `DOCS_LINT_*` constants, `_regenerate_codebase_map_safe`, the introspection trio, `_read_framework_pack_version` (import-time server identity), `_setup_notice_key` and index-monitor policy stay in the composition root by decision; the child-PID trio goes with index.
- Watchpoint: `1ymzm` must not regress the `1yj14` interlock or epoch recovery; substrate tests pass unmodified except the two optimize-contract mock-owner repoints with assertions unchanged; `1ymzl`'s named call-time read keeps the interlock fixture's patch observed.
- Watchpoint: `1ymzp` preserves each site's predicate and failure contract, adopts only the redundant clause at the stronger sites, and carries the security-reviewer lane's per-site table; two sites gain the escape tests they lack. Operator approved leaving `indexer._is_relative_to` and all its callers unchanged; resolution errors must continue aborting prepared-removal validation.
- Follow-up: search and `WaveIndex` extraction waits for a quiet evaluator chain; lifecycle and the review ledger stay in the composition root pending the gate-pipeline RFC, a deliberate deviation from the RFC-1 end state; the registrar split of `register_mcp_surface` follows once the families are out; a server-free dashboard control path and the graph indexer's language extractors are separate waves; nineteen containment sites stay allowlisted, including the exception-preserving indexer helper.
- Follow-up: the rotating-seat heuristic reads the machine-written context-efficiency block; worth a small tooling plan.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| READY-DELTA-CONTAINMENT-ERROR | do_now | no | completed | wave-council-readiness, security-reviewer |
| READY-DELTA-RECEIPT-IDENTITY | do_now | no | completed | wave-council-readiness |
| READY-ROOT-RESOLUTION-CONTRACT | do_now | no | completed | wave-council-readiness, security-reviewer |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- Operator authorization: current request "finish the wave everything should be stable now" authorizes completion and closure after gates pass; no current-wave commit requested.

## Review Checkpoints

### Final delivery reconciliation

Implemented all five admitted refactors: six handler modules now own 111 definitions and 32 objects; public registration is unchanged. Shared containment exposes resolving and pure already-resolved entry points at eleven adoption sites while preserving the indexer's exception contract. Upgrade keeps its old-installed-tree fallback and named call-time patch seams remain observed.

R1 passed against staged R0 (27 compared keys, zero violations). R2 is a completed NEW baseline on stable generation 1914, deliberately not comparable across the final evaluator membership/anchor changes. See `retrieval-evidence.md` for identities, limitations and every failed attempt. No full index rebuild was performed.

Delivery evidence: `evidence/code-delivery.md`, `evidence/qa-release-delivery.md`, `evidence/security-architecture-delivery.md` and `evidence/council.md`. Three fresh non-implementing contexts supplied all required perspectives; QA/release/docs-contract share one, and security/architecture/primer/Council share one. Counts overlap and are not summed. The original v1 freeze moved only through six gardening timestamps; all lanes renewed against `evidence/delivery-fingerprint.json` (v2). Final R2/pointer completion was independently approved in `evidence/qa-final.md` and `evidence/council-final.md`. All ACs/tasks are complete. Readiness clarifications are current under `review-policy-94b63f24a5c63152fa15`.

Retrospective: preserve caller IO/error policy with pure comparison, verify actual registered reload and same-object state, and freeze telemetry as well as source during measurements. Existing canonical architecture and evaluation policy carry these rules. Memory checkpoint examined candidate `1ypvn-mem`: rejected as duplicated canonical guidance with no additional durable action; source history retained. No new memory promotion warranted. No intentionally unmet `[~]` ACs; broader extraction follow-ups remain outside this wave in Watchpoints.

Wave-folder cleanup: retain every admitted plan, wave/ledger path, inventory, unique review and raw receipt. New reports/probes/fingerprints are grouped in `evidence/`; no verified disposable artifact required removal. Historical readiness and handoff notes below are historical, superseded by this final outcome and typed approvals. Retain ledger-cited paths without moving them. Unrelated wave 1ypy6 and generated documents are untouched by cleanup.

Probe reproduction: retained scripts capture this checkout's absolute path and write only scratch outputs. Run with `python3 -B`; for `code-mutations.py`, first copy `.wavefoundry/framework/scripts/` into `/private/tmp/1ymzq-code-review-scratch/.wavefoundry/framework/scripts/`. For `security-probe.py`, restore `evidence/delivery-fingerprint-v1.json` to `/private/tmp/1ymzq-delivery-fingerprint.json`; its final fingerprint diagnostic intentionally exposes the superseded metadata delta. QA's additional CE survivor expansion is retained in `evidence/qa-ce-mutant.txt`; its exact mutant and detector are in the QA report. These paths and requirements preserve reproducibility without rewriting historical results. The `:delivery` context suffix used by typed approvals distinguishes operation identity from readiness; it denotes the same reviewer worker, not an extra independent context.


### Earlier checkpoints

- Implementation complete: canonical full suite passed 9,508 tests /121 files /12 skips. Fresh code, QA/release and security/architecture reviews found no implementation blockers; final QA/Council receipt reconciliation approved R2 and AC-5. See the Wave Summary and durable evidence index above.

- Docs-contract-reviewer readiness perspective: no remaining findings in the bounded pure-comparison repair; explicit preconditions, symlink ownership and no-filesystem-work contract checked. Red-team tested the extra-resolution failure and pure-comparison alternative. Evidence: `pure-comparison-readiness.md`; same-worker correlation disclosed.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer, architecture-reviewer, security-reviewer, code-reviewer, qa-reviewer, release-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the containment primitive matched about eighty functions with seven failure conventions and would have weakened seven sites, and the index move edits the evaluator and made the receipt pair incomparable; strongest-alternative: three waves with one receipt pair each, rejected by the operator for one reordered wave with a three-receipt sequence; per-seat evidence in `readiness-review.md`)

## Dependencies

- External: wave `1ymzk handler-module-split-two` must be closed before R0; it delivers `memory_handlers.py`, `techdocs_handlers.py`, the tool-to-response `FAMILIES` map and parameterized reload template in `test_handler_modules.py`, and its after-receipt as the historical reference preceding the staged new-baseline R0. Wave `1yljp explicit-precision-rebuild` is closed with an explicit operator benchmark waiver; no after receipt is required.
- Intra-wave order: `1ymzp` containment, `1ymzl` context efficiency, `1ymzn` thin wrappers, `1ymzo` upgrade (needs `dashboard_handlers`), then R1, then `1ymzm` index, then R2. All four handler changes edit `server_impl.py` and `test_handler_modules.py` under one implementer.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 156 | 2,526,401 |
| implement | 18 | 608,204 |
| review | 300 | 5,786,220 |
| **Total** | **474** | **8,920,825** |

<!-- wave:context-efficiency-state {"generation":438,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":18,"content_source_credit":618472,"derived_artifact_credit":0,"direct_net":608204,"estimated_tokens_saved":608204,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":491,"response_debit":12248,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2471},"plan":{"calls":156,"content_source_credit":2935013,"derived_artifact_credit":2541,"direct_net":2526401,"estimated_tokens_saved":2526401,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35006,"response_debit":388281,"source_credit_count":101,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12134},"review":{"calls":300,"content_source_credit":6384670,"derived_artifact_credit":4689,"direct_net":5786220,"estimated_tokens_saved":5786220,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20786,"response_debit":584669,"source_credit_count":191,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":474,"content_source_credit":9938155,"derived_artifact_credit":7230,"direct_net":8920825,"estimated_tokens_saved":8920825,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":56283,"response_debit":985198,"source_credit_count":303,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":16921},"wave_id":"1ymzq handler-module-split-three"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 42 | 0 | 25 | 19,904,511 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":25,"estimated_exploration_avoided":19904511,"surfaced_events":42} -->
<!-- wave:exploration-avoided end -->
## Historical readiness repair

Operator approved the staged baseline sequence on 2026-09-21. Cycle-1 plan repair is open; no implementation source edits occurred. Existing readiness is withheld pending fresh focused verification of the revised receipt boundary and the separately reported containment error contract. Host fresh-agent spawning currently fails with `agent thread limit reached`; retained contexts will not be represented as fresh. Source investigation used MCP code navigation. Generic implementer will own serialized source edits; required reviewer roles remain unchanged. Requested inherited model capability was selected for filesystem-security and evaluator-provenance reasoning; actual runtime identity is unknown.


## Root-resolution repair authorization

Operator approved one bounded plan repair and focused reverification before implementation: preserve renderer/TechDocs root-resolution errors and non-strict missing write-target acceptance, with differential regression tests. Typed `READY-ROOT-RESOLUTION-CONTRACT` repair cycle 1 began before edits. No framework source edits occurred. Existing indexer-preservation and staged-baseline decisions remain unchanged.


## Historical implementation handoff — R2 pending

Operator requested finishing the implementation handoff with R2 pending on 2026-09-21. All five changes are applied. Full canonical suite: 9,508 tests across 121 files, 12 skips, green; receipt hash `23beca55d485bce9f4ed5e7097dac6df7e9bbbc6b374f8e6334c8380daae317e`. R0/R1 comparison passed; R2 was not started. Final baseline pointers are staged in the working tree and explicitly pending; do not use the absent after receipt as a baseline. Complete R2 under a quiet write window, finalize its documentation, verify the receipt remains current, then run fresh independent delivery review. No delivery approval, closure, or commit is claimed.
