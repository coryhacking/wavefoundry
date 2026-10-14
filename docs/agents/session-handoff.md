# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-10-14

## Current Session

**Active wave:** none. Waves `20nju optional-tensorwell-inference`, `20lul tensorwell-memory-reranking` and `20lkx test-suite-runtime` are closed.

**Last closed:** `20lkx test-suite-runtime` — removed 896 inherited test repetitions and bounded ordinary scanner fixtures while preserving unique coverage and the explicit checkout audit.

**Done:** Optional qualified Tensorwell inference now covers embedding, normal reranking and memory reranking before local model construction, with bounded startup, strict identity checks and preserved local fallback. All required reviews and closure gates passed. Wave folders retain only their wave/change records and authoritative ledgers.

**Next:** Commit the completed work, then produce an operator-confirmed 1.31.0 local test pack before new implementation. No official release or push is requested. Incoming private feedback remains outside committed records.

**Local packaging exception:** Operator explicitly approved retaining verified `uv==0.12.17` for this 1.31.0 local test pack on 2026-10-14. PyPI confirms all 18 recorded wheel hashes; the newer eligible 0.12.18 is deferred. This exception waives only the pin bump, not source/profile qualification or archive checks.

**Test state:** Current framework receipt is green for 11,609 tests / 187 files / 12 existing aggregate skips, 627.384 seconds, hash `b240480388326e02c42685eb78d282f68a335f98d052027b6326a2a6f655bae4`. Both close mutations verified it; full docs validation passed. Performance timings are observational on a contended host. Raw logs remain temporary and edit gates are closed.

**Open questions / Deferred decisions:** Further test scheduling and per-test profiling remain follow-ups. Three completed-review MCP servers retained host pipe connections and were stopped under explicit operator instruction; host connection cleanup and intermittent idle CPU work remain unimplemented follow-ups. Last setup assessment reported changed setup inputs; recheck readiness before relying on indexed retrieval. No setup or index rebuild was performed by this close.

**Official release:** [v1.30.0](https://github.com/coryhacking/wavefoundry/releases/tag/v1.30.0), build `1.30.0+pwgi`, tagged at `624c7f62d77ae28820de009a4ad4aa0baf87184a`. GitHub confirms a published, non-prerelease release with both assets uploaded. `wavefoundry-1.30.0.pwgi.zip`: 10,538,661 bytes, SHA-256 `f60cd13394bd352b3a06433e4f20aa4aa19686d3982a0957437a38b498004f2b`. `wavefoundry-models-3.zip`: 351,495,236 bytes, SHA-256 `10727d5324507acffa2a6c4459b1bdbc01e65252581dd8000d18fca92f65f291`. GitHub asset sizes and digests match the verified local archives. Feature CRC, safe paths, source parity, nested feature/bridge integrity, and model manifests, file digests, revisions and licenses passed; docs validation passed. This verifies archive contents and publication, not a downstream installation of this exact release.

**Privacy:** Source feedback and identifying downstream details remain private and outside committed records or external messages.

**Local test pack:** `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.30.0.pwg7.zip`, 10,538,653 bytes; SHA-256 `d52ae0e9606c35046813f68238e92cd2078e532b6f4fabb70a2f3d713e146521`. ZIP CRC, unique safe paths, 249 matching source files, changelog/version, nested feature parity and bridge digest checks passed. Internal composition files were removed; only the operator-facing archive remains for this build.

**Packaging qualification:** Default: 12,471 tests / 185 files / 12 skips. Renamed profile: 12,463 tests / 185 files / 28 skips, including 16 explicitly default-profile-only skips. Declared profile: 12,471 tests / 185 files / the same 12 exact skips. Both deterministic comparisons passed against source hash `83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520`. Reports remain in the ignored qualification cache as `package-1.30.0-20k-default.json`, `package-1.30.0-20k-second-retry.json` and `package-1.30.0-20k-declared-retry.json`. Initial concurrent profile attempts failed; the child runners did not inherit the outer two-worker flag. Sequential retries with inherited `PYTHON_CPU_COUNT=2` passed with no source edits, deadline changes or waivers. This is not a timing diagnosis. At the local-pack check, uv 0.12.17 was the newest eligible 21-day-mature cross-platform pin; all 18 wheel hashes and the three vendored npm packages verified against their registries. No undecided advisory sensors remain.

**Release policy exception:** For official 1.30.0 only, the operator explicitly chose to retain the tested `uv==0.12.17` bootstrap pin after 0.12.18 became eligible under the 21-day rule. The 18 pinned wheel hashes still match PyPI. This waives only the packaging step-3 pin bump; source/profile checks, docs validation, model verification and archive checks remain required. Existing user environments are not upgraded by this pin.

## Open questions / Deferred decisions

- Timing investigation and threshold changes remain deferred while other reviews run on this computer. Previous local-pack timing waivers applied only to their named artifact.
- Runtime reload work in 20jo3 remains separate; this batch does not expand reload guarantees.
- Current-user attribution means the local OS process account, not authenticated human identity. Lifecycle callbacks cover four selected completion paths only.

## Open questions / Deferred decisions

Field follow-up reports the 1.30.0+pw8f upgrade completed and the repeated guide notice is absent. The copied invalid-lock probe confirms apply refuses before discovery and preserves the lock; valid pending-run continuation was not field-tested. The dry-run contradiction and scanner scope gap are now repaired in closed waves 20kfq and 20kfr with isolated public-path controls; the updated implementation has not yet been tested in that field repository. The reported AGENTS.md defect was omitted from the pasted feedback; clarification is pending.

20h8h timing reassessment remains deferred by operator instruction because concurrent reviews are running. Subsequent packaging qualification and one diagnostic also hit timing assertions under concurrent load; they do not settle the deferred assessment. No timing thresholds changed, and no further timing probes or automatic suite reruns are planned.

Native Windows removal qualification and exact-release-archive qualification remain unverified follow-ups. The five previously reported non-default-profile upgrade-test failures are resolved, independently reviewed and closed in wave 203ha. No downstream Waveforge integration or new live Claude qualification was performed.

The crash-dialog investigation identified deliberate child-process SIGSEGV tests for isolation, CPU fallback and fatal-stack diagnostics; the supplied report matched that fixture pattern without exact PID correlation. A separate proposed change would use quieter routine process-death controls while retaining synthetic SIGSEGV parsing and explicit fatal-stack qualification. No test coverage or system CrashReporter preference was changed.

For 1yp0y, the operator emphasized accurate, visible diagnosis as the primary objective whenever python3 cannot run properly; distinguish evidence from suspected causes and provide a next step even when repair is unavailable. Repair mechanisms remain secondary. The operator also added a standard-user enterprise constraint: no default admin, Store or Developer Mode dependency. Prefer existing approved Python and permitted user-level repair; a user-local python3.exe launcher requires qualification before endorsement. Policy-blocked repair must stop with an actionable IT handoff while preserving mandatory python3 and unready status.

No deferred AC or task in 1yq6a. Earlier-wave follow-ups remain below; none was undertaken as part of this formatting fix.

No unfinished AC or task in 1ymzq. Broader search/WaveIndex, lifecycle/registrar extraction, server-free dashboard control and graph-language extractors remain separate work as recorded in wave Watchpoints. Native Windows and published-package qualification were not performed in this wave.

The historical default-policy eligibility re-add/reap loop is repaired by closed wave `204jj` / change `2038p`. Wave `20dkg` delivery verification reconfirmed six setup argv modes, detached docs/code child routes, MCP rebuild/refresh and rendered-hook bare launch shapes against the common layer-prefix reader. Three existing scratch tests pass; setup → incremental → setup converges, historical leaked test rows are removed once without later embedding, and eligible folded docs/docstrings/code remain. The unchanged corpus oracle rejects a runtime-only historical forward with “setup build: framework test rows in chunks_docs.” These are scratch/source results, not live-index, native-Windows or every-eligibility-fault qualification. `1ymzk`'s measured benefit remains removal of approximately 187 policy-ineligible test paths rather than extraction; its invalid receipt dispositions and original historical records remain unchanged. Explicit manual opt-in flag persistence and stray historical Progress Log bookkeeping remain separate work. Current delivery authority is recorded in `20dkg`'s typed review ledger.

Automatic reuse of a full-class embedding model on CPU remains outside this wave; the shipped guard preserves the index and reports compatible-provider or explicit-rebuild remedies. Waveforge owns its merge-time chunker version/invalidation verification and terminology-key remap; no downstream integration ran here.
