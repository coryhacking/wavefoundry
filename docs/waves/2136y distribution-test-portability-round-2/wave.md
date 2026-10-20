# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2136y distribution-test-portability-round-2`
Title: Distribution Test Portability Round 2

## Objective

A renamed distribution such as Waveforge gets a green test receipt on its own tree: the remaining tests that assumed our close rule, tool registration, layout, journal trigger or prompt names hold on any declared profile, and our shipped README and seed 050 say nothing false or default-named. Our own coverage is unchanged.

## Changes

Change ID: `2134w-enh distribution-test-portability-round-2`
Change Status: `implemented`

Change ID: `2134x-doc shipped-guidance-vocabulary-and-edit-gate-corrections`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `2136y` (Distribution Test Portability Round 2) delivered two changes: Make the remaining distribution-blocking tests portable and Correct shipped guidance: README shortcut names and the Claude edit-gate limit. Notable adjustments during implementation: Correct shipped guidance: README shortcut names and the Claude edit-gate limit: Implemented. `.wavefoundry/README.md` line 145 now says "When you type a lifecycle shortcut (listed in `docs/prompts/index.md`)" and line 202 "the distinct review phase (see the review shortcut in `docs/prompts/index.md`)". Seed 050 bullet rewritten (seed gate opened and closed around the edit); no rendered copy of the bullet exists, so no re-render. AC-2 code review: `render_platform_surfaces.CLAUDE_HOOKS` registers `pre-edit` with `matcher: None`; the rendered `.claude/hooks/pre-edit.py` returns early for `NON_EDIT_TOOL_NAMES` (`Read`, `Bash`) and `CORE_READ_TOOLS` (Wavefoundry read-tier, only while its contract hash matches), gates other non-edit tools only through `FILE_PATH_KEYS` (`tool_input.file_path`, `tool_input.notebook_path`, `tool_input.path`, `tool_info.file_path`, `file_path`, `path`) and otherwise prints a COMPATIBILITY warning and allows; the bullet matches. CHANGELOG bullet under Fixed. AC-1: in both Set/Wave scratch copies the retired-name scan reports no `.wavefoundry/README.md` offender; with the HEAD README restored it reports lines 145 (`Plan change`, `Prepare wave`) and 202 (`Review wave`). The root `README.md` and `AGENTS.md` offenders there are this repository's own docs, out of scope. test_wf_cli 54 OK on the default profile and under both profile runs.

**Changes delivered:**

- **Make the remaining distribution-blocking tests portable** (`2134w-enh distribution-test-portability-round-2`) — 7 ACs completed. Key decisions: Fix each test against the contract it guards; no expected-failure mechanism.
- **Correct shipped guidance: README shortcut names and the Claude edit-gate limit** (`2134x-doc shipped-guidance-vocabulary-and-edit-gate-corrections`) — 3 ACs completed. Key decisions: Reword rather than render.
## Watchpoints

- Watchpoint: open `framework_edit_allowed` for test edits and `seed_edit_allowed` for seed 050, whatever the edit tool; close each after.
- Watchpoint: qualify with the 2134q Set/Wave scratch tree and `run_tests.py --profile second` / `--profile declared` before claiming portability.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | code-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 17 | 16,121 |
| implement | 49 | 0 |
| review | 20 | 24,807 |
| **Total** | **86** | **40,928** |

<!-- wave:context-efficiency-state {"generation":82,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":49,"content_source_credit":3254,"derived_artifact_credit":0,"direct_net":-9729,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1507,"response_debit":12694,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1218},"plan":{"calls":17,"content_source_credit":28254,"derived_artifact_credit":7815,"direct_net":16121,"estimated_tokens_saved":16121,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2331,"response_debit":22045,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":20,"content_source_credit":70778,"derived_artifact_credit":1123,"direct_net":24807,"estimated_tokens_saved":24807,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4341,"response_debit":45967,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":86,"content_source_credit":102286,"derived_artifact_credit":8938,"direct_net":31199,"estimated_tokens_saved":40928,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8179,"response_debit":80706,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8860},"wave_id":"2136y distribution-test-portability-round-2"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
