# Signatures For Every Tool Entry

Change ID: `237ek-enh signatures-for-every-tool-entry`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-12
Wave: `237ei tool-reference-and-guru-description-follow-ups`

## Rationale

Change `237eh` made `docs/specs/mcp-tool-surface.md` the enforced tool inventory. Its index test (`test_tool_spec_index_matches_registration` in `test_server_tools.py`) checks each tool's main signature against the registered input schema. A definition bullet (`` - `name` — description ``) also counts as a main entry, and a bullet has no parameters to check (237eh Requirement 3.1). The `237ef` ledger recorded this as DEFBULLET-DEL-1 (`dont_do_later`).

Measured with the test's own parser, 19 registered tools are documented only by a definition bullet, so the spec can name a wrong, missing or renamed parameter for them without failing:

1. `code_callgraph`, `code_callhierarchy`, `code_commit_provenance`, `code_constants`, `code_definition`, `code_dependencies`, `code_graph_community`, `code_graph_path`, `code_hover`, `code_impact`;
2. `code_keyword`, `code_lexical`, `code_list_files`, `code_outline`, `code_pattern`, `code_read`, `code_references`, `code_risk_score`;
3. `wf_graph_report`.

These are the code-navigation tools agents call most often, so their parameters are the ones most worth getting right.

Separately, the `237ef` delivery council found two parser rules in the test redundant on the final tree. They are the cycle-5 continuation pattern `_TOOL_SPEC_CONTINUATION` and the cycle-6 accepted-parameter check in `_tool_spec_continues`. The cycle-7 and cycle-8 rule in `_tool_spec_signature_end`, which requires the closing paren to end the code span, now catches every case they caught, and removing them still passes both index tests. Redundant rules make the parser harder to trust and maintain.

## Product Intent

Agents and maintainers who read the tool reference get parameter lists, checked against the server, for every registered tool outside the `wf_new_<kind>` family, and the test that enforces it is simpler and has no silent-pass gap for unparseable arguments. Before: 19 tools, including most code-navigation tools, have no checked parameters, and the parser carries two rules that do nothing. After: every tool except the `wf_new_<kind>` family has a checked main signature, and the parser keeps only rules a known-bad control needs. Boundary: the spec and the test only; no tool or handler changes. AC-1 and AC-2 test the intent.

## Requirements

1. **A signature for every tool.** Give each of the 19 tools in the Rationale a main signature listing exactly the parameter names its registered input schema accepts, written from the schema and handler (types and defaults as registered). Turn each definition bullet into a signature bullet that keeps the existing description (`` - `name(params)` — description ``), in the same section, so each Tool Index row still names the right heading.
2. **Definition bullets stop counting as main entries.** For every registered tool except the `wf_new_<kind>` family, the index test requires the main entry to be a signature. A tool whose only entry in its section is a definition bullet fails with a problem naming the tool.
3. **Parse every argument strictly.** Today `_tool_spec_arg_names` silently drops an argument that does not start with a parameter name, and it reads only how an argument starts. So these pass on one line: `` `code_read(path: str, the bogus_flag: bool)` ``, `"bogus"=1`, `path: str bogus_flag: bool` (a missing comma hides `bogus_flag` inside the type of `path`), and `**bogus_flag`. Every top-level argument part must match the strict form `name[*] [: type] [= default]`, with no further top-level `:` or `=` after the name's own. The only other accepted part is a bare `...` placeholder. Any other part is a problem naming the tool and the argument text. The `**` exemption is dropped, because the spec has no `**` argument. A usage form's literal value such as `event="list"` already fits the form as `name=default`. This closes the gap on one line and in wrapped signatures alike.
4. **Remove the redundant parser rules.** With Requirement 3 in place, remove `_TOOL_SPEC_CONTINUATION` and the accepted-parameter check from the wrapped-signature loop. A wrapped signature then continues until its closing paren, and the scan stops at a blank line, a heading or a fence. That stop only bounds the scan; it detects nothing, because an unclosed signature already rescans from its next line and `_tool_spec_signature_end` rejects a span that crosses a backtick. If any known-bad control fails without a removed rule, keep that rule and record the control that needs it in the Progress Log. Update the parser docstring and the in-loop comment to describe the remaining rules, including that the stop is a bound, not a check.
5. **Profiles.** The index tests run, not skip, in the default, declared and second profiles.

## Scope

**Problem statement:** 19 tools have unchecked parameters in the enforced tool reference, and its parser carries redundant rules.

**In scope:**

- `docs/specs/mcp-tool-surface.md`: signatures for the 19 tools
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: the main-entry rule, the parser simplification and controls

**Out of scope:**

- Tool, handler or registration changes
- Tool descriptions served by the server (change `237el`)
- The Tool Index summaries, which follow the registered descriptions

## Acceptance Criteria

- [x] AC-1: Each of the 19 tools has a main signature listing exactly its accepted parameters, and the index test passes, in the default, declared and second profiles without skipping. The code-reviewer cross-checks each new signature against the registered schema and handler and records one line per tool in the Progress Log.
- [x] AC-2: Known-bad controls fail the index test for each of these:
   1. a tool documented only by a definition bullet;
   2. a missing parameter in one of the new signatures;
   3. an invented parameter in one of the new signatures;
   4. a prose-led argument on one line (`path: str, the bogus_flag: bool`);
   5. the same argument in a wrapped signature, both mid-line after an accepted name and leading its own continuation line;
   6. a quoted argument name (`"bogus"=1`);
   7. a missing comma on one line (`path: str bogus_flag: bool`);
   8. a missing comma before a wrapped line holding an invented parameter;
   9. a `**bogus_flag` argument.

   The Progress Log records, from a scratch copy, which controls pass silently on today's parser and which pass silently with the two rules removed but without Requirement 3. The existing controls, including the unclosed-signature controls, still fail as before. Each new control is named in the Progress Log.
- [x] AC-3: `_TOOL_SPEC_CONTINUATION` and the accepted-parameter check are gone, or a kept rule's Progress Log entry names the control that fails without it. The parser docstring and in-loop comment describe only the rules that remain, and say the blank-line, heading or fence stop is a bound, not a check.
- [x] AC-4: The edited documents validate, and the change's tests pass in the default and declared profiles.

## Tasks

- [x] Write the 19 signatures from each tool's registered schema and handler.
- [x] Open `framework_edit_allowed`; make signatures the required main form; remove the redundant rules; add controls; close the gate.
- [x] Run the index tests in the default, declared and second profiles and full docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| spec-and-test | implementer | — | Signatures, the main-entry rule and the parser simplification |


## Serialization Points

- `docs/specs/mcp-tool-surface.md`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

N/A: documentation and one test, with no boundary, flow or verification-architecture impact.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The intent: checked parameters for every tool |
| AC-2 | required | Proves the new rule detects the gap |
| AC-3 | required | The parser simplification |
| AC-4 | required | Validation |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-12 | Planned from `237ef` follow-ups DEFBULLET-DEL-1 and the council's redundant-layer note. The 19 tools were listed by running `parse_tool_spec` over the spec with the live base registry. | Scratch census over `test_server_tools.parse_tool_spec` |
| 2026-11-12 | Readiness review round 1 amendments. Red-team RT-1 (medium): removing `_TOOL_SPEC_CONTINUATION` alone would let an invented parameter inside a wrapped signature pass, because `_tool_spec_arg_names` drops argument parts it cannot parse, a gap already open on one line. Added Requirement 3 and AC-2 controls 4 to 6. QA-RDY-6: the stop rule is stated as a bound, not a check. Code CR-EK-1 and CR-EK-2, QA and red-team confirmed the 19-tool list and that both index tests pass with the two rules removed. | `.wavefoundry/work/237ei/redteam-readiness.md`, `qa-readiness.md`, `code-readiness.md` |
| 2026-11-12 | Readiness review round 2 amendments. Red-team RT2-1 (medium): Requirement 3 checked only how an argument starts, so a missing comma hid an invented parameter in the previous argument's type, and removing the accepted-parameter check would make the wrapped form silent. Requirement 3 now uses red-team's strict-form alternative, which also covers RT2-3 (the literal-value exemption is no longer needed) and RT2-4 (`**` arguments). Added controls 7 to 9 and both forms of control 5 (QA advisory A1). Code CR2-EK-1 and RT2-2: the claim that controls 4 to 6 pass silently today was false for control 5, so AC-2 now asks the Progress Log to record which controls are silent today and which only after the rules are removed. | `.wavefoundry/work/237ei/redteam-readiness-r2.md`, `code-readiness-r2.md`, `qa-readiness-r2.md` |
| 2026-11-12 | Readiness round 3: code, QA and docs-contract PASS on receipt `review-policy-930b8ca5639151606138`. Red-team RT3-1 (medium), with QA A3 and code A1: free-form type and default text still absorbs a bare name after a missing comma (`path: str bogus_flag`, `path="x" bogus_flag`, and the wrapped forms). Implementation commitment, read as Requirement 3's meaning of `type` and `default`: a type is names joined by `\|`, each optionally followed directly by one bracket group; a default is one literal, name, bracket group or `...`. Anything else in either position is a problem. Controls are added for the one-line bare-name case, the wrapped bare-name case and a wrapped prose line, named in this log beside AC-2's nine. Code A2: the empty argument part of a zero-argument signature stays skipped. Placeholder masking for quotes must not use an identifier character (red-team pitfall; control 6 guards it). RT3-2 (a name inside a subscript, such as `list[str, bogus_flag: bool]`) is left to the AC-1 per-tool schema cross-check. | `.wavefoundry/work/237ei/redteam-readiness-r3.md`, `code-readiness-r3.md`, `qa-readiness-r3.md`, `docs-readiness-r3.md` |
| 2026-11-12 | Implemented. The 19 definition bullets in `## Navigation Tools` became signature bullets, generated from each registered input schema (Python-style defaults) and kept in place, so no Tool Index row moved. `test_server_tools.py`: `_tool_spec_arg_names` now returns names and unparseable arguments under the committed grammar (`_tool_spec_parse_arg`, `_tool_spec_is_type`, `_tool_spec_is_default`, `_tool_spec_close_group`, `_tool_spec_split_top`); the empty part of a zero-argument signature and a bare `...` stay skipped; quotes are tracked by the splitter, not masked, so no placeholder can parse as a name. `_TOOL_SPEC_CONTINUATION` and `_tool_spec_continues` are removed: no control needed either. A wrapped signature continues to its closing paren, and a blank line, heading or fence bounds the scan; the comment says the bound detects nothing. `tool_spec_problems` reports `main: ... is a definition bullet` and `argument: ... has unparseable argument`. The live spec yields no problems. | `run_tests.py`, six files, three profiles |
| 2026-11-12 | AC-2 controls, all in `test_tool_spec_index_known_bad_controls`, each reported after the change: (1) definition bullet as main entry; (2) new signature missing a parameter; (3) new signature with an invented parameter; (4) prose-led argument on one line; (5a) prose-led argument wrapped mid-line; (5b) prose-led argument leading a wrapped line; (6) quoted argument name; (7) missing comma before a typed name; (8) missing comma before a wrapped invented parameter; (9) double-star argument; plus the RT3-1 commitments: X1 missing comma before a bare name, X6 missing comma after a default, X2 bare name on a wrapped line after a missing comma, X10 wrapped prose line. Thirteen legitimate shapes pass (quoted defaults with `=` or `:`, `dict[str, int] = {}`, `Literal[...]`, `str \| None`, `-1`, `path="list"`, `path=...`, `rewrite_*`, `memory_ids=[...]`, `applicability=null`, `...`, empty). Silent-pass record from the pre-wave tree, measured by the readiness reviewers in scratch copies (`code-readiness-r3.md` table; `redteam-readiness-r3.md` for X1, X2, X6, X10): today 4, 5a, 6, 7, 9, X1 and X6 are silent, and 5b, 8, X2 and X10 are reported as unclosed; with the two rules removed and no Requirement 3, 5b, X2 and X10 also go silent, and 8 is reported only as a missing parameter. The after-change column was measured on this tree. | `.wavefoundry/work/237ei/code-readiness-r3.md`, `redteam-readiness-r3.md`; scratch `237ek-silent/after.py` |
| 2026-11-12 | Gapfill: implementation of all three wave changes used harness reads, `grep` and `git log` rather than the MCP `code_*` tools. The edit sites were already pinned to exact symbols and lines by the three readiness rounds, so each step was a targeted read of a known region, a git-history census (which the MCP tools do not cover) or an executed probe. The 237el implementer subagent used the MCP retrieval tools. Delivery reviewers are briefed MCP-first. | wave `retrieval_posture_gap` advisory |
| 2026-11-12 | AC-1 code-reviewer cross-check (delivery): each of the 19 new signatures matches the registered schema and the handler in names, order, types, defaults and required-ness: `code_callgraph`, `code_callhierarchy`, `code_commit_provenance`, `code_constants`, `code_definition`, `code_dependencies`, `code_graph_community`, `code_graph_path`, `code_hover`, `code_impact`, `code_keyword`, `code_lexical`, `code_list_files`, `code_outline`, `code_pattern`, `code_read`, `code_references`, `code_risk_score`, `wf_graph_report`; verdict match for all 19 (per-tool table in the artifact). Red-team independently confirmed the same and that each bullet's description text is byte-identical. Strict-grammar delivery checks X1, X2, X6, X10, `"bogus"=1`, `**` and missing commas are reported. Accepted residual, not introduced by this wave: a name inside a bracket group in a type or default, and a `prefix*` wildcard standing in for names (RT-DEL-3, RT-DEL-4, CODE-DEL-A1). Tests: five touched files, 855 tests, default and declared no skips; second one existing profile skip. | `.wavefoundry/work/237ei/code-delivery.md`, `redteam-delivery.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-12 | Convert bullets in place to signature bullets | Keeps each description and section, so Tool Index rows do not move | Add separate signature lines above each bullet (duplicates the entry) |
| 2026-11-12 | Remove the redundant rules, keeping one only if a control needs it | The council found them redundant; the controls decide | Pin them with new controls (keeps rules that do nothing) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A new signature misstates a type or default the test does not check | Code-reviewer per-tool cross-check against schema and handler (AC-1) |
| Removing a rule reopens a gap the controls do not cover | Unparseable arguments become problems first (Requirement 3); every existing control must still fail, and a failing control keeps its rule (Requirement 4) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
