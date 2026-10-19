# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `212yk setup-readiness-source-only-stamp`
Title: Setup Readiness Source Only Stamp

## Objective

Agents and operators in a checkout whose framework scripts changed, at an unchanged framework version with every live setup check passing, stop being told to run `wf setup` when it has nothing to do; version, configuration, surface and environment changes still request setup.

## Changes

Change ID: `212b9-bug setup-readiness-source-only-stamp-mismatch`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `212yk` (Setup Readiness Source Only Stamp) delivered one change: Setup readiness: ignore a source-only stamp mismatch. Notable adjustments during implementation: Setup readiness: ignore a source-only stamp mismatch: Delivery review: code, QA, architecture and docs-contract approved delivery, each with independent scratch-copy known-bad probes (QA six mutants, all killed); council delivery recorded (red-team, security-reviewer, no blocker). Red-team ran `setup_wavefoundry.py --check --json` against this repository's real stamp with the on-disk code: `ready`, no reasons or actions, `SOURCE_ONLY_STAMP_LIMITATION` in limitations. Follow-ups, not in scope: N-1 (security) an error computing the live configuration identity (oversized or unreadable `VERSION` or launcher file, malformed `docs/workflow-config.json`) is caught by the stamp block's handler and reported as the stamp-unreadable limitation; pre-existing when sources matched, now also reachable when they differ; computing `_configuration_identity` outside that handler would fix it. Red-team wording note: the renderer gap covers launcher bytes only for an edit that was not re-rendered, since rendered launcher bytes are compared through the configuration identity. Whole suite last: `python3 .wavefoundry/framework/scripts/run_tests.py` ran 11914 tests across 200 files, OK (12 skipped), green receipt written. Only operator signoff remains; Setup readiness: ignore a source-only stamp mismatch: Readiness red-team RT-1 (blocking): the in-process fixture refuses differing on-disk scripts before the stamp block, so AC-1 could not pass there. Repaired by narrowing AC-1/AC-2 to a rewritten stamp `sources` entry in-process and keeping the real on-disk edit in the fresh-process fixture; also added the identity-equality census test to Scope and widened the accepted renderer gap.

**Changes delivered:**

- **Setup readiness: ignore a source-only stamp mismatch** (`212b9-bug setup-readiness-source-only-stamp-mismatch`) — 3 ACs completed. Key decisions: Treat a source-only stamp difference at an unchanged framework `VERSION` as a limitation note, not a setup request; Accept the gap that a source-only edit to `model_bundle.py` (a `MODEL_SET_VERSION` bump) or to `render_platform_surfaces.py` is no longer flagged when `VERSION` is unchanged. For the renderer this covers every output no live check reads: `.wavefoundry/bin/` launcher bytes, `.claude/settings.json`, the rendered host hooks (`.claude/hooks/`, `.cursor/hooks/`, `.github/hooks/`) and `.wavefoundry/git-hooks/`
## Watchpoints

- Watchpoint: waves 2136j, 2136r, 2136s and 2124l are paused and uncommitted in the same tree; this wave shares only CHANGELOG.md, `docs/contributing/build-and-verification.md` and `docs/specs/mcp-tool-surface.md` with them; edit only the stamp paragraphs there and leave their uncommitted hunks intact.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 32 | 2,192,498 |
| implement | 21 | 52,440 |
| review | 47 | 1,449,617 |
| **Total** | **100** | **3,694,555** |

<!-- wave:context-efficiency-state {"generation":99,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":21,"content_source_credit":58887,"derived_artifact_credit":1271,"direct_net":52440,"estimated_tokens_saved":52440,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":878,"response_debit":7888,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1048},"plan":{"calls":32,"content_source_credit":2255077,"derived_artifact_credit":3250,"direct_net":2192498,"estimated_tokens_saved":2192498,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4275,"response_debit":65982,"source_credit_count":54,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":47,"content_source_credit":1522710,"derived_artifact_credit":1684,"direct_net":1449617,"estimated_tokens_saved":1449617,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4687,"response_debit":73304,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":100,"content_source_credit":3836674,"derived_artifact_credit":6205,"direct_net":3694555,"estimated_tokens_saved":3694555,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9840,"response_debit":147174,"source_credit_count":118,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8690},"wave_id":"212yk setup-readiness-source-only-stamp"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 769,690 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":769690,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
