# Combined readiness review — wave 1x5tq

Owner: Engineering
Status: active
Last verified: 2026-09-05

Phase: readiness. Changes: `1x81w` dry-run zero-change safety and `1x8e1` later-created doc-link target recovery. The frozen scope includes `indexer.py` idle caller integration, the focused dry-run branch matrix, graph fragment changes, builder pins/report and architecture updates. This is a fresh combined review; prior single-change council approval was not reused.

## Council verdict

Approve readiness. No mandatory plan amendment or new blocking finding. No implementation or delivery acceptance is granted; all change tasks/AC remain uncompleted until actual evidence exists.

## Protocol and independence

Full primer depth is warranted by persisted graph state, recovery acknowledgment, the unlocked dry-run boundary, and lock/epoch publication. A new isolated red-team agent ran first using all five stances and three questions. Four fixed seats ran in separate agent contexts and did not see one another’s outputs. The rotating performance seat ran after those initial judgments, supplied a concrete alternative, and each fixed seat independently appended its response. A further fresh agent received only randomized Seat1–5 texts and the attributed primer for the first merit synthesis; it did not receive the identity key. The coordinator reattaches identities only after that merit pass. No required-lane blocker was anonymized away. No reviewer implemented this wave or wrote canonical review evidence.

Roster: red-team `/root/combined_readiness/primer`; architecture `/root/combined_readiness/architecture`; security `/root/combined_readiness/security`; QA `/root/combined_readiness/qa`; reality `/root/combined_readiness/reality`; rotating performance `/root/combined_readiness/performance`; first merit pass `/root/combined_readiness/blind_synthesis`; coordinator `/root/combined_readiness`. Seats used a bounded 90-second review budget and 20-second alternative response. The phase’s probes were finite current-tree reproductions, not delivery sweeps.

## Decision and implementation guidance

Preserve extraction/rescan ownership and durable unresolved obligations per referring document. Persist them in both artifacts and fragment summaries, including zero-edge documents. Eligibility must survive skipped or failed reads and be acknowledged only after successful extraction; a global newly-created-path delta is insufficient.

Compute pending graph recovery without mutation before the outer idle return; use the same decision for dry-run reporting and locked real-build dispatch. Do not instantiate a graph session/store for unlocked preflight: `_ensure_store` can delete legacy state or reset an incompatible store. Existing read-only SQLite access offers a suitable boundary. Position the dry-run return before drift reconcile and the dirty-epoch missing-Lance hash reset as well as epoch/reap/heal/orphan writes.

Preserve required distinct dry-run branch tests and a genuine no-op, with a bounded combined graph-pending/dirty-epoch fixture to catch interaction. Verify precise pending Python fields and CLI diagnostics, never merely a dry-run flag. Run actual unchanged graph recovery through the outer caller. Check persisted state across reopen/unrelated merges, exact doc-node/edge triples plus full-build equality, node-less target exclusion from node set, unreadable and failed-read recovery, and cessation of rescans. These refine already-admitted AC, not new plan gates.

Reuse one loaded merge-state blob, preserve existing no-row-hydration/no-write assertions, and spy on unaffected-doc text reads. Whole-blob decode has real time/memory cost; selectivity of doc reads is not proof of constant-time planning. No latency improvement is claimed.

Strongest alternative: persist all normalized raw candidates and resolve during assembly. That can avoid source rereads and recover while the referring doc remains unreadable, but relocates edge ownership and adds provenance/deletion/outage equivalence obligations. Every fixed seat weighed it and preferred the admitted bounded retry repair. Full scans violate selectivity; a new sidecar adds unneeded synchronization/migration; global creation deltas lose retry acknowledgment. No backlog is created for rejected alternatives.

## Current-tree evidence and limits

Moderator independently executed current frozen tree using /Users/coryhacking/.wavefoundry/venv/bin/python -B. No product implementation exists yet.

Finite full-depth risk budget: four parameterized probes (target creation noded/node-less; never-present control; unreadable-doc unchanged recovery; public dry-run healthy/dirty epoch). No fuzzing or whole-suite runs. Graph probes use existing _RepoDriver with real graph SQLite state and fresh full-build oracle; public build_index probe uses real SQLite/Lance stores and dim4 mock embedders to avoid model/network activity.

Executed:
- /tmp/1x8e1-readiness/probe.py: target-only creation subsequently followed by unrelated build leaves 0 edges vs oracle1 for src/later.py and assets/.gitignore; assert_equivalent rejects each known bad; explicit referring-doc rescan restores equality. Never-appearing target gives 0 doc rescans and oracle equality.
- /tmp/1x8e1-readiness/recovery_probe.py: target arrives while docs directory unreadable; unchanged recovery retains0 edges vs oracle1; assert_equivalent rejects known bad.
- /tmp/1x5tq-combined-readiness/idle_probe.py: public build_index(dry_run=True,content='all') healthy idle leaves identical epoch and generation1, dispatches0 graph builds. Dirty-epoch case mutates building/generation1 to complete/generation2; _index_build_lock patched to fail on any call, proving the observed write bypasses the lock. Result also omits dry_run and reports up_to_date. Full output in idle-output.json.

Independent reference: declared no-write contract and observable generation/state identity; graph full-build equivalence plus positive explicit-rescan/negative absent-target controls. Graph oracle shares extractor with incremental path, so common extraction bugs remain unproven; admitted delivery AC pairs exact source/target/relation/doc-node and node-less assertions with differential checks.

Readiness integrity only: probes ran without skipped tests, observed real public build path or graph-session boundary, used real persistence with mock numeric embedders, asserted concrete graph differences/state transitions, detected pre-fix behavior. No claim that future repair, complete dry-run branch matrix, full-store byte-identity, CLI rendering, lock/epoch recovery integration, or failed-file-read recovery already passed. These are explicit implementation/delivery obligations. No external/network/credential-bearing calls, repository mutations, or canonical ledger writes performed.


## Frozen working-tree scope

All 11 SHA256 hashes and corresponding git hash-object fingerprints were checked against current files. Source/plan edits were prohibited during review. `wave.md` metadata and review report are excluded.

```json
{
  ".wavefoundry/framework/scripts/indexer.py": "79d01472680597430a3e74422e0070a55042712c790918a07af2624b1e910e5d",
  ".wavefoundry/framework/scripts/graph_indexer.py": "dc937661a2363381a509b110e94d1a1bf518839e649116692d4116722a9ac4d6",
  ".wavefoundry/framework/scripts/tests/test_indexer.py": "246d8e98cf62c0aabe2876a9e69026781a0640fa655eedfde2cac72fe7ba9341",
  ".wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py": "23462649ca4bcc9a1394f56de7d9f66f0c7cb0183f6e0befba957885579bee98",
  ".wavefoundry/framework/scripts/tests/test_graph_indexer.py": "974ee82dee4986f5745812259b09c9dfb1d3374f7abff84df792ee3d6802c9b8",
  "docs/architecture/data-and-control-flow.md": "112d0b1a48df3d4be2caf5d04c51deb2b6d68f1a29d51854abd98d3b6c6e5614",
  "docs/architecture/graph-index-system.md": "1d082e978453af57e4ff7d96d68f924e9fd703044d5d756deeed87bbc620f3fa",
  "docs/reports/graph-quality-post.json": "f53f805442ad856c51dcebfd3fa73cc115eaa9adf19a60ffae2cec6790c8f09b",
  "CHANGELOG.md": "fefe636c09afc7bcbd6d942b12131d5e09bc268a2a661cf5eb0f6d9c8856c75d",
  "docs/waves/1x5tq later-created-doc-link-targets/1x8e1-bug doc-link-into-later-created-target-never-gains-edge.md": "ecf70e3321ea751096e21d61c49f1ee6a39f4017c48ed5ab9c4b6b5d4ac4c773",
  "docs/waves/1x5tq later-created-doc-link-targets/1x81w-bug dry-run-reaches-zero-change-writes-unlocked.md": "ca040dad08f9610bbf6438283238521a3e6809a37b480bba42a6de9e3b9cdbe8"
}
```

Git object fingerprints:

```json
{
  ".wavefoundry/framework/scripts/indexer.py": "e8726013d02d1841de9ddd54cbb4ded8019fa7e2",
  ".wavefoundry/framework/scripts/graph_indexer.py": "da952e74b12d8a428a5399456b586f7c1079c066",
  ".wavefoundry/framework/scripts/tests/test_indexer.py": "81ec61097dc0a3a7350c434a1434274ae989a8db",
  ".wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py": "84e1593d89720d62d6cee3a20abf83fe9c8a7520",
  ".wavefoundry/framework/scripts/tests/test_graph_indexer.py": "9876da4836a2da14ca1de7d932fa650cc57713ab",
  "docs/architecture/data-and-control-flow.md": "aaf509e83a9730761bf480f2f720d6e433f9b787",
  "docs/architecture/graph-index-system.md": "4d67a26e3a9d3023430cce2d2f935b61d64472ca",
  "docs/reports/graph-quality-post.json": "6a121e7042cec3c395c05a473613e05d0fa8870b",
  "CHANGELOG.md": "a058e60570e866df18f9f7d9d8bc08558247d04e",
  "docs/waves/1x5tq later-created-doc-link-targets/1x8e1-bug doc-link-into-later-created-target-never-gains-edge.md": "af2e163ac6cb9387d3ffe40eb81bf25f50a7f36c",
  "docs/waves/1x5tq later-created-doc-link-targets/1x81w-bug dry-run-reaches-zero-change-writes-unlocked.md": "99bad005f2525292e4306a1c91c6107cbf29be59"
}
```

## First anonymized merit synthesis

# First anonymized merit synthesis — combined readiness, wave 1x5tq

Scope: changes 1x81w + 1x8e1. Inputs were only anonymized.md and the attributed primer.md. No seat key or named reports were read. Judgment is readiness, not delivery.

- seat_agreement: unanimous
- max_severity: none (actual readiness findings)
- mandatory_plan_gaps: none
- readiness_recommendation: approve
- challenge_round_required: false
- explicitly_blocking_authority: none asserted in the supplied reports

All five seats independently support readiness; one says approved-with-notes while explicitly identifying no mandatory gap. Their notes describe required implementation and verification already covered by the admitted contract. Current graph omission and unlocked dry-run mutation are concrete admitted correctness defects, supported by shared graph probes and independently repeated public Python idle probes. They are the repair's motivation, not newly discovered readiness gaps. No repaired-behavior proof exists and none is needed to label the plan ready.

The strongest agreement concerns the shared orchestration boundary: discover graph and idle maintenance obligations read-only before a no-op decision; report them through Python and CLI before a dry-run return; execute selected recovery within the existing build lock and epoch. Construction of a graph session can mutate stores, so implementing read-only discovery requires a truly read-only path. The evidence makes this a concrete hazard, but every seat identifies an already-explicit no-write contract and caller-integration requirement covering it.

The other load-bearing agreement is retained per-document retry state. A target-creation event cannot acknowledge an unresolved obligation when the referring document was unreadable. Successful extraction must replace the unresolved set, with persistence across reopen, skipped/failed reads, unrelated merges, and unchanged public caller retries. Exact edge/node expectations supplement full-build comparisons to avoid a shared-oracle failure. Whole-blob decode cost is acknowledged; document-read selectivity alone is not evidence of constant-time preflight.

There is no substantive verdict disagreement. Evidence depth varies: some seats executed the dirty-epoch reproduction, others inspected shared outputs or code. The graph probe models an unreadable-directory skip; an individual-file read failure remains a distinct future fixture. This limitation does not contradict approval because the necessary fixtures are explicitly admitted rather than claimed complete.

Strongest alternative judgment: persist normalized raw candidates and resolve links during assembly. This could recover while referring text remains unreadable and reduce rereads, but moves edge ownership and expands provenance, deletion, outage, and assembly-path equivalence obligations. No executed cost or correctness evidence establishes its superiority for this bounded scope. Prefer the admitted extraction-owned durable retry; do not create a backlog merely to retain the rejected alternative. The shared read-only preflight remains necessary under either design.

Recommendations for implementation and subsequent delivery review:

1. Retain the existing plan and scope. No readiness amendment is required.
2. Exercise combined graph-pending and idle-maintenance states, all five maintenance branches, healthy idle, Python/CLI reporting, and storage identity during dry-run. Cover the dirty epoch's missing-Lance hash reset as part of its branch.
3. Prove retry acknowledgment only after successful extraction, persisted zero-edge representations, exact noded/node-less link recovery, and unchanged public caller dispatch after both failed file reads and directory skips.
4. Observe unaffected and already-resolved document reads, reused merge-state loading, row hydration/write controls, and genuine idle no-op. Do not turn one whole-blob load into an unsupported latency claim.
5. Require the admitted regression, mutation, migration/version, documentation, and suite evidence during implementation/delivery. Existing known-bad reproductions do not satisfy completion ACs.

The primer's strongest adversarial challenge was answered consistently with concrete code seams and falsifiable planned evidence. With no unresolved premise dispute, blocking authority, or missing plan obligation, an additional challenge round is unnecessary.


Coordinator reattachment: {"Seat 1": "performance", "Seat 2": "qa", "Seat 3": "security", "Seat 4": "architecture", "Seat 5": "reality"}. Agreement is unanimous; maximum severity among actual readiness findings is none; no challenge round is triggered. Current admitted product defects are not laundered into delivery approval.


## primer source record

Full-depth isolated red-team primer (/root/combined_readiness/primer).
Strongest challenge: combined graph recovery discovery beside unlocked dry-run boundary risks planning mutation or premature return hiding pending work. Plans already require both obligations.
Best alternative: retain existing orchestration with one read-only pending-work decision, reused graph merge state, unresolved/current intersection; dry-run reports then returns; real build dispatches under lock/epoch. No new sidecar/general framework.
Stances: adversarial combined conditions; constructive shared decision; simplicity existing fragments; first-principles per-doc obligation; analogical acknowledgment-after-success and query/command separation.
Questions:
1. What caller arrangement reports graph recovery plus each idle branch without mutation while real builds execute within lock/epoch?
2. What combined-state/retry fixtures distinguish durable obligations from consumed creation events, including unchanged build_index/CLI recovery?
3. How establish useful reporting and no unaffected text reads, no repeated resolved rescans, one merge-state load, genuine idle no-op?
No mandatory plan gap identified. Contract-presence read only, no executed product proof.


## architecture source record

# Architecture readiness — combined wave 1x5tq

Verdict: approve readiness; no mandatory plan gap. Phase readiness, full scope, bounded 90-second review. This is plan-fit evidence, not implemented-behavior proof. All eleven freeze hashes match. No repository or ledger edits.

Boundaries: indexer orchestration → graph session/fragment store; build lock and durable index epoch → graph publication; Python result → CLI diagnostic. Existing ownership is retained; no new service, sidecar, dependency layer, or MCP response contract is required. Sources: domain-map and layering-rules; data-and-control-flow items 12–15; graph-index-system persistence and incremental-merge sections. The plans explicitly require both architecture-document updates, builder-version migration/pins, and CHANGELOG. No ADR needed for this bounded repair.

Strongest challenge answered: moving the dry-run return too early can hide graph recovery, while placing eligibility below either current no-op return loses unchanged retries. The combined requirements address both, rather than relying on one fix accidentally covering the other. Code confirms the concern: indexer.py:4399 bypasses the lock for dry-run; :5101 mutates drift before :5116 idle decision; :5176 opens the maintenance epoch; graph_indexer.py:13826 has an early no-change return before the symbol-only rescan at :13973. These are current-state defects already admitted, not readiness blockers.

1. Caller arrangement: compute a read-only pending-work description before the idle return, combining drift/reap/heal/dirty-epoch/orphans with graph eligibility. Dry-run returns that description before any executing mutation. A real graph recovery enters existing lock ownership from build_index and an idle epoch before graph persistence, finishing publication only after required reconciliation. Retain ordinary build dispatch; reuse graph planning state. The plans explicitly require this caller integration and unchanged Python/CLI recovery.

2. Durable fixtures: scan a doc before noded and node-less targets exist; close/reopen; create target alone; assert exact referring doc node and edge source/target/relation plus full-build equivalence. Fail/skip the referring read at target creation, perform an unrelated merge, then retry unchanged; unresolved state must survive until successful extraction. Never-created targets and post-resolution unchanged builds establish selectivity. Pair graph-pending with each distinct idle condition and verify dry-run state identity/reporting, then real recovery under lock/epoch. Requirements already cover these dimensions; fixtures are implementation guidance.

3. Cost/reporting: spy doc extraction/text reads, graph blob loads and record hydration/writes. Check no unrelated doc read, retained obligation through failure, no repeated resolved rescan, and one merge-state load shared between eligibility and merge. Assert named pending conditions in Python result and CLI output; assert no epoch/generation advance on genuine idle. Whole-blob decode remains an explicit admitted cost. No detached MCP forwarding claim is made.

Mutation accounting: no landed mechanism exists in this readiness snapshot, so no product mutations or tests executed. Planned guard-deletion, consumed-global-delta, clear-before-success, missing outer idle dispatch, and unconditional-rescan mutations belong to implementation/delivery evidence. They are NOT CAUGHT by this read-only readiness assessment. No fresh schema SQL/DML is proposed: existing artifact/blob JSON gains unresolved targets with builder invalidation, as the graph persistence documentation already describes.

Actionability: not_issue for a new plan blocker; implementation guidance above is already required by admitted AC/tasks. Unrun: behavioral probes, mutation replay, suites, and latency measurement. These remain delivery proof, not prerequisites to admitting this specified repair.

Shared-probe response: inspected moderator idle-output.json; the dirty-epoch dry-run moves generation 1→2 and building→complete, while healthy idle remains generation 1 with zero graph calls. This corroborates the admitted mutation/dispatch seams; it is moderator execution, not independent execution by this seat. Independently read graph_indexer.py:11168–11202: _ensure_store deletes legacy state and calls ensure_current. Consequently the shared read-only alternative must inspect persisted state via a read-only store path (for example SQLite mode=ro) rather than constructing the mutating session during unlocked planning. This is necessary implementation of the already-explicit no-write contract, not a new mandatory plan amendment. Verdict unchanged.

Rotating-alternative response (20-second bounded): read performance.md only. The strongest raw-candidate assembly alternative has a real architectural advantage: it can restore a newly resolvable link without reopening its referring document, avoiding retry latency during a read outage. Its price is a change of ownership from document extraction to graph assembly, requiring retained candidate provenance and consistent positive/negative path treatment through ordinary merges, zero-change recovery, pruning, and outage preservation. That is materially broader than adding durable obligations to the existing extraction/rescan owner. The admitted retry approach preserves that owner and acknowledges obligations only after successful extraction; its delayed success while a document remains unreadable is explicit and tested. Shared read-only preflight solves orchestration for either design, so the assembly alternative does not eliminate the dry-run boundary work. Prefer the admitted plan and single reusable blob; no measured performance result justifies moving ownership now. Verdict unchanged: approve readiness, no mandatory plan gap. Alternative disposition: dont_do_later for this wave, no backlog.


## security source record

# Combined readiness — security-reviewer

Verdict: approved-with-notes. Overall security severity: none. No mandatory plan gap identified. Phase: readiness, full-depth within 90-second budget; current implementation is not approved as delivered.

Frozen scope: SHA-256 verification of all 11 freeze.json entries passed. Inspected both admitted plans, security-reviewer role, threat model, indexer.py build_index and idle-maintenance boundary, graph_indexer.py extraction/link resolution and escaped matcher through MCP outline → keyword → targeted reads.

Strongest primer challenge: discovering graph repair inside the currently unlocked dry-run path must not instantiate a mutating session or consume persistent recovery obligations; placing a return before discovery would conceal needed work. The combined plans explicitly require a read-only pending-work decision before zero-change return, dry-run reporting without mutation, and real graph repair within existing lock/epoch. This is sufficient readiness coverage; implementation must prove it.

1. Caller arrangement: compute drift/reap/heal/dirty-epoch/orphan and graph recovery eligibility without writes, produce the Python result and CLI diagnostic, then return for dry_run. A real build already enters _index_build_lock at indexer.py:4415; dispatch selected graph repair in that path under its epoch before finalization. Avoid a helper constructor that silently creates/upgrades a store during planning. This is implementation guidance under 1x81w Requirements 1–3 and 1x8e1 caller integration, not a new AC.

2. Combined/retry evidence: run each pending idle condition plus graph pending recovery in dry-run and real-build cases, and genuine idle. For graph state, retain each doc obligation across failed reads/unreadable-directory skips, session reopen and unrelated builds; unchanged recovery via build_index/CLI must recover exact doc node and edge (including a node-less target) without consuming the obligation at target creation. Byte identity plus mutation evidence in 1x81w and persisted-state/differential assertions in 1x8e1 cover these obligations. No delivered-code execution claim is made by this readiness seat.

3. Reporting/cost: assert actual pending Python fields and CLI diagnostics, spy on unaffected doc text reads and repeated resolved rescans, reuse one decoded merge-state blob, retain zero-change row/write assertions, and pin the true idle no-op. Plans already include these observables; a whole-blob read has acknowledged nonzero cost.

Threat classification: controlling actors here are the operator, trusted repository content read as data, and same-user local processes. The existing dry-run write defect at indexer.py:5101, 5166, 5176 is an integrity/correctness contract failure, not a demonstrated security escalation: no evidenced less-trusted actor or authority delta passes the threat model gate. Recovery does not add network input, execution, credentials, new path semantics, or a promotion trigger. No vulnerability findings or exploit chains.

Confinement and regex: existing local-link candidate resolution and current-path membership remain the mandated boundary; implementation must reuse normalization/exclusions when persisting unresolved candidates rather than dereference arbitrary candidate strings. graph_indexer.py:13690 uses re.escape for interpolated matcher terms; no matcher change is admitted. No new caller path tool is proposed. No chains identified.

Limitations: read-based plan approval plus executed freeze verification, not behavioral proof of unimplemented code. No repository or ledger edits. No security-driven scope expansion, new backlog, or mandatory refinement.

## Cross-response to rotating performance alternative

Read performance.md only. The strongest raw-candidate assembly alternative could avoid source rereads and recover during temporary read failures, but relocates edge ownership and adds provenance/deletion/outage equivalence work. It supplies no demonstrated security benefit under the unchanged trusted-operator model. Prefer the admitted durable per-doc retry and shared read-only preflight: it preserves extraction semantics and already requires no mutation before the dry-run return plus locked/epoch-fenced real recovery. Confinement continues to depend on existing normalization/exclusions and current-path eligibility; neither approach authorizes reading arbitrary persisted candidates. No new threat boundary or mandatory requirement emerges. Verdict remains approved-with-notes; no mandatory plan gap. Alternative actionability for this wave: dont_do_later, no backlog.

Moderator-supplied executed baseline evidence (not execution by this seat) reports incremental/full edges 0 versus 1 and public unlocked dry-run generation 1→2; this reinforces the two existing correctness defects without changing their actor/authority classification. Moderator reports all 11 hashes still unchanged.


## qa source record

# Independent QA readiness — combined wave 1x5tq

Verdict: approve readiness. No mandatory plan gap. This is authorization to implement the specified verification, not delivery approval or evidence that the unimplemented fix works.

I independently read both consolidated change documents and qa-reviewer.md, the shared red-team primer, graph-output.json, idle-output.json and idle_probe.py. MCP outline → keyword → targeted reads investigated test_indexer.py:4424-4434,7428-7442 and test_graph_incremental_merge.py:57-199,823-865. SHA256 matches freeze.json for both plans and those two test files. No other seat conclusion was supplied.

Strongest challenge: moving the early return can either hide graph recovery or invoke graph/store mutation on the unlocked dry-run path. The combined requirements explicitly cover read-only discovery, useful Python/CLI reporting, the no-write return, real execution within the existing lock/epoch, and a true no-op. This is an implementation hazard already covered by the admitted contract, not missing scope.

Primer question 1: a read-only pending-work decision should collect graph recovery and drift/reap/heal/dirty-epoch/orphan obligations before deciding to return. Dry-run returns that plan; real dispatch executes inside the existing locked epoch. Reuse the graph merge-state already loaded for eligibility. Reject graph-session setup that silently initializes or migrates a store while planning. Covered by 1x81w Requirements 1-3 and 1x8e1 caller-integration scope/task.

Primer question 2: use doc-before-target fixtures for noded and node-less targets, inspect zero-edge artifacts/fragments across reopen, fail/skip the referring read at creation, then retry with unchanged inputs and unrelated merges. Assert exact doc node and edge triples before differential equality. Run through build_index and CLI to detect outer dispatch bypass. An additional combined pending-graph plus dirty-epoch dry-run case should assert both reports and full storage identity, followed by real recovery. These are concrete implementation guidance within the existing combined-wave and retry AC; no plan amendment needed.

Primer question 3: use spies on doc extraction and merge-state loading alongside the existing DeltaCostTests row/blob-write assertions; never-appearing and already-resolved targets must not re-read, and an unaffected doc must not be read. A no-pending build remains no-op. Python results and CLI diagnostic assertions should name pending reasons rather than merely assert a dry_run flag. One whole-blob read is explicitly accepted; state_reads=0 is a row-hydration assertion, not proof of zero decode cost.

AC evidence suitability:
- 1x81w AC-1: future tests must snapshot generation, epoch, metadata and Lance contents for all five distinct branches plus no-op; current reap-record-only test at 7428 proves one record, not whole-store purity. Plan already expands that coverage.
- 1x81w AC-2: explicit Python/CLI diagnostic requirement supplies falsifiable pending-work assertions; no detached MCP propagation claim.
- 1x81w AC-3: delete the landed guard in scratch and require a named storage-identity test to fail. Current baseline reproduction confirms a sensitive defect boundary exists.
- 1x8e1 AC-1: exact edge/node assertions avoid shared-oracle common-mode blindness; the existing helper uses production update_graph_index and fresh full rebuilds of the same tree. Deferred-read and outer caller tests are explicitly required.
- 1x8e1 AC-2: existing cost tests assert no unchanged rows read and no zero-change writes. Additional rescan and blob-read spies are explicitly planned, including resolved cessation.
- 1x8e1 AC-3: relevant suites, builder-version pins, docs validation and attribution of unrelated failures are explicit; no completed checkbox is being accepted prematurely.

Executed evidence: I reran `python3 -B /tmp/1x5tq-combined-readiness/idle_probe.py`; exit 0, both cases executed, no skips. Healthy baseline epoch remained identical with zero graph calls. Reachable interrupted epoch created with begin_build_epoch stayed generation 1 before public build_index(dry_run=True), then became complete generation 2. A lock spy would raise if acquired; it did not. This detects the known-bad unlocked write through the public Python boundary. Mock embedders inherited from the suite isolate embedding cost; real temporary store/Lance state is used. This reproduction asserts the bad behavior and must be inverted for the eventual regression test.

Bounded known-bad table:
| Mechanism | Detection | Observation |
| --- | --- | --- |
| Unlocked dirty-epoch maintenance | Pre-fix public-path reproduction rerun independently | CAUGHT: generation 1→2, building→complete |
| Later-created graph target | Shared current-tree graph evidence, independently inspected oracle harness | CAUGHT in shared evidence for noded/node-less and unreadable-directory skip recovery; not independently rerun here |
| Future guard deletion / future obligation loss | Planned scratch mutations | Not run: implementation does not exist; delivery obligation |

Limitations: bounded readiness review does not execute all five mutation branches, CLI recovery, combined graph/idle storage identity, or future regression/mutation suites. Those are required implementation/delivery work already in scope, not evidence claimed by this approval. No repository edits or ledger writes made.


Rotating alternative considered: I read only performance.md after completing my independent verdict. Persisting raw candidates and resolving them during assembly could remove referring-text rereads and survive a temporary individual read failure. From QA's perspective it also relocates ownership of edges and requires broader deletion/outage, provenance and zero-edge parity coverage. The admitted durable per-doc retry preserves extraction semantics and combines cleanly with one shared read-only preflight; its selectivity and retry assertions are already concrete. I prefer the admitted approach for this scope; the alternative supplies no missing requirement and does not change approval. No benchmark advantage is assumed. Precision: shared graph recovery evidence models an unreadable-directory skip, not a failed individual file read; the separate individual-read failure/retry fixture remains required future verification.


## reality source record

# Reality-checker readiness — combined 1x5tq

Verdict: APPROVE readiness. Mandatory plan gaps: none. This approves the admitted, observable repair plan, not unimplemented behavior.

Inspected both frozen change documents in full, reality-checker role, primer, shared graph/idle outputs and idle probe. Used MCP outline → keyword → targeted reads of indexer.py:5060–5268 and graph_indexer.py:13785–13857,13970–14062. SHA-256 verification matches freeze.json for both inspected source files and both change documents. No repository edits or ledger writes.

## Strongest challenge and answers

Strongest challenge: moving the dry-run return before mutators can erase useful reporting, while moving graph discovery after either zero-change return can silently retain missing edges. The combined plans explicitly admit both caller integration and read-only planning, so this is an implementation obligation rather than an omitted scope.

1. Caller arrangement: compute the pending-work decision without mutation before the idle return, return a diagnostic Python result/CLI output for dry-run, and enter existing real-build lock/epoch execution for needed repair. Reuse one merge-state load for graph eligibility/execution. indexer.py:5101 currently reconciles drift before its idle return and :5176 opens an epoch before :5257's dry-run gate. The planned order directly addresses those observed seams. Verify graph recovery and each maintenance reason remain reportable, including combined graph+dirty state.
2. Durable obligations: per-doc unresolved/current intersection survives creation events and failed or skipped reads; only successful extraction replaces its unresolved set. Both persisted representations, session reopen, unchanged and unrelated retries, exact node/edge checks and the node-less target control are explicitly required. graph_indexer.py:13975 currently only enters impact discovery when symbols change; :13986 skips unreadable docs; :14000/14021 perform the reads. A global path delta cannot satisfy the admitted deferred-read recovery requirement.
3. Useful/selective reporting: branch-specific Python/CLI diagnostics are required by 1x81w Requirement 3. 1x8e1 AC-2 and Requirement 2 explicitly pin unaffected-text-read avoidance, no repeated resolved rescans, no row/write regression and one reused merge-state blob. An idle no-pending-work build remains a no-op; whole-blob decode cost is explicitly accepted and no latency claim is made.

## Assumptions and evidence

- Current dirty-epoch dry-run writes without lock: TESTED independently by rerunning shared idle_probe.py (exit 0). Expected known-bad failure observed: generation 1→2, building→complete, no lock acquired, result still up_to_date true without dry_run marker. Healthy control retained identical epoch state and zero graph calls. This independently confirms the motivating seam, not all repair cases.
- Current graph target-only creation misses edges: shared executed evidence reports 0 incremental versus 1 full edge for both noded and node-less targets, with oracle rejection and explicit-rescan recovery. Read validation independently confirms the symbol-only trigger and pre-merge-state zero-change return. Shared probe was not independently rerun here.
- Existing rescan machinery can implement this bounded repair: INFERRED from inspected code, not product-tested. Accepted for readiness because the plan expressly requires red-first retry, absolute and differential tests plus public build_index/CLI integration.
- All idle mutation reasons preserve bytes after repair: UNPROVEN future implementation claim. The five-branch matrix and true-no-op control are explicitly admitted; do not mark AC-1/2 done until they pass. Include the dirty epoch's missing-Lance hash-reset path (:5166) under the existing dirty-epoch branch to prove the new return precedes that write as well; this is implementation guidance, not new scope.
- No silent scope expansion identified. The outer zero-change dispatch gap, builder-version propagation and architecture surfaces are named in the frozen plan.

Actionability: no do_now readiness repair. Implementation guidance above is already admitted work. No backlog or hypothetical blocker. Review limits: bounded current seam inspection and one public build_index fixture replay; no full suite, no repaired implementation, no independent CLI replay in this readiness seat.

## Rotating alternative weighed

Read performance.md only after completing independent judgment. Raw-candidate assembly would eliminate retry-time source reads and could recover during temporary document unreadability. Its load-bearing assumption is that relocating resolution to assembly preserves deletion/outage semantics and provenance; this alternative has no executed performance or correctness proof and changes more edge ownership than the admitted fix. Durable per-doc unresolved retries accept deferred success until a readable extraction and already require unchanged recovery, which is the stated contract. A shared read-only preflight preserves dry-run reporting and real lock/epoch execution without requiring that semantic relocation. Therefore retain the admitted design; raw-candidate assembly is dont_do_later for this wave, with no backlog. Whole-blob decode remains an explicitly accepted cost, not a free operation. Verdict unchanged: APPROVE readiness, no mandatory plan gaps.


## performance source record

# Performance reviewer — best alternative readiness seat

Verdict: approve combined readiness for wave 1x5tq (1x81w + 1x8e1). No mandatory plan gap identified. This is a source/contract review, not implementation or runtime proof.

Strongest alternative: persist every normalized raw local-link candidate and resolve candidates against current paths during assembly. This would avoid reopening unchanged referring docs when a target appears and recover links despite temporary source-read failure. It is plausibly better for source I/O, especially high fan-in target additions. However it moves local-link edge ownership into assembly and must preserve candidate provenance, zero-edge documents, deletion/outage semantics and equivalence across all assembly paths. Reject for this bounded repair: the admitted retained per-doc unresolved obligation reuses extraction and rescan machinery with less semantic relocation. Existing extraction resolves against current paths (graph_indexer.py:13586–13593), while impacted-doc selection and reread live at 13973–14028; fragment summary persistence is centralized at 14048–14061. No measured speedup is claimed for the alternative.

Prefer the admitted read-only pending-work preflight with one reusable merge-state blob. It can report graph recovery together with drift/reap/heal/dirty-epoch/orphan work before the dry-run return, then dispatch real repair under the existing build lock/epoch. Current indexer.py:5099–5115 executes drift reconciliation before its idle return at 5116, making the shared ordering a concrete integration seam. Both admitted plans already cover this interaction, including Python/CLI reporting, unchanged build recovery and genuine idle no-op.

Reject unconditional/full document scans: cost follows all document text on every build, violating 1x8e1 AC-2. Reject a new sidecar solely for cheap pending-work lookup: it adds synchronization, migration and crash-consistency obligations without evidence that existing blob decode is unacceptable. Reject a global newly-added-path delta: it consumes the trigger before a temporarily unreadable referring doc succeeds; retained per-doc unresolved state is the required retry acknowledgment.

Cost caveat: one merge-state load still decodes the entire blob and consumes memory proportional to that blob. Set intersection bounds document rereads, not total preflight latency. One loaded blob, unaffected-doc read spies, never-appearing/resolved controls and preserved row/write assertions are explicit requirements, so this cost is reviewed rather than an invented readiness blocker. Existing impacted docs can be read twice (13999 and 14021); this is a concrete implementation cost to observe within the admitted verification, not a reason to expand scope into a rescan redesign.

Actionability: raw-candidate/sidecar/full-scan alternatives = dont_do_later for this wave (no backlog); missing-cost-control finding = not_issue because requirements and AC already cover it. Mandatory repairs: none. Residual limit: no benchmark or executed product probe performed by this seat; delivery must provide the admitted differential, state-persistence, no-write/reporting and selectivity evidence.

Evidence: both admitted change docs, shared primer and freeze; MCP code_outline on graph_indexer.py/indexer.py, code_keyword on mentioned_symbols/reconcile_non_git_drift, targeted code_read ranges above. Reviewed frozen files remained unchanged at completion.


## Final integrity declaration

All 11 frozen paths match at completion. Probes ran without unintended skips, reached the claimed public path or faithful graph-session boundary, used realistic persistent stores, asserted observable differences/state transitions, and detected the known-bad current behavior. The independent reference is the no-write contract plus full-build graph equivalence and positive/negative controls; common-extractor limitations and unrun delivery tests are stated above. Typed approval may honestly attest to this readiness review only. No source, plan, wave, or ledger mutation was performed by this council.

## Typed-authoring preflight

The coordinator previewed the exact approval through `wf_review_event(mode="dry_run")` after completion; no ledger entry was written. The server rejected the old single-change policy receipt as stale: current `review-policy-dc757cf812191880cf2d`, pending combined receipt `review-policy-9704b9e5a6a5c754b59d`; differing semantic fields were `policy_input_digest`, `requested_lanes`, and `required_lanes`. Its recovery is `wf_prepare_wave(wave_id="1x5tq", mode="ready")`, then resubmit the supplied approval against the current combined receipt and complete Prepare. This is lifecycle bookkeeping for the already-reviewed combined scope, not a new plan defect or approval withdrawal. Repository/source fingerprints remained unchanged.


# Specialist readiness publication follow-up

The original combined council review completed with unanimous readiness approval. After its typed council approval and successful Prepare, `wf_implement_wave(mode="create")` additionally required current typed readiness approvals from code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer and security-reviewer. This follow-up supplies those actual tool prerequisites without repeating the council or treating unimplemented delivery behavior as proven.

QA, architecture, security and performance use their completed independent readiness contexts. Where a seat had not personally run a behavioral baseline, it executes the existing finite public dirty-epoch/no-op fixture to honestly affirm all phase-specific integrity fields. A new independent code-reviewer checks the same frozen plan/tree and runs that baseline. The no-write normative contract is the independent reference for the observed forbidden generation change; all fixtures use disposable local roots, real SQLite/Lance persistence and mock embedders. No source or plan mutations occur. The coordinator supplies exact typed arguments; root owns publication.

QA payload: approval-qa-reviewer.json, actor/context /root/combined_readiness/qa, completed plan judgment and personally executed known-bad fixture; full frozen hash map reverified. Other seat reports and payloads are returned separately as they complete.

## Completed specialist evidence

### qa-reviewer

Context: `/root/combined_readiness/qa`. Independent completed QA readiness judgment approved with no mandatory plan gap. Personally executed python3 -B /tmp/1x5tq-combined-readiness/idle_probe.py: exit 0, both cases executed without skips; public build_index(dry_run=True) on a reachable dirty epoch advanced generation 1 to 2 and changed building to complete while lock spy remained uncalled. Healthy control retained identical epoch state and zero graph calls. Independently read both frozen plans and targeted test harness/cost assertions; weighed rotating raw-candidate alternative without changing verdict. All freeze hashes verified again before preparing this approval.

Limitations: Readiness approval only; unimplemented product behavior is not approved. Five-branch full storage identity, CLI and combined graph/idle behavior, failed individual read retry, and future mutation suites remain explicitly admitted delivery work. Shared graph recovery evidence models unreadable-directory skips, not individual-read failure. Mock embedders isolate embedding cost; public Python path uses real temporary index store and Lance state.
### architecture-reviewer

Context: `combined-1x5tq-architecture-independent-20260905`. Independent source/plan council review found no mandatory plan gap. Personally executed idle_probe.py once, exit 0: healthy complete epoch generation 1 unchanged with zero graph calls; dirty epoch changed building generation 1 to complete generation 2 through unlocked public dry_run=True, detecting admitted current-tree defect. Alternative raw-candidate assembly rejected for this bounded wave because it relocates extraction ownership.

Limitations: Readiness of specified repair, not proof of future implementation. Own execution covers dirty epoch and healthy idle only; other admitted branch, retry, mutation and performance assertions remain delivery evidence. Real SQLite/Lance; fixture mocks embedding backends.
### security-reviewer

Context: `1x5tq-combined-readiness-security-independent-20260905`. Completed independent combined-plan security judgment: approved-with-notes, no mandatory plan gap or credible less-trusted actor/authority delta. Personally ran idle_probe.py once, exit 0: healthy complete generation 1 remained exactly unchanged; dirty building generation 1 became complete generation 2 under public dry_run with lock tripwire unreached. Confirms admitted correctness defect and plan boundary relevance; no delivered implementation approval. Readiness review and rotating alternative assessment recorded in security.md.

Limitations: Readiness only. Real SQLite and Lance, mocked embedding services; bounded dirty-epoch and healthy controls only. Other idle branches and graph recovery remain implementation/delivery obligations.
### performance-reviewer

Context: `1x5tq-combined-readiness-performance-independent-20260905`. Completed independent combined plan and cost-bound judgment: approve readiness, no mandatory gap. Personally executed the finite baseline once, exit 0: healthy idle state unchanged at generation 1 with zero graph calls; dirty epoch dry run changed building/generation 1 to complete/generation 2 without entering the lock. This corroborates the admitted dry-run defect and idle caller boundary; no implementation or performance improvement is claimed. All 11 frozen files match.

Limitations: Readiness approval of plan and current-tree baseline only. Real SQLite/Lance fixture with mocked embeddings; no latency benchmark, no fixed-product proof, and no full maintenance branch matrix executed by this seat.
### code-reviewer

Context: `code-readiness-1x5tq-ac3abe4e534844f2982637ed070d48b7`. Exit 0: dirty epoch generation 1→2 and building→complete, no lock acquisition; healthy epoch identical with zero graph calls. All 11 SHA256 fingerprints matched. Independently read source and both plans; no mandatory gap.

Limitations: Readiness only. No repaired implementation exists; no delivery approval, full suite, independent graph probe, CLI execution or all-branch byte-identity proof claimed.

## New independent code-reviewer report

# Independent code-reviewer readiness — combined wave 1x5tq

Verdict: approve readiness for admitted 1x81w and 1x8e1. No mandatory plan gap identified. This approves the current plan and verification strategy, not unimplemented product behavior.

Read code-reviewer.md, both admitted change documents, packet/freeze and council report. Independently used MCP code_outline, code_keyword and targeted code_read to validate indexer.py:5096–5185 and graph_indexer.py:13970–14065. All 11 SHA256 fingerprints in freeze.json matched after the probe. No repository or ledger writes.

Current code grounds both repairs: drift reconciliation precedes the idle return at indexer.py:5101; missing-Lance dirty recovery resets hashes at :5166; the idle epoch opens at :5176. A plan-only decision must return before these mutators and preserve diagnostic output. Graph rescan currently gates on changed symbols at graph_indexer.py:13975, skips unreadable directories at :13986, and preserves artifacts on failed reads at :14000–14002. Summary propagation at :14048–14061 is the existing seam for durable unresolved obligations. The admitted per-doc persistence, unchanged retry, node-less target coverage and outer build_index/CLI integration directly cover those seams.

Personally executed `/Users/coryhacking/.wavefoundry/venv/bin/python -B /tmp/1x5tq-combined-readiness/idle_probe.py`, exit 0, both cases executed without skips. The healthy control retained identical epoch state at generation 1 and zero graph calls. The interrupted epoch was created through begin_build_epoch and public build_index(dry_run=True) changed generation 1 to 2 and status building to complete without taking the lock; the lock spy would raise on acquisition. Result omitted a dry_run marker. This is a detected known-bad contract violation on the current tree. Real temporary SQLite/Lance stores and suite mock embedders isolate cost without mocking the mutation boundary.

Independent reference: the independently read no-write requirement and public dry-run contract. Promised property is unchanged persistent state; the observed generation/status changes falsify it. The shared fixture does not independently prove every storage byte or every maintenance branch; those are explicit future AC obligations. Combined graph/maintenance reporting, read-only planning before real lock/epoch execution, per-doc retain-until-success retries, one merge-state load and no unaffected text rereads are all admitted. No requirement expansion needed.

| Mechanism | Known-bad detection | Outcome |
| --- | --- | --- |
| Public unlocked idle-maintenance writes | Personally rerun pre-fix reproduction against healthy and interrupted epochs | CAUGHT: generation 1→2, building→complete |
| Future dry-run guard removal | Required scratch mutation after implementation | Not run; guard does not exist yet |
| Future graph obligation loss / repeated rescans | Required differential, absolute, persistence and cost assertions after implementation | Not run; implementation does not exist yet |

Actionability: no do_now readiness blocker. Ensure implementation includes the missing-Lance hash-reset path within the already-required dirty-epoch no-write branch. Existing double-read rescan at graph_indexer.py:14000/:14021 is an implementation cost to observe, not a demand to expand scope. Limitations: finite readiness probe, no full suite, no independent graph probe or CLI execution, no future behavior approval.

All 11 original source/test/plan/doc/report fingerprints remain unchanged after the last specialist finishes. Each JSON was supplied by that acting reviewer context. No canonical ledger write was performed by these reviewers or this coordinator.
