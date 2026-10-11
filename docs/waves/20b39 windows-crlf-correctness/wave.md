# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20b39 windows-crlf-correctness`
Title: Windows Crlf Correctness

## Objective

Make the upgrade and docs-lint paths correct on Windows checkouts: CRLF wave records and managed docs no longer break review-evidence reprojection or the review-policy parity check, the storage migration no longer fsyncs a read-only handle, and a leading BOM no longer hides Owner metadata. Driven by field feedback from a 1.15.4 to 1.28.0 Windows upgrade.

## Changes

Change ID: `208l3-bug crlf-safe-review-evidence-and-parity`
Change Status: `implemented`

Change ID: `20b31-bug fsync-readonly-handle-windows-storage-migration`
Change Status: `implemented`

Change ID: `20b32-bug docs-lint-leading-bom-owner-metadata`
Change Status: `implemented`

## Participants

- Coordinator: Engineering (implementing agent under operator direction)
- Write-owning roles: implementer (all three changes)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-10

## Wave Summary

Wave `20b39` (Windows Crlf Correctness) delivered 3 changes: CRLF-Safe Review Evidence Reprojection and Parity Check, Storage Migration fsync on a Read-Only Handle Fails on Windows, and Docs-Lint Misreads Owner Metadata After a Leading BOM. Notable adjustments during implementation: CRLF-Safe Review Evidence Reprojection and Parity Check: Product Intent: waived (bug fix, no product scope; default applied by the planning agent, not yet confirmed by the operator); CRLF-Safe Review Evidence Reprojection and Parity Check: Round-2 readiness repair: dropped the server_impl wrapper (universal-newline read), added end-marker `\r` and whole-block newline handling, scoped the drift claim to the owned region, named test files and fixture construction; Storage Migration fsync on a Read-Only Handle Fails on Windows: Product Intent: waived (bug fix, no product scope; default applied by the planning agent, not yet confirmed by the operator).

**Changes delivered:**

- **CRLF-Safe Review Evidence Reprojection and Parity Check** (`208l3-bug crlf-safe-review-evidence-and-parity`) — 9 ACs completed. Key decisions: Fix at the readers and the compare (tolerate and preserve newlines), not by normalizing files on disk; Treat the Review Evidence regex and the parity compare as one change
- **Storage Migration fsync on a Read-Only Handle Fails on Windows** (`20b31-bug fsync-readonly-handle-windows-storage-migration`) — 5 ACs completed. Key decisions: Open the staged file `r+b` for fsync on all platforms
- **Docs-Lint Misreads Owner Metadata After a Leading BOM** (`20b32-bug docs-lint-leading-bom-owner-metadata`) — 7 ACs completed. Key decisions: Strip the BOM at the shared read helpers
## Watchpoints

- Watchpoint: the Windows failures are taken from the field report and are unreproduced on macOS; tests emulate Windows semantics (CRLF fixtures, a mode-recording fsync stub) rather than assuming a Windows host.
- `208l3` and `20b32` both add tests to `tests/test_docs_lint.py`: serialize `20b32` after `208l3`. `20b31` is independent of both.
- `208l3` keeps the LF-only `events.jsonl` contract by decision; a CRLF ledger is still refused, with an explicit message.
- `208l3` does not preserve CRLF on the `server_impl.py` Prepare publish path: it reads universal-newline text and keeps rewriting a CRLF wave.md as all-LF, recorded as a decision and pinned by a test. The newline rule is "CRLF if any CRLF present", so one stray CRLF restores a whole file as CRLF (pinned by a fixture).
- `20b31` tests must not sit in a class gated on the native APSW runtime, or they skip and pass vacuously; the seam is named in the change.
- `20b32` must settle the Prepare and lifecycle-gate Owner path, because the field symptom included `wf_prepare_wave` failing; a fix in a bypass reader file is a scope addendum.
- Product Intent is waived for all three changes (bug fixes, no product scope), recorded in each Progress Log.
- The review-policy digest covers change docs, so any further edit to them after readiness requires re-Prepare.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 40 | 204,093 |
| implement | 278 | 1,728,322 |
| review | 234 | 2,077,183 |
| **Total** | **552** | **4,009,598** |

<!-- wave:context-efficiency-state {"generation":571,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":278,"content_source_credit":2024827,"derived_artifact_credit":971,"direct_net":1728322,"estimated_tokens_saved":1728322,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14275,"response_debit":290187,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6986},"plan":{"calls":40,"content_source_credit":245253,"derived_artifact_credit":1170,"direct_net":204093,"estimated_tokens_saved":204093,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5226,"response_debit":46305,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9201},"review":{"calls":234,"content_source_credit":2627110,"derived_artifact_credit":412,"direct_net":2077183,"estimated_tokens_saved":2077183,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13758,"response_debit":539437,"source_credit_count":92,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":552,"content_source_credit":4897190,"derived_artifact_credit":2553,"direct_net":4009598,"estimated_tokens_saved":4009598,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33259,"response_debit":875929,"source_credit_count":184,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":19043},"wave_id":"20b39 windows-crlf-correctness"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 48 | 0 | 26 | 28,461,278 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":26,"estimated_exploration_avoided":28461278,"surfaced_events":48} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

### Implementation allocation — 2026-10-10

Readied wave activated after the isolated pvqp pack finished. One generic implementer owns all three changes in order: 208l3 newline projection/parity and tests, 20b31 writable migration flush and portable real-callsite tests, then 20b32 leading-BOM metadata/cache and bounded reader census. Shared test_docs_lint edits are serialized. Scope is admitted scripts/tests and corresponding changelog; trust boundaries are immutable review-ledger/carrier interpretation and staged storage cutover, without a ledger format, database schema or Prepare newline-policy change. Existing pre-edit LF baseline is preserved from the actual producer. Parent memory briefing has no needs_reverification advisory; apply producer/validator equivalence, operator-owned byte preservation and named guard-mutant guidance. Requested implementer gpt-6.1-sol/high, observed runtime identity unknown. Native Windows proof remains simulated. Canonical suite runs after bookkeeping is frozen, followed by fresh independent required code/QA and council delivery review, then pause for operator closure. No new permanent evidence folder.

### Implementation evidence — 2026-10-10

Implemented the three admitted changes in order: CRLF-tolerant evidence headings and normalize/restore upgrade payloads, carrier-wide newline replacements preserving outside bytes and exact parity; writable staged-file flush at both real migration sites; then exactly one leading BOM removed before either shared read cache. The captured pre-edit LF byte fixture remains unchanged. Prepare publication still emits LF and CRLF event ledgers are still refused. Nineteen new methods passed their focused runs without skips; named old-behavior/guard mutants failed for headings, upgrade payload restoration, owned-region newlines, exact parity, writable descriptors and single-leading-BOM stripping.

Focused named modules passed: review_evidence 192, review_policy 111, render_agent_surfaces 165, server_tools_lifecycle 621 (2 existing skips), sqlite_storage_migration 127 (1 existing skip), storage_upgrade_resume 14 and docs_gardener 24. The storage resume run uses the existing tool venv and child PATH; a bare-Python attempt without numpy is excluded as behavior evidence. The docs_lint log reports 1,223 tests OK and docs-lint: ok; its transferred process exit code was unavailable, so the canonical run supplies the integration proof. Every implementation task is checked; only the combined test/document-validation AC remains pending for each change, to be completed by the coordinator after canonical integration.

The BOM bypass census is recorded in 20b32's Progress Log with the clarified bounded dispositions: raw first-line status, lifecycle record/policy section, carrier structural/parity and gaps-summary parsers retain their existing BOM exposure outside the shared-helper Owner repair. No bypass parser source changed. Native Windows has not run; descriptor validity is simulated through both actual staging paths with writable positive and EBADF negative controls. Source and bookkeeping are handed off frozen for the coordinator's refreshed readiness, canonical suite and independent delivery review. No close, commit or package was performed.

### Focused readiness refresh — 2026-10-10

Current receipt `review-policy-7e9fe1da3b0ff5f90f1a` was approved after clarifying 20b32's existing bounded raw-reader disposition and correcting its Prepare source route. No source/API/format scope changed. The chair ran a bounded standard red-team primer, independent architecture/code, QA, security and reality seats, followed by rotating docs-contract review. All seats found no blocker; anonymous merit synthesis preceded attribution. The strongest challenge was an unsupported claim of universal raw-reader BOM tolerance. The optional full-Prepare alternative was weighed by all fixed seats and adds integration evidence beyond the admitted metadata oracle, without becoming a new requirement.

QA's active, lookup-proven deletion control failed the Owner-first assertion; the chair's real first-status control returned None raw and active through the shared reader. Invalid preliminary controls were excluded. Source and normalized plan regions stayed unchanged. Current code/QA/council readiness approvals were recorded through the typed tool, and Prepare-ready passed. These facts establish readiness only; canonical and fresh delivery review remain pending. Temporary seat reports and captures are not retained as repository evidence folders.

### Canonical integration repair — 2026-10-10

The first isolated run found the structural patch census rejecting the new forbidden cache-read mock: its deliberate unused path lacked the required explanation. A separate 15-test file run reproduced that exact failure. The admitted test now binds the mock, explains why a cache hit must not call it, and asserts no call. Production and the structural audit are unchanged. Both named cache/census tests pass; an active cache-miss control retaining the real mock lookup fails specifically at the no-call assertion (one failure, no errors/skips). The original snapshot stays unchanged while its remaining files finish; its failed run is not qualification evidence. A fresh canonical run must cover the repaired test tree before delivery review.

The completed first run executed 12,153 tests across 181 files with 12 skips in 1,190.524 seconds and exited 1. Its second failure was the declaration census: each retained pre-edit LF baseline literal needs its own reasoned fixture classification. The actual baseline/projection checks passed. Add adjacent classification comments without changing either byte string or any assertion; keep both audit rules intact. Both repairs belong to the admitted tests. This run remains failed, with no new green receipt.

### Canonical qualification — 2026-10-10

The repaired isolated snapshot passed all 12,153 tests across 181 files with 12 existing skips in 1,196.734 seconds, exit 0. Both previously failing audit files passed, as did all named change suites. The runner wrote a genuine receipt at 21:12:38 UTC for framework inputs `ec35ebdfac85b72577a69498da7fb9a9d850cee84fbb078cf1a6b99dbdbc9864`; root and snapshot hashes were verified before transferring that receipt byte-for-byte (SHA256 `0632143416ab3dffb1a7735c74742dc008e4af29af46f41b8981a8e49f257b8b`). Full docs validation passed. All AC/task checkboxes and member implemented statuses are reconciled; independent delivery authority is still pending.

Fresh delivery chair and isolated specialist/council contexts review the frozen current tree. Requested gpt-6.1-sol/high fits the bounded implementation and test-oracle review; observed runtime identity is unknown. Existing canonical proof is reused rather than rerunning whole modules per seat. Seat controls and reports remain temporary; the final verdict belongs here and in the typed ledger. Native Windows remains unrun, and the local pvqp pack still precedes this wave.

### Delivery review — 2026-10-10

Full delivery council PASS. A fresh five-stance red-team primer preceded independent architecture/code (one disclosed combined context), QA, security and reality seats, followed by rotating docs-contract review. Each seat found no admitted blocker. The strongest challenge concerned LF ledger authority and overly broad BOM/CRLF interpretations. The rotating alternative was a separate, configured-root LF checkout pin for event ledgers; all four fixed seats weighed effective attributes, operator policy, nested roots and already-converted worktrees, and retained approval. Anonymous merit synthesis preceded attribution; agreement was unanimous with no material disagreement or concrete finding. Introductory aspirational goals were distinguished from the explicit bounded requirements and current shipped claims.

Required code review ran 17 selected methods without skips and verified live-globals upgrade, both actual staged-flush and metadata/cache/fallback mutants. Independent QA mapped all 21 ACs and priorities, ran all 19 new methods without skips, preserved both captured LF literals and detected four active old-behavior controls, including the cache no-call assertion. Security's permissive-reader mutant failed the real CRLF-ledger refusal; reality verified real metadata and cache lookups. The chair's own ordinary/record one-BOM controls passed, while double-BOM and injected old record decoding produced the expected Owner findings. An invalid copied-global mutation was excluded before a corrected, lookup-preserving control was credited. No full suite or module was repeated by reviewers.

Code, QA and council-delivery approvals are current typed authority; only operator signoff remains. All 11 source identities and the genuine framework receipt stayed unchanged across review. Chair/code/QA captured their own before/after identities; security lacked its own pre-probe capture and reality used the supplied initial identities, bounded by the chair's complete freeze checks. An optional auto-removed temporary Git checkout demonstration involved no commit/push or root/global Git writes and was excluded from load-bearing approval. Native Windows, complete public Prepare execution, broad raw-parser BOM normalization, ledger checkout policy and release archive qualification remain outside the delivered proof. No required AC deferral and no unresolved finding remains. No unique memory candidate was added; routine proof is consolidated here and the immutable ledger, with temporary controls/reports outside the repository.

Implementation and review are complete. Pause for operator-owned closure; proceed to readied 20b3a without closing, committing, pushing or rebuilding the local pack.
