# Brief modernization plugin agents with Wavefoundry operating instructions

Change ID: `21cpn-enh modernization-plugin-context-briefing`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-22
Wave: 21a5a modernization-plugin-wavefoundry-briefing

## Rationale

The installed Code Modernization plugin has its own specialist agents and workflow. Its agent definitions list shell/file tools without the Wavefoundry retrieval tools or a deferred-tool loader. This does not itself violate Wavefoundry: the canonical delegation contract permits an explicit capability fallback. The integration opportunity is to ensure delegated plugin workers receive the repository's scope, retrieval and evidence expectations rather than relying on accidental inheritance or changing vendor cache files.

The operator requested a wave for the proposed scoped briefing hook and coordinator instructions. The subsequent operator request authorizes preparation, review, implementation and the bounded read-only qualification below; permission expansion and plugin replacement remain outside scope.

## Product Intent

Operators using Code Modernization in a Wavefoundry-managed repository can give its workers the repository's existing operating contract and receive scoped, evidence-bearing results with honest tool-access limitations. The observable improvement is delivery and use of that briefing in a bounded read-only assignment, not a claim that prompt text enforces compliance or makes every plugin operation safe. AC-1 and AC-2 establish delivery; AC-5 establishes the limited observed behavior.

**Distribution decision:** the operator chose shipped support on 2026-10-22, scoped to Code Modernization plugin agents. Canonical framework renderer/seed sources own the implementation; self-hosted surfaces are regenerated.

## Requirements

1. Add a Claude Code project-level `SubagentStart` briefing scoped to the `code-modernization:` plugin namespace. Derive the matched set from the plugin-scoped agent identifier, not a hard-coded list of the eight currently installed agents. Anchor the matcher so unrelated plugins, similarly named project agents and built-in agents do not receive it. The hook must not depend on a plugin cache path, installed version directory or scan of the user's home directory.
2. Deliver a concise fixed briefing using the host's documented `hookSpecificOutput.additionalContext` response. Point to existing repository instructions and delegation rules rather than copying the retrieval exploration order. State scope/write ownership, actual-tool verification, MCP-first when available, documented `Gapfill:` fallback when unavailable, evidence return and coordinator-owned lifecycle tracking. It grants no tools or permissions and supplies no substitute for readiness, review, closure or commit authorization.
3. Add coordinator guidance to include the applicable change/AC references, owned and forbidden paths, expected evidence and relevant limitations in modernization assignments. Investigation can occur before readiness; implementation remains subject to the repository's stage gate. Plugin plan approval or a plugin proof verdict does not replace Wavefoundry approvals. Plugin workers return results; the coordinator records wave evidence through existing tools.
4. Keep the runtime hook bounded, local, read-only and non-blocking. It must not read transcripts, execute payload-provided instructions, call MCP, run tests/setup, inspect arbitrary paths, change lifecycle state or write telemetry/state files. Validate the event and agent identifier before emitting fixed guidance; malformed or irrelevant input cannot produce a matching briefing or block the host. Preserve existing hook entries and settings, including operator-authored entries, through repeated render/setup/upgrade. A missing plugin results in no matching invocation, not a setup dependency.
5. Preserve existing canonical guidance as authority. Own the hook in the framework renderer and coordinator guidance in seed 180, then regenerate self-hosted surfaces. Do not introduce a generic plugin integration registry.
6. Qualify the emitted host response and a bounded actual Claude Code read-only assignment. Record observed host/plugin versions, actual agent identifier, briefing receipt and how unavailable retrieval access was reported. Separate structural delivery tests from observed agent behavior; if the supported host/plugin cannot be exercised, leave AC-5 pending and report the limitation rather than claiming live integration. Do not automatically install or enable a plugin to obtain evidence.

## Scope

**Problem statement:** third-party plugin delegation lacks an explicit Wavefoundry integration briefing at the worker boundary.

**In scope:** scoped Claude context delivery, coordinator briefing guidance, preservation of existing settings, focused tests and bounded read-only host qualification. Framework distribution ownership is selected.

**Out of scope:** changing plugin agent tool lists; cloning/shadowing agents; tool/permission expansion; plugin enablement, disablement or installation; vendor/synced cache edits; global user settings; automatic modernization; enforcement of all plugin behavior; changes to review policy or gates; support for new host hook APIs; machine-wide auditing; unrelated audit corrections.

## Acceptance Criteria

- [x] AC-1: A rendered/configured matching `SubagentStart` event yields the host's valid context response containing the briefing. Nonmatching namespaces, misleading bare names and malformed payloads receive no such briefing and do not block startup. The oracle executes the delivered hook and checks host response semantics rather than only matching source text.
- [x] AC-2: Repeated reconciliation preserves operator hook entries and unrelated settings while producing exactly one integration entry. No plugin installation or cache path is required; existing other-host output is unchanged. Coverage follows the selected delivery boundary.
- [x] AC-3: The briefing and coordinator guidance preserve investigation-before-readiness, implementation gates, operator-owned actions and evidence return. Missing MCP access produces the documented fallback obligation rather than a fictitious tool or permission grant; the guidance references canonical rules without duplicating their retrieval ordering.
- [x] AC-4: Executing the hook leaves fixture files, lifecycle state, permissions and plugin definitions unchanged, starts no child command or network operation, and emits no payload contents beyond the fixed response. Relevant failure cases terminate without blocking the host.
- [x] AC-5: One bounded actual read-only modernization-agent assignment receives the integration briefing and returns scoped cited evidence plus an accurate statement of its retrieval capabilities/fallback. Record expected versus observed behavior and the limits of this single observation. This does not claim comprehensive plugin compliance or performance improvement.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] T-1: Record the shipped scope, finalize intended write targets and confirm current Claude hook behavior before Prepare.
- [x] T-2: After admission/readiness, implement the scoped fixed-context hook and preserve existing reconciliation behavior.
- [x] T-3: Add concise coordinator guidance using the selected ownership model; regenerate only the relevant owned surfaces.
- [x] T-4: Exercise delivery, negative matching, malformed payload, settings preservation and read-only behavior through the emitted hook path.
- [x] T-5: Run and record the bounded actual host/plugin assignment; keep structural and live evidence distinct.
- [x] T-6: Obtain required independent reviews, run appropriate framework qualification and full docs validation, and maintain AC/task evidence as work completes.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Scope and host contract | coordinator | selected shipped scope | Confirm host contract before readiness |
| Hook and guidance | implementer | admitted/readied wave | One write owner for shared renderer/settings/guidance |
| Focused and live evidence | implementer with independent QA review | hook and guidance | Read-only live assignment; no plugin installation implied |
| Required review | code, QA, architecture, security and docs-contract reviewers | phase-specific evidence | Read-only lanes; coordinator owns lifecycle evidence |

## Serialization Points

No source/config/seed edits before readiness. One implementer owns the selected write set; reviewers and the host-qualification lane are read-only against repository source. Preserve unrelated generated surfaces, all user-home plugin/skill caches, `.claude/settings.local.json`, MCP registrations, all permission allowlists and existing wave ledgers.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_session_start_hook.py`
- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`
- `.claude/hooks/wf-modernization-briefing.py`
- `.claude/hooks/simulate-hooks.py`
- `.claude/settings.json`
- `docs/prompts/implement-change.prompt.md`
- `docs/contributing/agent-team-workflow.md`
- `docs/agents/platform-mapping.md`
- `docs/architecture/data-and-control-flow.md`

Use the existing `CLAUDE_HOOKS` registry, settings reconciliation and canonical seed guidance. The named generated hook/settings/simulation helper are refreshed from those sources; the existing implementation prompt already points to seed 180 and needs no copied workflow text if that pointer remains sufficient. Project docs explain the boundary. Additional write targets require an explicit plan amendment before implementation.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`: the selected hook's source of truth, context delivery boundary and explicit lack of permission/lifecycle authority.
- `docs/agents/platform-mapping.md`: Claude-only invocation semantics and fallback on hosts without this integration.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Deliver only to intended workers through the host contract |
| AC-2 | required | Durable integration must coexist with project settings |
| AC-3 | required | The guidance must preserve existing authority and capability rules |
| AC-4 | required | Briefing must not become a new mutation or execution surface |
| AC-5 | required | Structural output alone cannot prove the host/worker integration |
| AC-6 | required | Change-local correctness and documentation quality |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-22 | Original planning: drafted common integration behavior and alternatives; distribution scope remains pending operator answer. No source edits or plugin execution. | Current renderer registry/settings merge, seed 180 delegation contract, installed plugin agent allowlists, official Claude hook documentation |

| 2026-10-22 | Operator selected shipped support; reviewed current official SubagentStart event and namespace contract. Claude Code 2.1.306 and installed plugin 1.0.0 are present. Final targets declared; live execution remains pending. | Official hooks reference, local version probe and installed agent headers |


| 2026-10-22 | Implemented fixed bounded SubagentStart briefing, canonical seed coordinator packet and scoped generated hook/settings/simulator. Default existing launcher bytes and other-host outputs preserved. Eight new tests and full renderer module (161 tests) pass; seven guard mutants detected. Readback/ownership and runtime boundaries followed; no permission expansion or vendor-cache edit. | 21a5a-implementation-freeze.json, 21a5a-platform-tests.log and 21a5a-mutants.json under /private/tmp/wf-audit-remediation |
| 2026-10-22 | Actual Claude Code 2.1.306 / installed Code Modernization 1.0.0 invoked code-modernization:legacy-analyst once. SubagentStart hook returned fixed context with exit 0; worker acknowledged injected receipt, cited repository lines and accurately reported Read/Glob/Grep plus no MCP/deferred loader/shell/writes and a Gapfill note. Session intentionally disabled MCP and write/command tools. Child made four Read and four Grep calls; nine declared source/config hashes unchanged; process exited 0 in 50.48s. | modernization-live-evidence.json; bounded local stream retained for independent verification |
| 2026-10-22 | Live limitation: worker skipped mandatory project-overview, codebase-map and guru orientation despite receiving instructions; AGENTS.md was reported already provided. This observation establishes AC-5's narrow delivery/evidence/capability outcome, not comprehensive plugin compliance or performance. Accepted payload limit is 16384 bytes; implementation reads one extra sentinel byte, correcting the worker's abbreviated description. Final canonical suite, independent delivery and docs validation remain pending. | Actual child report and configured hook source; no repeated run to conceal noncompliance |

| 2026-10-22 | Initial canonical qualification failed: 12,067 tests across 206 files, 12 existing skips, 710.965s. Five files report one failure each: declared-extension skill output roster, actor-token census, profile-literal census, legacy session-start timeout assertion and renamed-skill cleanup. Source-wave completion/approval remains pending repair; no failures waived. Earlier progress sampling missed three FAIL lines; final tracebacks are authoritative. | /private/tmp/wf-audit-remediation/canonical-initial.log; independent typed findings and bounded repair planning underway |

| 2026-10-22 | Repair scope amendment: added test_session_start_hook.py to Review targets. Restrict its no-timeout preservation oracle to the three legacy event families; retain SessionStart15s and modernization5s pins. Use the canonical record-layout helper in the new read-only fixture rather than a default docs/waves literal. No runtime contract, timeouts, skip policy or census allowance changes. Re-Prepare before edits. | Canonical tracebacks for session-start and profile-literal failures; reviewer finding and new target declaration |

| 2026-10-22 | Cycle1 fixture repair frozen after recorded repair_start: existing legacy hook timeout pins now enumerate their original hook families; the read-only fixture derives record location and filename from the profile. Runtime, hook and settings unchanged. 34 focused tests passed with no skips; renamed layout/filename control passes and five known-bad controls fail as intended. Fresh independent QA reverification and coordinated final suite remain pending. | 21a5a-fixture-repair-freeze.json, 21a5a-fixture-repair-controls.json and 21a5a-fixture-repair-tests.log in /private/tmp/wf-audit-remediation |

| 2026-10-22 | Final canonical run completed red: 12,072 tests across206files,12skips,1056.567s. All five original failing files now pass. Two other files fail: registered reload ownership reports second writer; TechDocs escaping-symlink fixture lacks unsafe_survivor_targets. Fresh independent QA/code/security/docs reviews found no new admitted-scope blocker; repaired findings are terminal, but delivery approvals and qualification ACs remain pending the required green suite. No test waiver, threshold change or unchanged retry. | /private/tmp/wf-audit-remediation/canonical-final.log; final-code-architecture-review.md; final-security-review.md; fresh-qa-docs reports; final-source-preservation.json |

| 2026-10-23 | Qualification completed after the requested retry: canonical suite passes12,072tests across206files with12existing skips in648.998s. Both formerly failing files pass; fresh green receipt recorded, reviewed implementation fingerprints unchanged. All five specialist delivery approvals are current, ACs/tasks met, change implemented. The live worker orientation omission remains an explicit limitation. Operator signoff/closure remain pending; no commit or close performed. No new memory candidate warranted beyond current tests/guidance and records. | .wavefoundry/framework/scripts/run_tests.py; /private/tmp/wf-audit-remediation/canonical-requested-requalification.log; typed delivery approvals; post-requalification-source-check.json |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-22 | Select scoped context hook plus coordinator briefing | Adds instructions at the worker boundary and preserves vendor updates without claiming new capability | Coordinator-only reminders rely on consistent prompt propagation; project-owned agent copies need update maintenance and verified command routing |
| 2026-10-22 | Keep tool-access customization outside this wave | Existing rules permit truthful capability fallback; missing MCP access is not itself a defect | Cloning all agents or granting broad MCP tools adds unnecessary authority and maintenance |
| 2026-10-22 | Ship framework support, scoped to modernization agents | Explicit operator selection on 2026-10-22 | Repository-local integration was considered but would not benefit consuming repositories |

## Risks

| Risk | Mitigation |
| --- | --- |
| Host API or plugin identifiers differ from documentation | Verify actual host version and one bounded matching invocation; leave live acceptance pending if unavailable |
| Instruction injection mistaken for enforcement | Preserve existing gates and clearly describe context-only behavior |
| Additional context duplicates large policies | Brief pointers plus task-specific coordinator packet; no whole-file injection |
| Plugin worker cannot access MCP | Verify actual tools and disclose the existing documented fallback |
| Generated/local ownership becomes ambiguous | Use canonical renderer/seed ownership and protect local settings |

## Sources

- [Claude Code SubagentStart hook](https://code.claude.com/docs/en/hooks#subagentstart): plugin-scoped matching and context response; the hook cannot block agent creation.
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents): agent capabilities and plugin limitations.
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`: `CLAUDE_HOOKS`, `render_claude_settings` preserve operator entries while replacing owned commands.
- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`: delegation briefing, actual capability checks and documented fallback.

## Session Handoff

Shipped scope selected; typed readiness completed and implementation performed. Focused and bounded live evidence recorded above; final canonical qualification and independent delivery remain pending. See `docs/agents/session-handoff.md` for other work; this planning effort does not replace unrelated handoff state.

Operator direction on 2026-10-22: prepare, review and implement the audit items in appropriate waves; pause between waves and continue. Wave closure and commits remain unrequested.
