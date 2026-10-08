# Preserve Unresolved Receiver Calls and Expose Graph Attribution Counts

Change ID: `201wg-bug graph-receiver-call-target-integrity`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-07
Wave: 203pu graph-call-attribution-integrity

## Rationale

Fix incorrect graph call targets exposed by Rust iterator calls in Tensorwell, and add attribution counts so agents and operators can distinguish resolved call edges from extracted candidates in structural reports. Success means an unknown receiver cannot acquire an unrelated project target solely through a name collision, while legitimate calls remain available and report uncertainty is explicit.

The read-only investigation found complete project source coverage but inaccurate topology. A consistent SQLite snapshot at generation 262 represented all 46 source files: 36 Rust, 3 Swift, 4 shell, 2 Python and 1 C. The graph contained 5,064 nodes and 18,523 edges. Database integrity and chunk/vector correspondence passed. Lexical postings covered token-bearing chunks; one punctuation-only code chunk legitimately had no postings. Coverage and storage consistency do not establish call-target correctness. The operator's earlier report recorded 18,454 edges and 45 incoming edges; these are historical measurements, not fixed test expectations. Its concurrent-refresh observation was not independently replayed.

Confirmed example: `encoding.get_ids().iter().map(|&x| i64::from(x)).collect()` inside `crates/tensorwell-inference/src/preprocess.rs::capture` targets `crates/tensorwell-inference/src/qualification.rs::collect`. The latter is a free function taking `Vec<Running>` and `Instant`, not the iterator method. The stored edge is `EXTRACTED` with `receiver_unknown: true`. The same incorrect target was verified for `cls_normalize`, `embedding_batches`, `reranking_batches` and `service/state.rs::random_hex`. Examined source hashes matched the indexed hashes. The project-only fan-in ranking put this target first with 46 incoming edges from 44 distinct source nodes, including 40 `EXTRACTED` and 6 `RECEIVER_RESOLVED` edges. Only the named examples were classified; this does not assert that all 40 extracted edges are false.

Wavefoundry's and Tensorwell's `graph_indexer.py` and `graph_query.py` were byte-identical. Scratch builds using builder 52 on Python 3.14.8 reproduced same-file and cross-file collisions. A genuine bare `collect(...)` control remained `RECEIVER_RESOLVED`. Editing the target without editing the caller preserved the wrong cross-file edge; renaming the unrelated function made the unchanged iterator caller revert to `external::collect`. A fixture report counted the genuine call and wrong edge together.

Mechanism verified against current source:

- `graph_indexer._resolve_rust_receiver_type` cannot establish the type of a chained call-expression receiver; `_resolve_rust_call_target` then returns `None`.
- `GraphIndexSession._extract_tree_sitter_artifact` records `_ts_call_has_receiver` as `receiver_unknown`, but still runs `_ts_resolve_target`, whose simple-name lookup can bind a same-file free function.
- `_resolve_fragment_edge` passes the external candidate to `_resolve_external_call_target`, whose unique simple-name branch can bind a cross-file free function. The unknown-receiver check prevents confidence promotion, not target assignment.
- `GraphQueryIndex.report` aggregates call edges without an attribution-confidence partition.
- `test_all_member_profiles_keep_unknown_receiver_confidence` and `test_unknown_import_target_stays_extracted` pass on the defective tree: their uncertainty checks do not reject the unrelated callable target.

Source anchors: `.wavefoundry/framework/scripts/graph_indexer.py` (symbols above), `.wavefoundry/framework/scripts/graph_query.py` (`GraphQueryIndex.report`) and `.wavefoundry/framework/scripts/tests/test_graph_call_integrity.py` (the named tests). Tensorwell is field evidence; acceptance fixtures must be generic and self-contained.

## Requirements

1. Derive the affected set from syntax and binding evidence: receiver-method calls reaching the shared tree-sitter fallback without an established receiver/type or authoritative callee owner. Do not use a method-name denylist, Rust-only filename filter, or `receiver_unknown` alone. `_ts_call_has_receiver` also marks qualified paths such as Rust `a::b::c()`, which are not equivalent to an unknown instance-method receiver.
2. Preserve an unresolved external member target at `EXTRACTED` confidence with unknown-receiver provenance for that set. Neither same-file lookup nor cross-file resolution may bind an unrelated project callable merely because its simple name is unique. Retain the unresolved call as evidence rather than dropping it.
3. Preserve established binding paths: genuine bare free-function calls, receiver/type-resolved methods, constructor calls, and qualified module/associated-function calls supported by authoritative ownership evidence. Ambiguous or unsupported dispatch remains unresolved; add no Rust type checker or arbitrary return-type inference.
4. Enforce the rule through extraction, stored fragments, deduplication, publication and incremental re-resolution. A symbol addition, edit, removal or rename cannot turn an unchanged unknown receiver into a name-only project bind. Genuine established evidence must not be downgraded or erased when it coexists with unresolved evidence.
5. Add `call_edge_counts` to rows in `fan_in`, `fan_out`, `chokepoints` and `file_hubs`, including their Evidence/Data counterparts. Each object has nonnegative integer `total`, `resolved`, `extracted`, `unclassified` and `receiver_unknown` fields. In the row's direction and effective graph view, `total` counts only `calls` edges; `resolved` counts `RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED` edges without unknown-receiver provenance; `extracted` counts `EXTRACTED` edges; `unclassified` counts remaining call edges, including absent/unrecognized confidence or contradictory resolved-plus-unknown metadata. `total = resolved + extracted + unclassified`; `receiver_unknown` is an overlapping subset of `total`, not another summand. These are edge counts, not distinct caller/callee counts or proof of runtime dispatch.
6. Preserve existing row fields, `count`, sorting, limits, thresholds, production/Evidence partitions, external/generated filters and collapse behavior. Existing `count` may include SQL data-layer relations under the standing contract; the new object counts calls only. Confidence separation is additive, not a silent switch to resolved-only ranking. Corrected edges will legitimately change topology and rankings after rebuild.
7. Update graph architecture and public tool documentation to explain unresolved-target ownership and count semantics. Bump the graph builder version through the existing invalidation mechanism so old extraction artifacts cannot retain defective bindings. Verify replacement through canonical rebuild/publication without consumer-source edits or a second migration mechanism.

## Scope

**Problem statement:** unknown receiver-method calls can acquire unrelated project targets through name matching, and reports aggregate their uncertain edges with resolved calls.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py`: Rust/shared fallback classification, binding safeguards, provenance/incremental handling and builder version.
- `.wavefoundry/framework/scripts/graph_query.py`: attribution counts for degree-based report rows.
- `.wavefoundry/framework/scripts/wf_server/graph_handlers.py`: response plumbing if needed; `wf_server/server_impl.py`: registered `wf_graph_report` description.
- `.wavefoundry/framework/scripts/tests/test_graph_call_integrity.py`, `test_graph_indexer.py`, `test_graph_incremental_merge.py`, `test_graph_query.py` and relevant registered-tool tests: generic regression and contract fixtures.
- `docs/architecture/graph-index-system.md`, `docs/specs/mcp-tool-surface.md` and `CHANGELOG.md`: behavior, compatibility and count semantics.

**Out of scope:**

- Rust trait/`dyn` dispatch, arbitrary return-type inference, compiler/LSP integration or a complete Rust type system.
- A blanket rewrite of all heuristic call resolution, method-name blacklists or suppression of unresolved calls.
- Default ranking changes, risk-score weights, centrality/community redesign or a new report filtering API.
- Dashboard styling/confidence badges, owned by planned change `1p30y-enh dashboard-rendering-fidelity-phase-2`.
- Semantic retrieval ranking, file discovery, refresh scheduling, Tensorwell product edits or automatic consumer upgrades/rebuilds.

## Acceptance Criteria

- [x] AC-1: Generic Rust same-file and cross-file fixtures with iterator `.collect()` and an unrelated free function `collect` produce no iterator-call edge to that function. The unresolved call survives with `EXTRACTED` confidence and unknown-receiver provenance; a genuine bare call binds to the free function. Verify extracted artifacts and merged/published edges.
- [x] AC-2: A second iterator/member name collision verifies structural behavior rather than a `collect` exception. Representative affected shared-fallback language fixtures preserve unresolved identity; supported bare, qualified, receiver-resolved and construction controls retain their established targets and confidence.
- [x] AC-3: Incremental target addition, unrelated target edit, rename/removal and restoration leave an unchanged unknown-receiver caller unresolved. Fresh and incremental builds agree on affected edges; publication and deduplication retain provenance and genuine-call controls.
- [x] AC-4: Known-count report fixtures expose `call_edge_counts` on every degree-based production and Evidence/Data row, with correct direction, arithmetic, unknown-receiver subset and unclassified handling. Mixed SQL/call fixtures preserve existing `count` while separating calls only.
- [x] AC-5: Public `wf_graph_report` fixtures preserve existing fields, sorting, limits, filters, partitions, thresholds and supported collapsed views while returning the new counts. Documentation labels edge counts accurately and does not describe extracted evidence as resolved callers.
- [x] AC-6: A version-transition fixture demonstrates that the existing builder invalidation/rebuild path replaces a stored pre-fix collision with the corrected unresolved target, without consumer-source edits or bespoke migration.
- [x] AC-7: Independent reference evidence verifies target ownership against generic Rust source semantics and separately specified report arithmetic; restoring name-only binding or removing attribution separation causes the corresponding regression evidence to fail.
- [x] AC-8: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] At admission/readiness, confirm current symbols, files, reviewer lanes and graph version; obtain current readiness before code edits.
- [x] Add failing-first generic Rust same-file/cross-file iterator collision fixtures and genuine bare/qualified/typed controls.
- [x] Implement structural fallback safeguards at local binding and cross-file re-resolution, preserving unresolved call evidence.
- [x] Exercise shared-fallback language controls and record supported paths and unsupported dispatch limitations.
- [x] Add incremental symbol-transition, fragment/publication and deduplication coverage; compare affected output with fresh builds.
- [x] Implement report attribution counts and test arithmetic, SQL compatibility, partitions, filters, thresholds and collapse views through the registered surface.
- [x] Bump the builder version once and verify old-artifact replacement through canonical rebuild/publication.
- [x] Update architecture, MCP spec/tool description and CHANGELOG Unreleased entry.
- [x] Run change-scoped graph, server-package and registered-tool checks using isolated fixtures.
- [x] Obtain independent code/QA/architecture/docs-contract review evidence; reconcile AC/task checkboxes as evidence completes.
- [x] Validate docs at handoff and run the canonical framework suite for a current close-time receipt when closure is requested.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Binding correction and transition fixtures | implementer | readiness | graph_indexer and extraction/incremental tests. |
| Attribution report contract | implementer | readiness | graph_query, report plumbing and tests; integrate before review. |
| Docs and tool contract | implementer | integrated implementation | Named architecture/spec/tool-description updates and CHANGELOG. |
| Independent delivery review | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer | frozen integrated tree | Ownership, compatibility, rebuild and arithmetic checks; Council policy determined at Prepare. |

## Serialization Points

Freeze the integrated tree before delivery review. Serialize shared graph-indexer/server edits with other admitted work. Stored production graphs change only through canonical rebuild/publication under implementation authorization.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/graph_query.py`
- `.wavefoundry/framework/scripts/wf_server/graph_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_graph_call_integrity.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py`
- `docs/architecture/graph-index-system.md`
- `docs/specs/mcp-tool-surface.md`

CHANGELOG.md is also in scope; it is a root-level file and is named as prose rather than a review path token.

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md`: fallback ownership, unresolved targets, stored provenance, invalidation and report attribution.
- `docs/specs/mcp-tool-surface.md`: public fields and edge-count semantics.
- No new architecture hub page or ADR: this corrects existing resolution ownership and extends an existing report contract.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reproduces and closes the observed wrong target. |
| AC-2 | required | Avoids name-specific patches and protects supported calls. |
| AC-3 | required | Incremental refresh must not restore the defect. |
| AC-4 | required | Explicit, correct attribution arithmetic. |
| AC-5 | required | Public compatibility and graph-view transformations. |
| AC-6 | required | Correct existing indexes as well as fresh fixtures. |
| AC-7 | required | Detect wrong targets and vacuous count separation. |
| AC-8 | required | Change-local verification and documentation quality. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Final takeover verification and handoff complete; this wave remains paused awaiting operator close, commit and push. | Shared canonical repository suite: 11,885 tests across 173 files, OK with 20 intentional skips; current matching framework receipt proven. DEL2 independently reverified and terminal; all tasks and ACs complete. Delivery-memory candidate rejected as nonactionable bookkeeping. No wave closure, commit or push performed. |
| 2026-10-07 | Read-only verification confirmed the target defect and complete source coverage. | Tensorwell SQLite snapshot generation 262; named source hashes matched graph_file_state; 46 sources, 5,064 nodes, 18,523 edges; collect target: 46 edges/44 sources, 40 extracted and 6 receiver-resolved. |
| 2026-10-07 | Executed generic scratch reproductions on builder 52/Python 3.14.8; current uncertainty tests pass despite wrong identity. | Same-file/cross-file collision, bare-call control, unchanged-caller target edit and rename; two named CallIntegrityTests passed. Temporary probes are exploratory, not durable acceptance evidence; implementation must add repository fixtures. |
| 2026-10-07 | Authored staged bug plan with additive report enhancement. | MCP pending-plan inventory found no duplicate binding correction; wf_new_bug created this plan. Related dashboard work stays separate. No admission/readiness or implementation performed. |
| 2026-10-07 | Admitted into wave 203pu and completed Prepare wave and optional Review plan; no readiness blocker or unresolved operator decision. | Five required independent readiness lane approvals plus Council synthesis; canonical Prepare returned readied=true, transitioned_to_active=false, lint/garden passed. Ownership, positive controls, effective-view arithmetic, canonical version transition and test feasibility validated; implementation remains deferred. |
| 2026-10-07 | Operator authorized implementation ("prepare, review, and implement"); close, commit and push stay operator-owned. | Operator instruction in the coordinating session. |
| 2026-10-07 | Implemented the binding safeguard: `_ts_call_receiver_unowned` classifies, from syntax, a member call whose receiver cannot own a name-only binding (a computed receiver in every tree-sitter grammar, plus non-self receivers of Rust `.` and C/C++ `->`). Such a call emits `external::<candidate>` at EXTRACTED with `receiver_unknown` and new `unowned_member_call` provenance; same-file and import-alias lookups, `_resolve_fragment_edge`, `_edge_lookup_keys` and the inheritance output pass all skip it; `_merge_call_evidence` keeps the flag only when every witness carries it (order-independent). Bare, this/self (incl. Kotlin/Swift self expressions), typed, construction, qualified/associated and bare-identifier dot receivers are unchanged. GRAPH_BUILDER_VERSION 52 -> 53. | graph_indexer.py; UnownedMemberCallTests (10 tests) in test_graph_call_integrity.py: Rust same-file/cross-file collect with artifact, payload and published-row checks; 14-grammar `render` collision matrix; prior/fixed equality for Rust/TS controls; six-step incremental add/edit/rename/restore/remove/readd vs oracle; fragment/lookup-key, dedup, inheritance-pass and builder 52 -> 53 transition tests. |
| 2026-10-07 | Implemented `call_edge_counts` on fan_in, fan_out, chokepoints, file_hubs and their evidence rows: one classification per effective calls edge, tallied for both endpoints; legacy SQL-inclusive count, ranking, limits and thresholds unchanged. | graph_query.py (`_call_edge_category`, report tallies); CallEdgeCountsReportTests (4) and CallEdgeCountsRegisteredSurfaceTests (2) in test_graph_query.py with an independent arithmetic oracle, known counts (hub 10 = 3 resolved + 4 extracted + 3 unclassified, 2 receiver_unknown), mixed SQL/call legacy count, limits 1/3/50, threshold, eligibility, exclude_external/exclude_generated and all three collapse views through wf_graph_report_response, plus raw/collapsed first-representative order controls. |
| 2026-10-07 | Reconciled confidence-only tests and contract fixtures. | test_unknown_receiver_cross_file_and_incremental_ceiling now requires external::authenticatedUser; test_all_member_profiles_keep_unknown_receiver_confidence requires external::getValue; builder pins 52 -> 53 in test_graph_call_integrity, test_graph_indexer and test_graph_quality_eval; docs/reports/graph-quality-post.json regenerated (only version label, hashes, provenance changed; totals unchanged); wf_graph_report handler digest updated in register-surface-handler-digests.json; test_server_tools_retrieval byte-for-byte report tests keep legacy fields byte-for-byte and check call_edge_counts separately. |
| 2026-10-07 | Docs: architecture (unowned member calls, legacy SQL-inclusive degree prose corrected, call_edge_counts semantics), MCP spec, wf_graph_report description, CHANGELOG 1.29.0 operator-action note plus Added/Fixed bullets, docs/RELIABILITY.md builder version. | wf_validate_docs passed. |
| 2026-10-07 | Verification. | Focused repo runs: test_graph_call_integrity 33, test_graph_query 98, test_graph_indexer 549, test_graph_incremental_merge 58, test_graph_quality_eval 102, test_graph_snapshot_readers 51, test_tool_surface_golden 25, test_mcp_tool_registry 27, test_handler_modules 13, test_server_package 31, test_server_tools_retrieval 1044, all ok. Scratch mutation probes: 15 of 15 killed. Scratch full suite: 11729 tests across 170 files, OK (scratch receipt is not the close-time receipt). |
| 2026-10-07 | Deviation for review: docs/RELIABILITY.md (builder-version statement), docs/reports/graph-quality-post.json, tests/fixtures/register-surface-handler-digests.json, tests/test_graph_quality_eval.py and tests/test_server_tools_retrieval.py are outside the named Serialization Points review targets; each edit is a direct consequence of the builder bump or the additive report field (coordinator directed the RELIABILITY.md edit). No requirement changed. | git diff of those five paths. |
| 2026-10-07 | Deviation for review: two existing fixture expectations changed meaning rather than only tightening. A computed receiver now never binds a unique cross-file method of the same name (Java `b.subject().authenticatedUser()` previously bound Other.authenticatedUser at EXTRACTED), and a bare identifier receiver in a `.`-namespace language (`b.go()`, `pkg.Fn()`, `C.m()`) deliberately keeps the existing heuristic because its head may name a module or type. The affected set is therefore computed receivers everywhere plus Rust `.` and C/C++ `->`; PHP `->` and Ruby identifier receivers are not in it. | graph-index-system.md 'Unowned member calls' section. |
| 2026-10-08 | DEL-1 repair (regressions on established owned receivers, AC-2): `_ts_lexical_owner_receiver` keeps Ruby constant-only `scope_resolution` receivers (`M::K.baz()`, `::K.baz()`) and Java `Outer.this` / `Outer.super` (`field_access` ending in `this`/`super`) owned; the Rust declaration search strips one reference layer (`_rust_reference_inner_type`: `&S`, `&mut S`, `&'a S`) and `_rust_value_type` reads `let s = S;` as unit struct `S`. HEAD-vs-fixed probes: Ruby `a.rb::M.K.baz`, `a.rb::K.baz`, cross-file `k.rb::M.K.baz`, `k.rb::K.baz` and Java `Outer.foo` now match HEAD exactly (target, EXTRACTED, no unowned flag); Rust `&S`, `&mut S`, `let s = S;`, `let s: &S` bind `S.foo` same-file and cross-file as at HEAD, now at RECEIVER_RESOLVED instead of HEAD's name-only EXTRACTED with receiver_unknown. `&Vec<u8>` and `&mut u8` receivers stay unowned (bounded stripping, no inference). Builder version stays 53 (unreleased within this wave). | graph_indexer.py; new UnownedMemberCallTests: test_ruby_constant_and_scope_receivers_keep_existing_binding, test_java_qualified_this_keeps_existing_binding, test_rust_reference_receivers_resolve_the_named_type. Against HEAD's indexer the Ruby and Java tests pass and the Rust test differs only in confidence and the new unowned control. |
| 2026-10-08 | DEL-2 repair: controls for `super` (TS `super.foo()` keeps `B.foo`), Ruby `constant` (`K.baz()` same-file and cross-file) and the parenthesized-receiver unwrap (TS `(this).foo()`, Rust `(self).foo()`), all equal to HEAD. Docs: architecture lists the Rust reference stripping and known residual gaps (PHP `$x->m()` on non-`$this`, C/C++ `obj.m()` with `.`, Ruby lowercase identifier receivers, JS `super.foo()` with an external parent); CHANGELOG 1.29.0 operator note now reads Rust `.` and C/C++ `->` on non-`self` plain identifier receivers, and the 201wg Fixed bullet names the Rust stripping and residual gaps; MCP spec says non-`self`. graph-quality-post.json regenerated: only graph_indexer_sha256, digest and timestamps changed (totals 10/0/2 unchanged). | test_self_super_and_parenthesized_receivers_keep_existing_binding. Scratch mutation probes 7 of 7 killed: scope_resolution branch, Outer.this branch, reference stripping, unit-struct let, `super` and `constant` removed from the self set, paren unwrap removed. Focused repo runs OK: test_graph_call_integrity 37, test_graph_query 98, test_graph_indexer 549, test_graph_incremental_merge 58, test_graph_quality_eval 102 (7 skipped), test_server_tools_retrieval 1044, test_tool_surface_golden 25. |
| 2026-10-08 | Reverification found the callee-side paren unwrap untested; coordinator added `test_parenthesized_callee_keeps_its_computed_receiver_unowned` (JS `(b.subject().render)()` stays `external::render` unowned). Removing the unwrap in a scratch copy fails it; repo file 38 tests OK. | test_graph_call_integrity.py; scratch rM4 |


| 2026-10-08 | Takeover reconciles DEL-2's inherited evidence gap. Source/tests/public caveats were repaired before this host and before a contemporaneous DEL-2 repair-start event; no event is backdated. Cycle 2 starts the remaining documentary/evidence repair only, preserving the original nonblocking `do_now` classification. Fresh independent QA/docs context `graph-del2-independent-20261008` verifies 15 ownership controls and 6 call-count/public-response tests, zero skips. | Four full-script scratch mutants remove super, Ruby constant, receiver-parenthesis and callee-parenthesis handling; each fails its target assertion. Separate TS cross-file super binds `b.ts::B.foo`; all four documented residual gaps reproduce. Current graph/docs fingerprint `c85079411e486287999dfaac325d1fa7957c237eb15f8d318eb81dead7f6be90`, stable start/end. Canonical suite/docs boundary remains coordinator work. |

| 2026-10-08 | DEL-2 cycle-2 independent reverification recorded; current typed head is completed and terminal, with the mandatory convergence checkpoint derived by the tool. Historical repair chronology and original finding remain visible. | `wf_review_event` source authority; operator-signoff remains withheld until operator approval. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-07 | Select structural ownership safeguards plus additive report attribution in one bug change. | Corrects topology and its opaque presentation through existing mechanisms. | Method denylist: misses arbitrary collisions and can hide genuine calls. Report-only filtering/resolved-only default: leaves wrong topology and changes ranking semantics. Full Rust type inference: substantial machinery beyond the bounded fix. |
| 2026-10-07 | Preserve unresolved edges and established bare/qualified/typed calls; classify syntax rather than blocking every receiver_unknown edge. | Receiver detection also marks qualified namespace paths. | Drop unresolved calls: loses evidence. Reject every qualified call: breaks supported ownership paths. |
| 2026-10-07 | Preserve legacy count/order and add call-only fields. | Avoids a silent ranking change and respects existing SQL relation counts. | Rename count or sort only by resolved calls: separate compatibility decision needed. |
| 2026-10-07 | Use generic fixtures; retain Tensorwell as historical field evidence. | Acceptance remains portable, offline and independent of concurrent consumer work. | Require a Tensorwell checkout/rebuild: couples the gate to external state. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Blanket rejection blocks supported qualified calls. | Syntax/ownership rule and positive bare, qualified, typed and construction controls. |
| Shared fallback correction affects other languages. | Representative affected-profile controls; disclose unsupported dispatch. |
| Incremental fragments restore wrong targets or lose provenance. | Symbol-transition tests, fresh-build comparison and published-row checks. |
| Report transforms omit or misaggregate fields. | Independent edge arithmetic through registered-tool and effective-view fixtures. |
| Resolved counts are read as runtime proof. | Document static evidence tiers, edge counts and unclassified/unknown subsets. |
| Old indexes retain defective extraction. | Existing builder-version invalidation and pre-fix artifact transition test. |

## Session Handoff

Admitted, independently reviewed and readied in wave 203pu graph-call-attribution-integrity. All five required readiness lane approvals and council-readiness are current; Prepare and optional Review plan passed with no blocker or operator question. The wave remains planned/readied, not active. The operator explicitly instructed: do not implement yet. Only the admission/readiness task is checked; implementation ACs/tasks remain unchecked. Future implementation requires separate operator direction. No framework code, consumer source or production index was changed by this planning effort; no commit or closure was performed.
