# Distinguish mark previews from applied changes

Change ID: `22lif-bug mark-tool-preview-outcomes`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-05
Wave: 22ob1 distribution-integration-followups

## Rationale

Distribution feedback against bc9cfc8e reports an agent claiming 63 items marked after preview calls. The exact field session was not replayed. A local execution of the production mark handler in a temporary lifecycle fixture reproduced the response ambiguity: omitted mode, dry_run, creat, an empty string and yes all returned ok/changed=true without changing the file. Explicit create and apply wrote it. None returned mode or applied.

## Product Intent

Agents and operators should be able to tell from each successful mark response whether a checkbox was written or merely previewed, and get a clear correction for an invalid mode. AC-1 and AC-2 establish this response contract; they do not prove every agent will heed it. This supports the adopted vision's dependable delivery foundation without adding another acceptance gate.

## Requirements

1. Keep dry_run as the default. Accept only dry_run, create and apply after existing whitespace trimming and lower-casing. Refuse any other value with invalid_arguments naming those values, before mutation.
2. Every successful wf_mark_ac and wf_mark_task response includes mode (dry_run or create; apply normalizes to create) and applied. applied is true only when the document bytes were replaced. Retain changed's existing meaning. A create no-op reports mode=create, changed=false, applied=false.
3. A preview that would change the document adds advisory dry_run_not_written with the equivalent applying call, preserving the target, state and any supplied reason, and setting mode=create. Do not automatically apply or retry it.
4. Tool descriptions explicitly explain the default preview and the create/apply write modes. Preserve checkbox matching, newline handling, lifecycle authorization, deferral-reason requirements and transactional deferred-AC receipt refresh.
5. Audit other registered mutators with a dry_run default for comparable ambiguity. Record the bounded census and specific follow-ups; this does not authorize changing all their response schemas.

## Scope

In scope: _mark_change_item_response and the two registered tools in wf_server/server_impl.py, their lifecycle tests and published tool contract. Out of scope: changing the default, marking existing wave items, unrelated lifecycle mutators, new approval gates or automatic retries.

## Acceptance Criteria

- [x] AC-1: Actual registered mark calls distinguish default/explicit previews, create/apply writes and already-satisfied no-ops using mode, applied and changed; a changing preview provides the correct nonwriting advisory and applying call.
- [x] AC-2: Invalid modes refuse without writes; valid case/whitespace normalization, CRLF files, ordinary tasks, ACs and deferred-AC receipt handling retain their intended behavior.
- [x] AC-3: The two tool descriptions and published contract match the responses; the audit names its search scope and ambiguous peers without claiming they were repaired.

## Tasks

- [x] Implement the narrow response and argument checks.
- [x] Exercise registered paths and no-write/error controls, including the existing deferral transaction.
- [x] Update tool documentation, record the audit and summarize measured limits.

## Agent Execution Graph

One implementation stream; review the response contract and negative controls after it is complete. No additional orchestration layer is needed.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/specs/mcp-tool-surface.md`

CHANGELOG.md receives a concise bug entry. Review lanes read; implementation owns edits after wave readiness.

## Affected Architecture Docs

Update the mark-tool contract in docs/specs/mcp-tool-surface.md. No ownership or primary flow changes are intended.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Distinguishes preview from application. |
| AC-2 | required | Rejects typos and preserves lifecycle semantics. |
| AC-3 | required | Makes the contract discoverable and bounds the audit. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Preserve the safe default and make its result explicit. | This directly distinguishes the reproduced cases; agent use of the signal remains unmeasured. | Changing the default could silently write; documentation alone leaves identical responses. |

## Risks

An advisory may be ignored. The response fields make the distinction machine-readable; later field feedback should assess whether false completion reports recur.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Implemented normalized mode/applied and invalid-mode refusal without changing preview defaults or deferral transaction.14 registered/recovery and6 receipt/snapshot controls pass;3 semantic mutants fail assertions without errors/skips. Bounded17-tool static census sampled3 peer families; garden/sync previews already clear, successful-run mode uniformity remains optional follow-up. | delivery-evidence.json; named production tests and guard mutants; full canonical qualification and independent delivery review pending. |
| 2026-11-05 | Readback: make registered mark previews, writes and no-ops distinguishable; reject typo modes without writing. Example: an omitted mode reports dry_run/applied=false and an applying call, while create reports applied=true only after replacement. AC-1–3; coordinator owns server_impl.py, lifecycle tests and the bounded audit; preserve deferred-AC transaction and matching/newlines. | Current receipt review-policy-9f3ca64efa19fe8cfee4; Implement wave activation succeeded. |
| 2026-11-05 | Planned from distribution feedback and temporary-fixture reproduction; not admitted or readied. | Production helper execution; server_impl.py mark-handler and registration reads. |
| 2026-11-05 | Final delivery passed: canonical suite 12,369 tests / 217 files / 12 reported skips; full docs validation and independent required lanes plus Council approve. Four supporting test-fixture repairs were independently verified in cycle 1; no product repair or scope change was needed. | delivery-evidence.json and typed events.jsonl; current receipt 92ad0645. Wave remains open for operator signoff. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
