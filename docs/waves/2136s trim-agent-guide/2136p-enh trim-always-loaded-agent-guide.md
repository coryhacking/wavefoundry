# First reduction of the always-loaded agent guide, measured against total startup reading

Change ID: `2136p-enh trim-always-loaded-agent-guide`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: 2136s trim-agent-guide

## Rationale

The Claude Code best-practices guide warns that an over-long `CLAUDE.md` makes Claude "ignore half of it because important rules get lost in the noise". Its test for each line is: "Would removing this cause Claude to make mistakes? If not, cut it."

`AGENTS.md` is 46,762 bytes, and `CLAUDE.md` imports it into every session. It is only part of what an agent reads at startup: `AGENTS.md` "Start Here" and `CLAUDE.md` "Startup Order" also direct a read of five documents. Measured 2026-10-18:

| File | Bytes |
| --- | --- |
| `AGENTS.md` | 46,762 |
| `docs/agents/session-handoff.md` | 28,385 |
| `docs/references/codebase-map.md` | 20,527 |
| `docs/references/project-overview.md` | 18,275 |
| `docs/prompts/index.md` | 13,461 |
| `docs/ARCHITECTURE.md` | 10,272 |
| `CLAUDE.md` | 2,490 |
| **Total** | **140,172** |

Cutting `AGENTS.md` alone to about 36 KB leaves about 130 KB. This change is therefore a first reduction, not a solution to the startup context problem. It measures the whole startup set before and after, and names the next reductions without making them.

Plan review (2026-10-18) established four facts:
- Most reference detail in `AGENTS.md` already exists at its destination: the platform tier tables (`docs/agents/platform-mapping.md:13-45`), MCP Resources (`docs/specs/mcp-tool-surface.md:2634-2680`), the code-tool chooser (`mcp-tool-surface.md:2709-2727`), the bytecode cache (`docs/contributing/build-and-verification.md:420-425`) and the close receipt (`build-and-verification.md:431-470`). For those, the change is a deletion with a pointer, not a move.
- Seed 050 tells every target to write the **Agent platform routing** subsection into `AGENTS.md` (050:107, 050:279), and a test pins its TechDocs row (`test_render_agent_surfaces.py:4473-4475`). That subsection stays.
- Keeping every rule verbatim puts the realistic result near 36.5 KB, not 28 KB. Readiness code review trimmed a scratch copy: deleting every Requirement 2 block outright gives 32,810 bytes, and keeping each rule sentence verbatim plus one pointer per block gives 36,503. Getting lower means rewording rules, which is out of scope. A readiness simulation deleted every Requirement 2 block with no pointers and reached 34,880 bytes; adding the `## MCP Server` intro reduction gives a 31,878-byte floor before rules and pointers are added back.
- The per-host registration table and the copy-ready stdio entry already exist in `docs/prompts/install-wavefoundry.prompt.md` (Step 2), pinned there by `test_install_prompt_uses_path_python_not_tool_venv_python`. The spec holds no copy.
- The **Available tools** census and the **Graph index** paragraph are one regex-pinned block (`test_server_tools.py:2815-2819`). Keeping them avoids a second flat tool list in the spec, which already enumerates every tool (`mcp-tool-surface.md:1395`).

## Requirements

1. Every behavioural rule in `AGENTS.md` stays in `AGENTS.md`. A rule is any sentence that tells an agent to do, not do, ask, stop or route. That includes tool-usage directives such as "do not read `index-build.lock` directly" and "prefer MCP over shell launchers". A routing or imperative sentence that only enumerates a lookup (the code-tool chooser rows, the per-host registration rows, the resource list) is reference detail, not a rule. Reference detail is removed. When its destination already holds the substance, it is deleted with a one-line pointer. Otherwise, each sentence not already present at the destination is added there first.
2. Reductions, each with a pointer:
   - **MCP Server intro** (the `wf setup` and index description under `## MCP Server`, before **Check readiness after Git changes**): the dependency list, index layout and lock-file description are deleted to their reference homes, with any sentence missing there added first. Its rules stay: read the `held` boolean on `index_build_status` and do not read `index-build.lock` directly, ask the operator before rerunning setup with network access, and check `index_health()` before relying on retrieval.
   - **MCP Server per-host block** (the per-host MCP enabling subsection): the per-host registration table and the copy-ready stdio entry are deleted with a pointer to `docs/prompts/install-wavefoundry.prompt.md` Step 2, which already holds both. A host-table sentence missing there (for example that Antigravity reads `AGENTS.md` natively, or that Windsurf hooks are auto-rendered) is added there first. In the same edit, the pointers into the removed table are retargeted: the `AGENTS.md` Agent platform routing cell "Per `AGENTS.md` MCP table", `docs/agents/platform-mapping.md` (the Air row, "per `AGENTS.md` MCP table"), and the install prompt's own line "See `AGENTS.md → MCP / Wavefoundry server ...` for the full matrix", which is rewritten to name its own Step 2 table, so no pointer loops back to `AGENTS.md`. Seed 160's generic "per `AGENTS.md`" text is left unchanged: it describes a target's own `AGENTS.md`, and this repository's keeps a pointer. The python3 paragraph that follows the entry ("Use the `python3` on PATH ...") is rules and stays in `AGENTS.md`, as does the native-Windows diagnosis paragraph. The `code_ask` return-field description and the retired-kind paragraph are deleted where the spec already holds them, and moved otherwise. The **Available tools** census and **Graph index** paragraph stay.
   - **MCP Resources and Resource Templates**: deleted; the spec already holds it. The resources-vs-tools routing rule stays.
   - **Code Navigation**: chooser rows deleted; the spec and seed 211 already hold them. One routing sentence stays.
   - **Framework Script Hygiene**, bytecode-cache paragraph: detail deleted to `build-and-verification.md`. The rule sentences stay.
   - **Wave Close**, receipt paragraph: detail deleted to `build-and-verification.md`. The rule that close requires a current green receipt, and "run the suite last", stay.
3. These stay in full:
   - Start Here, and the auto-Guru section including Agent platform routing;
   - Purpose, Product Boundary, Self-Hosting Boundary;
   - Shortcut Phrases;
   - Implementation Principles, Stage Gate, Implementation Guard;
   - Change Doc Tracking, Git Commits, Wave Close rules;
   - Core Principles;
   - Check readiness after Git changes (byte-pinned to seed 050);
   - Docs validation and gardening;
   - Repository Shape, Safety Rules, Cleanup.
4. Retargeted tests keep their assertion strings unchanged and change only the file they read:
   - `test_shipped_reference_docs.py::test_agent_guide_copy_ready_entry_uses_path_python` keeps reading `AGENTS.md` for the python3 rule sentence, which stays. Its two JSON-entry assertions (`"command": "python3"` and the `server.py` path) leave with the entry; this is a move, not a loosened check, because `test_install_prompt_uses_path_python_not_tool_venv_python` already pins both strings in the entry's remaining home;
   - `test_server_tools_retrieval.py::test_the_agent_guide_lists_it_in_the_response_envelope`, if the `code_ask` description leaves: retargeted to the spec, unless a spec test already asserts the same field (readiness found `confidence_basis` asserted in the spec at `test_server_tools_retrieval.py:18410`), in which case the duplicate is deleted and the census names the remaining pin.

   Pins that stay on `AGENTS.md` must still pass:
   - the tool census;
   - `wf_upgrade` names;
   - the TechDocs row;
   - the auto-Guru anchor (`test_render_agent_surfaces.py:2497-2524`);
   - the allowlist sentence (`:359-362`);
   - per-area convention;
   - readiness parity;
   - the events-only residue census.
5. A rule census file, `docs/waves/2136s trim-agent-guide/evidence/rule-census.md`, names its baseline (the `AGENTS.md` content hash after waves 2136j and 2136r land) and gives every pre-change sentence one disposition: kept, relocated (naming the destination), or reference detail deleted (naming the destination that holds it).
6. The Progress Log records, before and after, the byte count of `AGENTS.md` and of the whole startup set in the Rationale table. It also names the next candidate reductions, each with its size, without making them: `session-handoff.md` (28 KB), `codebase-map.md` (21 KB), `project-overview.md` (18 KB), and whether every startup document needs a full read.
7. `docs/references/codebase-map.md` is regenerated, because `gen_codebase_map.py` fingerprints `AGENTS.md`.
8. Seed 050 gains one sentence for the root `AGENTS.md` it asks agents to write: rules and routing stay in it, and reference detail beyond the sections seed 050 requires is linked rather than copied. Seed 050 task 20 (Agent platform routing) is unchanged.
9. Documentation and test retargeting only. Behaviour is the same on Windows, macOS, Linux and WSL2. The native-Windows `wf.cmd` forms and the Windows diagnosis paragraph are rules and stay.

## Scope

**Problem statement:** the always-loaded agent guide is about 47 KB of a 140 KB startup read, and much of it duplicates reference docs.

**In scope:**

- `AGENTS.md`, plus pointer retargets in `docs/agents/platform-mapping.md` and the install prompt, and additions to `docs/specs/mcp-tool-surface.md`, `docs/prompts/install-wavefoundry.prompt.md` and `docs/contributing/build-and-verification.md` where content is missing.
- The rule census file.
- The retargeted tests.
- The codebase map regeneration.
- One seed 050 sentence.

**Out of scope:**

- Reducing the other startup documents. They are named as next candidates only.
- `CLAUDE.md` project sections.
- Rewording rules.
- Seed 050 task 20.
- Other hosts' entry files.

## Acceptance Criteria

- [x] AC-1: `AGENTS.md` is at most 36,500 bytes, a cut of at least 21%. The baseline is the file after waves 2136j and 2136r land. The Progress Log records the before and after bytes for `AGENTS.md` and for the whole startup set.
- [x] AC-2: The rule census file gives every pre-change sentence a disposition, and every sentence marked kept is still in `AGENTS.md`.
- [x] AC-3: Every removed block's substance is present at its destination, either already or newly added, and the census file names which. Every pointer resolves and names a heading that exists at its destination; docs-lint link checks count here. A search of `AGENTS.md`, `docs/` and the seeds for "MCP table" and "enabling per host" finds no pointer to a removed block, apart from the seed 160 line that Requirement 2 leaves unchanged on purpose.
- [x] AC-4: Each retargeted test passes against its new file, and fails when its content is removed there. Shown with scratch-copy mutants.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Measure the startup set, and write the rule census file from the pre-change `AGENTS.md`.
- [x] Under `framework_edit_allowed` (the pre-edit hook classifies `AGENTS.md` as a framework-maintenance surface), make the Requirement 2 reductions, and add any missing destination content first.
- [x] Retarget the tests, and run the AC-4 mutants in a scratch copy.
- [x] Add the seed 050 sentence under `seed_edit_allowed`.
- [x] Regenerate the codebase map, and measure again.
- [x] Validate docs, and run the touched test files, then the whole suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | none | Requirements 5 and 6 |
| reduce | implementer | census | Requirements 1 to 3 |
| tests | implementer | reduce | Requirements 4 and 7 |

## Serialization Points

- `docs/specs/mcp-tool-surface.md`, `docs/prompts/install-wavefoundry.prompt.md`, `docs/agents/platform-mapping.md`, `docs/contributing/build-and-verification.md`, `docs/references/codebase-map.md`, `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`, `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `AGENTS.md`

## Affected Architecture Docs

N/A: documentation placement, with no system boundary or flow change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The point of the change, with the whole-set measurement. |
| AC-2 | required | No rule may be lost. |
| AC-3 | required | Removed detail must stay reachable. |
| AC-4 | required | The pins must still bite. |
| AC-5 | required | Tests pin the guide. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned. Section byte sizes were measured, and the project-owned sections and their pinning tests were identified. | Guru investigation; awk section sizes |
| 2026-10-18 | Replanned after plan review. It is now framed as a first reduction measured against the 140,172-byte startup set. Agent platform routing and the tool census stay. Duplicated blocks are deletions with pointers. The target is set at 33 KB, because keeping every rule floors near 31 KB. The census is a file, and the edit gate and codebase-map regeneration are added. | Operator plan review; Fable plan review |
| 2026-10-18 | Readiness red-team repairs: the measured floor showed 33 KB unreachable, so AC-1 is 34,000 bytes and the `## MCP Server` intro joins Requirement 2. The host table and stdio entry point to the install prompt, which already holds and pins them, rather than gaining a second copy in the spec. The python3 paragraph stays as rules. The census baseline is the post-2136j, post-2136r file, since 2136l edits the skills paragraph. | 2136s readiness red-team primer |
| 2026-10-18 | Readiness lane repairs: AC-1 is 36,500 bytes, from the code reviewer's scratch trim that kept every rule verbatim (36,503 bytes); pointers into the removed host table are retargeted so none loops back; the census gives each sentence a kept, relocated or reference-detail disposition, with lookup enumerations defined as reference detail; the seed 050 sentence exempts the sections seed 050 requires. | 2136s readiness QA and docs-contract lanes |
| 2026-10-18 | Implemented under `framework_edit_allowed` and `seed_edit_allowed`, drafted by an implementer in a scratch copy and ported after the repository files were confirmed unchanged since the copy. Census baseline: `AGENTS.md` after 2136j and 2136r, 46,932 bytes, sha256 5e6e559d...a226. After: 36,413 bytes (22.4% cut), sha256 809f5c0a...c296. Startup set before 140,728 bytes (AGENTS.md 46,932, session-handoff 28,384, codebase-map 20,527, project-overview 18,275, prompts index 13,461, ARCHITECTURE 10,272, CLAUDE.md 2,877); after 130,209. Census: 362 rows; 280 kept verbatim (script-verified substrings), 11 relocated, 66 reference detail already at destination, 5 kept with a pointer retarget or merge. Destinations gained: build-and-verification.md onboarding setup detail; mcp-tool-surface.md `code_ask` envelope fields and `queries=[...]`; install prompt Copilot and Antigravity row details, and its matrix line now names Step 2. Two pre-existing pointers to nonexistent spec headings were retargeted. The AC-3 search finds only seed 160:779, left unchanged on purpose. Tests in scratch: test_shipped_reference_docs 28, test_server_tools_retrieval 1060, test_server_tools 406, test_render_agent_surfaces 170, test_vocabulary_prompt_names 36, test_docs_lint 350 OK; test_per_area_agents_context one error from `git ls-files` in a .git-less copy, reproduced on an unmodified copy, so environmental. AC-4 mutants: removing the python3 paragraph fails test_agent_guide_copy_ready_entry_uses_path_python; renaming confidence_basis in the spec fails test_the_specification_names_the_field_and_every_value. Codebase map regenerated. Next candidates, not made here: session-handoff.md (28 KB), codebase-map.md (21 KB), project-overview.md (18 KB), and whether each startup document needs a full read or only a pointer. Reviewer attention: two sentences were treated as reference detail ("The Wavefoundry MCP server ships at server.py..." and "The gate is not a whole-repository guarantee..."), both held at their destinations. Gapfill: scratch-copy shell edits, because the repository suite was running and the wave was not yet open. | evidence/rule-census.md; scratchpad s2136 |
| 2026-10-18 | Delivery repair QA-CODE-2136S-1: restored five original instructions (root selection, background-mode conditions, test/generated inclusion, rerank trust and large-feature planning) after the initial trim incorrectly treated them as reference detail. Shortened only newly authored reference pointers in the admitted blocks. AGENTS.md now 36,374 bytes, 22.50% below the 46,932-byte baseline; startup set now 130,170 bytes versus 140,728 before. Census remains 362 rows: 285 exact-kept, 8 relocated, 64 descriptive deletions with destinations, 5 explicitly retargeted/merged pointers; result sha256 0b84b3a1e9cfb45855a16f43baf6a1d3b72053f6334f78ef7014e3588469dec5. Direct retention probe changed from baseline5/current0 and assertion failure to baseline5/current5 and exit0. Regenerated the codebase map. Focused independent reverification and final combined qualification remain pending. Gapfill: mechanical sentence restoration/census updates and byte/hash accounting used a bounded script; no source behavior or requirement changed. | wave finding QA-CODE-2136S-1; evidence/rule-census.md; python3 -B /private/tmp/2136s_rule_retention_probe.py |
| 2026-10-18 | Fresh focused code/QA and docs/council contexts independently verified the repaired source; all three required lanes and council approved. Five individual omission mutants each detect exactly one missing rule; three existing document-pin mutants each yield one assertion failure, zero errors/skips. All 285 exact-kept entries remain, 362 rows cover the baseline, and 19 destination/label combinations resolve. AC-1 through AC-4 and the first five tasks are complete. Final combined qualification and full docs validation remain pending under AC-5 and the final task. | Typed cycle-1 reverification/approvals; wave Review Checkpoints; evidence/rule-census.md |
| 2026-10-18 | Final canonical qualification: `/Users/coryhacking/.wavefoundry/venv/bin/python .wavefoundry/framework/scripts/run_tests.py --no-cache` passed 11,911 tests across 200 files in 764.084 seconds, with 12 reported skips. Green receipt matches current framework inputs `de1645bfd5b392a8a9bb5b71d98df4fc5ddd8e05f5e0b46a597447420aa722cd`. Full `wf_validate_docs` passed with zero errors/warnings and `git diff --check` is clean. The earlier sandboxed attempt was interrupted after a localhost-bind refusal; it is not qualification evidence, and no tests or thresholds were changed to bypass it. This one completed run qualifies all four settled waves; no duplicate full profiles were added. Implementation, required delivery review, AC-5 and the final task are complete; operator closure remains pending. | `.wavefoundry/framework/test-cache.json`; existing named regression tests; wave Review Checkpoints; /private/tmp/wf-four-wave-final-suite.log |
| 2026-10-19 | Delivery review (docs-contract, red-team and code lanes) found a missed AC-3 site: the wf-guru skill body in `render_agent_surfaces.py` still said "see the `AGENTS.md` MCP table", rendered into `.claude`, `.codex` and `.agents` wf-guru skills. Red-team also showed the premise for leaving seed 160 unchanged was false: no seed or renderer writes a host table into any target's `AGENTS.md`. Both now point at Step 2 of `docs/prompts/install-wavefoundry.prompt.md`, which every target has through seed 100; skills re-rendered. A repository-wide search over scripts, seeds, rendered host surfaces, `AGENTS.md` and `docs/` (excluding wave history) now finds no "MCP table" pointer. Focused: test_render_agent_surfaces 171, test_declared_extension_skills 60, test_vocabulary_prompt_names 36, test_docs_lint 350 OK. Earlier full suite before this fix: 11906 tests OK. | delivery lane reports |
| 2026-10-19 | Whole suite `--no-cache` on the settled combined tree (2136j, 2136r, 2136s and wave 2124l, which another session implemented while this wave was paused): 11911 tests OK, fresh green receipt. One earlier run failed only `test_context_efficiency.WriteThroughLedgerTests.test_candidate_scale_p95_budgets` (10000-candidate p95) while other test suites ran concurrently at load average about 15; the file alone passed (104 OK), so that failure was environmental, not attributable to this change. Delivery: docs-contract, qa, code and red-team lanes approved after the pointer repair. | scratchpad suite-final.txt |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | -------- |
| 2026-10-18 | Remove reference detail and keep every rule. | The guide's test is whether removal causes mistakes; rules pass it, and duplicated reference tables do not. | Rewrite the guide; it risks losing rules added after real incidents. |
| 2026-10-18 | Plan this as its own wave. | It touches many pinned docs. | Fold into 2136r; it would slow the small items. |
| 2026-10-18 | Treat this as a first reduction, and measure the whole startup set. | `AGENTS.md` is a third of a 140 KB startup read (operator plan review). | Claim the problem solved at 28 KB. |
| 2026-10-18 | Keep Agent platform routing and the tool census in `AGENTS.md`. | Seed 050 mandates the routing subsection; the census is regex-pinned and the spec already lists every tool. | Amend seed 050 task 20, and move the census; more surface for less gain. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A rule is mistaken for reference detail and removed. | AC-2 census file, reviewed by the docs-contract lane. |
| Agents stop finding tool details. | One-line pointers. `docs_search` indexes the destination docs. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
