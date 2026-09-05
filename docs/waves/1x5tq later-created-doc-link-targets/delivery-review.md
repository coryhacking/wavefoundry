# Delivery review — wave 1x5tq

Owner: Engineering
Status: active
Last verified: 2026-09-05

**Final result: PASS.** All five required technical lanes and the delivery council have current typed approvals. The review found and repaired one high correctness defect, ARCH-DEL-1; fresh architecture and QA reverification cleared both required lanes in repair cycle 2. No blocker was waived. Operator signoff and closure were recorded on 2026-09-05 after the review. The operator also authorized committing the delivered changes.

The repair makes idle preflight use the existing read-only payload-binding proof. A consumed retry obligation can no longer hide interrupted graph publication: missing, pending, size/mtime-mismatched or summary-fingerprint-mismatched payloads select the existing locked full merge. Publication ordering, ownership and admitted requirements remain unchanged. Independent probes verify exact edge/node recovery, bound metadata before epoch completion, unchanged dry-run state and subsequent idle convergence.

Final verification: **8,480 tests across 74 files, 3 skips, OK in 206.302 seconds**. Fresh framework receipt hash `a549e665607736b8b03d1b0f000d09e328f3189d5a98d3f978c3ebed3baabb91`. Full docs validation and diff check pass. Framework edit gate closed. Full runner log: `/tmp/1x5tq-delivery-repair-framework.log`. Complete seat reports, exact caller facts, observations, frozen snapshots and receipt are preserved in `delivery-evidence.json`; canonical approval authority remains `events.jsonl`.

All six required ACs retain verification evidence; no AC priority, scope or deferral changes were needed. Memory capture proposed one readiness record; focused validation rejected it because its targets were temporary probes and the durable decision already exists in the change doc. No active memory or speculative backlog was added.

## Focused repair review


Verdict: approve delivery. The coordinator confirms architecture and QA have terminalized their independent repair chain and recorded fresh approvals; code, security and performance approvals are also recorded. This is the focused continuation of the completed round0 full-depth primer, four fixed seats, rotating best-alternative seat, one challenge round and anonymous first synthesis. No full council restart: inspection of the actual round0-to-round2 delta establishes a shared pure read-only predicate and one summary/binding equality check; ownership, durable authority, trust boundaries, public contract, graph format and publication order remain unchanged.

Original seat-agreement aggregate remains historical `split`, maximum severity `high`. It is not rewritten as independent unanimity. The original publication disagreement resolved into one ARCH-DEL-1 defect, with architecture and QA preserving blocking authority. Current fresh affected-lane evidence converges on repair completion; no material disagreement remains. Security/code approvals remain their own unaffected lane evidence, managed by the coordinator.

| Finding | Disposition | Current evidence and resolution |
| --- | --- | --- |
| ARCH-DEL-1 | do_now, repaired | Architecture and QA each independently executed the original interrupted-publication replay and adjacent controls, then supplied lane-specific reverification/approval. Council independently ran three public tests and its own known-bad control. No blocker waived. |

The primer and rotating seat's strongest alternative was to share the existing read-only publication proof and route unknown bindings into the existing locked full-merge recovery. The repair adopts it. Unconditional graph dispatch is weaker because it adds healthy-idle work; another durable retry ledger adds authority and crash ordering complexity without evidence of benefit. The delivered improvement is the shared proof plus the public interruption/binding regression matrix; no speculative follow-up is created.

## Executed council evidence

Own execution: 3 public IdleDocLinkRecoveryTests pass, 0 failures/errors/skips: failed publication then unchanged recovery; missing/size/mtime/summary-fingerprint binding census; node-less target plus dirty epoch. These assert byte-identical lock-free preview, exactly one real recovery dispatch, exact EXTRACTED link/doc node, bound metadata, complete epoch, and following idle with no graph dispatch or generation change. Own binding-omission mutant rejected with 1 assertion failure and 0 errors/skips. All13 packet hashes match after probes. Independently inspected source predicate, two production helper call sites via MCP code_references, and round0-to-round2 patch delta: no publication order, authority, contract, ownership or format change. Architecture and QA fresh replay/reverification approve repair; performance fresh approval clears reliability condition. Full runner inspected: 8480 tests/74files/3skips, OK in206.302s. Coordinator reports full wf_validate_docs clean.

Same-root-cause census is bounded to idle preflight and graph finalization's cached/fast-return proof. MCP AST call-site retrieval finds the helper in read_pending_doc_link_repairs and GraphIndexSession._payload_binding_ok. Own public tests exercise pending publication, missing payload, size mismatch, mtime mismatch and merge-summary fingerprint mismatch, then healthy idle. Architecture additionally checks bound payload and exact edge while the epoch is still building. QA independently covers dryrun, unreadable/deferred targets and orphan/dirty controls. Performance reports zero idle scans and selective one-document repair, and runs its own public interrupted retry. These are attributed executions, not multiple independent discoveries of ARCH-DEL-1.

## Falsification Check

Working verdict is approval. The strongest counterargument is the original failure where the durable obligation was consumed before graph publication and a later success hid the missing edge. Own current-tree public replay recovers, its old-proof mutant fails the recovery assertion, and architecture independently verifies binding/edge publication before epoch completion. This counterargument therefore does not change the verdict. Arbitrary unenumerated corruption or hardware failure is outside this finite claim.

## Limits and provenance

Focused postrepair synthesis extends completed round0 full council and anonymous first synthesis; no new five-seat council was run, no independent unanimity claimed. Moderator did not implement repair. Prior finding/seat reports are shared synthesis inputs, never substituted for own execution. Own tests use real public build_index/walker/SQLite/Lance/lock/epoch with deterministic mock embeddings; fresh sessions within one process, no hardware disk-full or process-kill test. Pre-completion ordering instrumentation belongs to architecture lane. Performance timing belongs to performance lane and is descriptive. Whole suite was executed by coordinator and its log inspected; docs validation is coordinator-reported. No frozen source/docs, real index, ledger, closure or commit writes.

Artifacts: council-probe.py, council-probe-results.json, council-baseline.log, council-knownbad.log, council-repair-delta.patch; architecture-reverification.json, architecture-approval.json, qa-reverification-caller.json, qa-approval-caller.json, performance-approval-caller.json; prior protocol record /tmp/1x5tq-delivery-round0/council-final.json and blind-synthesis.json.

## Initial full council — historical round 0

The following records the blocker before repair; it is superseded by the final result above.

Full isolated council completed for changes 1x8e1 and 1x81w. **Delivery approval withheld: ARCH-DEL-1 is a high, required-lane correctness blocker.**

The new idle preflight treats a structurally valid merge snapshot with no unresolved targets as no graph work even when its payload publication is unbound. The architecture seat injected a graph payload write failure after durable graph state committed and consumed the obligation. The next unchanged public build dispatched zero graph merges, returned `up_to_date=true`, and completed generation 3 while the promised document edge remained absent and `payload_stat_state=pending`. A supported full rebuild restored the edge and bound state at generation 4. This is a supported correctness/recovery defect, with no demonstrated attacker authority delta.

Architecture and QA jointly own ARCH-DEL-1; architecture owns the publication execution. QA independently verified the admitted ACs with 16 targeted tests and two known-bad controls before reviewing and accepting the publication trace. Required blocking lanes: architecture-reviewer and qa-reviewer. Recheck approvals: architecture-reviewer, qa-reviewer, wave-council-delivery. Performance separately withholds its whole-lane approval because its role includes reliability. Code/security scoped approval evidence remains available.

Protocol: full five-stance red-team primer with three questions; four isolated fixed seats (architecture, security, QA, reality); rotating performance seat; one bounded post-fixed challenge with every fixed seat explicitly weighing the alternative; independent first synthesis on randomized anonymous seat reports, retaining the required blocker's lane attribution throughout. The initial divergent scoped verdicts must not be rewritten as independently unanimous approval. The final challenge aligns on repairing the blocker.

Preferred repair: share the existing pure/read-only publication proof between idle preflight and graph finalization/cached snapshot validation. Require the bound marker, merge/meta fingerprint agreement and existing size/mtime binding; unproven publication selects existing locked full-merge recovery. Keep selective snapshot reuse, the one-merge lock/epoch boundary and read-only preview. Unconditional merging discards healthy idleness; a separate retry ledger duplicates state and adds consistency obligations. This restores an existing invariant and needs focused repair replay, not a new full council unless the actual implementation changes a load-bearing boundary.

Executed evidence is finite and local. Seven allocated fixture families cover preview persistence, deferred-link lifecycle, publication/persistence, selectivity/cost, invalid summaries/builders, unreadable preservation and exact-edge/metamorphic reference checks. Every formal lane and council moderator executed its own targeted checks plus a known-bad control; no full-suite run or real-project index mutation was performed by this council. All 13 reviewed file hashes remained equal to packet.json throughout round 0.

| Reviewer | Own executed evidence | Known-bad control | Final status |
| --- | --- | --- | --- |
| Architecture | 3 current idle-recovery tests; publication interruption, unchanged retry and full-rebuild positive control | Expected edge assertion fails after interruption/retry; rebuild restores it | ARCH-DEL-1; approval withheld |
| Security | Combined dirty epoch + orphan + pending-link preview and real CLI recovery | Disabled dry-run return changes persisted rows; assertion rejects | Scoped security approval maintained |
| QA | 16 focused AC/edge/preview/retry tests, zero skips | Removed dry-run gate and disabled deferred trigger both rejected | Joint ARCH-DEL-1 ownership; approval withheld |
| Reality | Missing/malformed-summary public recovery and dirty/orphan CLI controls | Suppressed rebuild request produces 0 dispatches instead of 1 | Delivery withheld for shared blocker |
| Performance | 400–401-file public graph corpus: idle/no unrelated doc scans; one target scans/writes one doc; snapshot avoids repeat blob read | All-docs-pending selector yields 200 scans instead of 0 | Efficiency passes; reliability approval withheld |
| Council moderator | 3 CLI/public preview and retry tests, zero skips | Injected unlocked real maintenance under preview violates persisted-state equality | Council approval withheld |

Performance observations are single local samples, not production latency claims: preflight 3.9 ms; healthy graph API idle 44–47 ms; one-target repair 51.7 ms; unrelated edit 53.3 ms. The suggested extra stat cost is inferred until the repaired code is measured.

Limits: deterministic mock embedding vectors; real temporary SQLite/Lance/graph stores; publication retry uses fresh sessions/connections in the same Python process, not an OS kill. SQLite checks cover persisted rows and durable artifact/Lance bytes, excluding transient WAL/SHM reader bookkeeping. Exact normative edge assertions reduce, but cannot eliminate, the common assumptions shared by incremental/full extraction. No native Windows, model inference, broad concurrency, production percentile or exhaustive corruption claim.

Evidence: packet.json/diff.patch; primer.json; architecture.json and architecture_probe_results.json; security.json and security-probe-results.json; qa.json, qa-mutations.json and qa-ack.json; reality.json and reality-observed.json; performance.json and performance-observed.json; all four *-ack.json files; council-tests.json/log; blind-packet.json, identity-map.json and blind-synthesis.json; council-final-hashes.json.

Exact typed caller objects are preserved in architecture.json.caller_json and security.json.caller. QA and performance caller drafts are expressly WITHHELD, and council-not-approved.json records no approval. The root coordinator owns typed ledger recording and repair routing. No commit or closure authorized or performed.

Final independent blind synthesis: `needs_revision`. Canonical initial `seat_agreement_aggregate`: `split`, maximum severity `high`. One bounded challenge resolves classification and preferred repair; it does not turn shared-evidence convergence into initial independent unanimity. Role identities were restored only after merit assessment: Seat1 security, Seat2 performance, Seat3 QA, Seat4 reality, Seat5 architecture. Round0 freeze released after all13 hashes matched and all review contexts finished.

## Initial code lane — unaffected scope

Verdict: approve in the bounded code lane; no actionable defect found.

Fresh independent review of changes 1x8e1 and 1x81w, their requirements and actual implementation diff. The 13 packet hashes matched before and after execution. Scope remains the admitted unresolved-link obligations and idle dry-run/caller integration.

Independent reference: change 1x81w Requirements 1–3 promises persistent state invariance for dry runs; change 1x8e1 Requirement 1 and caller-integration task promise retained per-document retry after failed reads through unchanged public builds. Those promises predict exact edge/doc presence, lock-held/building-epoch recovery, one graph merge, and stopped dispatch after success. Tests use real walk, Lance/SQLite stores and CLI main; embedding vectors are mocked, which does not prove semantic retrieval quality.

MCP-first source/test outlines followed by targeted code_read verified indexer._build_index_locked, graph_indexer.read_pending_doc_link_repairs and GraphIndexSession.finalize. Tool output on initial full outlines/diff was truncated; subsequent selected reads and a source diff with long lines clipped recovered the load-bearing changes. Scoped shell rg located helper definitions after orientation; framework tests are excluded from code_keyword, so direct test outline/read was used. No full-repository absence claim.

Executed two family groups (F1, F2), four named tests total:
- DryRunIdleMaintenanceTests.test_dirty_epoch_dry_run_is_byte_identical_and_reports_recovery: dry-run reports dirty_epoch, no build lock, persisted SQL rows/artifact bytes and epoch unchanged.
- IdleDocLinkRecoveryTests.test_unchanged_public_recovery_after_failed_doc_read: exact referring doc/edge returns through unchanged CLI recovery; lock held and epoch building; one graph dispatch; next unchanged call has no dispatch/generation advance.
- IdleDocLinkRecoveryTests.test_nodeless_link_and_dirty_epoch_share_one_locked_recovery: the same invariant with a node-less target plus dirty epoch; target stays node-less.
- IdleDocLinkRecoveryTests.test_pending_link_and_orphan_reap_share_one_graph_merge: graph link repair and orphan/Lance removal converge in one graph merge.

Current tree: four tests pass, zero errors/skips. Baseline log: code-baseline.log (3-test run plus exact mutant counterpart 1-test run).

| Mechanism | Scratch mutation | Failing test | Observation |
| --- | --- | --- | --- |
| Idle pending-graph eligibility | Remove `and not _needs_graph_recovery` from the idle-return guard | IdleDocLinkRecoveryTests.test_unchanged_public_recovery_after_failed_doc_read | AssertionError: graph.call_count 0 != 1; exactly one failure, no errors/skips |

Own known-bad run: code-mutant.py builds a scratch source copy and substitutes only the compiled _build_index_locked function into the test-loaded module. Frozen repository source unchanged. code-mutant.log ends KNOWN_BAD True; source code-indexer-mutant.py retained for reproduction.

Limitations/unrun: no whole framework suite; no comprehensive mutation census. Other newly added guards (summary/version validation, candidate normalization, failed-read retention, unreadable-directory skip, fragment persistence, rescan selectivity and cached-blob reuse) were read but not independently mutated in this lane. Full-build parity and other pending dry-run reasons are not claimed from this sample. WAL/SHM transient reader locking is excluded by the persisted-state comparison. Mock embeddings and local platform only. Initial high-volume orientation output was truncated and no claim of exhaustive startup text review is made.

No repository, frozen artifact, or canonical review ledger edits. Caller JSON is code-approval.json.
