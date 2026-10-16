# Windows path limits, BOM, read-only and shim diagnostics

Change ID: `20qru-bug windows-path-and-diagnostic-fixes`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20qrv windows-review-follow-ups`

## Rationale

This change contains bounded diagnostic and compatibility fixes inferred from current source; it does not claim all six original reports were reproduced on Windows. Long-path failures need conditional hints while normal missing parents remain absent. UTF-8 BOM input should parse without changing the mapping reader's non-raising failure contract. Read-only targets need a distinct diagnostic. Shim discovery should explain refusal rather than introduce shell execution. A chmod failure is safe to ignore only if the actual new descriptor already has the intended mode.

The warm-up claim is withdrawn: run_tests._BYTECODE_WARM_CODE ignores compileall.compile_dir's Boolean return, and a False result does not produce the claimed nonzero child exit. Warm-up path skipping/reporting is deferred pending demonstrated need. No new reporting transport, blanket 260-character skip, timing threshold or warm-up change is admitted.

## Requirements

1. Preserve normal absent handling for WinError2 and short missing-parent WinError3/NotADirectoryError. For WinError3 on a path beyond the legacy limit without established long-path capability, report unreadable with a conditional long-path hint, not a proven OS-setting diagnosis. EINVAL remains unreadable with a possible reserved/invalid-name hint. No registry mutation or automatic path rewriting.
2. Defer warm-up changes: the alleged compileall-return failure is disproven by current code; run_tests.py is outside this implementation scope.
3. Decode workflow_include_prefixes input with utf-8-sig. Preserve its mapping-only, never-raises contract for malformed JSON and existing validation surfaces unchanged. Do not promise or add a new diagnostic channel from this reader in this wave.
4. Before Windows replacement retries, distinguish a known READONLY target from a sharing/in-use failure and return the existing permission diagnostic with a specific reason. Preserve the original target; cleanup may make only the owned temporary writable as necessary. Do not publish a writable replacement first and repair its permissions later. Unknown or unprovable permission state remains a refusal.
5. Keep executable trust policy unchanged: do not execute uv.cmd or uv.bat. When a shim-only PATH is found, report its safely rendered name and the existing exact hash-pinned bootstrap guidance. uv.exe discovery and bootstrap authorization are unchanged.
6. Tolerate a named fchmod failure (EPERM, EACCES/PermissionError or ENOTSUP) only when fstat on the actual new descriptor proves its permission bits already equal the intended final mode. Comparing only the old target's mode is insufficient. Otherwise preserve the original and fail, removing only the owned temporary; do not relax unrelated errors or compare after publication.
7. Native Windows and WSL2/drvfs behavior remains unverified. Name operator probes and distinguish source-grounded hypotheses, synthetic tests and actual platform results.

## Scope

**Problem statement:** bounded diagnostic and compatibility gaps; unsupported warm-up claim deferred.

**In scope:**

- `.wavefoundry/framework/scripts/record_paths.py`, `review_evidence.py` (errno classification)
- `run_tests.py` warm-up is explicitly deferred; no source edits
- `.wavefoundry/framework/scripts/workflow_include_prefixes.py`
- `.wavefoundry/framework/scripts/contained_files.py` (read-only cause, fchmod tolerance)
- `.wavefoundry/framework/scripts/setup_index.py` (`uv` shims)
- Focused tests per admitted item

**Out of scope:**

- Enabling long paths or rewriting paths with the extended-length prefix
- The reparse and junction rule (change `20qrs`) and the lock scan (change `20qrt`)

## Acceptance Criteria

- [x] AC-1: Long-path WinError3 produces unreadable plus conditional hint; short missing-parent WinError3 and WinError2 preserve absence; EINVAL is unreadable with a possible invalid-name hint. No platform-setting success claim.
- [~] AC-2: Warm-up skip/count remedy intentionally deferred during 2026-10-15 readiness: actual child returns success when compile_dir returns False, so the stated failure premise is unsupported. No timing or cache-warmup changes in this wave.
- [x] AC-3: BOM JSON yields declared prefixes; malformed JSON retains the existing non-raising empty mapping behavior. No new reader diagnostic surface is claimed.
- [x] AC-4: Windows READONLY is distinguished from sharing violation with the existing diagnostic class and specific reason; original target is unchanged, owned temporary cleaned, no publish-first permission change.
- [x] AC-5: Shim-only uv.cmd/uv.bat PATH is refused with safe shim name and exact bootstrap guidance; uv.exe behavior and trust checks are unchanged, no command-script execution added.
- [x] AC-6: Named fchmod failure succeeds only when actual new-fd permission bits already match intended final mode; umask-induced mismatch and changed/executable/read-only modes refuse before publication and preserve original bytes/mode. Unrelated errors still fail.
- [x] AC-7: Focused tests and authored docs pass with no attributable regression; native qualification limitations remain explicit.

## Tasks

- [x] Add focused regressions for admitted items 1, 3, 4, 5 and 6, including permission and missing-parent negatives.
- [x] Implement only conditional diagnostics, BOM parsing, owned-temp permission handling and shim refusal guidance.
- [x] Verify actual new-fd mode before tolerating named chmod errors; no publish-first mode repair.
- [x] Document deferred warm-up claim and native Windows/drvfs operator probes; no runtime result invented.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Five bounded fixes | Implementer | Readiness | Single owner; independent sites |
| Delivery review | QA, required reviewers | Five bounded fixes | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/workflow_include_prefixes.py`
- `.wavefoundry/framework/scripts/contained_files.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/native-windows-support.md`

## Affected Architecture Docs

N/A. Diagnostics and tolerance at six sites; no boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Silent loss of a wave |
| AC-2 | important | Explicitly deferred: failure premise disproven |
| AC-3 | important | Silent config loss |
| AC-4 | important | Wrong diagnosis |
| AC-5 | important | Setup refusal on shim hosts |
| AC-6 | important | Unverified drvfs path |
| AC-7 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from Windows source review; no native execution claimed | Current source |
| 2026-10-15 | QRV-RD5/RD6/RD7 bounded permission proof, deferred unsupported warm-up, and narrowed diagnostics/shim contract. | Bounded readiness repair; owning requirements and ACs |

| 2026-10-15 | Readback: preserve missing-parent behavior and permission boundaries while adding conditional long-path hints, BOM input, readonly/sharing diagnostics, uv shim refusal guidance and proof of actual temporary descriptor mode. No warm-up or shim execution changes. Setup/BOM files first; permission and errno files serialize after 20qrs predicate edits. | AC-1,3–7; admitted plan and current-source MCP reads |

| 2026-10-15 | Implemented conditional long-path/invalid-name diagnostics, BOM parser, explicit non-executing shim guidance, pre-publication readonly refusal and new-fd mode proof. Five new diagnostics tests and 132 record/fail-closed controls passed. Setup module: 203 tests, two mocked-bootstrap fixture permission failures passed when rerun with access to their temporary tool-venv files. Four mutants detected removed mode proof, readonly refusal, long-path distinction and BOM parsing. | test_platform_diagnostics_followups; setup/record tests; native execution not claimed |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Group the bounded diagnostics; defer unsupported warm-up remedy | Current source disproves the stated child-exit premise | New reporting machinery without a demonstrated failure rejected |
| 2026-10-15 | Preserve shim execution refusal and provide existing bootstrap guidance | No new shell or trust boundary needed | cmd/bat execution rejected for this wave |
| 2026-10-15 | Prove actual replacement descriptor mode before tolerating chmod failure | Old target mode does not determine umask-filtered new-file mode | Silent failure or post-publication chmod rejected |

## Risks

| Risk | Mitigation |
| --- | --- |
| Platform oracle differs from host | Conditional diagnostics and explicit native probes |
| Permission tolerance weakens publication | Actual descriptor mode proof before replacement; retain original on mismatch |
| Shim detection becomes execution | Detection/refusal only; existing bootstrap path |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
