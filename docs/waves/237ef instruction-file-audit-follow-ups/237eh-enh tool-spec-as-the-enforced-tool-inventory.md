# Tool Spec As The Enforced Tool Inventory

Change ID: `237eh-enh tool-spec-as-the-enforced-tool-inventory`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-12
Wave: `237ef instruction-file-audit-follow-ups`

## Rationale

The `/doctor prompt-audit` (finding F1) flagged the `**Available tools:**` list in `AGENTS.md`: 92 tool names loaded into every session, duplicating the tool list the host already gives the model. Checked against the tree, the list turns out to be this repository's only complete tool inventory. `test_agents_available_tools_census_matches_registration` in `test_server_tools.py` forces it to equal the live registration. Meanwhile `docs/specs/mcp-tool-surface.md`, which `AGENTS.md` names as the tool reference, has no completeness check and has drifted:

1. Measured against Requirement 2's entry forms, 17 registered tools have no detailed entry: `memory_add`, `memory_brief`, `memory_search`, `wf_open_gate`, `wf_close_gate`, `wf_gate_status`, `wf_get_handoff`, `wf_set_handoff`, `wf_run_sensors`, the four dashboard tools (`wf_start_dashboard`, `wf_stop_dashboard`, `wf_restart_dashboard`, `wf_open_dashboard`), `code_dependencies`, `code_graph_community`, `index_build_status` and `wf_gpu_doctor`. Several are discussed in prose or named in a table; none has an entry.
2. Its tool documentation has no single list. Entries take several forms (signature lines, definition bullets, table rows, a family row for `wf_new_<kind>`) and sit in several sections, so 16 registered tools are documented only outside `## Current Tool Surface` and `## Navigation Tools`.
3. Measured with Requirement 3's main-signature rule, five tools' main signatures disagree with the registered schema: `wf_validate_docs(mode: str = "run")` documents a parameter the tool does not take, `code_search` omits `graph`, `graph_limit` and `layer`, and `memory_reconcile` omits `superseded_by`. For `wf_review_event` and `memory_consolidate` the first form in `### Lifecycle Mutations` (a section with no subheadings) is a mode-specific call, `wf_review_event(event="list")` and `memory_consolidate(mode="dry_run", limit=10)`, so no complete signature currently comes first.

Signature lines for non-tools such as `list_waves` and `migrate_journals` are legitimate Python helper signatures in `## Distribution Extension Tools`, not stale tool entries.

Deleting the `AGENTS.md` list would therefore lose the only accurate inventory, and keeping it leaves the reference people read incomplete. The operator directed doing the correct, accurate thing regardless of cost.

## Product Intent

Agents and maintainers who look up a Wavefoundry MCP tool find every registered tool documented in the tool reference, and a tool added, renamed or removed without updating that reference fails the suite. Sessions in this repository stop loading a 92-name list the host already provides. Before: the complete list lives in `AGENTS.md`, and the spec has no detailed entry for 17 tools. After: the spec carries one Tool Index that exactly matches the registration, every tool has an accurate detailed entry, and `AGENTS.md` points to the index. Boundary: documentation and one test; no tool, handler or registration changes. AC-1 and AC-2 together test the intent.

## Requirements

1. **A tool index.** Add a `### Tool Index` table at the start of `## Current Tool Surface` in `docs/specs/mcp-tool-surface.md`, with exactly one row per first-party tool registered on the shipped base declaration, including each `wf_new_<kind>` member and the retired-but-registered `wf_new_feature`. Columns:
   1. the tool name;
   2. its tier, as `mcp_tool_roster.all_tool_tiers()` reports it after the base declaration is applied;
   3. its summary, which is the first sentence of the registered tool description (whitespace normalized), so the summary cannot drift from what the server tells the model;
   4. the exact text of the spec heading that holds the tool's detailed entry.
2. **A detailed entry for every tool.** A section is the span from a heading to the next heading of the same or higher level. Each indexed tool has a detailed entry in the section its row names, in one of these forms:
   1. a signature at the start of a line or of a list item (`` `name(params)` `` or `` - `name(params)` ``), including a second signature joined on the same line (`` … and `name(params)` ``) and a signature whose parameter list wraps onto following lines;
   2. a definition bullet (`` - `name` — description ``);
   3. for the `wf_new_<kind>` members, the family row in Core Verbs.

   A table row elsewhere in the spec is not a detailed entry, so under this rule the 17 tools listed in the Rationale need new entries today. Each tool has exactly one **main signature**: the first signature or definition bullet for that tool in the section its index row names. For `wf_review_event`, `memory_consolidate` and `memory_reconcile`, whose first form in their section today is a mode-specific call, add a complete signature placed before those forms, so the mode-specific calls become ordinary usage forms. Write each from the registered tool's input schema and description and the handler's behavior, not invented, in the section that owns the tool's domain. A prose call inside a sentence (for example `wf_prepare_wave(create)`) is not an entry.
3. **Accurate signatures.**
   1. Each tool's main signature (Requirement 2) lists exactly the parameter names the registered input schema accepts: none missing and none extra, where a documented wildcard such as `rewrite_*` matches by prefix. A definition bullet or the `wf_new_<kind>` family row is not checked for parameters.
   2. Every other signature of a registered tool in the spec (usage examples such as `code_search(query=..., language=...)`, mode-specific forms, calls with a literal value such as `event="list"`, or a `...` placeholder) may show a subset of the parameters, but may not name a parameter the schema does not accept. A bare `...` argument is a placeholder, not a parameter name.
   3. Correct the five existing main-signature mismatches named in the Rationale, including the complete signatures Requirement 2 places first.
4. **Accurate behavior.** Each new detailed entry's description of modes, side effects and read or write behavior is cross-checked against the tool's handler during delivery review by the code-reviewer lane, which records one line per tool in the Progress Log (tool, handler, verdict). A reviewer finding of a behavior mismatch is a delivery blocker.
5. **Move the enforcement.** Replace `test_agents_available_tools_census_matches_registration` with a test that boots the shipped base declaration, as today, and fails when:
   1. the index's tool names are not exactly the registered set;
   2. an index row's tier differs from `mcp_tool_roster.all_tool_tiers()`;
   3. an index row's summary differs from the first sentence of the registered description;
   4. an index row names a heading that does not exist exactly once, or whose section holds no detailed entry for that tool under Requirement 2's forms;
   5. a tool's main signature omits a parameter the schema accepts or names one it does not accept;
   6. any other signature of a registered tool names a parameter the schema does not accept.

   The test must run, not skip, in the default, declared and second profiles; an `ImportError` skip does not count as passing.
6. **Point `AGENTS.md` at the index.** Replace the `**Available tools:**` paragraph with one sentence naming `docs/specs/mcp-tool-surface.md` § Tool Index as the complete tool reference and `wf_help` for discovery. Keep the surrounding MCP Server text.
7. **Retarget every reader of the removed paragraph.** An executable census found the readers: in a scratch copy with the paragraph replaced, every test file that reads `AGENTS.md` was run. Two tests depend on it:
   1. `test_agents_available_tools_census_matches_registration`, replaced by Requirement 5;
   2. `test_shipped_reference_docs.py::test_tool_lists_and_spec_name_wf_upgrade_tools`, which asserts `AGENTS.md` names `wf_upgrade` and `wf_upgrade_status`. Retarget its `AGENTS.md` assertion to the spec's Tool Index containing both tools, and keep its existing spec assertion.

   A third failure in the census (`test_per_area_agents_context.py`) came from the scratch copy not being a git repository and passes on the real tree. Rerun the same census on the real tree after the edit; every test file that reads `AGENTS.md` passes.

## Scope

**Problem statement:** The only complete tool inventory sits in a file loaded every session, while the designated tool reference is incomplete and unenforced.

**In scope:**

- `docs/specs/mcp-tool-surface.md`: the Tool Index, new detailed entries and corrected signatures
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: the replaced test
- `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`: the retargeted `AGENTS.md` assertion
- `AGENTS.md`: the `**Available tools:**` paragraph

**Out of scope:**

- Any tool, handler, registration or MCP behavior change
- Tool descriptions served by the server itself
- Other docs that describe tools (for example `docs/references/dashboard-install-upgrade.md`), except where an entry points to them for detail
- Seeds: no seed ships the `AGENTS.md` tool list, so target projects are unaffected

## Acceptance Criteria

- [x] AC-1: The Tool Index lists exactly the tools registered on the shipped base declaration, each with its registered tier and its registered first-sentence summary, and every row's named section holds a detailed entry for that tool. The new test fails on today's spec (no index; 17 tools with no detailed entry; 5 main-signature mismatches) and passes after the change, in the default, declared and second profiles without skipping.
- [x] AC-2: The new test fails, in known-bad controls on spec copies, for each condition in Requirement 5: a registered tool missing from the index, an index row for an unregistered name, a wrong tier, a summary that differs from the registered description, a row naming a missing or duplicated heading or a section with no entry for the tool, a main signature missing a parameter (on one line and wrapped), a main signature with an extra parameter, and a usage example naming an unknown parameter. A further control shows that after the change the accurate usage examples (for example the `code_search` language examples, `wf_review_event(event="list")` and `memory_consolidate(mode="dry_run", limit=10)`) pass as non-main forms. Each control is named in the Progress Log.
- [x] AC-3: Every tool's main signature lists exactly the accepted parameter names, and no other signature names an unknown one; the five Rationale mismatches are corrected (`wf_validate_docs` no longer documents `mode`, `code_search` lists `graph`, `graph_limit` and `layer`, and `memory_reconcile`, `wf_review_event` and `memory_consolidate` each have a complete main signature before their mode-specific forms), enforced by the test; and the Progress Log holds the code-reviewer's per-tool behavior cross-check for every new detailed entry, with no unresolved mismatch.
- [x] AC-4: `AGENTS.md` contains no `**Available tools:**` list and its MCP Server section names `docs/specs/mcp-tool-surface.md` § Tool Index and `wf_help`, checked by an assertion; the old census test is removed; `test_tool_lists_and_spec_name_wf_upgrade_tools` asserts the Tool Index instead of `AGENTS.md`; and every test file that reads `AGENTS.md` passes on the edited tree.
- [x] AC-5: The documents this change edits validate, and the change's own tests pass in the default and declared profiles.

## Tasks

- [x] Census registered tools, tiers and input schemas on the base declaration against the spec.
- [x] Write the missing detailed entries from each tool's registered schema, description and handler, and correct mismatched signatures.
- [x] Add the Tool Index table.
- [x] Open `framework_edit_allowed`; replace the test with the index test and its known-bad controls; close the gate.
- [x] Replace the `AGENTS.md` paragraph with the pointer.
- [x] Run the focused test in the default and declared profiles and full docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| spec-and-test | implementer | — | Spec entries, stale reconciliation and the replaced test |
| agents-pointer | implementer | spec-and-test | `AGENTS.md` edit after the spec is complete |


## Serialization Points

- `docs/specs/mcp-tool-surface.md`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`
- The root `AGENTS.md` is also edited, in a different section from change `237eg-enh permit-direct-retrieval-and-trim-dated-instructions`.

## Affected Architecture Docs

N/A: the change documents the existing tool surface and moves one completeness test; no module boundary, data or control flow changes. `docs/specs/mcp-tool-surface.md` is itself the edited contract document. Behavior is identical on Windows, macOS, Linux and WSL2: the test reads text and the in-process registration only.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The reference must be complete before the `AGENTS.md` list can go |
| AC-2 | required  | Without enforcement the spec drifts again |
| AC-3 | required  | Entries must be accurate, not merely present |
| AC-4 | required  | The audit finding itself: no duplicate list loaded every session |
| AC-5 | important | Change-local validation |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-12 | Planned from audit finding F1 after the operator directed the accurate fix; census executed against the live base-declaration registration and the spec's entry forms | Session census: 92 registered, 18 without a spec entry, several unregistered signature entries |
| 2026-11-12 | Repaired before lane review from the red-team primer: Tool Index with exact-equality test replaces the prose detector; parameter check covers every signature; non-tool helper signatures confirmed legitimate | `.wavefoundry/work/237ef/primer-237eh.md` |
| 2026-11-12 | Bounded readiness repair of READER-RDY-1 (docs-contract) and ACCURACY-RDY-1 (QA): executable census of `AGENTS.md` readers (scratch copy with the paragraph replaced; two dependent tests, one environmental false positive); retargeted `wf_upgrade` reader; summaries derived from registered descriptions; signatures equal the schema both ways; per-tool behavior cross-check at delivery; 20 tools need entries under the stated forms; non-skipping runs in all three profiles | `.wavefoundry/work/237ef/docs-237eh.md`, `qa-237eh.md`, `code-237eh.md` |
| 2026-11-12 | Second bounded readiness repair, authorized by the operator after focused verification left SIGSCOPE-RDY-1: main-signature scope for the both-ways check, unknown-parameter check elsewhere, three named real mismatches, corrected counts (17 tools, 5 long summaries) | `.wavefoundry/work/237ef/qa-237eh-reverify.md`, `code-237eh-reverify.md` |
| 2026-11-12 | Follow-up repair authorized by the operator after QA and code measured 5 main-signature mismatches: complete main signatures placed first for `wf_review_event`, `memory_consolidate` and `memory_reconcile`; AC-2's usage-example control restated as after the change. Implementation notes: `code_search` `limit` default is 7 in the schema and 5 in the spec | `.wavefoundry/work/237ef/qa-sigscope-reverify.md`, `code-sigscope-reverify.md`, `docs-final.md` |
| 2026-11-12 | Readied on receipt `review-policy-3644fe6b6c58a9425d1e`: code, QA and docs-contract approvals current; all four findings terminal; `council-readiness` intent fit `establishes`. Implementation notes, non-blocking: (1) the test does not check that each new entry sits in its domain's section, so place each of the 17 entries in the section that owns its domain and have the delivery code-reviewer confirm placement in the per-tool cross-check; (2) for `memory_reconcile`, insert the complete signature as planned rather than adding `superseded_by` to the existing form; (3) `AGENTS.md` carries uncommitted edits (the gate paragraph), so build on the working tree, not `HEAD` | `.wavefoundry/work/237ef/council-final.md`, `code-final.md`, `qa-final.md` |
| 2026-11-12 | Readback: add a `### Tool Index` (92 rows: name, tier, registered first-sentence summary, detail heading) at the start of `## Current Tool Surface`; write detailed entries for the 17 undocumented tools from schema, description and handler in their domain sections; fix the 5 main-signature mismatches, placing complete signatures first for `wf_review_event`, `memory_consolidate` and `memory_reconcile` (AC-1, AC-3); replace the `AGENTS.md` census test with an index test plus known-bad controls (AC-2); replace the `**Available tools:**` paragraph with a pointer and retarget `test_tool_lists_and_spec_name_wf_upgrade_tools` (AC-4). Example: adding a tool without a spec row now fails the index test instead of the `AGENTS.md` list test. Serves Product Intent by making the reference readers use the one complete, enforced inventory. Boundary: docs and tests only; no tool, handler or registration change. Files: `docs/specs/mcp-tool-surface.md`, `test_server_tools.py`, `test_shipped_reference_docs.py`, `AGENTS.md` | Plan Requirements 1 to 7 |
| 2026-11-12 | Implemented. `### Tool Index` (92 rows generated from the live base-declaration registration with the test's own helpers) is the first heading under `## Current Tool Surface`. New entries, each written from its handler in `wf_server/`: `wf_get_handoff` and `wf_set_handoff` (`edit_gate_handlers`), `memory_add`, `memory_search`, `memory_brief` (`memory_handlers`), `wf_gpu_doctor` and `wf_run_sensors` (`server_impl`, `sensor_runner`), `index_build_status` (`index_handlers`), `wf_open_gate`, `wf_close_gate`, `wf_gate_status` (`edit_gate_handlers`), the four dashboard tools (`dashboard_handlers`), `code_dependencies` (`codenav_handlers`) and `code_graph_community` (`graph_handlers`), each in its domain section. Signature fixes: `wf_validate_docs()`; `code_search` adds `graph`, `graph_limit`, `layer` with `limit` default 7; complete first signatures for `memory_reconcile` and `memory_consolidate` inserted before their existing forms; `docs_search` `limit` default corrected to 7 (opportunistic, same drift). Deviation from the literal Requirement 2 wording, AC-3 still met: for `wf_review_event` the complete 23-parameter signature replaces the old partial main form in place, and the earlier cross-tool bullet in the unreadable-records block is reworded to prose ("The read-only `wf_review_event` listing (`event="list"`)"), so the complete signature is the section's first form without being placed inside an unrelated refusal block; `wf_review_event(event="list")` remains as a usage form. Test: `test_agents_available_tools_census_matches_registration` replaced by `ServerToolRegistrationTests.test_tool_spec_index_matches_registration` and `test_tool_spec_index_known_bad_controls` (shared parser helpers at module level). AC-1 before-change: HEAD spec reports "heading 'Tool Index' found 0 times"; HEAD spec plus the index reports exactly the 17 missing entries and the 5 main-signature mismatches; current spec reports none. AC-2 controls, embedded as subtests and each observed failing: missing row, unregistered row, wrong tier, summary differs, missing heading, duplicated heading, section without an entry, main missing a parameter (one line, `wf_open_gate`; wrapped, `wf_context_efficiency_eval`), main extra parameter (`wf_validate_docs` with `mode`), usage naming unknown `languages`; after-change control: the eight `code_search` language examples, `wf_review_event(event="list")` and `memory_consolidate(mode="dry_run", limit=10)` parse as non-main forms with no problem. AC-4: the `**Available tools:**` paragraph is replaced by a pointer to `docs/specs/mcp-tool-surface.md` § **Tool Index** and `wf_help`, asserted by new `test_shipped_reference_docs.py::test_agents_md_points_at_the_tool_index_instead_of_listing_tools`; `test_tool_lists_and_spec_name_wf_upgrade_tools` asserts the Tool Index. Census on the edited real tree: all 25 test files that mention `AGENTS.md` pass (4,314 tests, 4 skips, none in this change's tests). Profiles: `test_server_tools.py` and `test_shipped_reference_docs.py` pass in default, declared and second (438 tests, 0 skipped). Docs validation passes. Notes for the delivery code-reviewer: check the dashboard state outcomes, `memory_add` id minting and refusal codes, and `wf_run_sensors`'s 120-second default timeout and shell use for string commands; `wf_run_sensors` has a read-only annotation but roster tier `write`, and the index reports the roster tier; the first-sentence rule ends at `.`, `!` or `?` followed by whitespace, correct for all 92 descriptions today | `test_server_tools.py`, `test_shipped_reference_docs.py`; controls in the session scratchpad `237eh/controls.py` |
| 2026-11-12 | Requirement 4 per-tool behavior cross-check by the delivery code-reviewer (fresh context). Tool, handler, verdict: `memory_add`, `memory_handlers._memory_add_response_locked` and `memory_records.mint_memory_id`, mismatch (validation code is `invalid_memory_record`, not `invalid_arguments`), repaired; `memory_brief`, `memory_handlers.memory_brief_response`, accurate; `memory_search`, `memory_handlers.memory_search_response`, accurate; `wf_open_gate`, `edit_gate_handlers.wave_open_gate_response`, accurate; `wf_close_gate`, `edit_gate_handlers.wf_close_wave_gate_response`, accurate; `wf_gate_status`, `edit_gate_handlers.wf_gate_status_response`, accurate; `wf_get_handoff`, `edit_gate_handlers.wf_get_handoff_response`, accurate; `wf_set_handoff`, `edit_gate_handlers.wf_set_handoff_response`, accurate; `wf_run_sensors`, `server_impl.wf_run_sensors_response` and `sensor_runner.run_sensor`, accurate; `wf_start_dashboard`, `dashboard_handlers.wf_start_dashboard_response`, accurate; `wf_stop_dashboard`, `dashboard_handlers.wf_stop_dashboard_response`, mismatch (missing the `dashboard_lock_unverified` outcome), repaired; `wf_restart_dashboard`, `dashboard_handlers.wf_restart_dashboard_response`, accurate; `wf_open_dashboard`, `dashboard_handlers.wf_open_dashboard_response`, accurate; `code_dependencies`, `codenav_handlers.code_dependencies_response`, accurate; `code_graph_community`, `graph_handlers._code_graph_community_response_pinned`, mismatch (`hub_label` never returned; `generated` node field omitted), repaired; `index_build_status`, `index_handlers.index_build_status_response`, accurate; `wf_gpu_doctor`, `server_impl.wf_gpu_doctor_response`, accurate. All 17 entries are in the section that owns their domain. The three repairs (finding SPECBEHAVIOR-DEL-1) await the code-reviewer's reverification | `.wavefoundry/work/237ef/code-delivery.md` |
| 2026-11-12 | Delivery repair cycle (findings SPECBEHAVIOR-DEL-1, PARSER-DEL-1): three spec entries corrected from handler code; `parse_tool_spec` now ends a wrapped signature at a blank line, heading or fence and reports an unclosed signature (`signature: <tool> (line N) has no closing parenthesis`), with a new `unclosed signature` control in `test_tool_spec_index_known_bad_controls` that also proves an invented parameter before and after the unclosed form is still caught. Landing: deleting the new stop condition on a scratch copy fails that control. Accepted as dont_do_later with promotion triggers: DEFBULLET-DEL-1 (19 definition-bullet tools are not parameter-checked, as Requirement 3.1 allows), SKIPPATH-DEL-1 (the sibling-test `ImportError` skip path; 0 skips in every profile), INDEXSUMMARY-DEL-1 (summaries copy registered descriptions, some with lifecycle IDs) | Repair mutant run in the session scratchpad `237ef-repair-mut` |
| 2026-11-12 | Code-reviewer reverification (fresh context): SPECBEHAVIOR-DEL-1 and PARSER-DEL-1 resolved; all 17 new entries accurate against their handlers (AC-3 cross-check complete). Second repair cycle for its new finding PARSER-DEL-2 (an unclosed signature followed directly by prose with a stray `)` swallowed that paragraph): a wrapped signature now continues only through lines that read as parameter text (`name: type`, `name=value`, `name,`, `...` or `)`), and a new `unclosed signature before prose` control reports it. Landing: restoring the blank-line-only rule on a scratch copy fails that control; the real spec still parses with every wrapped main signature exact | `.wavefoundry/work/237ef/code-reverify-delivery.md`; scratchpad `237ef-c5-mut` |
| 2026-11-12 | Code-reviewer cycle-5 reverification: PARSER-DEL-2 resolved (all 85 real closing-paren deletions reported; every real wrapped signature parses). Its residual PARSER-DEL-3 (prose starting like parameter text, such as `Note:`, could still continue an unclosed signature) was introduced by this wave's parser, so the ledger requires it fixed now. Third repair cycle: `_tool_spec_continues` also requires a continuation line's leading name to be one of that tool's accepted parameters (prefix for `name*`), using the registry `tool_spec_problems` already passes; new `unclosed signature before parameter-like prose` control. Landing: removing the parameter check on a scratch copy fails that control | `.wavefoundry/work/237ef/code-reverify-c5.md`; scratchpad `237ef-c6-mut` |
| 2026-11-12 | Code-reviewer cycle-6 reverification: PARSER-DEL-3 resolved (85 of 85 real closing-paren deletions reported). Its residual PARSER-DEL-4 (prose led by a real parameter of the same tool, plus a stray `)`, could still close an unclosed signature) was also wave-introduced, so a fourth cycle applied the reviewer's class-ending fix: a signature counts as closed only when its closing paren ends the code span (is followed by a backtick), for every line-start signature. New control `unclosed signature before prose led by a parameter`. Landing: dropping the backtick rule on a scratch copy fails that control; the real spec and all index tests still pass | `.wavefoundry/work/237ef/code-reverify-c6.md`; scratchpad `237ef-c7-mut` |
| 2026-11-12 | Code-reviewer cycle-7 reverification: PARSER-DEL-4 resolved (85 of 85 deletions reported; real spec unchanged). Two remaining items were also wave-introduced: PARSER-DEL-5 (no single-line control for the backtick rule) and PARSER-DEL-6 (a later code span ending in `)` on the same line closed an unclosed signature). Cycle 8: a signature is one code span, so its argument text may not contain a backtick; two single-line controls (`single-line unclosed signature before prose`, `single-line unclosed signature before a code span`). Landing: limiting the rule to wrapped signatures fails both controls; dropping the no-backtick rule fails the code-span control. The reviewer's other notes are loud false reports only, not silent misses (an unclosed joined form reports a missing entry; a space before the closing backtick reports unclosed) | `.wavefoundry/work/237ef/code-reverify-c7.md`; scratchpad `237ef-c8-mut` |
| 2026-11-12 | Code-reviewer cycle-8 reverification: PARSER-DEL-5 and PARSER-DEL-6 resolved (85 of 85 deletions reported; no real signature has a backtick in its arguments). Its PARSER-DEL-7 (the ")`" clause had no control of its own, and the joined `and` tail still used the earlier close rule) is fixed in cycle 9: one helper, `_tool_spec_signature_end`, applies the close rule to line-start and joined forms; two controls (`wrapped unclosed signature without a backtick on its first line`, `unclosed joined signature`). Landing: keeping only the no-backtick clause fails the first control; giving the joined tail the bare paren match fails the second | `.wavefoundry/work/237ef/code-reverify-c8.md`; scratchpad `237ef-c9-mut` |
| 2026-11-12 | Code-reviewer cycle-9 reverification: PARSER-DEL-7 resolved; no new findings; no invented, missing or renamed parameter passes silently; code-reviewer delivery approval recorded and AC-3 marked. Delivery council PASS, intent_fit establishes. Correction to the cycle-5 and cycle-6 rows above: the council chair found those landing claims no longer hold on the final tree, because the cycle-7 and cycle-8 backtick rules (`_tool_spec_signature_end`) now catch every case the continuation layers caught; removing the cycle-5 continuation pattern or the cycle-6 parameter check in `_tool_spec_continues` still passes both index tests. Those layers are redundant, not wrong; removing them (or pinning them) is a recorded follow-up, not done in this wave | `.wavefoundry/work/237ef/code-reverify-c9.md`, `council-delivery.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-12 | Make the spec the enforced inventory and point `AGENTS.md` at it | The `AGENTS.md` list is the only complete, enforced inventory, but it is loaded every session and duplicates the host's tool list; the spec is the designated reference and has no detailed entry for 17 tools. Moving the enforcement fixes the reference and removes the duplicate. Mechanism efficacy: replaying the motivating case, a tool added without docs fails the new test instead of the `AGENTS.md` one, so drift is caught where readers look; the test controls the outcome (it fails the suite) and checks only registered tool names, so helper signatures in other sections are never flagged | Delete the list only (loses the only accurate inventory and points to an incomplete reference); keep the list (duplicate loaded every session; wrong home); add completeness to the spec but keep the list too (two inventories to maintain) |
| 2026-11-12 | An explicit Tool Index checked for exact equality with the registration, instead of detecting entries in prose (readiness primer repair) | The primer showed a prose detector is heuristic (one detector variant reports 35 missing tools, another 18) and that "Current Tool Surface is complete" would be false while a whole-spec check passed. An index makes completeness exact, like today's `AGENTS.md` test, keeps one list in the document readers use, and lets the test check tiers and detail locations without guessing | A prose entry detector over the whole spec (the first draft); pointing `AGENTS.md` at the whole spec |
| 2026-11-12 | Check parameter names on every signature line, not only new ones (primer question 2) | Accuracy is the goal; the primer found existing drift (`wf_validate_docs(mode)`) that a new-entries-only check would leave | Check only the new entries |
| 2026-11-12 | Enforce accuracy, not presence (ACCURACY-RDY-1 repair): summaries equal the registered description's first sentence, signatures equal the schema in both directions, and behavior gets a recorded per-tool handler cross-check | QA showed a false summary and a parameter-omitting signature passed every AC. The registered description is the text the server already gives the model, so deriving the summary from it makes the index accurate by construction (measured: the first sentence is well defined for all 92 tools; 5 exceed 200 characters but are accurate). Prose behavior cannot be machine-checked, so the oracle is a named reviewer cross-check with a delivery-blocking outcome | Hand-written summaries reviewed by eye; narrowing the intent claim to "present" |
| 2026-11-12 | Scope the exact both-ways parameter check to each tool's main signature; check other call forms for unknown parameters only (SIGSCOPE-RDY-1 repair, operator-authorized) | QA and code measured the unscoped rule against today's spec: 15 mismatches, 3 real (`wf_validate_docs`, `code_search`, `memory_reconcile`) and 12 accurate usage examples or mode-specific forms. Scoping keeps the omission check where a signature claims to be the tool's parameter list and still rejects invented parameters everywhere | Drop the both-ways check (loses the omission check that found `code_search` and `memory_reconcile`); keep it everywhere (fails accurate examples) |
| 2026-11-12 | Place a complete main signature first for `wf_review_event`, `memory_consolidate` and `memory_reconcile` (SIGSCOPE-RDY-1 follow-up repair, operator-authorized) | QA and code both measured the scoped rule: their first form in `### Lifecycle Mutations` is a mode-specific call, so the rule reported 5 mismatches, not 3, and an AC control could not pass. A complete signature placed first keeps the rule simple and turns the mode calls into ordinary usage forms | Pick the main signature by a "most complete form" heuristic (ambiguous); split the section with new subheadings (larger edit for the same result) |
| 2026-11-12 | A separate change in wave 237ef, not part of 237eg | Different deliverable with its own acceptance criteria; the routing-guidance change stays focused | Fold into 237eg Requirement 6 |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| New entries describe a tool inaccurately | Summaries are the registered description's first sentence (test-enforced); parameters must equal the schema (test-enforced); behavior is cross-checked per tool against the handler at delivery review |
| The detail-entry check misreads an inline call as an entry | It looks only in the section the index row names and only at line-start signatures, definition bullets and the family row |
| A distribution's declared tools would fail the test | The test boots the shipped base declaration, as the current test does; the declared profile run confirms it |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
