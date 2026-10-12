# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-10-12

## Current Session

**Active wave:** none; implemented waves `20gz3 uv-release-bootstrap` and `20gz5 child-log-timeout-check` are paused. Follow-up `20h6q combined-log-tail-check` / change `20gz6` is admitted and planned, not readied or implemented. No tests are running.

**Last closed:** `20gx1 distribution-test-fixtures`. This closure batch also completed `20gfj qualification-bookkeeping`, `20gfk bounded-runtime-reads` and `20gx0 bounded-upgrade-diagnostics`: routine recording preserves qualification, runtime reads and retained diagnostics are bounded, and distribution fixtures own their baselines. All admitted ACs and tasks are complete, required independent approvals and explicit operator signoffs are recorded, and no review finding remains unresolved. Both edit gates are closed.

**Done:** Operator approved uv 0.12.17. Wave 20gz3 was readied and its pin/hash constants and changelog were updated; exact 18-wheel inventory, real wrong-hash refusal/disposable installation and 203 setup tests pass. The operator separately authorized updating the shared local tool-venv uv, now verified at 0.12.17; other users are not forced to update. Independent delivery code/security approvals are recorded.

**Next:** Independent QA/release/council delivery checks passed under the explicit release exception and their approvals are recorded; all implementation tasks are complete. Operator authorized release with both alternate-profile exceptions deferred. Feature/model assets are built and verified; source commit is the remaining operator-owned prerequisite for the clean-tree release workflow. Do not retry timing checks or implement follow-up 20h6q in this release.

**Files touched:** setup_index.py bootstrap constants; test_child_tee.py large-log timeout fixture; CHANGELOG.md; waves 20gz3/20gz5 and handoff. Both source changes are implemented; all edit gates are closed.

**Test state / blockers:** The operator explicitly requested follow-up wave 20h6q for the log-tail fixture, then authorized release now. Wave 20gz3 AC-3 records the release-only qualification exception with [~]. The declared failure occurred in the unchanged nonzero-exit leg: both per-stream in-memory endings passed; combined capped log retained OPENING, elision and FINAL-STDERR but omitted FINAL-STDOUT. The test assumes each stream ending survives combined-tail truncation. Exact scheduling was not captured; no further timing investigation or source repair is authorized for this release.

**Qualification:** Final source hash `7ed6f72bf5f7df9eb7940d2f5039f915634c10d145f54598c409b960b6dcabac`. Default: 12,402 tests/185 files/12 skips, green receipt. Second: all 12,394 tests/185 files completed, 28 skips, one warm-estimator p95 assertion failure. Declared: all 12,402 tests/185 files completed, 12 skips, one log-tail marker assertion failure. Both profile reports are complete but red; canonical comparisons refuse them. Independent read-only audits of the unmodified reports confirm 16 correctly marked second-profile extra skips and exact declared/default skip IDs/reasons. Full docs validation and git diff --check pass. Durations under concurrent machine load are not performance conclusions.

**Evidence / memory:** Durable outcomes and limitations remain in each wave record and authoritative ledger, with admitted change docs and canonical regression tests. No permanent evidence folder or duplicate readiness artifact was created. Bounded memory proposals returned no eligible candidates; the retrospective lessons already live in canonical docs and tests. Scanner coverage remains limited for recorded binary/compressed artifacts and one overlong vendored line; this is advisory, not complete scan coverage.

**Local pack:** Release candidate `1.29.0+pw6p`, `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.29.0.pw6p.zip`, 10,499,586 bytes, SHA256 `e766964f6334d33a5db1ed7e0365aed6087114563145dda365ca16acb80bea5a`. Archive CRC, safe unique paths, bridge entry, all 248 corresponding framework files, stamped VERSION, prompt manifest and embedded changelog verified. Runtime guard ships; tests/bootstrap/qualification caches do not. No intermediate bridge artifacts remain. Prior pw55 is superseded for this task.

**Official release preparation:** Operator approved 1.29.0 and release with two documented profile exceptions. Online npm verification passed for all three vendored libraries; uv 0.12.17 has 18 exact eligible wheel hashes. Default receipt remains green and the canonical runner reused exact detail after packaging. Final feature/model assets pass structural/hash checks. GitHub v1.29.0 does not yet exist; no commit, push or publication has occurred.

**Offline model release asset:** `/Users/coryhacking/.wavefoundry/dist/wavefoundry-models-3.zip`, 351,495,236 bytes, SHA256 `c3de8d60e8dd55dd6c357f8256af4748a90b089ec92d6c677671b22c56030142`. Canonical manifest, all 15 payload hashes and Apache-2.0/MIT notices verified. Model set 3 and fingerprint `wf-model-set-2-20260811-arctic-s` unchanged; no model download.

**Publication:** Last pushed source/build baseline is `7738e5c8`. Four closed waves, uv/bootstrap and timeout-fixture work, planned follow-up 20h6q, docs and version stamps remain uncommitted. Release is authorized; AGENTS.md retains its explicit source-commit approval rule. The clean-tree release command will create a fresh final version stamp and release assets after that source commit.

**Other pending work:** Older unadmitted plans `1p30y`, `1p310`, `1rolq`, `1rppn`, `1rtar`, `1wq0b` remain outside this task. Generic Rust turbofish extraction remains a disclosed coverage limit; native Windows, complete Rust/Cargo resolution and live consumer/index qualification were not performed.

## Open questions / Deferred decisions

Native Windows removal qualification and exact-release-archive qualification remain unverified follow-ups. The five previously reported non-default-profile upgrade-test failures are resolved, independently reviewed and closed in wave 203ha. No downstream Waveforge integration or new live Claude qualification was performed.

The crash-dialog investigation identified deliberate child-process SIGSEGV tests for isolation, CPU fallback and fatal-stack diagnostics; the supplied report matched that fixture pattern without exact PID correlation. A separate proposed change would use quieter routine process-death controls while retaining synthetic SIGSEGV parsing and explicit fatal-stack qualification. No test coverage or system CrashReporter preference was changed.

For 1yp0y, the operator emphasized accurate, visible diagnosis as the primary objective whenever python3 cannot run properly; distinguish evidence from suspected causes and provide a next step even when repair is unavailable. Repair mechanisms remain secondary. The operator also added a standard-user enterprise constraint: no default admin, Store or Developer Mode dependency. Prefer existing approved Python and permitted user-level repair; a user-local python3.exe launcher requires qualification before endorsement. Policy-blocked repair must stop with an actionable IT handoff while preserving mandatory python3 and unready status.

No deferred AC or task in 1yq6a. Earlier-wave follow-ups remain below; none was undertaken as part of this formatting fix.

No unfinished AC or task in 1ymzq. Broader search/WaveIndex, lifecycle/registrar extraction, server-free dashboard control and graph-language extractors remain separate work as recorded in wave Watchpoints. Native Windows and published-package qualification were not performed in this wave.

The historical default-policy eligibility re-add/reap loop is repaired by closed wave `204jj` / change `2038p`. Wave `20dkg` delivery verification reconfirmed six setup argv modes, detached docs/code child routes, MCP rebuild/refresh and rendered-hook bare launch shapes against the common layer-prefix reader. Three existing scratch tests pass; setup → incremental → setup converges, historical leaked test rows are removed once without later embedding, and eligible folded docs/docstrings/code remain. The unchanged corpus oracle rejects a runtime-only historical forward with “setup build: framework test rows in chunks_docs.” These are scratch/source results, not live-index, native-Windows or every-eligibility-fault qualification. `1ymzk`'s measured benefit remains removal of approximately 187 policy-ineligible test paths rather than extraction; its invalid receipt dispositions and original historical records remain unchanged. Explicit manual opt-in flag persistence and stray historical Progress Log bookkeeping remain separate work. Current delivery authority is recorded in `20dkg`'s typed review ledger.

Automatic reuse of a full-class embedding model on CPU remains outside this wave; the shipped guard preserves the index and reports compatible-provider or explicit-rebuild remedies. Waveforge owns its merge-time chunker version/invalidation verification and terminology-key remap; no downstream integration ran here.
