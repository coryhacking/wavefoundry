# Exclude Windows Virtual Environments from the Secrets Scan

Change ID: `1uhfx-bug windows-virtualenv-secrets-scan-exclusion`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-08-04
Wave: `1uhfy windows-secrets-scan-scope`

## Rationale

The framework secrets scanner normalizes Windows paths to forward slashes, but its shipped virtual-environment exclusion only recognizes `venv/lib/...`-style paths. A native Windows `.venv/Lib/site-packages/...` tree is therefore scanned when it is selected by the scanner, potentially starting many worker processes and reading a large dependency tree. The semantic and graph walker already prune virtual environments, but not Graphify's default output directory; this change keeps the scanner and index walker away from their respective generated/dependency trees.

## Requirements

1. The shipped scanner path allowlist must exclude dot-prefixed Windows virtual-environment library trees such as `.venv/Lib/site-packages/package/module.py` before the scanner reads the file.
2. The scanner must exclude Graphify's documented default generated-output directory, `graphify-out/`, before reading its derived artifacts.
3. The corresponding Betterleaks prefilter and the active Python-scanner allowlist must retain the same exclusion semantics.
4. The exclusions must remain narrowly limited to virtual-environment library trees and the exact default Graphify output directory; ordinary project source files must remain scannable.
5. The shared semantic-and-graph repository walker must prune the exact default `graphify-out/` directory before it descends into the directory.

## Scope

**Problem statement:** The virtual-environment regex does not recognize the dot-prefixed Windows venv layout, so the secrets scanner can traverse an entire dependency environment.

**In scope:**

- Update the duplicate virtual-environment path pattern in `.wavefoundry/framework/scan-rules.toml` to accept an optional leading dot.
- Exclude the default `graphify-out/` directory in the same two rule representations.
- Add regression coverage for `.venv/Lib/site-packages/...`, the existing POSIX venv form, Graphify output, and normal-source non-matches.
- Keep the inactive Betterleaks prefilter and active Python allowlist synchronized.
- Add `graphify-out` to the shared index-walker directory exclusions; the normal incremental index update must reap any previously indexed artifacts.

**Out of scope:**

- Additional semantic-index or graph-walker exclusions beyond the exact default `graphify-out/` directory; those already prune `.venv` by directory name.
- Arbitrary custom Graphify output directories set through `GRAPHIFY_OUT`; a project can ignore those through its own scan rules or Git ignore policy.
- Changing scanner worker counts, scheduling, file-size guards, or Git/non-Git file selection.

## Acceptance Criteria

- [x] AC-1: The shipped active allowlist matches `.venv/Lib/site-packages/package/module.py` and therefore skips it before file content is read.
- [x] AC-2: The equivalent POSIX `venv/lib/python3.11/site-packages/package/module.py` path remains excluded, while `src/module.py` remains scannable.
- [x] AC-3: The shipped active allowlist matches `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`, while `src/graphify-output.ts` remains scannable.
- [x] AC-4: The Betterleaks prefilter and active allowlist contain equivalent venv and Graphify-output exclusion semantics.
- [x] AC-5: The shared repository walker prunes `graphify-out/` before descending into it, while ordinary `src/graphify-output.ts` remains eligible; one normal incremental `content=all` update removes previously indexed Graphify artifacts from both semantic and graph state.
- [x] AC-6: Focused scanner and indexer tests, the framework test suite, and docs validation pass.

## Tasks

- [x] Change the two virtual-environment path patterns in `scan-rules.toml` to recognize dot-prefixed venv directories.
- [x] Add the exact default `graphify-out/` path rule to both `scan-rules.toml` representations.
- [x] Extend the existing shipped-allowlist tests with Windows, POSIX, Graphify-output, and normal-source cases.
- [x] Add the shared index-walker exclusion and incremental-removal regression coverage for Graphify output.
- [x] Verify the prefilter/allowlist and scanner/indexer boundaries, then run the required checks.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Rules and tests | implementer | — | One small, serialized configuration-and-test change. |
| Verification | qa-reviewer | Rules and tests | Exercise the actual allowlist matcher, index walker, and full suite. |

## Serialization Points

- `.wavefoundry/framework/scan-rules.toml` contains both representations of the rule; update them together in one patch.
- The existing incremental removal path must remove the prior Graphify artifacts from both semantic and graph state; do not introduce a walker-version rebuild for this subtractive filter.

## Affected Architecture Docs

N/A — this is a configuration correction and regression test within the existing secrets-scanner boundary; it does not change architecture, control flow, or supported-platform policy.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents the reported Windows venv scan. |
| AC-2 | required | Preserves existing coverage and prevents an overbroad path rule. |
| AC-3 | required | Prevents duplicate scanning of Graphify's documented generated output. |
| AC-4 | important | Prevents the two shipped rule representations from drifting. |
| AC-5 | required | Prevents Graphify output from consuming semantic or graph-index resources without imposing a full rebuild. |
| AC-6 | required | Confirms the correction is safe to ship. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-04 | Change created from native-Windows field report; causal check separated the secrets scanner from the graph walker. | `scan-rules.toml`, `secrets_validators.py`, `indexer.py` review. |
| 2026-08-04 | Scope expanded to exclude Graphify's documented default output directory. | Graphify README documents `graphify-out/` as its default generated-artifact home. |
| 2026-08-04 | Implemented the rule changes and focused regression coverage. | `test_secrets_validators.py`: 146 tests passed. |
| 2026-08-04 | Scope extended to exclude Graphify's default output from the shared semantic-and-graph walker. | The scanner-only exclusion does not control index-walker traversal. |
| 2026-08-04 | Replaced the proposed walker-version rebuild with an incremental-removal proof. | An incremental build compares the prior metadata to the new walker result and propagates removed paths into semantic and graph reconciliation. |
| 2026-08-04 | Verified incremental Graphify removal. | `test_indexer.py`: 289 tests passed; seeded old Graphify output was removed from metadata, semantic rows, and graph state by one incremental build. |
| 2026-08-04 | Completed final verification. | `run_tests.py`: 6,820 tests across 62 files passed; focused scanner and indexer coverage passed, and docs validation passed. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-08-04 | Add an optional dot to the existing venv-directory pattern, and exclude the exact default `graphify-out/` directory, in both shipped representations. | The venv edit covers `.venv/Lib/...` after slash normalization; Graphify documents `graphify-out/` as its generated-artifact home. Neither edit changes scanner flow or adds a configuration concept. | (1) Add a Windows-only second venv rule — works but duplicates semantics. (2) Exclude arbitrary Graphify output locations — rejected: custom `GRAPHIFY_OUT` paths are project-owned and a global pattern would be overbroad. (3) Change the walker — rejected: it already excludes venv directories and is not the faulty path. |
| 2026-08-04 | Add the exact default `graphify-out` directory to the shared index walker without changing its version. | A normal incremental build detects prior Graphify paths as removed and reaps them from semantic and graph state, so a full rebuild would be unnecessary work. | (1) Force a walker-version rebuild — correct but needlessly expensive for this subtractive filter. (2) Rely on Git ignore — insufficient because Graphify output may intentionally be committed. (3) Exclude arbitrary custom output locations — rejected as overbroad. |

## Risks

| Risk | Mitigation |
| --- | --- |
| The optional-dot edit overmatches ordinary source. | Pin a normal-source non-match beside both Windows and POSIX positive cases. |
| The inactive prefilter drifts from the active scanner behavior. | Test and update both copies together. |
| A default Graphify rule hides a user-created source directory. | Match the exact `graphify-out` directory segment only, with a normal `graphify-output` source-path control. |
| Existing indexes retain Graphify artifacts after the rule changes. | Regression-test one normal incremental update against a fixture seeded with the former Graphify output; it must reap semantic and graph state. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
