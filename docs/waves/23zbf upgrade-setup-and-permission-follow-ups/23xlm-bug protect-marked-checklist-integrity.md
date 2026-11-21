# Protect checklist history and deferral reasons

Change ID: `23xlm-bug protect-marked-checklist-integrity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 23zbf

## Rationale

The security reviewer of 23zbc found three defects in the shared mark writer. It permits changes to a closed record in a live root, accepts a required deferral whose only explanation is the criterion itself, and accepts reason text that changes how the checklist reader interprets later items. These contradict the proposed permissions guidance. The operator chose to repair all three before offering low-risk write permissions.

## Product Intent

An operator who delegates routine checklist updates can trust a closed record to keep its history. Closing one spec protects that spec immediately. Other open specs in the same wave remain editable. On an editable record, the reviewer can see why a required criterion was deferred and still read every neighboring criterion. AC-1 through AC-3 establish these properties at the served writer. Actual downstream adoption remains a field observation.

## Requirements

1. Before previewing or applying either mark tool, check the owning wave and the selected admitted spec. Refuse a mark when the wave is closed or completed, including in the live root. Refuse a mark on an individually completed spec while the wave is open. Use the membership and visible status records that Close spec maintains. Do not treat an implemented spec awaiting review as individually closed. Preserve existing archive, unreadable-record, member-containment and admission refusals. Keep current supported nonterminal workflows. Do not rewrite historical records.
2. A required AC marked deferred must have a nonblank, explicit rationale. An existing valid canonical status note may satisfy an unchanged repeat request. The criterion description, regardless of length, is not a rationale. Read priority, criterion identity and status notes through the framework's existing readers. Preserve optional deferrals, normal completion, and existing canonical note replacement.
3. Reject a supplied deferral reason if it can introduce or close an HTML comment, span lines or break the canonical status note. A successfully written reason must remain visible as ordinary note text and preserve all other checklist entries. Refusals name the remedy and leave the spec bytes untouched. Dry runs use the same validation as writes.
4. Document the writer boundaries in the MCP tool reference and changelog. Keep mode, existing valid arguments, dry-run default, subprocess policy and gate/close authorization. Close spec completes only its target. If the wave contains exactly one admitted spec, the close instructions may offer Close wave after a successful spec close and must wait for an explicit answer. In a multi-spec wave, leave the wave open even when the selected spec was its last unfinished member. Close wave handles all eligible members under its existing review and closure rules. Ship these checks before adding the mark tools to the opt-in tier.

## Scope

The two mark tools share one writer. The fix belongs there and in any shared parsing helper needed to understand a mark. This change neither retroactively invalidates old ledgers nor asks a project to repair closed records. Task-prefix matching is owned by 23zbd. The host allowlist and its threat note are owned by 23zbc.

## Acceptance Criteria

- [x] AC-1: In a scratch target, both tools refuse preview and apply on closed and completed records under the configured live root. The spec bytes match before and after. Close one of two eligible specs with the served Close spec tool. Check that its wave stays open, both mark tools refuse preview and apply on that completed spec, and the active sibling still accepts ordinary marks. Repeat with a single admitted spec and verify that closing it leaves the wave open. A historical status quoted in a fenced example leaves the actual live status effective.
- [x] AC-2: On a live target, a required criterion whose long description has no status note refuses an empty or whitespace-only deferral reason. Its bytes remain unchanged. A valid reason produces one visible rationale. Repeating the deferral preserves it. A non-required criterion and a task can still be deferred without a reason.
- [x] AC-3: The served writer refuses comment delimiters, multiline reasons and asterisks in deferral notes before writing. Test the begin and end delimiters independently. A supported ordinary reason is accepted, leaves adjacent items visible with their original marks, and preserves the review-policy digest for a normal checklist-only edit.
- [x] AC-4: The tool reference and Unreleased changelog describe the three bounds. The shipped and project-local Close spec instructions offer an optional wave close only for a sole admitted spec, after its own close succeeds. The affected lifecycle tests and canonical suite pass, including existing archive, admission and valid marking cases.

## Tasks

- [x] Check both owning wave and selected member status before mark preview or write.
- [x] Validate the target criterion's actual priority and its explicit note. Refuse structurally unsafe reasons.
- [x] Exercise the served mark paths with negative and positive controls in scratch targets.
- [x] Align the shipped and local Close spec instructions, MCP reference and changelog, validate docs and run the canonical framework tests.

## Agent Execution Graph

| Workstream | Owner | Depends on | Evidence |
| --- | --- | --- | --- |
| Mark integrity | Implementer | Readiness | Both writer paths and scratch tests |
| Verification | QA and security reviewers | Mark integrity | Refusals preserve exact bytes and ordinary edits work |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/specs/mcp-tool-surface.md`
- `.wavefoundry/framework/install/lifecycle-prompts/close-change.prompt.md`
- `docs/prompts/close-spec.prompt.md`

Coordinate shared writer and tests with 23zbd. Complete the integrity repair before enabling the opt-in permission group in 23zbc.

## Affected Architecture Docs

Update the MCP tool reference. The shared writer already owns validation and persistence, so no new architecture boundary is introduced.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Protect closed history |
| AC-2 | required | Preserve the operator's reason |
| AC-3 | required | Keep the visible checklist intact |
| AC-4 | required | Verify and communicate the changed contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-21 | Readback: Both mark tools must protect a closed wave or completed spec while accepting marks on an open sibling. A required deferral must carry a visible explicit reason. | Shared mark writer, scratch lifecycle tests, shipped and local Close spec instructions, MCP reference and changelog (AC-1 through AC-4). |
| 2026-11-21 | Implemented history and reason checks before both mark modes. Served Close spec left a one-member wave open and protected only the selected member in a two-member wave. The canonical reason stayed visible, preserved adjacent marks and kept the same review-policy body. | MarkChangeItemRecoveryTests, test_close_change and HandlerDigestTests passed 73 tests. The 23xlm discovery correction changes the wf_mark_ac pin alone to b15eec37. Full-suite verification follows all wave changes. |
| 2026-11-21 | Added on operator instruction during Prepare. | 23zbc security readiness finding and operator choice A |
| 2026-11-21 | Repair for 23zbf-active-mark-publication-interleaving. Both mark tools now share the close tools' lifecycle lock. The registered task call lacked a busy refusal before the repair. With the lock, the second caller retries after the first finishes and both changes persist. | test_contended_registered_marks_retry_and_preserve_both_updates pauses an active AC call before reading. All 45 focused mark, Close spec write and extension lifecycle tests passed. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-21 | The operator selected shared writer guards and retained the opt-in tier. | All callers receive the same protection. | Documentation alone leaves the defects in place. Removing the mark tools from the tier still leaves direct callers exposed. |
| 2026-11-21 | Close spec affects only its selected member. After closing the only admitted spec, the agent can offer Close wave as a separate action. | The operator wants a one-spec shortcut while retaining control of wave closure. | Automatically closing a wave would remove that choice. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Unrelated historical text changes upgrade outcomes. | Limit the new enforcement to mark requests. Use live and historical fixtures. |
| Wider text filtering rejects ordinary prose. | Restrict the new delimiter rule to syntax affecting the status note or HTML comments and verify ordinary reasons end to end. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
