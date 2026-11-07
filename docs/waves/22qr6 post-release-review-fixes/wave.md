# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22qr6 post-release-review-fixes`
Title: Post Release Review Fixes

## Objective

Operators see an incomplete secret scan only when a scan really failed, with its true cause and a working remedy. Scanner rules that Go rejects fail locally too. Wave work areas stay cleanable after transient failures, reload and upgrade-inspection states are reported truthfully, and no framework process writes bytecode beside the sources. Scanner completion policy, review authority and release publication are unchanged.

## Changes

Change ID: `22qoz-bug scanner-false-incomplete-outcomes`
Change Status: `implemented`

Change ID: `22qp0-bug go-regex-nested-repetition`
Change Status: `implemented`

Change ID: `22qr4-bug work-owner-and-reload-recovery`
Change Status: `implemented`

Change ID: `22qr5-debt scanner-config-sent-once-per-worker`
Change Status: `implemented`
Depends On: `22qoz-bug scanner-false-incomplete-outcomes`

Change ID: `22qoy-bug stray-framework-bytecode-during-qualification`
Change Status: `implemented`

## Participants

- Coordinator: root agent session
- Write-owning roles: implementer; coordinator owns shared documentation and integration.
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, security-reviewer

Completed At: 2026-11-06

## Wave Summary

Wave `22qr6` (Post Release Review Fixes) delivered 5 changes: Scanner false or unexplained incomplete outcomes, Reject Go-invalid nested repetition in rule regexes, Preserve work ownership and report reload and inspection state truthfully, Send scanner configuration once per worker, and Stray framework bytecode during test qualification. Notable adjustments during implementation: Scanner false or unexplained incomplete outcomes: Requirement 1: added `betterleaks_engine.exceeded_input_limit`, one predicate used by both the engine's `scan` and the parent. It uses the engine's `MAX_CONTENT_BYTES` and `MAX_LINES` and copies neither. The checks are encoded byte length > `MAX_CONTENT_BYTES`, then `content.count("\n")` > `MAX_LINES`, never `splitlines()`. The parent runs it in the upstream branch of `scan_file_raw` after `_upstream_path_excluded` and after CRLF normalisation. The two reasons are `decoded content too large` (detail `<n> bytes > <cap> decoded cap`) and `too many lines` (detail `<n> newlines > <cap> cap`). The encode uses the engine's existing `surrogateescape` form: any string that strict `encode('utf-8')` accepts encodes identically, and the parent's replacement-decoded text has no surrogates. The engine and worker `MAX_CONTENT_BYTES` are both 5 MiB. Under the full 474-rule ruleset, the just-under-cap control (5,242,878 decoded bytes) scanned completely in 0.74 s; line and mixed Latin-1 variants took 0.42 s and 1.06 s, all far inside the 115 s budget.; Scanner false or unexplained incomplete outcomes: Requirement 3: added one `scanner_skips` projection: `fixed_limit_remedy(row)`, backed by `allowlist_entry(rel)` and `incomplete_guidance(rows, retry)`. `scanner_completion` rows with a fixed-limit reason (`file too large`, `decoded content too large`, `too many lines`) gain `remedy`, which names the TOML-valid anchored entry `'^' + re.escape(rel) + '$'`; that reaches the CLI and MCP payloads. The two `[scan-incomplete]` summaries use the same projection: `secrets_validators` (the old "retry" line) and `scanner_completion_failures`. They stay path-free, so the existing `test_parallel_path_skips_oversized_file_in_worker` passes unchanged. Without a fixed-limit row the summaries keep their current "retry" text. Updated `docs/specs/mcp-tool-surface.md`, `docs/contributing/build-and-verification.md` and `CHANGELOG.md`. `data-and-control-flow.md` names no reasons, so it is N/A. Out of the serialization scope and left unchanged: the generic `scan_incomplete` diagnostic text in `wf_server/docs_handlers.py` and the close messages in `server_impl.py`.; Reject Go-invalid nested repetition in rule regexes: Tests added to `test_expr_filter.py`: nested-repetition refusals (message asserted), flag-group refusals (multiple groups, `{n}`, lazy-before), unchanged lazy and literal quantifier forms, and compilation of every shipped regex source. Known-bad: the same tests run against HEAD's `expr_filter.py` in a scratch tree fail 14 subtests (8 nested, 6 flag-group) and pass with the fix. Shipped rules: 811 regex sources (rule `regex`/`path`, global allowlist `regexes`/`paths`, backtick literals in rule and global filter/prefilter) compile with 0 refusals both before and after. Platform: pure Python, identical on Windows, macOS, Linux and WSL2.

Intent outcome: partially. 22qoz, 22qp0, 22qr4 and 22qr5 establish their intent. Incomplete scans now name their true cause, and the fixed-limit cases carry a working anchored-allowlist remedy. Go-invalid nested and flag-fused quantifiers are refused. Work-area owners survive post-unlink failures. Reload reports stopped monitors. The upgrade inspection judges only staged modules. Scanner configuration is sent once per worker per digest. 22qoy is partial: the identified writer (framework imports placed before the bytecode guard in `indexer.py`, `setup_index.py`, `upgrade_wavefoundry.py` and `qualification_worker.py`) is fixed, and a real-tree census now fails runs that leave bytecode. AC-1 is `[~]` by operator decision, however, because the any-process trace was not run and the historical writes are not attributed. That gap is tracked as non-blocking finding `22qr6-chair-22qoy-writer-exhaustiveness`. Evidence: default suite 12,557 tests / 227 files / 12 skips green; `second` profile 227/227 files green with no framework bytecode; code, QA and security delivery approvals; council-delivery `ev-approval-council-delivery`. All runs were on macOS only.

**Changes delivered:**

- **Scanner false or unexplained incomplete outcomes** (`22qoz-bug scanner-false-incomplete-outcomes`) — 5 ACs completed. Key decisions: Readiness repair 2 (chair finding `22qr6-chair-22qoz-line-cap-remedy`, operator-chosen bounded repair): one parent-side check of both fixed engine input limits, decoded bytes and `MAX_LINES`, each with its own reason and the shared remedy. Efficacy: the chair's 210,000-line, 1.26 MB fixture gets an accurate reason and a working remedy.; Readiness repair (red-team RT-1): engine-cap remedies are scoped out; the remedy comes from one projection. Red-team alternative `surrogateescape` decoding (which would scan such files fully) is rejected: it changes line hashes for lines with invalid bytes and churns existing exceptions. The decoded-oversize file remains a real resource-limit failure under the 22q2w policy.
- **Reject Go-invalid nested repetition in rule regexes** (`22qp0-bug go-regex-nested-repetition`) — 4 ACs completed. Key decisions: Reject in the translator's quantifier branch.
- **Preserve work ownership and report reload and inspection state truthfully** (`22qr4-bug work-owner-and-reload-recovery`) — 4 ACs completed. Key decisions: Truthful response rather than an automatic monitor restart.; One try block covering all post-unlink work, with `(OSError, _Refused)`.
- **Send scanner configuration once per worker** (`22qr5-debt scanner-config-sent-once-per-worker`) — 5 ACs completed. Key decisions: Readiness repair (red-team RT-6/RT-7): key on a client-computed digest of the exact config, reuse the existing `configure` operation, and use no mid-request retry.; Configure once per key, with resend on unknown key.
- **Stray framework bytecode during test qualification** (`22qoy-bug stray-framework-bytecode-during-qualification`) — 2 ACs completed
## Watchpoints

- Watchpoint: 22qoz and 22qr5 both edit `wave_lint_lib/secrets_validators.py` and the worker; implement 22qoz first.
- Follow-up: official release still waits for Waveforge feedback; commit `1ef5e0c9` is unpushed.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 22qr6-chair-22qoy-writer-exhaustiveness | maybe_later | no | pending | — |
| 22qr6-chair-22qoz-line-cap-remedy | do_now | no | completed | — |
| 22qr6-del-qa-22qoy-ac1-method | do_now | no | completed | qa-reviewer |
| 22qr6-qa-22qoy-trace-scope | do_now | no | completed | qa-reviewer |

*Machine review state — 4 findings; current: do_now 3, maybe_later 1, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-06: Intent outcome: partially. 22qoz, 22qp0, 22qr4 and 22qr5 establish their intent. Incomplete scans now name their true cause, and the fixed-limit cases carry a working anchored-allowlist remedy. Go-invalid nested and flag-fused quantifiers are refused. Work-area owners survive post-unlink failures. Reload reports stopped monitors. The upgrade inspection judges only staged modules. Scanner configuration is sent once per worker per digest. 22qoy is partial: the identified writer (framework imports placed before the bytecode guard in `indexer.py`, `setup_index.py`, `upgrade_wavefoundry.py` and `qualification_worker.py`) is fixed, and a real-tree census now fails runs that leave bytecode. AC-1 is `[~]` by operator decision, however, because the any-process trace was not run and the historical writes are not attributed. That gap is tracked as non-blocking finding `22qr6-chair-22qoy-writer-exhaustiveness`. Evidence: default suite 12,557 tests / 227 files / 12 skips green; `second` profile 227/227 files green with no framework bytecode; code, QA and security delivery approvals; council-delivery `ev-approval-council-delivery`. All runs were on macOS only.

- 2026-11-06 Prepare wave: after the focused readiness round, the council chair withheld `council-readiness` on finding `22qr6-chair-22qoz-line-cap-remedy` (files over the engine `MAX_LINES` but under 5 MiB get an unclearable "retry"). The operator chose a second bounded repair: extend 22qoz to check both fixed engine input limits (decoded bytes and line count) in the parent, each with its own reason and the shared remedy, plus just-under-limit controls. A focused re-verification by code, QA and security and a chair re-synthesis follow.
- 2026-11-06 Prepare wave: in that round, code and QA each found that "line count" in the 22qoz repair differed from the engine predicate (newline count). The operator chose a third bounded wording repair: state the exact predicate (`content.count('\n') > MAX_LINES` after path exclusion), and add at-limit, form-feed and residual-reason controls plus the anchored allowlist remedy. Security had already approved round 3. All lanes and the chair re-record on the new receipt.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 59 | 584,247 |
| implement | 90 | 1,515,671 |
| review | 53 | 476,807 |
| **Total** | **202** | **2,576,725** |

<!-- wave:context-efficiency-state {"generation":194,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":90,"content_source_credit":1562687,"derived_artifact_credit":0,"direct_net":1515671,"estimated_tokens_saved":1515671,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3036,"response_debit":47870,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3890},"plan":{"calls":59,"content_source_credit":728761,"derived_artifact_credit":7483,"direct_net":584247,"estimated_tokens_saved":584247,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":27221,"response_debit":130284,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5508},"review":{"calls":53,"content_source_credit":626164,"derived_artifact_credit":4922,"direct_net":476807,"estimated_tokens_saved":476807,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26257,"response_debit":131800,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":202,"content_source_credit":2917612,"derived_artifact_credit":12405,"direct_net":2576725,"estimated_tokens_saved":2576725,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":56514,"response_debit":309954,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13176},"wave_id":"22qr6 post-release-review-fixes"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 807,794 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":807794,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
