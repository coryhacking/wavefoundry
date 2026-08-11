# An Undecodable Wave Record Crashes Every Lifecycle Tool

Change ID: `1v0lw-bug wave-record-reads-crash-every-lifecycle-tool`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-10
Wave: 1uzwh artifact-read-fail-closed

## Rationale

Wave `1uwpf` (`1uu9z`) made every lifecycle tool report an unreadable **change document** instead of raising. The same crash shape survives one file over, and it is worse there: an undecodable `wave.md` raises `UnicodeDecodeError` out of **eight of eight probed lifecycle tools** — `wf_current_wave`, `wf_list_waves`, `wf_get_change(wave_id=…)`, `wf_prepare_wave`, `wf_implement_wave`, `wf_close_wave`, `wf_pause_wave`, and `wf_mark_ac` — executed against a synthetic repository on 2026-08-10. The wave record is read by more tools than any change document, including the two inspection tools an operator would reach for first to diagnose the problem, so the recovery path is a second stack trace exactly as it was for `wf_get_change` before `1uu9z`.

This boundary was **disclosed, not missed**: `1uu9z`'s Scope declared "reads of documents other than admitted change docs" out of scope, and its delivery reverification (red-team seat) executed the reproduction and recorded it as a carried-forward finding. This change closes it.

The site census is larger than the change-document one was: an AST scan finds **24** `read_text` calls in `server_impl.py` whose receiver mentions `wave_md`/`wave_path` (against `1uu9z`'s twelve change-document functions). Many share a small number of parse helpers (`_parse_wave_record` is the crash site the reverification named), so the fix should land in the shared readers where possible rather than at 24 call sites.

Readiness-council correction (2026-08-10): the plan-time claim that the file has "no read-failure handling at all" was falsified by the red-team seat. Two resolution-path sites already swallow `OSError` silently (`_resolve_wave_md_matches` wraps the parse in `except OSError: continue`; `_wave_match_payload` substitutes an empty parse), so today a permission-unreadable `wave.md` is not a crash but a silent skip that every by-id tool misreports as `wave_not_found`. On the resolution path only the decode cause crashes (`UnicodeDecodeError` is not an `OSError`); unwrapped read sites such as `wf_list_waves` raise on either cause. Both fail-open shapes are in scope: the crash becomes a diagnostic, and the misdirection becomes the same diagnostic instead of `wave_not_found`.

## Requirements

1. **No lifecycle tool raises on an unreadable `wave.md`.** Every tool that reads a wave record returns a diagnostic naming the file and the cause, following `1uu9z`'s established pattern: `(OSError, UnicodeError)` pairing, `change_doc_unreadable`'s sibling code `wave_record_unreadable` (a new code — a wave record is not a change doc, and the recovery differs), and message text routed through `_read_error_detail` so no absolute path ships.

2. **Decision tools refuse; enumeration tools degrade per entry.** The `1uu9z` / `1upba` split carries over: `wf_prepare_wave`, `wf_implement_wave`, `wf_close_wave`, and `wf_mark_ac`/`wf_mark_task` **refuse** — a gate cannot be evaluated over a record it cannot read. `wf_list_waves` and `wf_current_wave` **degrade per entry** — the unreadable wave is listed with a `read_error` and its own diagnostic while readable siblings are returned, matching `wf_list_plans`.

3. **A census establishes the real fix set before any edit.** 24 raw call sites is the upper bound, not the plan: map each to its enclosing parse helper by AST, fix the shared readers, and enumerate any call site that bypasses them. `1uu9z`'s census was corrected twice (two → five → twelve); this one starts from the executed tool matrix and the AST count, and AC-1 requires the census recorded in this document before the first edit.

4. **No behavior change for a wave record that decodes.** Responses for readable records stay byte-identical, per the `1uu9z` AC-7 method: an executed before/after comparison across the touched tools, plus the durable regression half (ok status, zero read diagnostics, determinism).

5. **Resolution failure is not `wave_not_found`.** The wave-resolution path (`_resolve_wave_md_matches` / `_wave_match_payload`) stops swallowing `OSError`: a wave record that exists but cannot be read surfaces `wave_record_unreadable`, never a `wave_not_found` misdirection. Today's silent skip is the second fail-open shape this change closes. The AC-1 census also records a disposition for the non-matching-sibling sub-case: an unreadable unrelated wave encountered mid-resolution surfaces its diagnostic without refusing resolution of the requested wave (dirname matching permits skipping the sibling without reading it).

## Scope

**Problem statement:** the file read by more lifecycle tools than any other fails open in two shapes: most read sites have no failure handling at all (an undecodable record raises out of all eight probed tools, including the two an operator would use to diagnose it), and the wave-resolution path silently swallows `OSError`, so a permission-unreadable `wave.md` is misreported as `wave_not_found`.

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`: the wave-record parse helpers and any call site that bypasses them.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: red-first reproductions at each tool boundary, both causes, modeled on `BulkWaveGetChangeTests`.
- `docs/specs/mcp-tool-surface.md`: the `wave_record_unreadable` contract at the tools that gain it.

**Out of scope:**

- Change-document reads — shipped by `1uu9z` and verified by six lanes.
- Reads of prompts, seeds, handoff, and MCP resources. The resource readers already return `# Not Found` markdown for absent files; extending unreadable-file handling there is a separate, smaller change if wanted.
- `events.jsonl` reads — the ledger has its own fail-closed validation path (`review_evidence.py`) and already reports `ledger_errors`.

## Acceptance Criteria

- [x] AC-1: The census (Requirement 3) is recorded in this document before the first edit: every `wave.md` `read_text` site mapped to its parse helper, with its disposition.
- [x] AC-2: Each of the eight probed tools plus `wf_mark_task` returns rather than raises on an unreadable `wave.md`, reproduced **red-first** with per-cause expectations matching today's actual behavior: the decode cause fails with `UnicodeDecodeError` against current code; the permission cause pins the current misbehavior per site class (unwrapped read sites raise `PermissionError`; wave-resolution sites silently skip and misreport `wave_not_found`). A single expected exception for both causes is not satisfiable and is not the contract.
- [x] AC-3: The diagnostic names the wave record and the cause, asserted on message content (document **and** exception type), and carries no absolute filesystem path — asserted with the `1uu9z` leak-test pattern.
- [x] AC-4: `wf_list_waves` and `wf_current_wave` degrade per entry: the unreadable wave appears with `read_error`, readable siblings are returned, envelope status stays `ok`.
- [x] AC-5: The decision tools refuse with `status: error`; a mutation restoring any raw read at a decision boundary is killed by a named test, covering `wf_mark_ac` and `wf_mark_task` each at their own boundary.
- [x] AC-6: Byte-identical responses for readable wave records at every touched tool (executed before/after), plus the durable regression half.
- [x] AC-7: The spec documents `wave_record_unreadable` at the tools that gain it.
- [x] AC-8: The full framework suite and docs-lint pass.
- [x] AC-9: A permission-unreadable `wave.md` at the wave-resolution path yields `wave_record_unreadable`, not `wave_not_found`, asserted red-first against today's misdirection.

## Tasks

- [x] Run and record the census (AC-1).
- [x] Write the red-first nine-boundary matrix (eight probed tools plus `wf_mark_task`), per-cause expectations.
- [x] Guard the shared parse helpers; enumerate and guard bypassing call sites.
- [x] Route all new message text through `_read_error_detail`.
- [x] Update the spec; run the full suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | — | AC-1; 24 raw sites is the bound, helpers are the fix surface |
| red-tests | implementer | census | Nine boundaries × two causes, red-first |
| guards | implementer | red-tests | Shared readers first; `1uu9z` pattern throughout |
| spec | implementer | guards | AC-7 |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`N/A` with rationale: this extends `1uu9z`'s established read-failure contract to a second artifact class. No boundary moves; the decision-vs-enumeration split is the one `docs/architecture/data-and-control-flow.md` already describes for change documents, and the close-gate outcome for unreadable wave records (refusal) is new behavior this plan discloses here rather than a change to a documented flow.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | `1uu9z`'s census was corrected twice; this one starts recorded. |
| AC-2 | required | The reported defect, at all nine boundaries. |
| AC-3 | required | The `1uu9z` leak class must not recur on a new code path. |
| AC-4 | required | The recovery tools must recover, not crash — the exact `1uu9z` AC-2b argument. |
| AC-5 | required | A gate evaluated over an unreadable record is fail-open. |
| AC-6 | required | The change must be invisible for normal input. |
| AC-7 | important | New public diagnostic code needs spec coverage — `1uwpf`'s reverification caught exactly this omission for `wf_list_plans`. |
| AC-8 | required | Standard gate. |
| AC-9 | required | The misdirection sibling: a read failure reported as a nonexistent wave sends the operator to the wrong recovery. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Planned from wave `1uwpf`'s carried-forward findings. Premises executed before authoring: all eight probed tools raise `UnicodeDecodeError` on an undecodable `wave.md` (synthetic repo, both inspection tools included), and the AST census counts 24 `read_text` calls with a `wave_md`/`wave_path` receiver | executed tool matrix and AST scan, 2026-08-10 |
| 2026-08-10 | Readiness council (red-team and docs-contract seats): plan repaired pre-receipt. The "no read-failure handling" claim was falsified (the resolution path swallows `OSError` and misreports `wave_not_found`), and AC-2's single-exception red-first contract was unsatisfiable for the permission cause. Requirement 5 and AC-9 added; AC-2 and AC-5 rewritten with per-cause, per-site-class expectations; `wf_mark_task` added to the probe matrix | red-team seat report (executed `code_read`/`code_keyword` verification), 2026-08-10 |
| 2026-08-11 | Thought: the readiness code lane's executed census falsified the shared-helper default (only ~5 of 24 sites reach `_parse_wave_record`; 23 are inline reads across 20 bodies; six additional tools raise beyond the probed nine), so the Decision Log's pre-authorized `read_wave_record` seam is the design: one seam returning record-or-structured-failure, every wave-record read routed through it, enforced by a residue census test keyed by RESOLVED TARGET (any `wave.md` read), not receiver name, because the qa lane demonstrated the receiver-name key misses `contained_wave.read_text` in `_publish_prepare_policy_state`. Delegated to a dedicated implementer lane owning `server_impl.py`, `test_server_tools.py`, and the spec, with both lanes' findings carried in the brief (per-tool site-class map, sibling-contamination and only-wave fixtures, reach-guards, envelope nuance, byte-identity mechanics) | readiness lane reports, 2026-08-11 |
| 2026-08-11 | AC-1 census (implementer, by RESOLVED TARGET, pre-edit): 119 `read_text` sites in `server_impl.py`; 26 reach `wave.md`. The receiver-name key finds 24; resolution adds L7490 (`contained_wave`, produced by `_contained_wave_review_paths`) and L16884 (`_wave_has_gapfill_note`, mixed-target `*.md` loop that includes `wave.md`), and excludes one name-era false positive (L5503 `_detect_wave_status_drift` skips `wave.md` explicitly and reads change docs). Dispositions: (a) shared parse helper L2847 `_parse_wave_record` rebuilt on the seam as `_read_wave_record` (readable payload unchanged, degraded record with `read_error` on failure; covers `wf_list_waves`, `wf_current_wave`, cache, `_review_evidence_cost_focus`); (b) resolution sites L6078 `_wave_match_payload` plus the `_resolve_wave_md_matches` loop stop swallowing `OSError` and carry `read_error` / skipped-candidate payloads (Requirement 5); (c) 15 decision/mutation boundary reads across 12 tool bodies refuse via the seam with `wave_record_unreadable`: L5719 get_change-bulk, L6413 mark refresh re-read, L7701 create_wave, L7830 add_change, L8003 remove_change, L15403+L15512 review_event, L15859+L15976+L16270 prepare, L16312 pause, L16556 review_wave, L16950 implement, L17470 close, L17673 reopen; (d) mid-transaction re-read L7490 raises a sanitized ValueError into the existing structured handlers; (e) 8 internal consumers degrade via the seam preserving current shape, extended to the decode cause: L14821 (False), L14855 (sanitized detail), L15224 (list sub-path diagnostic, ok envelope), L16799 (None), L16884 (continue), L25542 (empty checkpoint), L25572/L25682 (persistence failed); (f) resource readers L30858/L30869 (`_validated_wave_markdown`) stay out of scope per Scope and are allowlisted by the residue test | executed AST census, 2026-08-11 |
| 2026-08-11 | Implemented (implementer lane). Seam: `_read_wave_record_text(wave_md) -> (text, read_error)` is the sole raw-read boundary; `_read_wave_record(root, wave_md)` replaces `_parse_wave_record` (readable payload byte-identical, degraded record with `read_error` on failure); resolution returns `(matches, unreadable)` and `_find_wave_md_detailed` adds the requested-record read_error plus skipped siblings. Twelve by-id tools plus `create_wave` refuse with `wave_record_unreadable`; `wf_list_waves`/`wf_current_wave` degrade per entry including the only-unreadable-wave case; eight internal consumers degrade through the seam; the `wavefoundry://wave/{wave_id}` resource renders `# Unreadable Wave` instead of raising or `# Not Found`. Red-first record: 38 failures across 9 tests against pre-seam code (decode raised `UnicodeDecodeError` at all nine probed boundaries and the six census-added tools; permission raised `PermissionError` at both enumeration tools and `create_wave` and misreported `wave_not_found` at every by-id boundary; sibling-decode crash and zero-match `wave_not_found` pinned). Green: 9/9 new tests; the residue census test enforces the seam by resolved target. AC-6 executed half: 16 readable-fixture surfaces byte-identical before-build vs after-build (canonical JSON, sorted keys, temp-root token normalized), plus the durable regression test. AC-5 kill probe executed: restoring the raw read at `wf_close_wave` in a scratch tree flipped exactly the two close subTests plus the residue test naming the restored line. Suites: test_server_tools 1672 OK twice, test_review_evidence 152 OK, test_dashboard_server 189 OK (1 pre-existing skip), docs-lint ok | red/green unittest runs, AC-6 capture diff, scratch mutant probe, 2026-08-11 |
| 2026-08-11 | Implementation complete (delegated lane). Seam shipped: `_read_wave_record_text` as the sole raw-read boundary and `_read_wave_record` replacing `_parse_wave_record` with the `_parse_plan_record` degrade shape; resolution returns matches plus unreadable candidates (`_find_wave_md_detailed`), never `wave_not_found` when unreadable candidates were skipped. Twelve tools refuse; both enumeration tools degrade per entry including the only-unreadable-wave case; `wf_get_change` follows its own `change_doc_unreadable` refusal convention. Residue census test (`WaveRecordReadSeamCensusTests`, by resolved target) enforces AC-1 mechanically. AC-6 executed: 16 surfaces byte-identical before vs after (canonical JSON, root-token normalization). AC-5 mutant probe: restoring the raw read at close flipped exactly the two close subTests plus the residue test. Recorded deviations: sibling diagnostics stay OFF gate-success envelopes (blocking semantics; documented in spec and code comment); the `_publish_prepare_policy_state` mid-transaction re-read raises a sanitized ValueError into existing retryable handlers; `resource_wave` gained minimal `# Unreadable Wave` branches for non-regression; census corrected to 26 resolved-target sites (L16884 mixed loop in, L5503 false positive out); degraded record paths repo-relative, readable paths byte-identical absolute | implementer report; test_server_tools 1672 OK twice, test_review_evidence 152 OK, test_dashboard_server 189 OK, 2026-08-11 |

| 2026-08-11 | Delivery review (three lanes plus delivery council, red-team fixed seat + docs-contract rotating): 4/4 APPROVE. Corrections from the audit, recorded here without rewriting the historical rows: the red matrix tally is 37 failures (qa reproduced at HEAD; the recorded 38 was off by one) and the current file-scope count is test_server_tools 1678 (the 1672 figure predated 1uzwi's later additions). The qa lane independently regenerated the AC-6 captures from a HEAD extract (byte-identical) and killed six mutants including one at a boundary the implementer never probed; the red-team seat verified byte-identity across all 214 real wave records and confirmed the census-detector blind spot at the seam-routed `_wave_has_gapfill_note` glob loop (documented, degrade-only site). Carried forward for a future change: the dashboard's `collect_waves` reads wave records raw (pre-existing crash class, now also mixed path types in the degraded payload) and `McpRepoCache`'s (count, max-mtime) fingerprint is blind to permission flips on enumeration surfaces | delivery lane and council seat reports, 2026-08-11 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | New diagnostic code `wave_record_unreadable` rather than reusing `change_doc_unreadable` | The artifact class and the recovery differ: a broken change doc is repaired or removed from the wave; a broken wave record blocks the whole wave and its fix is restoration | Reuse `change_doc_unreadable` (rejected: an operator filtering by code could not tell which artifact class failed) |
| 2026-08-10 | Fix at the shared parse helpers, not the 24 call sites | The call sites funnel through a small helper set; per-site guards reproduce the `1uu9z` drift where a census grows every review round | Per-site guards (rejected: 24 sites, and the count is the least stable fact in this plan) |
| 2026-08-10 | Readiness-council alternative recorded, implementer's option if the census finds bypass sites: a single `read_wave_record` seam with a no-`read_text`-outside-the-seam residue census test (the `1to78` facade shape) | The seam turns the 24-site census from a document into a mechanical invariant and makes silent-skip sites impossible to miss; compatible with every AC | Census-as-document only (the default if the census maps cleanly onto the existing helpers) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The census finds call sites that bypass the helpers | AC-1 records them with dispositions before edits; the `1uu9z` precedent is that the census is the gate |
| The fix changes behavior for readable records | AC-6 pins byte-identity, executed |
| A new leak of the `PermissionError` path class | AC-3 mandates `_read_error_detail` and the leak-test pattern from the start |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
