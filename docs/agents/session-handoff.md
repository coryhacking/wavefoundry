# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-11

## Current Session

**Active wave:** `1xq4f dashboard-lifecycle-integrity` — implementing.
**Last closed wave:** `1xny6 unified-index-database` — shared semantic/graph publication, safe source-rebuilt migration, and bounded in-memory preparation.

The operator approved targeted `files=` preservation (`1x81v`) alongside dashboard
lifecycle repair (`1xpo1`) and four shared-index compatibility findings (`1xoye`).
The three-change wave passed Prepare, specialist readiness and council review and
is open. Implementation and delivery review are complete. All six required
specialist lanes and the targeted council approve. One architecture-prose defect
was repaired and independently reverified in cycle 1; runtime source did not
change during delivery review. The canonical 8,898-test receipt (12 intentional
skips) still matches the framework tree. Consolidated reports, probe sources and
limits are in `delivery-review.json`, with typed authority in `events.jsonl`.
Memory proposal produced zero candidates. Operator signoff and closure remain pending. The operator subsequently authorized
a commit and local 1.24.0 test package.
Preserve the pre-existing uncommitted `1xny6` work.

## Last closed wave — 1xny6

Semantic and graph content now share `.wavefoundry/index/index.sqlite` and one publication transaction. Graph migration rebuilds from current source, verifies in a fresh process, then retires owned old artifacts. Memory remains separate. Preparation uses a 64 MiB retained-operation budget with lazy owned-filesystem overflow; small builds create no preparation artifacts. Large replay RSS can increase.

All ten delivery findings are repaired and independently reverified. The canonical suite passed 8,871 tests (12 intentional skips); the receipt matches the frozen framework tree. Complete real-model incremental deltas measured 12.02 s median versus 12.05 s baseline. The full delivery council passed unanimously. Live MCP recovery completed with schema 8, exact coverage, zero stale paths and semantic retrieval without fallback. Evidence, mutations, measurement limits and independent reports remain in the wave's existing delivery-review.json and runtime-qualification.json. Native Windows/Linux/macOS Intel package execution is still release gate G4, not demonstrated by mocks or wheel availability.

Memory checkpoint is complete. The durable timing lesson is recorded in `1xoyl-mem measure-acquired-writer-intervals-and-freeze-per-run-timing-`: measure acquired writer time after BEGIN returns through COMMIT return, separate acquisition wait, and freeze each timing record before reuse. The current request authorizes a local test package and commit; release publication and push remain unauthorized.

## Open questions / Deferred decisions

- Graph-expansion/reranking quality comparison (evaluation AC-4) remains intentionally deferred after the baseline deadline stop; current retrieval ordering remains unchanged.

- Native Windows/Linux/Intel execution remains release follow-through; local qualification and dependency wheel coverage do not prove it.
- Investigate MCP's initial `graph_rebuilt=false` notice on an all-content full rebuild: this observed run did execute graph maintenance. The final graph and semantic publication were healthy.
- The CoreML reranker probe fell back to CPU after `output_features has no value for logits`; embedding used CoreML acceleration and semantic retrieval passed. No reranker fix was included in this closure.
- Any other unfinished povc receipt must retain its original archive. Qualified revision-2 repair: `/Users/coryhacking/.wavefoundry/dist/povc-storage-rebuild-repair-v2.zip`; instructions/evidence are retained with that artifact. Completed destinations use normal upgrades.

## Operator test-receipt override

The operator waived a full-suite rerun for the framework README clarification only. The receipt preserves the original 8,898-test results and run timestamp, records the tested and accepted hashes plus `tests_rerun: false`, and accepts the current tree. Reversing only that sentence in memory reproduced the original tested hash exactly; no other framework changes are covered.

## Local 1.24.0 test package

Built `1.24.0+ppd0` at `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.24.0.ppd0.zip`. Archive integrity, all 196 framework members, packaged changelog and VERSION/manifest parity verified. SHA-256: `949998194a7892392439df00f13395e219d5e42df78d0dff39acc63e4a417078`. The test runner reused the explicitly authorized README-only receipt override; no suite rerun was claimed. Sensor `ac_asserts_repository_state` (introduced in `1wur7`) remains advisory; no polarity flip is included. Native package qualification remains pending. Wave `1xq4f` remains open; closure was not requested.
