# One link classification: refuse name surrogates, pass other reparse points, catch junctions

Change ID: `20qrs-bug reparse-tag-and-junction-classification`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20qrv windows-review-follow-ups`

## Rationale

Current sites disagree between refusing every reparse attribute and checking only POSIX symlinks or two known Windows tags. Cloud and dedup metadata need not be links, but an unknown name-surrogate tag can still redirect. The existing two-tag helper is therefore a baseline to repair, not a universal correct predicate. Microsoft defines the name-surrogate bit independently of its current tag list. Native cloud, dedup and drvfs behavior has not been qualified here.

## Requirements

1. Refusal classification is true for S_ISLNK or a Windows reparse tag with the generic name-surrogate bit (0x20000000), including known symlink/mount tags and unknown surrogate tags. A reparse attribute with absent, invalid or unusable tag metadata fails closed at refusal boundaries; an explicit valid non-surrogate tag is not a link. POSIX stat objects without Windows metadata retain S_ISLNK behavior.
2. Replace the listed bare-attribute and bare-S_ISLNK decisions consistently while preserving regular-file, containment, identity and size checks. No guarantee of cloud hydration follows from tag classification.
3. Keep contained_files' no-framework-import boundary: reuse a standalone predicate where imports permit, otherwise retain exact small copies pinned by parity tests. Extend parity to lifecycle_lock._is_link_entry and all actual copies; the lock helper's two-tag rule must change too.
4. Cover contained_files._judge_existing/open_contained_dir; wave_lint_lib.helpers.doc_entry_is_regular; render_agent_surfaces._is_link_or_reparse; bytecode_cache.is_linked; review_evidence authority guard; record_paths._has_symlink_component/_refusal_exempt/_list_subdirs/open_container_scope; upgrade_wavefoundry._retired_sidecar_path_error; lifecycle_lock._is_link_entry.
5. Native Windows, OneDrive, dedup and drvfs execution remain unverified. Do not promise detection of links when the host exposes no link metadata; document that boundary as an uncertainty, not a blanket claim about every drvfs mount.

## Scope

**Problem statement:** inconsistent Windows link classification across modules added this month.

**In scope:**

- `.wavefoundry/framework/scripts/contained_files.py` (no-follow branch, `open_contained_dir`)
- `.wavefoundry/framework/scripts/wave_lint_lib/helpers.py` (`doc_entry_is_regular`)
- `.wavefoundry/framework/scripts/render_agent_surfaces.py` (`_is_link_or_reparse`)
- `.wavefoundry/framework/scripts/bytecode_cache.py` (`is_linked`)
- `.wavefoundry/framework/scripts/review_evidence.py` (authority guard)
- `.wavefoundry/framework/scripts/record_paths.py` (four sites)
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` (`_retired_sidecar_path_error`)
- Tests with an `nt` stat oracle carrying `st_file_attributes` and `st_reparse_tag`

**Out of scope:**

- The lifecycle lock scan identity algorithm (change `20qrt`); predicate parity is in scope here
- Hydration state of OneDrive files or any OneDrive-specific handling beyond the tag rule

## Acceptance Criteria

- [x] AC-1: Valid non-surrogate regular-file tag oracles pass ordinary read/lint/render/cache classification while regular-file, cap and containment guards remain effective; no native cloud hydration claim.
- [x] AC-2: Known junction/symlink tags, an unknown surrogate tag, and reparse attributes lacking usable tag metadata are refused at every named refusal site with the existing diagnostic class. POSIX symlinks remain refused.
- [x] AC-3: Parity covers every predicate copy including lifecycle_lock and detects an injected two-tag-only or all-reparse implementation with exact expected outcomes.
- [x] AC-4: Existing POSIX refusal tests pass unchanged; explicit non-surrogate cases do not weaken unrelated checks.
- [x] AC-5: Focused tests and authored docs pass with no attributable regression; platform simulation and native qualification limits are explicit.

## Tasks

- [x] Build the `nt` stat oracle fixture once in the test support module.
- [x] Add failing tests for AC-1 and AC-2 at each site before editing.
- [x] Replace the bare attribute checks and the bare `S_ISLNK` checks with the predicate; extend the parity test.
- [x] Update the Windows support reference with the OneDrive, dedup and drvfs statements.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Predicate and parity | Implementer | Readiness | First, so other sites import or copy it |
| Site replacements | Implementer | Predicate and parity | Seven files, one owner |
| Delivery review | QA, security, required reviewers | Site replacements | Security-faithfulness: refusal must not weaken on POSIX |

## Serialization Points

- `.wavefoundry/framework/scripts/contained_files.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/helpers.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/bytecode_cache.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/lifecycle_lock.py` (predicate only)
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/native-windows-support.md`

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` if it describes path containment; add one sentence naming the single link predicate and the tag rule. Otherwise N/A.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | OneDrive checkouts cannot lint or upgrade today |
| AC-2 | required | Junction bypass of a security guard |
| AC-3 | required | Prevents the next divergence |
| AC-4 | required | POSIX refusal must not weaken |
| AC-5 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Readback: named boundaries disagree on all-reparse attributes, POSIX-only links and two known tags. Implement the generic name-surrogate bit and refuse unusable reparse metadata, preserve import boundaries and pin exact outcomes at every site. Census includes runtime_lock and upgrade_bridge_bootstrap standalone copies under requirement 3. | MCP outline/read/keyword callable; current-file reads used despite loaded-code-stale notice; no setup or index mutation. Runtime model identity unknown. Reproduce before source edit; focused POSIX and nt oracles plus guard mutants; final batch gates pending. |
| 2026-10-15 | Planned from Windows source review; no native execution claimed | Current source |
| 2026-10-15 | Serialization note: this change and `20qrt` both edit `lifecycle_lock.py` (the `_is_link_entry` predicate here; `push` and `drain` there). One implementer at a time on that file; land the predicate first so the scan keying in `20qrt` builds on the surrogate-bit rule. | Cross-wave plan review; no requirement or AC changed |
| 2026-10-15 | QRV-RD3 replaces the two-tag premise with generic surrogate and unknown-metadata rules; lock predicate included. | Bounded readiness repair; owning requirements and ACs |

| 2026-10-15 | Completed generic surrogate-bit classification, unknown reparse metadata refusal and every named boundary replacement; no import boundary expansion. Preserved incoming/old-runner compatibility by local exact copies in authority and lifecycle modules and a nested sidecar copy rather than importing a new runtime_lock symbol across extraction. | New test_windows_path_guards: 3 tests, exact tag oracles at 14 named sites (12 tag cases), seven module metadata helpers plus nested sidecar AST parity and lifecycle entry outcomes; contained_files 45 tests / 1 skip, runtime_lock 40 / 2 skips, bytecode_cache 67 / 0 skips green. Existing Windows fixture now injects junction metadata rather than mocking a replaced helper seam. Initial named-boundary tests reproduced broad-attribute false refusals and missing surrogate/unknown-metadata refusals; fixture max_bytes omission was corrected. |
| 2026-10-15 | Named guard mutants reject both original divergence directions; native support and architecture rule documented. AC-1–AC-4 and tasks complete; AC-5 remains open for batch docs/full-suite gates. | `two-known-tags-only` detected by `test_every_copy_and_lock_predicate_has_exact_outcomes` (1 failure), `all-reparse-refused` by the same exact oracle (2 failures); zero skips, mutations compiled in memory. Native Windows, OneDrive, dedup and drvfs remain unqualified. Three released source files include coordinator-owned 20qru edits; no other agent's edits overwritten. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | One predicate, copied verbatim across the import boundary, pinned by parity test | `contained_files` must import nothing from the framework; the parity test already exists for one copy | (a) Keep per-module checks and fix each: the drift recurs. (b) Move `contained_files` behind a shared module: breaks its no-import boundary. |
| 2026-10-15 | Fix both directions in one change | Both halves are "use the one correct test"; splitting would leave the parity test covering half the sites | Two changes (rejected) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Unknown name-surrogate tag bypasses an allowlist | Generic surrogate bit plus fail-closed unusable Windows metadata |
| Missing a duplicated predicate or changing an import boundary | Named-site census and parity including lock predicate; no new contained_files dependency |
| Native metadata differs from oracle | Explicit field-qualification limits; no cloud or drvfs universal claim |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
