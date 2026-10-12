# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-10-12

## Current Session

**Active wave:** none; implemented waves `20gz3 uv-release-bootstrap` and `20gz5 child-log-timeout-check` are paused. Follow-up `20h6q combined-log-tail-check` / change `20gz6` is admitted and planned, not readied or implemented. No tests are running.

**Last closed:** `20gx1 distribution-test-fixtures`. This closure batch also completed `20gfj qualification-bookkeeping`, `20gfk bounded-runtime-reads` and `20gx0 bounded-upgrade-diagnostics`: routine recording preserves qualification, runtime reads and retained diagnostics are bounded, and distribution fixtures own their baselines. All admitted ACs and tasks are complete, required independent approvals and explicit operator signoffs are recorded, and no review finding remains unresolved. Both edit gates are closed.

**Done:** Operator approved uv 0.12.17. Wave 20gz3 was readied and its pin/hash constants and changelog were updated; exact 18-wheel inventory, real wrong-hash refusal/disposable installation and 203 setup tests pass. The operator separately authorized updating the shared local tool-venv uv, now verified at 0.12.17; other users are not forced to update. Independent delivery code/security approvals are recorded.

**Next:** Official 1.29.0 is published. Waves 20gz3 and 20gz5 remain paused pending explicit closure; follow-up 20h6q is planned. Do not retry timing checks or implement the follow-up without a new task.

**Files touched:** setup_index.py bootstrap constants; test_child_tee.py large-log timeout fixture; CHANGELOG.md; waves 20gz3/20gz5 and handoff. Both source changes are implemented; all edit gates are closed.

**Test state / blockers:** The operator explicitly requested follow-up wave 20h6q for the log-tail fixture, then authorized release now. Wave 20gz3 AC-3 records the release-only qualification exception with [~]. The declared failure occurred in the unchanged nonzero-exit leg: both per-stream in-memory endings passed; combined capped log retained OPENING, elision and FINAL-STDERR but omitted FINAL-STDOUT. The test assumes each stream ending survives combined-tail truncation. Exact scheduling was not captured; no further timing investigation or source repair is authorized for this release.

**Qualification:** Final source hash `7ed6f72bf5f7df9eb7940d2f5039f915634c10d145f54598c409b960b6dcabac`. Default: 12,402 tests/185 files/12 skips, green receipt. Second: all 12,394 tests/185 files completed, 28 skips, one warm-estimator p95 assertion failure. Declared: all 12,402 tests/185 files completed, 12 skips, one log-tail marker assertion failure. Both profile reports are complete but red; canonical comparisons refuse them. Independent read-only audits of the unmodified reports confirm 16 correctly marked second-profile extra skips and exact declared/default skip IDs/reasons. Full docs validation and git diff --check pass. Durations under concurrent machine load are not performance conclusions.

**Evidence / memory:** Durable outcomes and limitations remain in each wave record and authoritative ledger, with admitted change docs and canonical regression tests. No permanent evidence folder or duplicate readiness artifact was created. Bounded memory proposals returned no eligible candidates; the retrospective lessons already live in canonical docs and tests. Scanner coverage remains limited for recorded binary/compressed artifacts and one overlong vendored line; this is advisory, not complete scan coverage.

**Published feature pack:** Release `1.29.0+pw75`, `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.29.0.pw75.zip`, 10,499,587 bytes, SHA256 `1faa86e3c5615c2ba5e6c21af18e536b15e74e92ea54e894cc5b772cdbab2bb7`. GitHub asset size/digest match. Archive CRC, safe unique paths, bridge entry, all 248 corresponding framework files, stamped VERSION, prompt manifest and embedded changelog verified. Changes from reviewed candidate pw6p are only VERSION and upgrade-protocol build metadata, including nested bridge payloads. Runtime guard ships; tests/bootstrap/qualification caches do not.

**Official release:** [GitHub v1.29.0](https://github.com/coryhacking/wavefoundry/releases/tag/v1.29.0) published 2026-10-12T21:34:14Z, neither draft nor prerelease. Both approved qualification exceptions are disclosed in the release notes. Online npm verification passed for all three vendored libraries; uv 0.12.17 has 18 exact eligible wheel hashes. Default receipt remains green; the two complete red alternate-profile reports remain preserved.

**Offline model release asset:** `/Users/coryhacking/.wavefoundry/dist/wavefoundry-models-3.zip`, 351,495,236 bytes, SHA256 `3a7cfb7b14ff5c60d00dc24819b7bddb5a6beacdb9d79c38ead476e49b82cc7d`. GitHub asset size/digest match. Canonical manifest, all 15 payload hashes and Apache-2.0/MIT notices verified. Model set 3 and fingerprint `wf-model-set-2-20260811-arctic-s` unchanged; no model download.

**Publication:** Operator explicitly authorized committing and pushing everything and creating the real GitHub release. Source commit `f8537e1a` and release-stamp commit `d20ed5f4` were pushed; annotated tag `v1.29.0` resolves to `d20ed5f4`. Four closed waves, uv/bootstrap and timeout-fixture work, planned follow-up 20h6q, docs and version stamps are committed. This final documentation update records publication; no framework source changed after qualification.

**Other pending work:** Older unadmitted plans `1p30y`, `1p310`, `1rolq`, `1rppn`, `1rtar`, `1wq0b` remain outside this task. Generic Rust turbofish extraction remains a disclosed coverage limit; native Windows, complete Rust/Cargo resolution and live consumer/index qualification were not performed.

## Open questions / Deferred decisions

Native Windows removal qualification and exact-release-archive qualification remain unverified follow-ups. The five previously reported non-default-profile upgrade-test failures are resolved, independently reviewed and closed in wave 203ha. No downstream Waveforge integration or new live Claude qualification was performed.

The crash-dialog investigation identified deliberate child-process SIGSEGV tests for isolation, CPU fallback and fatal-stack diagnostics; the supplied report matched that fixture pattern without exact PID correlation. A separate proposed change would use quieter routine process-death controls while retaining synthetic SIGSEGV parsing and explicit fatal-stack qualification. No test coverage or system CrashReporter preference was changed.

For 1yp0y, the operator emphasized accurate, visible diagnosis as the primary objective whenever python3 cannot run properly; distinguish evidence from suspected causes and provide a next step even when repair is unavailable. Repair mechanisms remain secondary. The operator also added a standard-user enterprise constraint: no default admin, Store or Developer Mode dependency. Prefer existing approved Python and permitted user-level repair; a user-local python3.exe launcher requires qualification before endorsement. Policy-blocked repair must stop with an actionable IT handoff while preserving mandatory python3 and unready status.

No deferred AC or task in 1yq6a. Earlier-wave follow-ups remain below; none was undertaken as part of this formatting fix.

No unfinished AC or task in 1ymzq. Broader search/WaveIndex, lifecycle/registrar extraction, server-free dashboard control and graph-language extractors remain separate work as recorded in wave Watchpoints. Native Windows and published-package qualification were not performed in this wave.

The historical default-policy eligibility re-add/reap loop is repaired by closed wave `204jj` / change `2038p`. Wave `20dkg` delivery verification reconfirmed six setup argv modes, detached docs/code child routes, MCP rebuild/refresh and rendered-hook bare launch shapes against the common layer-prefix reader. Three existing scratch tests pass; setup → incremental → setup converges, historical leaked test rows are removed once without later embedding, and eligible folded docs/docstrings/code remain. The unchanged corpus oracle rejects a runtime-only historical forward with “setup build: framework test rows in chunks_docs.” These are scratch/source results, not live-index, native-Windows or every-eligibility-fault qualification. `1ymzk`'s measured benefit remains removal of approximately 187 policy-ineligible test paths rather than extraction; its invalid receipt dispositions and original historical records remain unchanged. Explicit manual opt-in flag persistence and stray historical Progress Log bookkeeping remain separate work. Current delivery authority is recorded in `20dkg`'s typed review ledger.

Automatic reuse of a full-class embedding model on CPU remains outside this wave; the shipped guard preserves the index and reports compatible-provider or explicit-rebuild remedies. Waveforge owns its merge-time chunker version/invalidation verification and terminology-key remap; no downstream integration ran here.
