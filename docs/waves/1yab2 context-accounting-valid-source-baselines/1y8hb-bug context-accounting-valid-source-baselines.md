# Exclude Invalid Sources From Context Estimates

Change ID: `1y8hb-bug context-accounting-valid-source-baselines`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-17
Wave: 1yab2 context-accounting-valid-source-baselines

## Rationale

Brief: give developers credible, clearly qualified context-efficiency figures. Exclude binary/runtime storage from source-text credits, and make the whole-file baseline explicit without changing retrieval behavior or introducing token-provider integration. Success is that querying or inspecting an index never earns its entire database size as avoided text, and no interface presents the proxy as measured model usage savings.

Wave `1y9sv review-event-operator-identity` displayed 115714942 saved tokens. The local ledger contained one `plan-1` credit of 113050624 for `.wavefoundry/index/index.sqlite`, identified by the SHA-256 of its repository-relative path. That is about 98% of the displayed total. `context_efficiency.measure_source_proofs` estimated the whole source using `ceil(size_bytes / 4)`; source version proof did not establish text eligibility or a plausible alternative read. Its opaque source-credit record does not identify which original invocation supplied the credit, so the originating adapter still needs tracing rather than guessing.

The operator authorized a wave-local correction before closure. The exact credit was zeroed transactionally, retaining its key, original value and reason; standard projection and close then sealed the corrected result. [Audit](../1y9sv%20review-event-operator-identity/evidence/context-accounting-correction.json) and [review note](../1y9sv%20review-event-operator-identity/evidence/delivery-review.md) retain the evidence. The closing estimate was 3792818 after further review/closure calls. Removing the invalid credit does not establish that the remainder represents actual savings.

## Requirements

1. Credit only eligible source text represented by the retrieval result. A storage container, cache, archive, executable or other binary/runtime artifact is not source text merely because a result names its path or a proof confirms its file size/version. Cover instrumented MCP retrieval and first-party tool accounting through the same eligibility rule. A SQLite query may represent canonical source documents; it must never credit the containing database as their textual baseline.
2. Explicitly reject known framework storage and sidecars, including index.sqlite, retired index-state.sqlite, memory-state.sqlite, telemetry stores, WAL/SHM/journals and legacy vector-store artifacts. Also reject recognizable binary content outside those paths, including renamed SQLite fixtures, using the bounded prefix check. This is a conservative local heuristic, not a promise to detect every binary payload with an arbitrary text-looking prefix. Do not rely solely on the current index filename or an arbitrary credit cap. Use one shared source check: reject known binary/runtime paths, then inspect at most a small fixed byte prefix when no reusable text evidence exists. No whole-file reads, cache, schema or dependency changes solely for telemetry. A bounded UTF-8/NUL check must handle a multibyte character split at the prefix boundary. Uncertain eligibility earns no positive credit and must not make retrieval fail.
3. Preserve existing request/response debits and retry/phase deduplication. Keep the baseline against whole eligible files explicitly qualified: a partial result is not proof that an agent otherwise would have read the whole file, and separate phase/version credits are not proof of repeated avoided reads. This change does not invent a more realistic numerical savings baseline.
4. Use **Estimated context avoided** for the existing source-byte proxy in wave tables, dashboard and operator guidance; describe its whole-file baseline nearby. Do not call it measured token, monetary or billed-usage savings. Keep any separately evidenced paired-evaluation component distinguishable, with its actual method and quality limits. Preserve legacy persisted field readability; avoid an unrelated schema/API-key migration just to change labels.

## Scope

**In scope:** source-credit eligibility and its producer adapters; estimate terminology and baseline disclosure; focused regression coverage and documentation.

**Out of scope:** search/reranker/index architecture changes, token billing integrations, invented provider usage, new dashboards, arbitrary per-file caps as the fix, changes to identity attribution, and any history correction, reconciliation, backfill or rewriting of historical wave accounting. The one-off 1y9sv correction is already complete; its existing audit stays as-is. No repair kits or full-database backup artifacts are needed for this plan.

## Acceptance Criteria

- [x] AC-1: A public producer-path regression representing index.sqlite yields zero database source credit while retaining call debits. Real small SQLite fixtures, renamed binaries, WAL/SHM and representative runtime/archive artifacts cannot create positive source-text credit.
- [x] AC-2: Legitimate text results still receive the intended qualified credit; repeated same-version/phase results deduplicate and costs remain counted. Metadata-only paths and failed/uncertain classification earn no credit; the underlying retrieval result remains usable.
- [x] AC-3: Newly rendered wave output, also displayed by the dashboard, calls the proxy Estimated context avoided and explain the whole-file baseline. Existing closed-wave wording and persisted records remain readable without rewriting them; no surface claims the proxy measures billed tokens or dollars. Tests distinguish paired evidence from the proxy.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; no failure elsewhere is attributable to this change. An in-memory known-bad control restoring database credit is caught through a real producer path.

## Tasks

- [x] Trace the relevant source-credit producers and reproduce the database-credit path.
- [x] Implement one shared eligibility decision in measure_source_proofs with bounded prefix inspection and explicit binary/runtime exclusions.
- [x] Update wave/dashboard wording and method disclosure without unnecessary persisted-field churn.
- [x] Add real SQLite/binary and valid-text producer fixtures, repeat-call controls and a known-bad mutation.
- [x] Update accounting architecture, public surface docs and canonical seed guidance; render affected local surfaces under the seed gate.
- [x] Run independent code, QA and docs-contract review; run the framework suite last and verify the receipt before closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| accounting | implementer | producer trace | Shared eligibility rule |
| presentation | implementer | accounting contract | Labels and bounded disclosure |
| verification | independent reviewers | frozen implementation | Code, QA and docs-contract; targeted mutations |

## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/seeds/110-wave-memory-bootstrap.prompt.md`
- `docs/references/context-efficiency.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/prompts/create-wave.prompt.md`

Coordinator owns shared accounting and checkpoint rendering. Documentation work is disjoint; reviewers are read-only. Render create-wave guidance from its canonical carrier. Dashboard already displays wave Markdown, so no dashboard code changes. Existing checkpoint wording remains accepted by exact legacy-render validation; numeric/state consistency checks stay strict. No history correction or closed-wave rewrites.

## Affected Architecture Docs

Update the existing accounting method/telemetry description in the architecture and public tool documentation: source eligibility, whole-file baseline, and distinction from paired measurement. The canonical overview is docs/architecture/data-and-control-flow.md. No ADR is needed: storage and authority are unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevent the observed binary-database inflation |
| AC-2 | required | Preserve useful accounting and retrieval behavior |
| AC-3 | required | Explain what the metric actually supports |
| AC-5 | required | Demonstrate the changed boundaries |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-17 | Planned after operator-authorized correction and closure of 1y9sv; no estimator source changed or implementation started | Linked audit; measure_source_proofs and source_credit ledger inspection |

| 2026-09-17 | Operator narrowed scope: remove history correction requirements, AC-4, task and correction machinery; retain the completed one-off audit only | Operator direction: keep this simple |

| 2026-09-17 | Prepare discovery: shared measure_source_proofs covers retrieval and first-party state credits; dashboard reads wave Markdown. Narrowed targets; bounded prefix check and exact legacy-render acceptance cover binary/label cases without history machinery | context_efficiency.measure_source_proofs; ProcessTelemetry.record_tool_cost; server _STATE_SOURCE_EXTRACTORS; checkpoint_validation_errors |

| 2026-09-17 | Readback / Thought: AC1/2 shared bounded source check, AC3 exact old/new display acceptance and honest label, AC5 targeted producer controls and full verification. SQLite8192byte example must credit0 instead of2048; legitimate text/retry/debits unchanged. No history correction. Memory brief found no applicable schema change since this wave changes no columns. | Current readiness approvals and successful activation |

| 2026-09-17 | Implemented shared binary/runtime exclusions plus bounded UTF-8/NUL sniff; preserved text credit, debits and phase dedup. Generated carrier rendered; legacy wording accepted exactly without historical edits. | Real registered code_read SQLite and renamed SQLite controls; checkpoint tamper test |
| 2026-09-17 | Independent code/QA review repaired incomplete UTF-8 at exact 4096-byte EOF using existing stat size. Docs review removed stale captured-only fallback wording. Final focused review: 10 tests, zero skips; known-bad real producer bypass produces two expected failures (2048 versus zero). | Independent QA context identity_delivery_qa; docs consistency context accounting_surface_census |

| 2026-09-17 | Final validation: 59 accounting, 96 public accounting and 125 renderer tests pass in the full runner. Full docs lint passed with no errors or warnings; diff whitespace check clean. All scoped ACs met. | Full run 9152 tests / 17 skips; sole failure outside changed code described below |
| 2026-09-17 | Verification blocker: unchanged test_techdocs_audit_lib.test_a_segment_local_pattern_skips_the_ancestor_walk takes 219 ms and 222 ms versus 150 ms in two full parallel runs; isolated test passes in 54 ms. Do not weaken it or manufacture a receipt. Current green receipt remains stale. Final task stays unchecked pending full-suite proof before closure. | /private/tmp/1yab2-full-tests-final.log; /private/tmp/1yab2-full-tests-confirm.log; no native Windows/Linux execution |

| 2026-09-17 | Closure verification complete: unchanged full suite with Python -X cpu_count=2 passed 9152 tests, 17 skips, 97 files in 654.908 seconds. Receipt result ok and inputs hash independently matches current framework. Prior timing blocker resolved through lower concurrency; no assertion or limit changed. Independent delivery approvals and operator closure authorization recorded. | .wavefoundry/framework/test-cache.json; /private/tmp/1yab2-close-tests.log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-17 | Select source eligibility plus honest labels | Addresses invalid baseline directly without claiming unmeasured savings | Cap credits: hides the error and arbitrarily distorts valid text. Remove all accounting: avoids the claim but discards useful bounded telemetry. Provider billing integration: cannot establish the counterfactual and adds unrelated complexity |
| 2026-09-17 | Preserve legacy field readability; no historical correction feature | The affected wave is already corrected; future-credit prevention needs no history machinery | Rename every stored/API key now: unnecessary compatibility work |

## Risks

| Risk | Mitigation |
| --- | --- |
| Extension-only exclusion misses renamed binaries or extensionless source | Verify content/type evidence at producer boundary and test both cases |
| Accounting adds expensive I/O or blocks search | Reuse serving evidence, bounded fallback, no positive credit on uncertainty |
| Remaining proxy still interpreted as real savings | Explicit whole-file baseline, distinct labels, no dollar claim |

## Session Handoff

Prepared, reviewed and implementing. Shared source checks and labels are complete; all scoped tests and docs validation pass. A current matching full-suite receipt is green; closure is authorized. See docs/agents/session-handoff.md.
