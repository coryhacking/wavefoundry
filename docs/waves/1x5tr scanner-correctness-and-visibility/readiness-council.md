# Scanner readiness council

Owner: Engineering
Status: active
Last verified: 2026-09-05

Phase: readiness. Final verdict: APPROVED for readiness after bounded plan repairs and focused independent required-lane rechecks. No delivery behavior or AC completion is attested.

## Protocol and shared evidence

The full five-stance red-team primer ran in isolation first with three primer questions, followed by isolated architecture, security, QA, and reality seats. Performance ran as the rotating best-alternative seat after the fixed seats. Each fixed seat explicitly weighed that alternative in its own report before synthesis. Independent code and docs-contract lanes also reviewed the frozen plans. Shared evidence was the packet, both admitted plans, and primer; seats independently validated current source rather than adopting discovery conclusions. Source navigation used MCP outlines and targeted reads. Test-index gaps were explicitly bounded where shell fixture/test reads were used. No full suite, index build, network action, code edit, or canonical ledger mutation was performed by the council.

First convergence synthesis used randomly ordered anonymized reports: Seat 1 QA, Seat 2 security, Seat 3 reality, Seat 4 performance, Seat 5 architecture; identities were reattached only after the first merit assessment. Artifacts: `/tmp/1x5tr-review/anonymized-first-pass.md`, `first-merit-assessment.md`, `seat-identity-map.json`. Required-lane blockers remained attributed in their original evidence and the explicit retained-authority list throughout; anonymization never changed their blocking status.

## Initial synthesis

Initial seat_agreement_aggregate: seat_agreement=split, max_severity=medium. The difference was whether ambiguous plan language was acceptable before correction. No seat disputed the desired bounded implementation. Architecture/code/QA/docs required-lane blocking authority took precedence over contextual nonblocking interpretation. The single targeted challenge is resolved through accepted precise corrections and focused independent current-plan replay; no second design debate or adversarial sweep is warranted.

The red-team strongest challenge was independently confirmed: findings and the raw triple cannot distinguish complete empty scanning from allowlisting, unreadability, or guards. Moderator and multiple seats executed disposable controls falsifying that inference. Explicit per-file outcomes and worker/fallback transport remain required delivery evidence. The existing candidate wrapper also independently included machine authority in a non-git fixture. QA extended the primer with two real scanner/SQLite passes proving candidate filtering does not purge a historical machine row.

Three deduplicated required findings were accepted for repair:

- ARCH-READY-1: scope purity to the new advisory reader, preserving close validation and its scanner effects. Architecture, code, QA, and docs-contract blocking lanes retained. Persistence errors use nonblocking WARNING output.
- QA-R1: explicitly state fresh-cache pollution prevention; compare membership and count, without promising historical cleanup. QA blocking lane retained.
- DOCS-READY-1: add architecture ownership/deletion contracts and registered tool description to the planned documentation targets. Missing records never prove complete coverage. Docs-contract blocking lane retained.

Root recorded these findings and repair starts through the typed interface. Repaired plan hashes: 1x4om `3f8570fe808992efcc7fa52fe20a559506b5880d`; 1x550 `c5ffd3a9905e23456755e9a1e8e19229682c214d`. Moderator read the actual corrected plans and packet; they contain each bounded correction. Source hashes remain the original frozen tree. The repairs are planning changes; production documentation and source changes remain implementation work.

## Strongest alternative and improvements

Existing SQLite offers cheaper transactional path updates, but its derived-state reset and custom scan-directory semantics conflict with fixed-root durable observation history. Separate SQLite adds schema without measured need; append-only JSONL adds replay and compaction obligations. All fixed seats explicitly prefer the small JSON ledger with a short read/merge/atomic-publication lock. No scanning or worker waiting belongs under that lock. No speedup or quantitative performance result is claimed.

Concrete improvements retained in the corrected plan and delivery obligations: explicit complete/guard/no-outcome transport; long-line partial coverage independent of rule keyword filtering; root-local authority; scanner-version invalidation for initial observations; ordinary-line finding preservation; exact machine-authority census with positive lookalikes and unchanged git candidates; separate advisory-reader purity and close response propagation; malformed/prior-byte/concurrent-delta controls; named deletion mutations.

## Evidence limits

Council baseline artifact `/tmp/1x5tr-review/council-baseline.json` records executable candidate/raw API controls. Other seats distinguish source-level plan refutations from runtime fixtures. No existing or future probe claim is promoted into delivery approval. Worker spawn, persistence publication, concurrent merging, close responses, complete authority census, mutations, and required suite/docs validation remain delivery obligations. No credible lower-trust attacker or new authority escalation was established.

## Final disposition

Fresh independent architecture, code, QA, docs-contract and security rechecks approve the actual corrected plans; performance inspected corrected plan hashes and maintains its original independent readiness approval. This resolves the single targeted challenge over plan precision. Every required lane has returned current readiness approval; no required-lane blocker remains in reviewer evidence. The coordinator owns state-derived terminal events and approval publication. Original split/medium aggregate remains recorded as history; the final required-lane approval agreement is unanimous, with no residual material disagreement.

Council approval payload: `/tmp/1x5tr-review/council-approval.json`. Current six lane approval payloads: `arch-approval.json`, `code-approval.json`, `qa-approval.json`, `docs-approval.json`, `security-approval.json`, `performance-reviewer.json` in that directory. All declare the actual role authority, independent context, readiness phase, and exact evidence-integrity object. Existing performance context was preserved rather than mislabeled newly spawned. The council context was never an implementation or repair-author context.

Proceed to readiness validation and implementation. Review remains readiness only; no delivery signoff, AC completion, wave closure or commit is authorized by this report.

## Historical artifact locations

On 2026-09-05 the operator requested consolidating the individual readiness reports. Their complete text is retained below, with heading levels adjusted for this archive. Original verdicts, verification contexts, limitations, and temporary-probe references describe the review at that time; they are not new approvals. The append-only `events.jsonl` remains unchanged. Historical citations to the removed filenames resolve through this relocation table. The council synthesis above remains at its original path.

| Historical citation | Preserved report |
| --- | --- |
| `readiness-architecture-recheck.md` | [readiness-architecture-recheck](#readiness-architecture-recheck) |
| `readiness-architecture.md` | [readiness-architecture](#readiness-architecture) |
| `readiness-code-recheck.md` | [readiness-code-recheck](#readiness-code-recheck) |
| `readiness-code.md` | [readiness-code](#readiness-code) |
| `readiness-docs-recheck.md` | [readiness-docs-recheck](#readiness-docs-recheck) |
| `readiness-docs.md` | [readiness-docs](#readiness-docs) |
| `readiness-performance.md` | [readiness-performance](#readiness-performance) |
| `readiness-qa-recheck.md` | [readiness-qa-recheck](#readiness-qa-recheck) |
| `readiness-qa.md` | [readiness-qa](#readiness-qa) |
| `readiness-security-recheck.md` | [readiness-security-recheck](#readiness-security-recheck) |
| `readiness-docs.md#docs-ready-1` | [DOCS-READY-1](#archived-docs-ready-1) |

## readiness-architecture-recheck

### Architecture Readiness Repair Recheck

Owner: Engineering
Status: active
Last verified: 2026-09-05

Verdict: approve the current repaired plan for architecture readiness. This is an independent focused repair recheck, not delivery approval. Context: `1x5tr-architecture-focused-recheck-20260905-c`; actor: `architecture-reviewer`. The reviewer did not implement the plan repair and formed the source/plan assessment before consulting the prior finding payload for schema and historical judgment fields.

The whole-close no-scan premise is false in current source: `wf_close_wave_response` invokes `run_validate` in both modes (`server_impl.py:19604`); `run_validate` launches `docs_lint.py` (`server_impl.py:4761-4777`), whose entry invokes `wave_lint_lib.cli.main` (`docs_lint.py:23-27`). Its full-check branch calls `check_hardcoded_secrets(record_only=True)` (`wave_lint_lib/cli.py:250-267`). All paths are under `.wavefoundry/framework/scripts/`. The repaired 1x4om Design now preserves that scanner path and limits the new no-scan/no-write obligation to the advisory reader (lines 70-75).

The design requires nonblocking WARNING on scanner publication failure (1x4om:49-51,73-74), keeping advisory observations out of close-blocking diagnostics. Fixed root-local authority, short merge lock, affirmative scan/removal retirement and missing versus malformed semantics remain explicit (55-64). Missing/empty is not coverage proof; deleting index/ledger loses observation history (77-80).

Architecture source confirms why documentation changes are required: `docs/architecture/domain-map.md:27` currently treats the index as entirely rebuildable, and `docs/architecture/data-and-control-flow.md:202` names only indexer ownership. The repaired plan explicitly requires updates to both ownership surfaces and the public tool/spec contract (1x4om:149-155). These are delivery obligations; the current plan does not pretend historical observations can be reconstructed from current source.

The sibling 1x550 requirements and ACs explicitly start from a fresh cache and exclude migration of previously polluted rows (35-41,65-66). That is a bounded prevention contract, with historical cleanup outside scope. The shared lightweight exclusion owner remains consistent with the existing machine-authority-only boundary; semantic eligibility and git candidate membership are preserved by the plan. The performance alternative of reusing the broader semantic walker would suppress legitimate scanner candidates, so the narrower owner is appropriate.

| Mechanism | Known-bad control | Observation |
| --- | --- | --- |
| Reader purity boundary | Whole-close no-scan claim | Refuted by the current public-to-scanner source path; repaired text scopes purity to the new reader. |
| Advisory failure semantics | Publication failure as blocking lint error | Repaired requirement mandates WARNING, with explicit preserved validation. |
| Observation ownership | All index contents are reconstructible | Current architecture sentence identified; repaired plan explicitly requires ownership and deletion-loss corrections. |
| Fresh-cache prevention | Promise that exclusion cleans historical cache rows | Repaired requirements and ACs expressly exclude that promise. |

All five integrity booleans apply to the performed readiness source/plan review: the bounded review ran without an unintended skip, traced the public path in source, used actual branches and artifact states, made nonvacuous contradiction checks, and detected the known-bad whole-close premise. No runtime public-path execution, implementation mutation, suite, concurrency fixture, or index operation was run or claimed. Delivery tests and architecture edits remain unimplemented obligations. No additional architecture blocker within this focused repair scope.

## readiness-architecture

### Scanner readiness architecture review

Owner: Engineering
Status: active
Last verified: 2026-09-05

Verdict: blocked pending one bounded plan clarification. Required-lane identity: architecture-reviewer. Phase: readiness; independent fresh context `1x5tr-architecture-independent-20260905`. No implementation attestation or typed approval is supplied.

#### Finding ARCH-READY-1

File: `1x4om-bug scanner-guard-skips-invisible-at-close.md`, Design, paragraph beginning “Keep scan_file_raw”. Class: contradictory-control-flow-contract. Severity: medium. Confidence: high. Reachability: not-externally-reachable.

The literal sentence “Close only reads the ledger; it must not run scanning or write scan state” contradicts the existing close validation path and the requirement to preserve close rules. Independently checked source: `server_impl.wf_close_wave_response` calls `run_validate` even for dry_run; `run_validate` invokes `docs_lint.py`; that entry calls `wave_lint_lib.cli.main`; the full lint path calls `check_hardcoded_secrets(..., record_only=True)`. Do not remove this existing validation to satisfy the new sentence. Scope read-only/no-rescan to the added advisory reader and explicitly preserve existing close validation and its scanner effects. The response should read the ledger after validation so an existing scanner pass can contribute current observations.

Classification: validation_status=real; scope_relation=admitted; introduced_or_worsened_by_wave=true (plan obligation); contract_relevance=required_ac; supported_reachability=true; attacker_reachability=false; authority_domain=none; authority_delta=none; observable_impact=low; containment=unverified; fix_risk=lower; optional_value=positive; repair_scope_bounded=true; repair_safety=safe; benefit_vs_fix_risk=greater; rejection_basis=none. Disposition: do_now; blocking=true; blocking_required_lanes=[architecture-reviewer]. Readiness-safe control refutes the plan's literal no-scanner premise by current-tree call-path inspection; this is inferred source evidence, not an executed close fixture. Focused plan reread suffices after correction; no gate refactor is requested.

#### Strongest challenge and primer answers

**strongest_challenge:** Findings cannot prove coverage. My executed P1 shows empty text, allowlisting, and missing-file reads all return the identical raw triple. P3 shows NUL rejection returns it too while producing an in-process skip. Thus absence of hits cannot retire durable skips.

1. Add an explicit internal outcome set only after successful reading and complete eligible-line evaluation; long-line rejection marks partial coverage and retains ordinary-line findings. Transport the same outcome with each process worker result; serial fallback calls the same producer. Preserve the public raw triple. These are feasible plan semantics, not behavior verified as implemented.
2. The existing policy boundary is `indexer.walk_repo`'s exact `HARDCODED_EXCLUDE_PATHS`, four predicates (canonical wave event ledger, memory archive body, legacy memory pointer, scan-findings authority), and `HARDCODED_EXCLUDE_PREFIXES`. Its later dot-directory, filename, extension, and size policy must not move into scanner eligibility. Extraction to a small stdlib owner preserves dependency direction and avoids importing the semantic indexer into lint. I did not close a full path census; require the packet's table of canonical members and negative lookalikes at delivery. P2 executes the actual get_scan_files non-git boundary and preserves .env/package-lock.json while confirming current index pollution. Git and two-pass SQLite membership remain delivery probes for this seat.
3. Publish outstanding path/reasons in response data, coverage-unavailable on malformed/unreadable authority, and no advisory on missing/empty authority. None changes status or finding classification. Wording should say “no recorded guard skips,” never “fully scanned.” The added reader must not write or scan; existing close validation remains intact subject to ARCH-READY-1.

#### Ownership and additional scope question

The root-local scanner ledger has a clear scanner-writer/close-reader split and a short read-merge-publish lock. No scan work should hold that lock. Publish independent path deltas; unreadability and candidate omission do not constitute removal. Update the MCP secrets contract and the data/control-flow documentation to identify this authority and its deletion semantics: current domain-map wording calls the index wholly rebuildable, while outstanding historical coverage evidence is not reconstructed merely by an incremental cache hit. This is documentation work within the admitted persistence contract, not an ADR or broader state-store migration.

For old polluted cache rows, candidate filtering alone does not establish cleanup. AC-1 is explicitly about a non-git fixture; define that fixture's initial cache state and pin membership after both scans. I did not independently execute existing polluted-cache migration. Do not silently promise migration or modify the explicitly excluded orphan reconciliation. This is a bounded unresolved delivery-evidence boundary, not a separately proven blocker.

#### Executable evidence and limitations

Three selected baseline probes ran successfully using disposable roots: P1 raw completion ambiguity; P2 real get_scan_files candidate membership; P3 real raw parser NUL guard. Results: `/tmp/1x5tr-review/architecture-probes.json`. Expected and observed: empty/allowlisted/missing triples equal; index internals included alongside legitimate .env and lockfiles; NUL file equals empty raw result but emits a skip. Known-bad method: readiness-safe-control, refuted claims that empty triples prove completion and fallback already excludes internals. Public/closest faithful boundaries: get_scan_files and the public scan_file_raw contract. No product mutation was applied.

Initial fixture attempts failed on an incorrect keyword (`full` instead of `scan_all`) and on a .pptx assumption; neither is evidence of a product failure. Corrected controls completed without skips. Two incorrect source outline paths returned file_not_found and were corrected from the admitted source paths. Gapfill: test sources are outside semantic indexing; a scoped shell search located lifecycle tests, but no test execution or test-derived verdict is claimed. No area AGENTS.md was found under .wavefoundry. Startup architecture/source reads were bounded; no complete universal census is asserted.

Not run: process/spawn fallback, ledger transitions/concurrency, full close fixture, git control, two SQLite passes, deletion mutations, framework suite. These are future implementation/delivery cells; this readiness seat does not attest them. The 180-second substantive budget bounds this review. No source, plan, wave status, or canonical ledger was edited. No other fixed-seat output was read. Rotating alternative weighing remains pending moderator dispatch.

#### Rotating alternative weighed

Architecture weighs the performance seat's proposed existing-SQLite alternative against the admitted short-lock JSON owner. Transactions could simplify atomic path-delta merging, but sharing a derived index store would couple durable outstanding coverage history to index reset/recovery and custom-index location policy. Those lifecycle concerns are material to the fixed root-local authority contract. This weighing treats the moderator-supplied reset/custom-directory behavior as reported evidence, not as newly independently verified source. A separate SQLite store avoids that coupling but introduces schema and connection ownership without a measured requirement in this bounded wave; an append-only format adds replay and compaction duties.

Prefer the admitted small JSON owner with atomic replacement under one short read/merge/write lock, no scanning under that lock, and explicit failure preservation. Its correctness must still be demonstrated with concurrent independent deltas and publication-failure controls at delivery. This alternative weighing does not change ARCH-READY-1 or grant conditional approval: the architecture-reviewer blocker remains until the contradictory close sentence is corrected and independently rechecked.

## readiness-code-recheck

### Scanner readiness code recheck

Owner: Engineering
Status: active
Last verified: 2026-09-05

Fresh independent code-reviewer verdict: ARCH-READY-1 resolved for this lane. Current 1x4om Design restricts no-scan/no-write to the new advisory reader, explicitly preserves existing close validation and scanner publication, and requires WARNING output for publication failure. Requirement 6 and packet fixture 5 agree. Both admitted plans were read; this focused correction introduces no implementation scope expansion.

The independent reference is the current caller contract: server_impl.py:19604 calls run_validate in both close modes; lines 4761–4774 invoke docs_lint.py; wave_lint_lib/cli.py:267 invokes check_hardcoded_secrets(record_only=True). The known-bad control was the original whole-close no-scan assertion, which this actual source chain refutes. The repaired plan now agrees with that chain. This source readiness assessment reached the public caller in source; it did not execute close or attest to future implementation behavior.

The original finding classification is retained with completed repair and code-lane clearance only. Five integrity attestations apply to the completed, nonvacuous readiness source/plan comparison and known-bad source control. No runtime test, suite, mutation, spawn or concurrency probe ran; source and plans were not edited. Other lanes and canonical recording belong to the coordinator. Evidence payloads are /tmp/1x5tr-review/code-reverification.json and /tmp/1x5tr-review/code-approval.json; the coordinator must preserve other outstanding lanes when recording.

## readiness-code

### Scanner readiness code review

Owner: Engineering
Status: active
Last verified: 2026-09-05

Actor: `code-reviewer`. Context: `1x5tr-code-independent-20260905-b`. Verdict: readiness blocked by `ARCH-READY-1`; no delivery claims.

#### Strongest challenge and primer answers

The explicit outcome design addresses the primer's strongest challenge: an empty raw result cannot acknowledge complete coverage. `scan_file_raw` returns the same empty triple for an allowlist match, failed stat/read, binary guards and successfully read empty content. Preserve its triple and carry a separate complete/guard/no-affirmative-outcome channel. Partial long-line coverage must remain outstanding while ordinary-line findings survive. `_scan_file_secrets_worker` currently returns only the triple and cost; its parent and spawn-failure fallback require the same new outcome transport. This is feasible, but future implementation is unverified.

1. The exact completion observation must be reaching successful evaluation after reading, with no coverage guard fired, including empty text. Neither candidate membership nor empty findings suffices. Worker outcome propagation is an explicit requirement already present in the plan.
2. `indexer.walk_repo` applies exact authority paths, four predicate families and prefix exclusions separately from filename, dot-directory, extension and size eligibility. Sharing just these authority checks with `_get_all_files` fallback preserves the git branch's tracked and untracked enumeration. The two-build fixture must start with a clean cache and compare membership as well as counts. `update_secrets_scan` records newly enumerated candidates but deletes only explicit `removed` paths: excluding new candidates does not promise to purge old pollution. The fixture-scoped AC and the exclusion of orphan reconciliation permit this bounded interpretation without a new migration requirement.
3. Missing, outstanding and malformed ledger states can use close's existing data advisory plumbing without adding blocking diagnostics. However, the admitted Design's literal whole-close prohibition conflicts with the current validation callgraph, as detailed below. An empty advisory means no outstanding recorded guards, not complete repository coverage.

#### Blocking finding ARCH-READY-1

The plan states: “Close only reads the ledger; it must not run scanning or write scan state.” `wf_close_wave_response` calls `run_validate` before gate evaluation, including dry-run. `run_validate` launches `docs_lint.py`; `wave_lint_lib.cli._run_full_checks` calls `check_hardcoded_secrets(..., record_only=True)`. The scanner is deliberately a recording producer. Adding the proposed scanner-entry publication would therefore also publish during existing validation. Whole-close no-scan/no-write cannot be achieved while retaining this established validation contract.

Required bounded correction: state that the **new advisory reader** performs no scan and writes no scanner state, while existing close validation remains intact. Scope its no-write tests to that reader; an integration test must retain the validation call and verify advisory propagation on success and ordinary blocked responses. This is a plan-contract correction before implementation, not conditional approval or authority to remove scanning. No source was edited.

#### Alternative and bounded advice

Prefer the small explicit per-file outcome and short locked delta merge already admitted. Reusing the whole semantic walker would hide `.env` and other legitimate secret candidates; a full coverage manifest or journal adds unnecessary migration and authority scope. Extraction should leave semantic eligibility unchanged.

`scan_secrets.SCANNER_VERSION` and `update_secrets_scan` already provide version-change escalation to a real full scan that bypasses cache hits. Incrementing the version when this implementation lands is a bounded way to establish guard evidence after upgrade; it does not purge old cache rows and does not make an empty advisory a coverage certificate.

#### Evidence and limits

Independent source/plan review used MCP outline, keyword and targeted reads on `_get_all_files`, `scan_file_raw`, `_scan_file_secrets_worker`, `indexer.walk_repo`, `update_secrets_scan`, `wf_close_wave_response`, `run_validate` and `_run_full_checks`. The readiness-safe negative control was the concrete assertion that a close dry-run does not invoke scanning: tracing the actual caller disproved it. Adjacent control: raw triple ambiguity independently confirms that the proposed explicit outcome transport is necessary; the git branch independently confirms the candidate preservation boundary.

No runtime fixture, test suite, mutation, process spawn, concurrency test, network, index build or canonical ledger operation ran. The selected source feasibility review completed; future implementation checks are outside this readiness evidence. Two initial guessed file paths were absent; retrieval recovered through plan-owned paths and named symbols. No test Gapfill was needed. Confidence is high for the callgraph contradiction and medium for future implementation behavior.

## readiness-docs-recheck

### Docs Contract Focused Readiness Recheck

Owner: Engineering
Status: active
Last verified: 2026-09-05

Verdict: approve readiness for the docs-contract-reviewer lane. Fresh independent context `1x5tr-docs-fresh-focused-20260905-d`; reviewer did not repair plans.

Current Design confines no-scan/no-write to the new advisory reader and explicitly preserves run_validate's record-only docs-lint scanning; packet family 5 agrees. Requirement 6 and Design specify WARNING-only persistence errors. Independently inspected unchanged server_impl.py:19604 -> run_validate:4752-4777 -> docs_lint.py:23-27 -> wave_lint_lib/cli.py:267; this makes the earlier whole-close purity assertion fail the source control.

Current Design explicitly states missing/empty means no recorded skips, never complete coverage; deleting index/ledger loses history and subsequent scans repopulate observations. Affected Architecture Docs now names mcp-tool-surface.md, domain-map Dependency Direction Rules item 6, data-and-control-flow State Ownership, and registered wf_close_wave description. Targeted domain-map:27 inspection still detects the old entire-index-rebuildable statement and State Ownership:202 still assigns indexer ownership, so these remain explicit implementation edits, not claimed completed docs.

Known-bad controls: Readiness-safe negative controls: targeted unchanged source trace rejects whole-close no-scan; domain-map Dependency Direction Rules item 6 still says all index content is rebuildable, detecting the omitted-carrier defect. Current plan expressly corrects both boundaries; production edits remain delivery work.

Scope: current 1x4om Design, Affected Architecture Docs and readiness packet. Direct targeted source and contract inspection only; no runtime tests or future implementation attestation. Shell targeted reads were used, not an MCP source probe. Required production documentation updates remain implementation work. Original finding classification remains intact; payloads clear only this reviewer lane and the coordinator must adapt remaining lanes from current authority.

## readiness-docs

### Scanner readiness: docs contract review

Owner: Engineering
Status: active
Last verified: 2026-09-05

Actor: docs-contract-reviewer. Context: 1x5tr-docs-independent-20260905-b.
Verdict: changes required before readiness; two bounded documentation corrections.
No other seat report was read. Both admitted frozen plans, packet and primer were read.

#### ARCH-READY-1

Blocking lane: docs-contract-reviewer; disposition: do_now.
The 1x4om Design's literal “Close only reads the ledger; it must not run scanning or write scan state” conflicts with the existing close path. Source verification: registered wf_close_wave delegates at server_impl.py:32677; wf_close_wave_response invokes run_validate at :19604; run_validate launches docs_lint.py at :4761–4774; docs_lint.py:23 imports wave_lint_lib.cli.main; cli.py:267 invokes check_hardcoded_secrets(record_only=True). The new reader must be read-only, while existing validation retains its behavior. Qualify the plan and packet family 5 accordingly. Do not infer that a fixture mocking run_validate proves whole-close absence of scanner writes.

<a id="archived-docs-ready-1"></a>

#### DOCS-READY-1

Blocking lane: docs-contract-reviewer; disposition: do_now.
Exact contradictory architecture authority: docs/architecture/domain-map.md:27, Dependency Direction Rules item 6: “The semantic index (`.wavefoundry/index/`) is a derived artifact — it can always be deleted and rebuilt from source. Nothing outside `server.py` reads it directly.” The plan's new historical observation ledger cannot be reconstructed merely from source without rescanning; deleting its index directory loses recorded skip history. docs/architecture/data-and-control-flow.md:202 also assigns the whole directory to indexer.py, read by server.py and written by indexer.py.

The plan currently nominates only docs/specs/mcp-tool-surface.md as a documentation target. Add bounded updates to the two authority anchors above, and the registered wf_close_wave description at server_impl.py:32635 (already an owned source file). State the scanner publication owner, independent fixed root-local path, reader, and deletion limitation. Missing or empty means “no recorded outstanding guard skips”; it is never proof that every candidate was scanned. This needs no storage redesign.

#### Primer answers

Question 3, deepest review: require the same additive advisory interpretation for success and ordinary gate-blocked responses. A valid ledger with records surfaces paths/reasons in data.scanner_skips; absent/empty ledger surfaces no skip advisory and makes no coverage claim; malformed/unreadable ledger produces an explicit coverage-unavailable advisory, never an empty-success interpretation. None changes pending/suspected classification blocking or confirmed-secret reminders (current spec docs/specs/mcp-tool-surface.md:1269). The added reader neither invokes a scan nor writes scan state; existing close lint remains. State how deletion resets recorded history until subsequent scanner observations. The plan's error requirement and packet family 5 already support this matrix, once their read-only wording is bounded.

Question 1, bounded: the plan already requires affirmative complete outcomes, explicitly including empty text, and retention for cache hits, allowlisting, unreadability, unrelated scans and re-skips. Preserve the raw triple and add explicit internal outcome transport. This is a feasible contract, not an attestation that worker propagation exists. Partial long-line findings must coexist with outstanding coverage. No new blocker from this question.

Question 2, bounded: 1x550 explicitly owns narrow machine-authority policy reuse on non-git fallback, preserves git membership and ordinary .env/generated/lock/lookalike candidates, and excludes arbitrary custom-directory plumbing. Prefer clean-cache prevention evidence across two real scanner/cache passes with exact membership as well as count; do not promise to purge previously polluted caches. Adding an old-cache cleanup obligation would widen this plan.

#### Verification targets and evidence integrity

Add .wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py, especially WaveCloseSecretsGateTests (line 14483), to 1x4om Serialization Points for existing AC-2. Gapfill: tests are excluded from semantic indexing, so scoped rg and sed inspected this class. Its _close helper currently mocks run_validate and run_garden; it is suitable for advisory response serialization, but its mocking cannot establish the real whole-close side-effect claim.

The best alternative remains the small explicit outcome channel and short locked delta merge from the primer; a broader scan manifest or classification workflow is unnecessary.

Selected check was readiness source/contract comparison, completed without unintended skips. Named public boundary was followed through registered close and CLI scanner invocation. Concrete return cases were valid records, missing/empty, malformed and ordinary blocked close. Non-vacuous controls refuted the literal no-scan promise and found an omitted architecture authority; neither relies on future behavior. MCP targeted reads and exact keyword searches were used for production source. No suite, runtime fixture, index build, deletion, network or product edit was performed. Five integrity booleans apply only to this readiness check under seed-209:105–110.

Callable payloads: /tmp/1x5tr-review/docs-contract-reviewer.json (array of two wf_review_event argument objects, each successfully dry-run validated; canonical ledger untouched).

## readiness-performance

### Scanner readiness performance and best-alternative review

Owner: Engineering
Status: active
Last verified: 2026-09-05

Actor: `performance-reviewer`. Context: `1x5tr-performance-independent-20260905-1842`.
Verdict: readiness approved; no blocking finding. This is source-and-plan feasibility
evidence, not delivery execution or a latency measurement. No other seat report was
read; the common packet and adversarial primer were read.

#### Best-alternative brief

The strongest credible alternative is a dedicated skip table in the existing
SQLite index-state store. Transactions would naturally merge disjoint path updates,
avoid rewriting all outstanding records for each publication, and reuse existing
connection machinery. It becomes more attractive with a large outstanding set and
frequent concurrent writers.

It is worse for this wave's authority contract. `IndexStateStore` explicitly owns
derived state: corrupt opens delete and recreate the store, and schema mismatch
resets it (`index_state_store.py:364–418`). Outstanding guard evidence must survive
unrelated work and malformed prior state. Also, `update_secrets_scan` chooses its
cache store from `scan_dir.parent`, whereas the admitted guard authority is fixed
at the repository root even for custom index directories (`scan_secrets.py:251–258`).
Reusing this store safely would therefore require changing its reset lifecycle and
authority-location contract, not merely adding a table. A separate SQLite authority
would avoid reset coupling, but would still add schema and connection machinery
without measured need here.

An append-only JSONL alternative reduces individual append cost, but close must
replay historical skips and retirements, ordering becomes part of the authority,
and compaction needs another crash-safe protocol. It shifts recurring cost to the
operator-facing reader and accumulates history that the requirement does not need.

Retain the admitted path-keyed JSON snapshot with one read/merge/atomic-publication
critical section per scan run. Its cost is proportional to the outstanding set,
not all scanned content or all historical events. This cost is not constant and
has not been measured. No file scanning or worker waiting belongs under the lock.
No full-scanner lock is justified: it would serialize the expensive phase whose
existing full-scan reference is 18.2 seconds on this corpus, and could delay normal
incremental scans behind unrelated work (performance-budget.md, measured budgets).

#### Primer answers

1. Preserve the raw triple but return a small explicit internal outcome per file:
   affirmative completion, guard reasons, or no affirmative observation. The same
   outcome wrapper must feed the serial path, process batch result, and serial
   fallback. Current workers already return cost beside the raw triple, establishing
   a feasible transport seam (`secrets_validators.py:969–992, 1551–1615`). Empty raw
   output cannot prove completion: allowlist, stat/read failure, and binary guards
   return the same shape as empty text (`1039–1089`). Overlong-line status must be
   determined once for the file, independently of whether any rule's keyword filter
   happens to execute its line loop (`1115–1126`). Keep ordinary-line findings and
   mark the overall coverage partial. This adds a linear line-length pass at most,
   not another rules-by-lines pass or another file read.
2. The closed policy census is the two exact paths and four prefix exclusions at
   `indexer.py:574–585`, plus canonical wave events, memory archive bodies, legacy
   memory pointers, and scan findings at `875–936, 1021–1040`. Extract these to the
   lightweight owner, leaving subsequent semantic name/extension/size policy out.
   The scanner's git branch at `secrets_validators.py:182–195` remains intact;
   fallback at `167–180` receives the predicate. Delivery should compare actual
   cache path membership across two clean full passes, as well as counts, and use
   `.env`, lock/generated assets, and noncanonical names as preservation controls.
   This proves prevention in clean fixtures; it does not prove migration cleanup
   of already polluted caches. No extra embedding build is needed for that pin.
3. The new close reader should project known outstanding paths, report malformed
   or unreadable authority as coverage unavailable, and omit advisory for missing
   or empty authority. None of those outcomes changes close eligibility. An empty
   advisory means no recorded skips, not universal coverage. The reader performs no
   scanning and writes no scanner state; whole-close behavior must not be inferred
   from this new reader's narrower contract. The admitted documentation update
   supplies the field and error/lifecycle meaning missing from today's findings-only
   scanner description (`docs/specs/mcp-tool-surface.md:1265`).

#### Readiness controls and limits

Finite packet families selected for source feasibility: 2, 3, 4, 5, 6, and 7.
MCP outlines, targeted reads, and keyword retrieval reached the real scanner entry,
worker/fallback integration, semantic walker, store owner, and published scanner
contract. No suite, index build, network, process fixture, benchmark, mutation test,
or canonical review-ledger write was performed. No test Gapfill was needed. One
initial outline used the wrong scanner path; the admitted Serialization Points
resolved it and all load-bearing reads used the correct owner.

Known-bad readiness control: the tempting premise that the existing SQLite store
can preserve authoritative skips without lifecycle changes is refuted by its
explicit corrupt-open deletion/reset contract. Adjacent legitimate control: the
same source preserves busy/locked state and supports read-only opens; SQLite itself
is not rejected, only reuse of this derived store as unchanged authority. A second
source control refutes empty raw output as affirmative completion by comparing the
allowlist and I/O returns with empty-text scanning. These checks are falsifiable
source comparisons, not executed future behavior.

`SCANNER_VERSION` invalidation already escalates to a real full scan and bypasses
the cache (`scan_secrets.py:242–255`). Bumping it when landing the new reporting
semantics is the existing mechanism for initially populating coverage evidence;
this is feasible without a separate migration or changing cache-hit meaning.

No material plan blocker was established. Implementation and delivery still owe
actual merge/failure injection, worker equivalence, close response controls, cache
membership assertions, and named deletion mutations. The performance judgment is
structural; no new quantitative budget or measured speedup is claimed.

#### Current-plan scope confirmation

Independently reread the corrected plans in the original review context: `1x4om`
git-blob hash `3f8570fe808992efcc7fa52fe20a559506b5880d`, and `1x550` git-blob hash
`c5ffd3a9905e23456755e9a1e8e19229682c214d`. The advisory reader's purity is now
explicitly distinct from existing close validation; persistence failures remain
nonblocking WARNING output. Authority documentation identifies writers, reader,
and history loss on deletion. The existing scanner-version bump provides the
initial full observation pass. Cache guarantees now explicitly cover prevention
in a fresh cache with equal membership and counts, not historical cleanup.
These corrections preserve the storage/performance assessment and readiness
approval, and establish no new blocker. This is a bounded reread by the original
independent reviewer, not a newly spawned review; no implementation or additional
runtime probe was performed.

## readiness-qa-recheck

### QA focused readiness recheck

Owner: Engineering
Status: active
Last verified: 2026-09-05

Verdict: QA approves readiness of the corrected plans. Fresh independent context `1x5tr-qa-focused-recheck-20260905-fresh-c`; no implementation, plan repair or ledger authorship by this reviewer.

Current 1x4om Design confines no scanning/no writes to the new advisory reader, preserves run_validate and record-only docs-lint scanning, and requires WARNING for persistence failures. Current 1x550 Requirement 3 and AC-1/2 explicitly start with a fresh cache, compare membership and count across two passes, and exclude historical cleanup. Independent MCP reads confirmed server_impl.py:19604 invokes run_validate, 4752-4777 executes docs_lint.py, wave_lint_lib/cli.py:262-267 invokes check_hardcoded_secrets(record_only=True), scan_secrets.py:309-318 forwards only explicit removals, and index_state_store.py:3073-3124 upserts candidates and deletes only removed_rel_paths. These paths refute the old broad claims and agree with the revised bounded requirements.

QA-R1 and ARCH-READY-1 are repaired for the QA lane. The known-bad control is a source/plan contract comparison: upserts plus explicit removals contradict unconditional historical cleanup, while the close validation call chain contradicts whole-close purity. The corrected paragraphs distinguish those boundaries. WARNING is now an explicit requirement so advisory persistence failures must not become lint blockers.

All delivery ACs remain unchecked and unverified as implementation. Still required: real worker/fallback guard transport, retention and clear transitions, malformed/failed atomic publication preservation, reader isolation plus success/error propagation retaining validation, machine-authority exclusion census and git controls, two fresh-cache full passes comparing membership/count, and deletion mutations. No runtime probe, close invocation, suite, index build or mutation ran in this focused recheck. The five true integrity declarations attest to this completed readiness source/plan review only.

## readiness-qa

### QA readiness review

Owner: Engineering
Status: active
Last verified: 2026-09-05

Verdict: needs more evidence; two bounded plan-contract corrections precede readiness approval. This fresh isolated QA seat read no other seat outputs. No implementation or delivery approval is asserted.

#### Strongest challenge

A fresh-cache count test can pass while an existing installation retains the pollution described by the rationale. I executed two real `update_secrets_scan(full=True)` calls in a disposable non-git tree with actual SQLite. The first recorded `.wavefoundry/index/old.txt`; the second injected only the proposed index-prefix candidate filter, and that row remained. Candidate selection prevents new rows; it does not migrate old ones. Evidence: `/tmp/1x5tr-review/qa-probe.json`. The intended bounded correction is to state clean-cache prevention explicitly in 1x550 requirements and ACs and disclose historical rows; this review does not request orphan-reconciliation or a cache migration.

QA-R1: **do_now**, required-AC plan contradiction, blocking readiness until corrected. `secret_scan_record` upserts supplied paths and deletes only explicit `removed_rel_paths` (`index_state_store.py:3073–3124`); `update_secrets_scan` forwards only caller removals (`scan_secrets.py:309–318`). This is a real reproducible mismatch between the unconditional AC and candidate-only design, not a newly introduced shipped regression.

QA-R2: **do_now**, public-contract plan contradiction, blocking readiness until corrected. `wf_close_wave_response` calls `run_validate` even in dry-run (`server_impl.py:19604`); `run_validate` executes docs-lint (`server_impl.py:4752–4777`); `_run_full_checks` calls `check_hardcoded_secrets` (`wave_lint_lib/cli.py:262–267`). Therefore the plan sentence “Close only reads the ledger; it must not run scanning or write scan state” must scope this to the **new advisory reader** and explicitly preserve existing validation. Do not suppress established validation to satisfy a literal whole-close assertion. This claim is source-validated, not an executed close test.

#### Primer answers

1. There is no distinguishing observation in the current raw triple. Executed `scan_file_raw` on empty text, an allowlisted ordinary file, and an absent path; all returned `([], None, [])`. An explicit complete/guard/no-outcome channel must survive worker serialization and serial fallback. Long-line partial coverage must dominate completion even when ordinary lines contain findings. Delivery tests must assert ledger retention after cache hits, allowlisting, I/O errors and unrelated scans; empty successful rescan must retire it.
2. The required census is exact authority paths, canonical/legacy index and log/lock prefixes, and all four existing authority predicate families, with `.env`, lockfiles, generated assets, lookalikes and git tracked/untracked controls. I did not execute that whole census in this bounded readiness pass. Two clean-cache real scan passes must compare membership as well as count; historical cache rows must be an explicit limitation under the chosen prevention scope. The independently executed historical-row fixture falsifies an unconditional cleanup claim.
3. Success and ordinary gate-error responses must distinguish a populated outstanding ledger, malformed/unreadable coverage state, and missing/empty recorded state without altering gate status. Wording should say “no recorded outstanding guard skips,” never universal coverage. Scope the no-write/no-scan assertion to the new reader; the existing validation path remains an upstream scanner caller.

#### AC coverage and delivery obligations

- 1x550 AC-1/2: current unconditional wording is unsupported for existing polluted caches; clean-cache scope plus two real full scan passes and membership equality is a feasible prevention contract. AC-3 requires git tracked/untracked preservation controls.
- 1x4om AC-1: feasible explicit outcome transport; four guards, ordinary findings, real worker and spawn-failure fallback remain delivery evidence requirements.
- 1x4om AC-2: feasible read-only advisory helper after scoping correction; success/error response propagation and missing/malformed controls remain unexecuted.
- 1x4om AC-3: execute re-skip, clean-empty, removed, cache-hit, unrelated, allowlisted, unreadable, malformed and atomic-failure transitions; bounded concurrent independent path deltas must merge.
- 1x4om AC-4/5: implementation deletion mutation, new suites and final framework/docs validation remain delivery work. No AC is marked complete by readiness.

#### Executable evidence and limits

Selected fixture families: 3 and 7; source review of 5. All fixture calls completed without skips, using production scanner/cache APIs and realistic non-git filesystem state. The injected candidate filter models the narrow proposed policy; it is not a complete implementation or full authority census. The fixture rule matched its own rules file (one ordinary finding), which did not prevent scanning or SQLite publication; assertions inspect cache paths and raw outcome equality, so that finding is irrelevant to the demonstrated properties. Independent reference: the admitted required AC and public return contract, rather than packet runtime claims.

| Mechanism | Control / mutation | Result |
| --- | --- | --- |
| Candidate-only prevention | Inject candidate filter after baseline pollution, real full scan | Legacy machine row remains; unconditional cleanup claim falsified |
| Outcome distinction | Empty, allowlisted, absent public raw scans | Identical triples; raw-result inference falsified |
| Existing close validation | Targeted production call-chain inspection | Scanner invocation confirmed; runtime close not run |

No source mutation, full suite, live-root scanner/index, network, process-worker, atomic-failure or concurrency probe ran. No landed mechanisms exist yet, so delivery deletion mutations are pending. Gapfill: tests are semantically excluded; scoped shell inspection of `test_secret_scan_cache.py` supplied faithful fixture setup. The MCP source outline/read/keyword path was used for production ownership validation. Substantive work stopped at the packet cap; focused correction replay remains available.

#### Scanner-version migration guidance

Bump the scanner version when implementing durable outcome recording. The independently read `update_secrets_scan` version check (lines 242–247) already forces a full scan on mismatch, so existing content-cache hits will not indefinitely prevent first publication of historical guard skips. This uses the existing version contract without a cache schema change. Delivery must pin one prior-version cache fixture: first invocation escalates and records guards, next unchanged cache hit retains them. This is implementation guidance, not an additional readiness blocker or an executed version-migration test.

#### Rotating performance alternative — QA weighing

The performance seat's alternative is existing SQLite for cheaper transactional updates. From QA's perspective, that couples durable outstanding coverage evidence to the cache's corruption/schema-reset lifecycle and custom scan-directory routing, while the admitted contract requires fixed-root durable history. Separate SQLite would avoid some coupling but introduce another schema and migration test surface without measured need. An append-only journal adds replay, truncation and compaction cases. Prefer the small path-keyed JSON ledger with a short read/merge/atomic-publish lock and no lock during scanning. Pin prior-byte preservation on malformed state/publication failure and one concurrent distinct-path merge. This is a design tradeoff assessment, not a measured performance result or new execution evidence. QA-R1 and QA-R2 remain pending their focused correction replay; this addendum does not reverify edited plans.

## readiness-security-recheck

### Security Readiness Recheck

Owner: Engineering
Status: active
Last verified: 2026-09-05

Verdict: approved. Severity: none. Actor: security-reviewer; fresh independent current-plan assessment, no repair implementation.

Reviewed both current wave-owned plans and readiness packet. The controlling actor remains the trusted local operator; no remote, multi-user, or untrusted-repository promotion is proposed. No credible attacker authority delta or exploit chain was identified.

The revised 1x4om Design confines the new advisory reader to reading the fixed root-local guard ledger. It explicitly preserves existing close validation, confines persisted data to relative paths and guard reasons/details without source or secrets, requires WARNING-only publication failures, and preserves malformed prior bytes. Missing or deleted history explicitly does not attest to complete scanning. Complete outcomes require affirmative scan completion; allowlisting, unreadability and cache hits retain history. The scanner version bump addresses observation of previously cached candidates.

Independent MCP targeted reads confirm server_impl.py:19604 calls run_validate in both close modes; server_impl.py:4761-4776 invokes docs_lint.py; wave_lint_lib/cli.py:262-267 invokes the record-only scanner. This refutes the known-bad whole-close no-scan/no-write claim and confirms why the repaired reader-only boundary matters. No runtime public close call was executed.

The 1x550 plan explicitly limits cache guarantees to fresh-cache prevention, excludes migration, retains git candidate behavior and preserves ordinary secret-bearing file classes. Packet cases 5 and 7 match the repaired boundaries.

No new implementation exists to attest to confinement enforcement or regex interpolation. Planned fixed-root confinement is acceptable for readiness; implementation path checks remain delivery work. Symbol extraction/re.escape behavior is unchanged in the bounded plans. No exploit chains identified. No blocking findings or new threat assumptions.

Limitations: source/plan readiness review only; no runtime probe, suite, concurrency test or future behavior attestation. Known-bad detection is the source-refuted whole-close purity claim. Only this review artifact and the coordinator payload were written; no plans, source or canonical ledger edited.
