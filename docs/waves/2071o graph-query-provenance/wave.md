# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2071o graph-query-provenance`
Title: Graph Query Provenance

## Objective

Make graph hierarchy locations reflect persisted call expressions and restore non-exact symbol lookup in Rust-containing graphs. Capture provenance across ordinary supported-language extraction, then implement and independently review under the operator’s 2026-10-10 instruction.

## Changes

Change ID: `2073s-bug hierarchy-call-site-provenance`
Change Status: `implemented`
Depends On: `2073t-bug rust-symbol-lookup-name-error`

Change ID: `2073t-bug rust-symbol-lookup-name-error`
Change Status: `implemented`

## Participants

- Coordinator: root
- Write-owning roles: implementer for code, wave-coordinator for lifecycle/docs integration
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer
- Council: isolated red-team primer; architecture, security, QA and reality fixed seats; performance rotating fifth; independent council-chair synthesis

Completed At: 2026-10-10

## Wave Summary

Wave `2071o` (Graph Query Provenance) delivered two changes: Use stored call sites in call hierarchy and Restore symbol lookup in Rust-containing graphs. Notable adjustments during implementation: Use stored call sites in call hierarchy: Optional Review plan resolves contract branches from source and accepted summary ADR: stored provenance, nullable unproven snippets, compatible singular fields; bounded scope/work and reporting state; preserve producer protocol. No unresolved operator choice or implementation authorization inferred.; Restore symbol lookup in Rust-containing graphs: Optional Review plan resolves contract branches from source and accepted summary ADR: stored provenance, nullable unproven snippets, compatible singular fields; bounded scope/work and reporting state; preserve producer protocol. No unresolved operator choice or implementation authorization inferred.

**Changes delivered:**

- **Use stored call sites in call hierarchy** (`2073s-bug hierarchy-call-site-provenance`) — 6 ACs completed. Key decisions: Original narrow pre-plan choice; Broaden ordinary producers under operator direction
- **Restore symbol lookup in Rust-containing graphs** (`2073t-bug rust-symbol-lookup-name-error`) — 3 ACs completed. Key decisions: Divergent pre-plan choice
## Watchpoints

- Watchpoint: implementation and scoped delivery review are complete; the wave is paused for operator closure. Fixture repairs2080c and20asl are also implemented/reviewed/paused. The local pack awaits final declared-profile qualification of their combined frozen framework source.
- Graph callgraph provenance was fixed earlier; hierarchy remains a distinct defective query path.
- Indexed coordinates are source-version provenance; snippets require proven freshness, otherwise null. Legacy missing sites never justify name-only guesses.
- Do not confuse caller edge counts with invocation occurrence counts.
- Source and baseline captures are under evidence/readiness; probe source is a non-executed archival text capture, not a shipped test.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 2071o-qa-qualification-drift | do_now | no | completed | qa-reviewer |
| DOCS-DEL-1 | do_now | no | completed | docs-contract-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Hierarchy repair follows the resolver repair so bare-symbol impact analysis can operate during implementation. Shared retrieval tests have one write owner.
- No external wave dependency; wave2071p can be readied independently. Only one wave is opened at implementation time.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 449 | 1,600,096 |
| implement | 64 | 1,615,325 |
| review | 445 | 2,931,577 |
| **Total** | **958** | **6,146,998** |

<!-- wave:context-efficiency-state {"generation":545,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":64,"content_source_credit":1811238,"derived_artifact_credit":0,"direct_net":1615325,"estimated_tokens_saved":1615325,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1928,"response_debit":195437,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1452},"plan":{"calls":449,"content_source_credit":3204907,"derived_artifact_credit":2942,"direct_net":1600096,"estimated_tokens_saved":1600096,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25073,"response_debit":1589183,"source_credit_count":98,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":445,"content_source_credit":4814011,"derived_artifact_credit":12880,"direct_net":2931577,"estimated_tokens_saved":2931577,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":30196,"response_debit":1867974,"source_credit_count":203,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":958,"content_source_credit":9830156,"derived_artifact_credit":15822,"direct_net":6146998,"estimated_tokens_saved":6146998,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":57197,"response_debit":3652594,"source_credit_count":338,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10811},"wave_id":"2071o graph-query-provenance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 37 | 0 | 26 | 19,404,178 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":26,"estimated_exploration_avoided":19404178,"surfaced_events":37} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

- Current source packet has14 content hashes; no source repair has been made. Exact node IDs work while the confirmed non-exact Rust scan fails.
- Corrected scope: only Rust extraction currently stores call_sites. Ordinary Python AST and shared tree-sitter producers are now admitted; schema remains unchanged and normal builder-version invalidation regenerates records.

## Outputs produced or expected

- Two wave-owned complete plans with required/justified ACs and unchanged unchecked delivery tasks.
- Typed current readiness approvals and successful Prepare-ready; implementation and delivery evidence come later.

## Review checkpoints

### Planning and review scope — 2026-10-09

Optional Review plan: self-answered location authority from current stored graph and served-handler probe; preserve outgoing definition fields from the MCP spec; use nullable snippets when source identity is unavailable; retain exact-ID/ambiguity semantics. Operator questions: none. Stop condition: all Requirements/Scope/AC decision branches resolved.

Chair declares FULL primer depth for public graph data-path/source-version boundary: five stances, three questions. First isolated primer precedes all fixed seats; rotating performance seat proposes the best alternative before final fixed-seat weighing and anonymized chair synthesis. All judgments are readiness-phase only.

Allocation: root drafts/admits docs; independent reviewers use focused fresh contexts with source fingerprints. Requested gpt-6.1-sol/high for bounded source-contract review; chair retains its separate inherited context for synthesis, selected for complex boundary judgment and continuity. Observed runtime model/effort unknown where not exposed. Readiness work budget15min per seat, selected finite controls only; no full suite or downstream scan. No separate artifact per seat. One bounded plan-repair pass and one focused verification round maximum before operator escalation.

## Completion criteria

- Implement both admitted repairs and prove all ACs with meaningful independent delivery evidence.
- Pass applicable framework/profile qualification, docs validation and close dry-run; operator controls closure.

## Handoff or next-wave notes

Re-Prepare the revised language scope, implement resolver first, then provenance producers and hierarchy consumption, then independently review and qualify. Do not close without operator instruction.

### Independent readiness reviews — 2026-10-09

FULL isolated primer applied adversarial, constructive, simplicity, first-principles and analogical stances, with three questions per wave. Graph challenge: relationship confidence cannot authenticate guessed name-only locations; indexed coordinates do not prove current snippets. Scanner challenge: cooperative checks cannot enforce blocked I/O timeouts, and empty error channels cannot establish clean scans. Every fixed seat answered the primer questions independently before the performance rotating seat ran.

Architecture, security, QA and reality fixed seats approved with notes; required code and docs-contract reviews also approved with notes. Performance proposed shared callgraph/hierarchy projection and staged anchor mitigation before broader scanner work. All four fixed seats explicitly weighed those alternatives and retained the narrow graph repair and coherent scanner/reporting wave. Shared projection expands qualification; partial staging leaves candidate/other-pattern/corpus exposure and transitional contracts. Urgent partial release needs separate scope. No typed plan-blocking finding was demonstrated; current product defects remain the admitted repair rationale.

Finite evidence is current-tree/readiness-only: canonical served handler negatives and exact-ID controls, actual scanner/emitter boundaries, compatible/malformed summary controls and owned-child timeout controls. No implementation, full suite, downstream scan or whole-upgrade deadline is proved. Independent raw results and non-executed probe captures are retained under evidence/readiness, indexed by review-artifact-manifest.json; exact approval inputs are lane-approval-inputs.json. Source packet14 paths remained unchanged.

Implementation notes: bind any source freshness proof to the indexed graph generation; preserve null snippets when unavailable. Explicitly screen lexical symlinks before contained reads. Test candidate-dense and cumulative workloads, every work/retention cap, and positive/negative old/current summary compatibility. Compact summary status must survive old collection bounds. Reporting work and owned cleanup must respect remaining budget; unchanged old-parent fallback remains disclosed.

### Prepare council — final independent synthesis

Phase: readiness. Verdict: approved with notes. Primer depth: full; all five stances and three questions addressed. Architecture, security, QA and reality fixed seats; performance rotating fifth; code/docs-contract additional independent specialist inputs. Chair first weighed randomized anonymized outputs, then reattached identities while preserving required-lane authority. All four fixed seats explicitly weighed the rotating alternatives. Seat agreement: unanimous; max severity: none. No material disagreement or challenge round. Detailed synthesis and honest readiness-only execution limits: evidence/readiness/chair-synthesis.json.

| Recommendation | Reason |
| --- | --- |
| G-N1 | Normalize/deduplicate edge-site copies rather than mutating shared query snapshots; assert relationship counts separately from occurrence counts. |
| G-N2 | Treat any optional session-hash freshness mechanism as graph-generation bound. If existing artifacts cannot establish that binding, retain null snippets. |
| G-N3 | Pin outgoing definition fields and legacy Java filter-only authority beside collision, macro, adjacent function and same-line provenance controls. |

Recommendations are implementation notes, not additional scope or delivered proof. Keep current receipt and planned status; activate only under a later instruction.

### Prepare-ready succeeded — 2026-10-09

Canonical wf_prepare_wave(mode=ready) returned status ok, readied true, no activation, clean garden/full lint and no pending readiness lanes. All required lane approvals and council-readiness are current on the unchanged receipt. Durable result: evidence/readiness/prepare-ready-result.json. Status remains planned; delivery ACs/tasks remain unchecked.

### Supported-language scope correction — 2026-10-10

A fresh read-only Guru/architecture adviser exercised actual extraction → canonical SQLite publication → public incoming/outgoing hierarchy: wrong same-name locations reproduce in Python, JavaScript, C++, Go, Java and Rust; C loses distinct invocation locations. A non-Rust bare code_impact query succeeds alone and raises NameError after adding an ordinary Rust symbol; exact-ID control succeeds. Sources remained unchanged. Temporary diagnostic: `/private/tmp/wf-2071o-language-scope.json`; durable conclusions are recorded here, not a new evidence folder.

Optional Review plan resolved the broader requirement by admitting ordinary Python AST/shared tree-sitter coordinate capture, unchanged schema and normal builder-version invalidation. No eager index rebuild or new upgrade scan. Regex fallback caller ownership is unproven, so its locations remain unknown. Coverage must distinguish the supported registry from exercised call syntax and config/markup no-call cases. AC-5/AC-6 own the added verification requirements. This is a material source-boundary change, so prior readiness is historical and a fresh full readiness council is required.

Chair declares FULL primer depth: provenance crosses extraction, resolution, publication and public presentation boundaries. Independent red-team primer precedes fixed architecture, security, QA and reality seats; performance is rotating fifth. One generic implementer is the single source writer; root integrates lifecycle state; independent reviewers supply judgments without mutating lifecycle state. Requested inherited available model with high-effort task focus for boundary and adversarial reasoning; runtime settings are not independently observable. Finite budget: 15 minutes per readiness seat, bounded scratch probes only; no full suite per seat. Serialize graph handlers/shared retrieval tests and record summaries in this wave record.

### Fresh broader readiness succeeded — 2026-10-10

Current receipt `review-policy-1ce56bf4fae9992198dd`: all five readiness lanes and council approve in fresh independent contexts; Prepare-ready passes garden/full lint, then Implement activates. FULL isolated red-team primer preceded fixed architecture/security/QA/reality; rotating performance proposed consumer-only repair. Every fixed seat rejected it for broader accurate navigation because real non-Rust producers lack sites. Architecture+code and performance+docs judgments share disclosed contexts; QA and council contexts are separate. Unanimous, severity none, no findings. Actual known-bad parser/resolver/SQLite/handler controls and three transactional invalidation tests support feasibility only; no future repaired behavior claimed. Eight source/test/contract Git objects remained frozen: graph_query592687dd; graph_indexer a44f485d; graph_handlers540ed2d3; test_graph_query0181ed20; test_graph_indexer8e9c1ac8; test_server_tools_retrieval606f109a; mcp-tool-surface772ce02b; graph-index-system975a3abf. Temporary probes are not retained as a new evidence folder; load-bearing conclusions are here and in the typed ledger.

Allocation: one generic implementer owns resolver, producers, hierarchy, focused tests and the two admitted contract docs; root owns lifecycle integration and package qualification. Requested gpt-6.1-sol/high for coupled cross-language implementation, selected for coding capability and bounded context; observed runtime unknown. Serialize2073t before2073s and all shared paths. Initial useful checkpoint within3minutes; finite15-minute implementation checkpoint with actual progress/limits, no redundant full suites. Reviewers use fresh independent contexts after source freeze.

### Frozen implementation and delivery allocation — 2026-10-10

Final focused run58tests/0skips8.581s; earlier expanded713run had one obsolete builder54 pin, repaired and included in the final green selection. Ordinary repeated invocations retain coordinates through extraction/finalization/canonical publication/both hierarchy directions for Python and all15tree-sitter code modes. Extended syntax exercises constructors, PHP member/scoped calls, Objective-C messages, Bash commands, Rust macros, Unicode and multiline/physical CR-LF boundaries;11non-code profiles have no-call controls. Regex fallback exposes actual emitted edges with unknown sites. This does not qualify every grammar construct. Existing cross-confidence traversal coalescing selects one edge; do not union its sites with differently trusted witnesses. External IDs absent from graph nodes retain the existing incoming-resolution limit.

All13mutants killed in disposable copies; targeted tests per mutant, no whole-file survivor sweep needed:

| Mutation | Failing canonical oracle |
| --- | --- |
| Undefined regex binding | RustContainingSymbolLookupTests; TestRustContainingImpact.test_published_rust_and_mixed_non_exact_impact |
| Accept ambiguous trait alias | test_trait_alias_unique_and_ambiguous |
| Remove Python / tree-sitter capture (2) | CallProvenanceExtractionTests.test_every_code_mode_preserves_repeated_exact_invocations |
| Remove edge-specific selection | TestPersistedCallProvenance.test_stored_sites_ignore_other_receivers_macros_and_adjacent_callers |
| Remove wrong-file / boolean / span-coherence guards (3) | test_missing_malformed_and_wrong_file_provenance_is_unknown |
| Remove byte priority | test_byte_order_precedes_legacy_line_order_and_does_not_mutate |
| Restore Unicode string splitlines | PythonPhysicalLineProvenanceTests.test_unicode_string_separators_and_crlf_are_not_ast_line_boundaries |
| Remove builder bump | test_builder_bump_invalidates_unchanged_old_records |
| Remove unsafe path guard | test_unsafe_caller_paths_and_non_list_sites_stay_unknown |
| Accept unproven snippet | test_absent_changed_and_unreadable_source_never_supplies_snippets |

Eight owned paths fingerprint `7fd6c7884487a0fdbc4ae763f7bbc5f73c7635edc560119e058e466b8dd6fab5` (SHA256 of sorted path + NUL + bytes + NUL). Root added CHANGELOG Git blob `26ec170985ca326434ee7f432de19020f9a3c66f` and repaired the mandatory current builder claim in docs/RELIABILITY.md, blob `e9106046bc6b1c02072411d3d6104ddee9f69533`. The first full run started before that claim correction and may report its stale-doc failure; it cannot establish qualification of the corrected boundary. Fresh full qualification remains required.

Delivery uses a full isolated red-team primer before independent fixed seats, performance rotating fifth, required code/QA/architecture/docs-contract/performance lanes and anonymized chair synthesis. Reviewer budgets are finite, source paths frozen, actual public producers/handlers and independent references required; targeted tests per mutant, whole-file only for survivors. No review transcripts or new evidence folders retained. Final approvals wait for the fresh canonical green receipt.

### First delivery synthesis and bounded repair — 2026-10-10

FULL isolated primer preceded fixed architecture, security, QA and reality seats; performance was rotating fifth. Architecture/code and performance/docs shared disclosed contexts; other seats were separate. All fixed seats weighed append-then-final-normalize against per-insert maintenance or occurrence caps: caps lose required invocation evidence, and per-insert sorting adds repeated work. Anonymized chair synthesis was unanimous on withholding overall delivery, maximum severity high from qualification drift; no blocking disagreement or challenge round. Scoped architecture/security/performance/runtime findings were positive, not full qualification approvals. All reviewed source fingerprints remained unchanged.

Two typed delivery findings: `2071o-qa-qualification-drift` blocks QA because current fixtures/report retain builder54, Python-empty-site and Kotlin guessed-location expectations; `DOCS-DEL-1` blocks docs-contract because one architecture paragraph falsely describes callgraph rescanning. Cycle1 repair_start is recorded for both. The sole implementer owns five affected verification/report/architecture paths; runtime and admitted requirements remain frozen. Historical51 golden corpus and baseline report stay byte-identical. The pre-edit reproduction executes20tests,11failures,0skips; after narrow metadata adaptation, real55 extraction has unchanged targets, confidence, topology, counts and communities plus8 independently checked Python site-bearing edges.

The first full default run executed12,131tests/181files/13reported skips in741.749s; four files failed stale expectations, and concurrent bookkeeping invalidated its quiet-tree check. It is red and supplies no current receipt. Fresh full qualification must follow repair, focused independent QA/docs/code reverification, council reassessment and final bookkeeping; no MCP retrieval or repository edit during that run. Performance evidence covers real Python and JavaScript repeated/distinct128/512/1024-call workloads, not whole-corpus latency, p95 or memory guarantees. Permanent evidence stays in this wave record and the typed ledger.

### Repair1 frozen verification boundary — 2026-10-10

Exactly five repair paths changed: test_graph_quality_eval.py, test_graph_rust_provenance.py, test_server_tools_retrieval.py, docs/reports/graph-quality-post.json and docs/architecture/graph-index-system.md. Runtime and admitted requirements remain unchanged. Complete affected modules pass1,175tests/0skips167.113s; final expanded quality controls pass105tests/0skips7.322s. Current report regenerated through existing producer: builder55,10TP/0FP/2FN, report digest `ed4327421766e7b6f104cf93524f2020c4aaf9f4a1e7500ecb7680645dd00321`. Golden corpus and historical baseline report remain byte-identical.

Parity first pins55 and graph/community fingerprint `cd4bdc8e72e04ffcbad06f479e29fbaf387d62ac983d3cb8d07daa84b4a5b022`, independently checks exactly8Python occurrences from literal source bytes, then projects only that verified additive metadata back to historical comparison. Exact target/confidence/inventory/multiplicity/coverage/community assertions remain. Python publication expects helper() bytes30–38/line2/columns12–20 with unchanged RECEIVER_RESOLVED confidence. Kotlin existing callable-reference scanner retains its direct coverage; missing graph sites stay unknown, while traditional stored bytes81–92/line4/columns16–27 survive both hierarchy directions with null snippets.

Ten qualified mutations are killed: site precision, fingerprint, call multiplicity/inventory, non-call metadata, graph/community version guards (seven) fail the metadata-adaptation negative control; removed Python capture fails the exact persisted-location publication test; guessed missing Kotlin sites and unproven Kotlin snippets fail their respective public hierarchy tests. A deleted entire site oracle produced incidental KeyError and was excluded; its precision-loosening replacement is killed through named coordinate/byte/attribute assertions. No survivor remains.

Frozen11path fingerprint `9fdd7eac6b68727a004e231e839c87a032760810be5091a6d16b5e80c982e833`; runtime Git blobs unchanged. New fresh independent QA and combined code/docs-contract contexts reverify only affected boundaries; prior full council is reassessed by its independent chair. Combined lanes disclose shared context. Budgets8minutes each, targeted tests per mutant and whole-file only survivors; no repeated full suites or retained per-seat artifacts. Full garden/lint passes with no update, warning or error. Final canonical full qualification follows all reviewer/MCP and bookkeeping activity.

### Focused independent repair verification — 2026-10-10

Fresh independent QA passes78targeted tests/0skips and detects11own negative controls; all9required behavioral ACs verified. New combined code/docs context passes30tests/0skips1.927s and detects4own controls. Real callgraph returns storedline7 with source absent and zero scanner calls, preserves copy isolation, and removes legacyline999 without sites. Existing evaluator CLI reproduces current report substantive fields. Entry/exit11path fingerprint and both historical originals match. QA and docs typed reverification cycle1 marks each repair verified and clears its own required lane; no runtime/contract/scope change. Full canonical/profile qualification is still pending, not inferred from focused green runs.

Independent contexts: QA `2071o-repair-qa-fresh-20261010-independent-1`; code `2071o-cycle1-repair-code-20261010-fresh-combined`; docs `2071o-cycle1-repair-docs-20261010-fresh-combined`. Code/docs share the disclosed context and are independent of the implementer, not of one another. Chair independently passes7focused tests/0skips1.248s and isolates a column12→13 precision-guard mutation with a named assertion failure; previous unchanged full council evidence remains scoped to its frozen runtime. Final chair synthesis and full receipt still required before final approvals.

### Council repair reassessment and quiet qualification boundary — 2026-10-10

Independent chair approves the bounded repair with no new findings after fresh QA/code/docs agreement and its own7tests/0skips plus clean precision-guard negative control (1assertion/0errors). All11entry/exit identities and historical hashes match. Unchanged full-panel runtime facts remain limited to the original frozen scope; no panel rerun or broadened contract. One code/docs span-deletion probe also emitted an incidental error, excluded as proof; actual assertion controls and the chair's isolated clean control support precision. All independent agents stopped source/MCP investigation. Final delivery approvals await a quiet complete canonical run, then current profile/package qualification; no closure or commit authority inferred.

### Isolated qualification coordination — 2026-10-10

The host-access working-tree run passed all12,134tests/181files/13skips, but other-session edits to newly planned waves prevented its unchanged-tree receipt. The operator authorized an isolated checkout for qualification and the local pack. Reachable public history plus intended working changes are copied into an owned temporary parent; unrelated new waves and private ignored records are excluded. Framework hash matches both trees: `18b0ce1a6f18c334f04ee059d8a587ce7a30ab39d158da9178d4124b9dc763ea`. All11reviewed files and the qualification fixture remain byte-identical. The owned parent avoids an unrelated shared-temporary re.py shadowing the standard library; no source or unrelated file changed.

The nested isolated full run failed one timing budget and one TechDocs report-field assertion in a test with a two-second child deadline; both unchanged workers independently rerun together pass192tests/0skips18.941s. Contention is plausible, not proven as the TechDocs cause. No current receipt is claimed from either red run. A fresh full unchanged run is required; tests, deadlines and profile comparison rules remain intact. Temporary logs stay outside the repository; only exact replaceable qualification reports are retained in ignored cache.

### Green isolated default qualification — 2026-10-10

The fresh unchanged run passes all12,134tests/181files/13skips in783.834s and writes its genuine green receipt at2026-10-10T18:10:09.848793+00:00. Inputs hash remains `18b0ce1a6f18c334f04ee059d8a587ce7a30ab39d158da9178d4124b9dc763ea`, identical to the current working framework. The original runner-written receipt is copied byte-for-byte only after verifying that identity. It attests matching framework inputs and the isolated run, not current unrelated project-doc changes or native Windows. Command: `python3 -B .wavefoundry/framework/scripts/run_tests.py --no-cache --qualification-report .wavefoundry/cache/qualification/default.json`, with bytecode disabled and an owned temporary directory. All prior red runs remain excluded. Fresh required lane and council approvals may now be recorded; second/declared profile checks and the local pack remain packaging work.

All five required specialist approvals and council-delivery are now recorded from the actual independent review facts above. Typed continuation requires only operator-signoff; all9ACs and8tasks are met, changes implemented. No new memory candidate: existing canonical instructions already cover source identity, bounded unknown locations and honest qualification. Hold the OPEN slot until local packaging completes, then pause for operator closure before opening the next planned wave. No new closure, commit or push is authorized here.

### Qualification fixture repair and paused state — 2026-10-10

The wave was paused to admit20asl's one-line historical-fixture root repair, now independently approved and paused with all ACs/tasks met. Graph runtime, the11 reviewed graph paths and2080c fixture remain unchanged. The new combined framework hash is `c8d6a4134e202a505142cdd7ac3958048682eec85fad6207da27ac3671ffc88e`; the prior18b receipt and profile runs are historical, not current qualification. Fresh isolated default passes12,134tests/181files/12skips1244.080s; second passes12,126/181/28skips1253.143s and exact comparison passes (16 explicitly default-only extras). Declared-profile qualification and the pack are still pending. Only genuine current receipts/stamps will transfer after identity verification; no closure, commit, push or private-material publication is authorized.

### Local pack qualification complete — 2026-10-10

Fresh isolated default passes 12,134 tests/181 files/12 skips (1244.080s); second 12,126/181/28 (1253.143s); declared 12,134/181/12 (1254.164s). Both exact comparators pass: second adds 16 explicitly marked default-only skips, declared matches baseline IDs/reasons. Framework hash `c8d6a4134e202a505142cdd7ac3958048682eec85fad6207da27ac3671ffc88e` stayed unchanged through the build and genuine receipt/stamp copyback. Local `1.29.0+pvqp` pack, SHA-256 `775f1f1536040424b8f413af6ca476043d876a2bcb702cf9258b00febeed14f4`, has verified source/changelog bytes, generated protocol/inventory and outer/inner CRC. Current details are in [local pack report](../../reports/local-pack-1.29.0-test-build.md); raw reports remain ignored and logs temporary. Earlier qualification identities remain historical rather than current proof. All admitted work and independent delivery reviews remain complete; wave paused for operator closure. Native Windows is unqualified; no close, commit, push or publication.
