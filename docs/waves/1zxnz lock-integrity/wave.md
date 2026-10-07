# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zxnz lock-integrity`
Title: Lock Integrity

## Objective

Make record-style runtime locks immune to unrelated descriptor closes (OFD locks on POSIX with a lockf fallback) and make `runtime_lock` safe across MCP reloads, so lifecycle mutual exclusion cannot be lost mid-operation and a reload never fails on a stale lock module.

## Changes

Change ID: `1zx02-bug lifecycle-lock-ofd-and-reload-safety`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-07

## Wave Summary

Wave `1zxnz` (Lock Integrity) delivered one change: Make Record-Style Runtime Locks Immune to Unrelated Descriptor Closes and Keep runtime_lock Reload-Safe. Notable adjustments during implementation: Make Record-Style Runtime Locks Immune to Unrelated Descriptor Closes and Keep runtime_lock Reload-Safe: Implemented ws-1 to ws-4. `runtime_lock`: `flock_layout`/`pack_flock`/`unpack_flock` (layout table moved from `indexer`, padded to 32/24 bytes), OFD acquire via `F_OFD_SETLK`/`F_OFD_SETLKW` with per-acquire `lockf` fallback on EINVAL/ENOSYS/ENOTSUP/EOPNOTSUPP, `mechanism` attribute and symmetric release, preserve-if-present registry and guard. `indexer`: function-local layout import, `l_pid <= 0` returns `None`. `server_impl`: `_IN_PLACE_RELOAD_MODULES` reload with exception-class rebinding under `process_hold_guard()`; `_read_repo_text_checked`/`RuntimeLockTargetRefused` at every Requirement 10 site; `get_prompt` skip plus `refused` list; refused lookups not cached. `edit_gate_handlers`: handoff refusals. The found-prompt warning is marked `severity: warning` rather than `advisory=True`, because the sanctioned-advisory-sites test pins every `advisory` keyword. No `@mcp.tool` handler changed; the digest fixture is unchanged.; Make Record-Style Runtime Locks Immune to Unrelated Descriptor Closes and Keep runtime_lock Reload-Safe: Mutation probes (scratch, restored after each): forced fallback fails AC-1 tests in all three files; exception rebinding removed fails AC-9 (both reload tests) and AC-15; in-place reload removed fails AC-8 and the AC-10 guard; refusal removed fails all 15 AC-11/AC-16 reader tests; refused miss cached fails AC-16; pid normalization removed fails AC-6 (test_indexer and status test); registry not preserved fails AC-9; busy errnos falling back fails AC-2/AC-3 busy tests. In-test mutants cover AC-8 (no in-place reload raises ImportError) and AC-10.

**Changes delivered:**

- **Make Record-Style Runtime Locks Immune to Unrelated Descriptor Closes and Keep runtime_lock Reload-Safe** (`1zx02-bug lifecycle-lock-ofd-and-reload-safety`) — 16 ACs completed. Key decisions: Use OFD locks on supported POSIX, with a per-acquire `lockf` fallback.; Gate OFD on a known `struct flock` layout (Linux and macOS, 64-bit, x86_64 or arm64); everything else falls back.
## Watchpoints

- Watchpoint: sequencing and shared files below; follow-up items go to later waves, not this one.
- Implemented first of five sequential waves (A to E); shares `server_impl.py` and CHANGELOG with later waves.
- Public repository: describe defect classes only, no reproduction steps.
- Linux and WSL2 lock behavior is documentation-derived here; tests must skip cleanly where OFD constants are absent.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | pending | — |
| DEL-2 | do_now | no | pending | — |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 43 | 55,085 |
| implement | 6 | 0 |
| review | 10 | 37,170 |
| **Total** | **59** | **92,255** |

<!-- wave:context-efficiency-state {"generation":31,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":6,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-558,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":88,"response_debit":738,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":268},"plan":{"calls":43,"content_source_credit":79633,"derived_artifact_credit":13396,"direct_net":55085,"estimated_tokens_saved":55085,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3384,"response_debit":38368,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3808},"review":{"calls":10,"content_source_credit":57653,"derived_artifact_credit":1248,"direct_net":37170,"estimated_tokens_saved":37170,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2650,"response_debit":21465,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":59,"content_source_credit":137286,"derived_artifact_credit":14644,"direct_net":91697,"estimated_tokens_saved":92255,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6122,"response_debit":60571,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6460},"wave_id":"1zxnz lock-integrity"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
