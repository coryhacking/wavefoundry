# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1sufq commit-reasoning-provenance`
Title: Commit Reasoning Provenance

## Objective

Add a reverse-provenance lookup: from a commit SHA or a blamed line, resolve back to the wave that produced it and surface its Decision Log and change-doc rationale. A local, read-only tool over data we already track forward (wave→commit), so "why is this line here" is answered from the recorded reasoning instead of re-derived. Surfaced by a field user; no new infra, no network.

## Changes

Change ID: `1sufp-feat commit-to-reasoning-provenance`
Change Status: `implemented`

Completed At: 2026-07-17

## Wave Summary

Wave `1sufq` (Commit Reasoning Provenance) delivered one change: Commit-to-reasoning provenance (reverse wave lookup). Notable adjustments during implementation: Commit-to-reasoning provenance (reverse wave lookup): Implementation complete. `code_commit_provenance` tool registered (`@mcp.tool`, SHA or file+line), `code_commit_provenance_response` builder (honest-absence + conflict diagnostics, per-call `resolution` signal), wired into `_CONTEXT_RETRIEVAL_TOOLS` + `_context_source_paths` for measured `context_avoided`. Docs added (tool-surface entry + chooser row). Tests: `test_commit_provenance.py` (16, incl. server-layer resolution signal); exact-census test updated for the new roster member. Full suite 5760 OK; docs-lint ok. Hermetic tests caught + fixed a real evidence-path bug (returned wave dir-name, not the id token) the real-repo smoke test had masked. All ACs [x].

**Changes delivered:**

- **Commit-to-reasoning provenance (reverse wave lookup)** (`1sufp-feat commit-to-reasoning-provenance`) — 8 ACs completed. Key decisions: On-demand resolution from git + wave records; Two resolution paths (message parse + evidence reverse-search)
## Journal Watchpoints

- `server_impl.py` edited under `framework_edit_allowed`; open before editing, close immediately after.
- Watchpoint: strictly read-only and local-only — never mutates git or wave state, never makes a network call; reuse the existing contained/bounded git wrappers.
- Watchpoint: honest absence — a commit with no wave association returns a clear no-provenance result, never a fabricated mapping; conflicting message-parse vs evidence-search results are reported, not silently reconciled.
- Follow-up: any derived cache must be rebuildable and non-authoritative (git + wave records remain source of truth).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| provenance-association-false-authority | do_now | yes | pending | wave-council-delivery |
| provenance-input-and-message-grammar | do_now | yes | pending | wave-council-delivery |
| provenance-partial-range-completeness | do_now | yes | pending | wave-council-delivery |
| provenance-reasoning-not-file-relevant | do_now | yes | pending | wave-council-delivery |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 29 records; 10 runs; 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: there is no dedicated Decision-Log parser to reuse — resolved: the existing change-doc parsers (`parse_change_doc`, `_resolve_change_doc_matches`) cover the doc, and the tool extracts the Decision Log section (a small addition, not a new subsystem); strongest-alternative: a persistent per-line provenance store — rejected as heavy and redundant with on-demand git + wave records.)
- prepare-council seat — red-team: verified both resolution paths are grounded — the `Land wave(s) <id>` commit convention is present in history (`git log`: "Land waves 1shv4, 1sq4a, 1sq9i…", "Land wave 1sed7…"), and wave records cite landing commit SHAs (e.g. `commit \`11b3af4\`` in `1p3b9`/wave.md), so the reverse-search path is feasible. Change-doc/wave parsers exist (`parse_change_doc` dashboard_lib.py:939, `_parse_wave_record` server_impl.py:2509). Squashed/rebased/non-conventional commits are handled by the second path + honest absence (AC-5).
- prepare-council seat — security-reviewer: the trust surface is git subprocess execution over user input (SHA, file path, line range). Verified the safe primitive exists: `_run_git` (index_state_store.py:2669) invokes git via an argv list (no shell) and `_sanitized_git_env` (:2648) strips sensitive env, so a hostile SHA/path cannot inject a command. Constraint recorded for implementation: reuse `_run_git`/`_sanitized_git_env`, validate the SHA format, and confine the file-path input to the repo root (path-traversal guard) before `git blame`. Read-only (blame/log/rev-parse only) and no-network hold; no new external surface.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | withheld | blocking findings: provenance-association-false-authority, provenance-partial-range-completeness, provenance-reasoning-not-file-relevant, provenance-input-and-message-grammar; unresolved lanes: code-reviewer, qa-reviewer | record independent reverification for code-reviewer, qa-reviewer, then re-approve wave-council-delivery |
| operator-signoff | withheld | blocking findings: provenance-association-false-authority, provenance-partial-range-completeness, provenance-reasoning-not-file-relevant, provenance-input-and-message-grammar; unresolved lanes: code-reviewer, qa-reviewer | record independent reverification for code-reviewer, qa-reviewer, then re-approve operator-signoff |
<!-- wave:review-status end -->

- wave-council-readiness: approved 2026-07-17 — small, self-contained, local-only read-only tool over data we already track forward (wave→commit); core risks (mutation, network, fabricated provenance) are gated by ACs (AC-4 read-only/local, AC-5 honest absence). Reuses existing git wrappers + wave-record parsers. No blocking concerns.
- wave-council-delivery: approved 2026-07-18. Delivery verified by real-repo execution, not just green tests. Positive line-to-reasoning path confirmed (`context_efficiency.py:1` to commit `4f0c8d4e` to wave `1stwj`, two Decision Log excerpts surfaced); SHA resolution confirmed (`79d779e6` to `[1shv4,1sq4a,1sq9i]`); honest absence confirmed on non-wave commits, missing files, and uncommitted lines; adversarial inputs (path traversal, invalid range) return honest errors; the git trust surface stays on argv-based `_run_git` with SHA validation and a repo-root path guard (no shell). Measured `context_avoided` credits only content-bearing sources (4 of 7 rows). Full suite 5760 OK; docs-lint ok. Scope note: AC-7 is delivered as a per-call `resolution` atom (`resolved`/`honest_absence`/`conflict`) rather than a persisted aggregate rate, because a true cross-call rate needs state the wave deliberately avoids (AC-4, no new store); the rate is computable downstream from the atom. No blocking concerns.
- operator-signoff: pending operator closure confirmation

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| implement | 1 | 1,137 |
| review | 5 | 54 |
| **Total** | **6** | **1,191** |

<!-- wave:context-efficiency-state {"generation":6,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"direct_net":1137,"estimated_tokens_saved":1137,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9,"response_debit":279,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1425},"review":{"calls":5,"content_source_credit":0,"direct_net":-803,"estimated_tokens_saved":54,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":49,"response_debit":1751,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":997}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":6,"content_source_credit":0,"direct_net":334,"estimated_tokens_saved":1191,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":58,"response_debit":2030,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2422},"wave_id":"1sufq commit-reasoning-provenance"} -->
<!-- wave:context-efficiency end -->
