# Memory validation withholds every stored field, and markup matching ignores case

Change ID: `24885-bug memory-withhold-and-markup-case`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: `249ar memory-maintenance-by-signal`

## Rationale

Wave `249as` (change `249aq`) made `memory_validate` content-check a stored record's title, summary and refs, and withhold any field that matched from every response. Its delivery council declined two residual gaps, and the operator moved both into wave `249ar` on 2026-11-24:

1. The record view that `memory_validate` returns on reject and rewrite (`_memory_view` in `wf_server/memory_handlers.py`) still copies the stored `action_delta`, `validation_rationale` and `source_event` without the content check, and the `memory_id` and `path` carry the title slug unchecked. A record hand-edited or written by older code can hold a credential in those fields, and the response would repeat it.
2. The tool-call markup pattern in `wave_lint_lib/constants.py` (`MEMORY_CONTROL_TOKEN_PATTERNS`) matches tag names case-sensitively, so `<INVOKE name="x">` and `<Function_Calls>` pass admission and the record lint.

## Product Intent

Maintainers and agents who validate a memory record never see a stored credential or control token repeated in the response, whichever stored field holds it, and an upper-case or mixed-case tool-call tag is refused like its lower-case form. Records with no forbidden content, and prose that merely names a tag in words, behave as before.

## Requirements

1. `memory_validate` adds the stored `action_delta`, `validation_rationale`, `source_event`, `memory_id` and `path` to the stored-field content check that 249aq introduced. The check runs once per call, before any response names the record, for every verdict. `source_event` is checked exactly as the record lint checks its line: `wave_validators._memory_forbidden_match` on the rendered `` Source event: `<value>` `` line, so the hash separator of a generated decision-log source event stays exempt and a lint-clean record is never refused by the handler. `path` is checked on its own, because the filename and the stored id can differ in a hand-edited file.
2. Every record view that `memory_validate` returns is content-checked against the record it was built from, and each matching field is withheld the way 249aq withholds title and summary: the value becomes `[withheld: <codes>]`, and `withheld_reasons` lists the codes. A view built from the stored record (every refusal, including `memory_validation_not_pending`) uses the stored check; the success view after reject or rewrite is built from the updated record, whose `action_delta` and `validation_rationale` are the caller's already-checked values, so those clean values are shown, not withheld. A matching `memory_id` or `path` is withheld wherever the response would carry it: the view, the `{"memory_id": ...}` fallback when the updated record cannot be parsed, and diagnostic text such as `memory_validation_write_failed`, which then names no id. No response repeats the matched text.
3. Promote, retain and rewrite refuse, by reason and without echo, a record whose stored `action_delta`, `validation_rationale` or `source_event` matches, the same as for a matching stored title or summary; a refused rewrite writes no new record. Reject proceeds and withholds, because it is the recovery path for such a record.
4. The tool-call markup pattern matches its tag names (`function_calls`, `invoke`, `tool_call`, `tool_use`, `tool_result`, `parameter`) and the optional namespace prefix case-insensitively. The leading `<` or `</` and the word boundary are unchanged, so `<invoker>`, `<parameters>`, `<tool_calls>` and the bare word `INVOKE` stay clean. The other control-token patterns keep their current case rules.
5. The record lint and `memory_add` use the same patterns, so both refuse mixed-case markup with reason `model_control_token`, and neither prints the line.
6. No existing record under `docs/agents/memory/` matches the widened pattern, which an admission replay over every record confirms.

## Scope

**Problem statement:** two content-echo and pattern gaps left by 249aq.

**In scope:**

- `wf_server/memory_handlers.py` stored-field check and `_withhold_view`.
- `wave_lint_lib/constants.py` tool-call markup pattern.
- Tests in `tests/test_memory_records.py`.
- `docs/specs/mcp-tool-surface.md` and `CHANGELOG.md` sentences for the two behaviors.

**Out of scope:**

- New credential shapes (Stripe `sk_live_`, URL-embedded credentials) and invisible tag characters, which stay in 249aq's Risks.
- Case rules of the ChatML, `[INST]`, `<<SYS>>`, turn-marker and `system-reminder` patterns.
- `memory_search`, `memory_brief` and other read views, which 249aq did not change.

## Acceptance Criteria

- [x] AC-1: Fixture records, built in a temporary tree, cover each stored field.
    1. A pending candidate whose stored `source_event` holds a credential: promote, retain and rewrite refuse with the reason code, rewrite writes no new record file, and reject succeeds with `source_event` shown as `[withheld: secret]` and `withheld_reasons` naming `secret`. No serialized response contains any part of the credential.
    2. A finalized record whose stored `action_delta` or `validation_rationale` holds a credential: the `memory_validation_not_pending` response withholds that field and contains no part of the credential.
    3. A clean twin whose generated `decision-log:` source event has a change slug ending in `-token` (lint-clean under `_memory_forbidden_match`) is promoted, and its view returns every field unchanged; after a reject, the view shows the caller's new `action_delta` and `validation_rationale` unchanged.
- [x] AC-2: A fixture record whose `memory_id` slug and filename carry an id-compatible credential shape (`xoxb-` or `sk-proj-`): a reject response withholds `memory_id` and `path` in the view, and a forced write failure and a forced unparseable updated record each return a response with no part of the credential. A record with a clean id and a credential-shaped filename withholds `path` only.
- [x] AC-3: `memory_line_reasons` returns `model_control_token` for `<INVOKE name="x">`, `</Invoke>`, `<Function_Calls>`, `<ns:TOOL_USE>` and `<PARAMETER name="a">`, and returns nothing for `<invoker>`, `<PARAMETERS>`, `<Tool_Calls>`, `the INVOKE step` and `a < INVOKE b`. `memory_add` refuses a summary with `<INVOKE name="x">` by reason without echo, and the record lint names the reason for a record file carrying it.
- [x] AC-4: An admission replay over every record under `docs/agents/memory/` reports 0 content reasons before and after across every field this change checks (title, summary, refs, `action_delta`, `validation_rationale`, `source_event` through the lint checker, id and filename), and `git status --porcelain docs/agents/memory` stays empty.
- [x] AC-5: The touched test files pass under the default profile and `--profile second`, and the full suite passes.

## Tasks

- [x] Extend the stored-field check and `_WITHHELD_VIEW_KEYS` in `memory_handlers.py`, checking `source_event` through `_memory_forbidden_match`; check each view against the record it was built from; make promote, retain and rewrite refuse on the new fields; withhold a matching id or path from the fallback and diagnostic text.
- [x] Make the markup tag-name group case-insensitive in `constants.py`.
- [x] Add the AC-1 to AC-3 tests to `tests/test_memory_records.py`, each failing before its fix.
- [x] Update `docs/specs/mcp-tool-surface.md`: the `memory_validate` bullet's stored-refs clause, which now documents both the 249aq and the 24885 stored-field sets and the `[withheld: <codes>]` view, and the `model_control_token` text in Content reasons, which says tag names match case-insensitively. Add a CHANGELOG bullet in the style of the 249aq entry.
- [x] Run the AC-4 replay and the AC-5 suites.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| withhold-and-case | implementer | — | One workstream; shares `memory_handlers.py` and `test_memory_records.py` with `246to`, so it runs in the same implementer session. |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`, `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`, `.wavefoundry/framework/scripts/tests/test_memory_records.py`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: the change tightens two existing checks inside the memory admission path that `docs/architecture/cross-cutting-concerns.md` already describes; no boundary, flow or verification layer changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Closes the stored-field echo path. |
| AC-2 | required | Closes the id slug echo path. |
| AC-3 | required | The case-insensitive markup check. |
| AC-4 | required | Proves no existing record is newly refused. |
| AC-5 | required | Change-local and full-suite verification. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned from the two `249as` delivery-council DECLINE items, which the operator moved to wave `249ar` on 2026-11-24. | `docs/waves/249as memory-admission-hardening/evidence/249as-work.tar.gz` (`review/council-chair-delivery.md`). |
| 2026-11-24 | Readiness repair cycle 2 for the four findings recorded against this change (context `249ar-planner-repair-24885`): Requirements 1 to 3, AC-1, AC-2, AC-4 and Tasks rewritten per the Decision Log row of the same date. | `wf_review_event` repair_start records; reviewer notes `.wavefoundry/work/249ar/review/*-readiness-24885.md`. |
| 2026-11-24 | Readiness repair cycle 3 for `rt-24885-rewrite-residual-stored-echo` (context `249ar-planner-repair-24885-r3`), recorded here so the reviewed Requirements stand unchanged. Requirement 2's "every record view" and "no response repeats the matched text" bind two named paths. (1) `rewrite_record`, fresh or reused from a prior partial rewrite, is a record view checked against the record it was built from, and each matching field is withheld. (2) The `memory_rewrite_anchor_dropped` refusal (`_anchor_refusal`) leaves out of `original_anchors` and its message every stored ref that matched the stored check. Each path gets an AC-1 test that fails before the fix. Implementation notes from the round-2 DO advisories: Requirement 3's "the same as for a matching stored title or summary" means as promote and retain already refuse those; rewrite still proceeds on a stored title, summary or ref, because it replaces them with caller-checked values, and one assertion pins that; the handler renders the `Source event:` line with the same f-string `memory_records` uses when writing the record, so `_DECISION_LOG_SOURCE_EVENT_RE` matches; the handler does not copy the lint's prohibition-line skip; the Content reasons bullet in `docs/specs/mcp-tool-surface.md` says the decision-log hash separator is the only source-event exemption; the AC-1.3 clean twin and the AC-3 negatives are controls that pass before the fix. | Red-team probes B and C in `.wavefoundry/work/249ar/review/red-team-readiness-24885-r2.md`; round-2 lane notes in the same folder. |
| 2026-11-24 | Implemented, context `249ar-implementer`, in the same session as `246to`. `memory_handlers._stored_record_reasons` checks title, summary, refs, `action_delta`, `validation_rationale`, `memory_id` and the repo-relative path with `forbidden_content_reasons`, and `source_event` with `wave_validators._memory_forbidden_match` on `` f"Source event: `{source_event}`" ``, the f-string `render_memory_record` writes; the lint's prohibition-line skip is not copied. `_WITHHELD_VIEW_KEYS` adds the five fields. Promote and retain refuse on any stored match (so a matching id or path also refuses them, a consequence of the existing refusal; reject stays the recovery); rewrite refuses only on `action_delta`, `validation_rationale` or `source_event` and still proceeds on a matching title, summary or ref, pinned by `test_ac1_rewrite_proceeds_on_a_matching_stored_title`. Each view is checked against the record it was built from: the not-pending view against the stored record, the success view against the updated record, and `rewrite_record`, fresh or reused, against its own record. The unparseable fallback withholds a matching id, and `memory_validation_write_failed` names only the exception type when the id or path matched. `_anchor_refusal` still refuses when every resolving anchor is withheld (carry-forward 6), leaves matching anchors out of `original_anchors` and its message, says how many were withheld and reports `withheld_anchor_count`. `MEMORY_CONTROL_TOKEN_PATTERNS` puts the prefix and tag names in one inline `(?i:...)` group, so the other patterns keep their case rules. Controls: the AC-1.3 clean twin, the rewrite-on-title pin and the AC-3 negatives pass before the fix by design; every other new test failed on a `git archive HEAD` copy. | `tests/test_memory_records.py` `MemoryStoredFieldWithholdTests` and `MemoryMarkupCaseTests`; `.wavefoundry/work/249ar/evidence/fail-before-fix.txt`. |
| 2026-11-24 | AC-4 replay over the 197 parseable records under `docs/agents/memory/` (live and archive): 0 content reasons on every checked field with the HEAD code and with the changed code, and 0 `model_control_token` hits over 7072 lines of every file there; `git status --porcelain docs/agents/memory` empty. Docs: the `memory_validate` stored-fields bullet and the Content reasons bullet in `docs/specs/mcp-tool-surface.md` (both stored-field sets, `[withheld: <codes>]`, case-insensitive tag names, the decision-log hash separator as the only source-event exemption) and a `CHANGELOG.md` Fixed bullet. AC-5: touched files pass under the default profile and `--profile second` (see the `246to` verification row); the full suite is for the coordinator. | `.wavefoundry/work/249ar/evidence/ac4_replay.py`, `ac4_replay.txt`. |
| 2026-11-24 | Delivery note 4 (qa 2, coordinator DO): AC-2's "credential-shaped filename" is tested as a credential-shaped parent folder (`docs/agents/memory/<token>/mem-nested-clean.md`), because record lookup by id requires the filename stem to equal the id, so a clean id with a credential-shaped file name cannot be loaded. The reachable form, a clean id under a credential-shaped path, withholds `path` only. | `MemoryStoredFieldWithholdTests.test_ac2_matching_id_and_path_are_withheld_from_every_surface`. |
| 2026-11-24 | Operator sign-off and close. The work folder `.wavefoundry/work/249ar/` (briefs, implementer scripts, review notes, test logs and measurement evidence) is archived at `evidence/249ar-work.tar.gz`, so every `.wavefoundry/work/249ar/` path cited above resolves inside that archive. | `wf_review_event` operator-signoff, context `249ar-operator-signoff`; `evidence/249ar-work.tar.gz`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | A separate change in wave `249ar`, not new requirements in `246to`. | The items belong to admission hardening, not maintenance signals, and a separate spec keeps both reviews legible. | Fold into `246to`. |
| 2026-11-24 | Withhold a matching `memory_id` in the view rather than refuse the call. | Reject must stay available to remove such a record. | Refuse every verdict. |
| 2026-11-24 | Readiness repair: check `source_event` through the lint's `_memory_forbidden_match`; rewrite refuses on a matching stored field; each view is checked against the record it shows; `memory_id` and `path` are withheld from every response surface. | Findings `cr-24885-source-event-lint-exemption-and-rewrite-inherit`, `24885-source-event-exemption`, `24885-rewrite-copies-source-event` and `rt-24885-rewrite-propagates-stored-source-event`, and the reviewers' DO advisories. | Let rewrite drop the source event; withhold by the stored check on every view. |
| 2026-11-24 | DECLINE: withholding `pointer_to`, `superseded_by`, `archive_path` and `archive_reason`. | They are tool-written and not set on a pending record; an archived record exits through the not-pending view. | Check every view field. |
| 2026-11-24 | DECLINE: a `docs/architecture/cross-cutting-concerns.md` edit. | It names no case rule or withholding behavior. | Add a sentence there. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Case-insensitive tag names flag prose that writes a tag in capitals. | The leading `<` and word boundary stay required; AC-4 replays every record. |
| A withheld `memory_id` leaves the caller unsure which record answered. | The caller supplied the id; the response keeps `validated` and `verdict`. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
