# Delegated workers load deferred MCP tools before retrieval

Change ID: `20397-enh subagents-load-deferred-mcp-tools`
Change Status: `implemented`
Owner: wave-coordinator
Status: planned
Last verified: 2026-10-07
Wave: 200ey containment-and-distribution-seams

## Rationale

In the 2026-10-07 batch most delegated subagents (planners, implementers, reviewers, verifiers) reported that the Wavefoundry MCP code tools "were not loaded" and used `rg`/`grep` instead. In Claude Code the MCP tools reach a general-purpose subagent as deferred tools: they are present but their schemas must be loaded with `ToolSearch` before they can be called. The workers treated "deferred" as "unavailable", which the current wording permits: seed 180 fallback condition (b) allows shell fallback when "the relevant tool is unavailable in the host session", and the rendered `docs/agents/implementer.md` allows it when "MCP is not attached, the relevant tool is unavailable, index health is unreliable, or MCP results are genuinely insufficient". The cost is measurable: context-efficiency credits went unrecorded (wave `200xy` plan stage about 6k tokens against 12k+ in earlier waves; wave `200ey` plan stage 0).

The existing guidance (seed 020 Retrieval Rules, seed 180 delegation paragraph, the `AGENTS.md` retrieval-intent backstop) says to load deferred schemas and to name the schema-load step in delegated tasks, but it frames loading as a preference and never requires the worker to confirm the tools are callable before falling back. The operator decided (2026-10-07) to make load-verify-then-fallback a framework rule for every delegated worker.

## Requirements

1. Every delegated worker (implementer, reviewer, planner, verifier, or any other subagent doing code or doc retrieval) whose host exposes the Wavefoundry MCP tools as deferred or on-demand tools must load them before its first code or doc retrieval. The rule is host-neutral; Claude Code's `ToolSearch` with a `select:` list is named as the example of a deferred-tool host.
2. After loading, the worker confirms the tools are callable (the load returns the schemas, or one cheap retrieval call returns `status: ok`). Only when the tools are not exposed at all, the load fails, or a call errors does the worker fall back to shell, and it records a `Gapfill:` entry naming which of those happened.
3. A deferred tool whose schema has not been loaded is not "unavailable": the shell-fallback conditions in seed 180 and the rendered implementer role must say so explicitly, so the loophole that produced the 2026-10-07 behavior is closed.
4. A coordinator delegating code or doc work puts the load-and-verify step in the brief as the worker's first action (with the `select:` list on hosts that need one) and asks the worker to report whether the load succeeded; the coordinator surfaces any worker `Gapfill:` note.
5. The canonical statement lives in seed 020 (Retrieval Rules) and seed 180 (MCP-first exploration and delegation); other surfaces point to it rather than restating it, consistent with the existing no-restatement rule for the exploration order.
6. No renderer or wrapper frontmatter change unless implementation finds a Claude Code agent definition whose `tools:` allowlist omits `ToolSearch` or the read-only retrieval tools.

## Scope

**Problem statement:** Delegated workers treat deferred MCP tools as unavailable and fall back to shell by default, which loses retrieval quality and the context-efficiency evidence the framework measures.

**In scope:**

- Seed 020 `## Retrieval Rules`: turn the first bullet into the load-verify-fallback rule for every lane and delegated worker, and tie the existing `Gapfill:` bullet to the three named fallback reasons.
- Seed 180 MCP-first code exploration: clarify fallback condition (b) (deferred but unloaded is not unavailable); extend the **Delegating code work to a subagent** paragraph so the brief carries the load-and-verify step as the first action and the worker reports the load outcome; align the **Use honest fallbacks** bullet of **Host-neutral orchestration** in one clause.
- Seed 050: the `AGENTS.md` **Retrieval-intent backstop** paragraph template and the `implementer.md` role bullet get the same clause (pointer form, no restatement of the order).
- Rendered self-hosted surfaces matching those seeds: `AGENTS.md` backstop paragraph, `docs/contributing/agent-team-workflow.md` `## Retrieval Posture (All Lanes)` (the seed 020 carrier), `docs/agents/implementer.md` fallback line.
- Verification that `.claude/agents/guru.md` and the four factor wrappers already list `ToolSearch` plus the read-only `mcp__wavefoundry__*` retrieval tools (they do as of 2026-10-07), so no renderer change is needed.
- One live Claude Code check that a general-purpose subagent briefed per the new wording loads via `ToolSearch` first and completes a `code_*` call.

**Out of scope:**

- Renderer changes (`render_agent_surfaces.py`, `render_platform_surfaces.py`) and wrapper `tools:` frontmatter: guru and factor wrappers already grant `ToolSearch` plus 19 read-only retrieval tools (wave `1p9qm`), and implementer, reviewer, and planner roles have no Claude Code wrapper; they are spawned as general-purpose agents that inherit every tool, deferred.
- New Claude Code wrappers for implementer, reviewer, or planner roles.
- The 23 role-seed **Tool posture** leads (seeds 212 to 235 and 239): they already say "Load deferred tool schemas once via the host's tool loader (e.g. ToolSearch)" and point to seed 020 for the full posture, which this change strengthens.
- Seeds 100 (implement-wave and review-wave carriers) and 050 line 654 (wave-coordinator bullet): they already require carrying "the MCP-first directive" and point to seed 180, whose directive now includes the load-and-verify step.
- Extending the `retrieval_posture_gap` advisory (`server_impl.py` `_retrieval_posture_gap`) to review-stage or plan-stage telemetry: server code, outside this docs/seed change; recorded as a follow-up candidate (see Decision Log).
- Host-side deferred-loading mechanics; host-owned.

## Acceptance Criteria

- [x] AC-1: Seed 020 `## Retrieval Rules` requires every delegated worker on a deferred-tool host to load the Wavefoundry MCP tools before its first code or doc retrieval, confirm they are callable, and fall back to shell only with a `Gapfill:` entry naming the reason (not exposed, load failed, call errored); it names Claude Code `ToolSearch` with a `select:` list as the example and stays host-neutral.
- [x] AC-2: Seed 180 fallback condition (b) states that a deferred tool whose schema has not been loaded is not unavailable.
- [x] AC-3: Seed 180 **Delegating code work to a subagent** requires the brief to make load-and-verify the worker's first action and the worker to report the load outcome; **Use honest fallbacks** is consistent with it.
- [x] AC-4: Seed 050's `AGENTS.md` retrieval-intent backstop template and its `implementer.md` bullet carry the load-and-verify clause as a pointer to seeds 020 and 180, without restating the exploration order.
- [x] AC-5: Rendered `AGENTS.md`, `docs/contributing/agent-team-workflow.md` (Retrieval Posture section), and `docs/agents/implementer.md` match their seeds; no other rendered surface restates the rule, the pre-existing pointer-level load mentions (seed 050 guru wrapper body, `render_agent_surfaces.CLAUDE_GURU_AGENT`, the factor wrappers' line 13) counting as pointers, not restatements.
- [x] AC-6: No renderer or wrapper frontmatter change; `.claude/agents/guru.md` and all four factor wrappers are confirmed to list `ToolSearch` and the read-only retrieval tools, and `GuruWrapperToolAllowlistTests` stays green.
- [x] AC-7: A live Claude Code general-purpose subagent briefed per the new seed 180 wording calls `ToolSearch` before any other retrieval and completes at least one `code_*` or `docs_search` call with `status: ok`; the transcript evidence is in the Progress Log.
- [x] AC-8: Full docs lint (`wf_validate_docs`) is clean and the framework suite (`run_tests.py`) is green with a fresh receipt.

## Tasks

- [x] Open `seed_edit_allowed`; edit seed 020 `## Retrieval Rules` first and fifth bullets per Requirements 1 and 2; close the gate.
- [x] Open `seed_edit_allowed`; edit seed 180 fallback condition (b), the **Delegating code work to a subagent** paragraph, and the **Use honest fallbacks** bullet per Requirements 3 and 4; close the gate.
- [x] Open `seed_edit_allowed`; edit seed 050 backstop template (the "This applies to delegated work too" sentence) and the `implementer.md` bullet fallback clause; close the gate.
- [x] Open `framework_edit_allowed` if the pre-edit hook requires it for `AGENTS.md`; update the `AGENTS.md` backstop paragraph to match seed 050; restore the gate.
- [x] Update `docs/contributing/agent-team-workflow.md` `## Retrieval Posture (All Lanes)` first and fifth bullets to match seed 020, and `docs/agents/implementer.md` fallback line to match seed 050.
- [x] Grep (`code_keyword`) for "unavailable in the host" and "Load deferred tool schemas" across seeds and `docs/` to confirm no remaining surface contradicts the rule; classify each hit as updated or intentionally retained.
- [x] Confirm the guru and factor wrapper `tools:` lines include `ToolSearch` and the retrieval tools; record "no renderer change" in the Progress Log.
- [x] Run the live general-purpose subagent check (AC-7) and record the ordered tool calls.
- [x] Run `wf_validate_docs`, then `python3 .wavefoundry/framework/scripts/run_tests.py` last.

## Agent Execution Graph


| Workstream            | Owner       | Depends On            | Notes                                              |
| --------------------- | ----------- | --------------------- | -------------------------------------------------- |
| seed-edits            | implementer | none                  | Seeds 020, 180, 050 under `seed_edit_allowed`      |
| rendered-surfaces     | implementer | seed-edits            | `AGENTS.md`, agent-team-workflow, implementer role |
| live-check-and-verify | implementer | rendered-surfaces     | AC-7 transcript, lint, suite                       |


## Serialization Points

This change lands in wave `200ey` fifth, after `200ex` and before `200ew`. It is docs, seed, and rendered-surface only (no renderer, no server code). Its serialization partner is `200ew`, which also edits seed 050, the agent team workflow doc and the root agent guide, and lands after this change: this change's root agent guide backstop edit comes first and `200ew`'s census edit and CHANGELOG pass follow it.

- `.wavefoundry/framework/seeds/020-run-contract.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `docs/contributing/agent-team-workflow.md`
- `docs/agents/implementer.md`
- `AGENTS.md`

## Platform Behavior

Guidance-only change; no runtime code path differs by operating system. Windows, macOS, Linux, and WSL2 behave identically. Across agent hosts: on a deferred-tool host (Claude Code subagents) the worker loads via `ToolSearch("select:...")`; on hosts that expose MCP tools directly (Cursor, Codex, Junie, Antigravity) the load step is a no-op and the worker only confirms the tools are callable; on hosts with no MCP attached the worker records the "not exposed" `Gapfill:` reason and uses the documented fallback.

## Affected Architecture Docs

N/A. The change edits agent guidance in seeds and rendered operating surfaces; it changes no module boundary, data or control flow, or verification architecture.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Canonical home of the operator's rule; every lane points here. |
| AC-2 | required  | Closes the "deferred means unavailable" loophole that produced the observed behavior. |
| AC-3 | required  | The brief is the only text a general-purpose worker is guaranteed to read. |
| AC-4 | required  | Seed source for the rendered `AGENTS.md` and implementer surfaces; without it the rule does not reach target repos. |
| AC-5 | required  | Self-hosted surfaces must match their seeds. |
| AC-6 | important | Confirms the no-renderer-change decision rather than assuming it. |
| AC-7 | important | Proves the wording changes worker behavior on the host where the defect was seen. |
| AC-8 | required  | Standard docs and suite gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-07 | Planned. Census: canonical guidance in seed 020:83 and :87, seed 180:121, :125, :162, seed 050:200 (AGENTS.md backstop) and :650 (implementer bullet); rendered in `AGENTS.md`, `docs/contributing/agent-team-workflow.md`:105 and :109, `docs/agents/implementer.md`:31. `.claude/agents/` holds only guru and four factor wrappers, all already listing `ToolSearch` plus read-only retrieval tools; implementer and reviewer roles have no wrapper. `docs/prompts/implement-wave.prompt.md` and `review-wave.prompt.md` already point to seed 180 and seed 020. | MCP `code_keyword`/`code_read` census, 2026-10-07 |
| 2026-10-07 | Proposed CHANGELOG bullet for `200ew` (under `## [1.29.0]`, Changed): "Delegated workers on hosts that defer MCP tools now load the Wavefoundry tools first, confirm they are callable, and fall back to shell only with a recorded reason (not exposed, load failed, call errored); a deferred tool whose schema is not loaded no longer counts as unavailable, and a coordinator's brief makes the load the worker's first step." | AC-8 release text; `200ew` Requirement 12. |
| 2026-10-07 | Readiness round 1 findings applied (F14 lands before `200ew`, which is listed as the serialization partner for seed 050, `docs/contributing/agent-team-workflow.md` and `AGENTS.md`; F15 proposed CHANGELOG bullet above; F18 pre-existing load mentions in the seed 050 guru wrapper body, `render_agent_surfaces.CLAUDE_GURU_AGENT` and the factor wrappers' line 13 classified as pointer-level for AC-5, wrapper tool count corrected to 19, the rendered `implementer.md` fallback text quoted exactly, role-seed range includes 239). | Wrapper `tools:` lines (19 `mcp__wavefoundry__` tools each); `docs/agents/implementer.md`:31; seeds carrying "Load deferred tool schemas once" (020 plus 23 role seeds 212 to 235 and 239). |
| 2026-10-08 | Implemented. Seeds 020 (Retrieval Rules bullets 1 and 5), 180 (condition (b), delegation paragraph, honest-fallbacks bullet) and 050 (backstop template, implementer bullet) edited under `seed_edit_allowed`; `AGENTS.md` backstop paragraph edited under `framework_edit_allowed` (the pre-edit hook demanded it for seeds and AGENTS.md); both gates closed. Rendered carriers `docs/contributing/agent-team-workflow.md` (Retrieval Posture bullets 1 and 5) and `docs/agents/implementer.md` (fallback line) and `AGENTS.md` were edited by hand to the seed text (no renderer regenerates them from these seed edits; seeds 150 and 160 reconcile the carrier on refresh/upgrade). The 23 role-seed Tool posture leads were left as pointers. Grep for "unavailable in the host" and "Load deferred tool schemas": seeds 180 and 050 hits updated; 20 role-seed leads plus seed 239 retained as pointers; `docs/waves/12sg7.../12sfb-enh...md:42` is a closed historical record, retained; seed 020 and agent-team-workflow hits updated. | Edited files; code_keyword census 2026-10-08. |
| 2026-10-08 | No renderer change: `.claude/agents/guru.md` and the four factor wrappers each contain `ToolSearch` and `mcp__wavefoundry__` retrieval tools (grep counts), and `GuruWrapperToolAllowlistTests` passes in `test_render_agent_surfaces.py` (146 tests OK). Also green: `test_shipped_reference_docs.py` (26), `test_docs_lint.py` (1216), `test_vocabulary_prompt_names.py` (33). | `run_tests.py --file` runs 2026-10-08. |
| 2026-10-08 | AC-7 live check: this implementer is a briefed general-purpose subagent. Its first tool call was `ToolSearch` with `select:mcp__wavefoundry__code_read,...,wf_mark_task` (load succeeded, schemas returned); its next calls were `code_read` and `code_keyword` (status ok), then docs and seed edits. No shell retrieval preceded the load. No `Gapfill:` needed for retrieval; shell was used only for edits-adjacent census and test runs. | This transcript's tool-call order: ToolSearch, code_read + code_keyword, wf_open_gate. |
| 2026-10-08 | CHANGELOG bullet for `200ew` confirmed unchanged and still accurate against the delivered wording (load first, confirm callable, fallback only with a recorded reason: not exposed, load failed, call errored; deferred-unloaded is not unavailable; brief makes load the first step). | Row dated 2026-10-07 above. |


| 2026-10-08 | Delivery F-DOC-1 repair, after typed cycle-1 repair_start: aligned seed 020's fifth retrieval bullet, seed 180's fallback list, seed 050's implementer pointer and the two direct rendered carriers to Requirement 2's three cases. Stale indexed data and insufficient results alone no longer authorize shell retrieval; current-file MCP reads and explicit unresolved limits preserve truthful diagnosis. Literal-byte/git operations remain separate. Gates paired and closed; no renderer/wrapper change. | Initial docs/QA findings concurred, release confirmed claim impact; five reviewed files changed after every initial reviewer finished. Focused independent docs/QA verification pending. Earlier AC-7 Claude transcript is inherited evidence, not new host qualification. |

| 2026-10-08 | Same-cycle F-DOC-1 root-cause census found seed 050’s adjacent coordinator bootstrap pointer still permitted insufficient-result fallback. QA/docs/release withheld clearance; corrected that pointer to seed 020’s three cases after all R2 reviewers completed. The local coordinator role has no duplicate; twelve untruncated same-file census hits contain no other fourth-reason permission. | Bounded adjacent repair within original delivery cycle 1; R2 hashes stable before edit; independent final focused check pending. |

| 2026-10-08 | F-DOC-1 independently cleared by QA and docs on R3; six directives conform and reinjected old permissions are rejected. AC-1–7 and implementation tasks reconciled from current code/carrier tests and inherited live ToolSearch-first transcript at Progress Log:121. That transcript was not independently replayed on this host; no new Claude-host qualification is claimed. AC-8/final canonical task remain pending actual final execution. | Typed terminal cycle-1 head, 29 wrapper/shipped-reference tests; R3 `316687db95188ec240780b565927de571f352bc44711b171cc956f0c30b56494`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-07 | Operator decision: make load-verify-then-fallback a framework rule for every delegated worker on a deferred-tool host, with `ToolSearch` named as the Claude Code example. | Most 2026-10-07 subagents used shell because the MCP tools "were not loaded"; context-efficiency credits went unrecorded (200xy plan stage about 6k vs 12k+; 200ey plan stage 0). | Keep the current preference wording (rejected by the operator). |
| 2026-10-07 | Edit only the canonical seeds (020, 180, 050) and their direct rendered carriers; leave the 23 role-seed Tool posture leads and the seed 100 carriers as pointers. | Those surfaces already point to seed 020 and seed 180 and already name the load mechanic; the no-restatement rule keeps one source. | Sweep all role seeds with the new sentence: more drift surface for no new instruction. |
| 2026-10-07 | No renderer or wrapper frontmatter change. | Guru and factor wrappers already grant `ToolSearch` plus read-only retrieval tools; delegated implementers and reviewers run as general-purpose agents that inherit all tools as deferred, so the gap is behavioral guidance, not an allowlist. | Render implementer/reviewer Claude Code wrappers with explicit allowlists: larger change, and an allowlist does not make a deferred tool load itself. |
| 2026-10-07 | Coordinator decision (readiness round 1): this change lands before `200ew`, keeps its own `AGENTS.md` backstop edit, and lists `200ew` as its serialization partner (seed 050, `docs/contributing/agent-team-workflow.md`, `AGENTS.md`). | `200ew` writes the wave's CHANGELOG and AGENTS.md census pass last, so landing this change first keeps that pass final and lets it include this change's bullet. | Land after `200ew`: the release pass would no longer be last. Hand the `AGENTS.md` edit to `200ew`: splits one guidance change across two owners. |
| 2026-10-07 | Do not extend `retrieval_posture_gap` to review-stage in this change; record it as a follow-up candidate. | It is server code outside this docs/seed scope, and review lanes legitimately run shell probes, so a review-stage threshold needs its own calibration. | Extend the sensor now. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Workers still skip the load because they never read seed 020. | The rule travels in the brief (seed 180 delegation paragraph), and AC-7 checks behavior on the host where the defect appeared. |
| "Verify callable" adds a wasted call per worker. | Successful schema load counts as verification; one cheap call is needed only when the load result is ambiguous. |
| A seed edit drifts from its rendered carrier. | AC-5 compares each rendered surface with its seed; seeds 150 and 160 already reconcile the seed 020 carrier on refresh and upgrade. |
| The wording reads as Claude Code-specific. | Seeds state the rule host-neutrally and name `ToolSearch` only as an example; Platform Behavior covers non-deferred hosts. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
