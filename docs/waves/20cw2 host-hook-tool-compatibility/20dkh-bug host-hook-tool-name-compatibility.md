# Host hook tool-name compatibility

Change ID: `20dkh-bug host-hook-tool-name-compatibility`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-10-10
Wave: `20cw2`

## Rationale

Brief: make generated edit hooks report and safely inspect unfamiliar tool names, preserve known read and shell behavior, and deliver Codex patch-edit guidance through the existing managed Implement wave prompt. This is workflow-scoped instruction delivery, without native interception or automatic universal root-entry coverage. The operator requests planning, preparation and review only; this request does not authorize implementation.

Current Claude and Copilot handlers treat every nonempty name outside their closed edit-name lists as non-edit (`render_platform_surfaces.py:980–983`, `1372–1384`). A scratch probe of the actual generated pre-hooks supplied the same protected seed path with closed guards: known `Edit`/`edit` returned 2; synthetic `fixture_future_edit` returned 0 without a diagnostic; known `Read`/`view` returned 0. These are handler verdicts, not a live host invocation or file mutation. Claude's rendered matcher admits only its four named built-in editing tools, so a handler change alone cannot intercept a future unmatched tool.

Codex CLI 0.162.1 reports its hooks feature enabled. Current [official hook documentation](https://learn.chatgpt.com/docs/hooks) documents canonical `apply_patch` events with patch text at `tool_input.command`, including nested code-mode calls. Wavefoundry currently renders only Codex MCP configuration and instruction surfaces, with no verified project-owner native-hook adapter (`docs/agents/platform-mapping.md:79`; `render_platform_surfaces.py:2850–2851`). The current session exposes `tools.apply_patch` through `functions.exec`; this wrapper is distinct from the canonical hook name. Strengthen and check instruction carriers; do not claim native enforcement or agent adherence.

## Requirements

1. Derive the affected handler set from renderer-produced pre/post handlers that dispatch on a payload tool-name field. At planning time these are Claude and Copilot. Maintain a source-derived census so later renderer additions cannot escape the classification contract. Cursor/Windsurf file-edit events have no such dispatcher; retain and verify that distinction.
2. Separate supported edit, positively identified non-edit, and unknown classifications. Known read/shell exemptions require evidence for that host's exact name and applicable command; absence from the edit list is not evidence of a read. Preserve text-editor `view` handling and strict missing/unknown text-editor commands. Do not invent aliases or exempt arbitrary namespaces.
3. For an unknown named tool received by an existing pre-hook, inspect only that adapter's already supported explicit path fields. Apply existing seed/framework guards to every recovered path and emit a compatibility diagnostic: a protected path with closed guard blocks; ordinary paths/open guards preserve the existing verdict. Do not infer writes from shell commands, opaque strings, name substrings, arbitrary JSON recursion or guessed patch formats.
4. For an unknown name without supported inspectable paths, return a bounded terminal-safe advisory that edit coverage could not be established. Do not silently label it a read or invent new shell/MCP blocking. Preserve fail-closed behavior for known edits and absent/malformed identities, including known `apply_patch` calls without inspectable headers. Diagnostics show only a bounded escaped tool label and coverage instruction; never arguments, patch bodies or payload content.
5. Unknown post-tool calls may report uncertainty but must not launch lint/indexing solely from an unfamiliar name, even when a path field exists. Recognized edits retain docs feedback and refresh behavior; known reads/shell calls remain free of edit-specific subprocesses. Disclose that unfamiliar successful edits may need the existing integrity-boundary validation/refresh instruction.
6. Preserve existing subscriptions and enforcement limits: Claude's four-built-in edit matcher and Copilot's existing all-tool event. No Claude wildcard matcher, shell interception or complete MCP/write-coverage claim. Explain the difference between received-payload handler verdicts and host matcher coverage.
7. Put Codex patch-write guidance in the canonical `review_policy.REVIEW_POLICY_SURFACE_BLOCKS[_implement_doc]` prose entry and deliver it through existing `render_agent_surfaces.reconcile_review_policy_surfaces` into the profile-resolved Implement wave prompt (`docs/prompts/implement-wave.prompt.md` by default), read by the existing `wf-implement-wave` skill. Require `apply_patch` to be treated as a write regardless of wrapper spelling: inspect Add, Update, Delete and Move-to destinations, including both move paths, before invocation; honor existing stage gate and seed/framework approval policy; stop when intended write paths cannot be established. Shell-executed patches remain writes under instruction policy. Preserve evaluator algorithms/version and carrier registry. This provides instructions in that workflow, not automatic updates to existing root AGENTS, universal startup/single-change coverage, native enforcement or agent-adherence proof. Do not suggest tool/plugin renaming, guessed aliases, approval bypasses or unsupported native-hook config. Keep downstream-private evidence out public records.
8. Update existing platform/threat-model documentation, directly owned generated hooks and the managed implementation prompt. Prove the actual current consumer carrier is updated, project-authored surrounding prose is retained, and a second reconciliation writes nothing, including vocabulary-profile path resolution. Upgrades use the existing reconciliation/rendering pass only: no new scan, download, suite, readiness artifact or permanent evidence folder. Keep final outcomes and limits compactly in the change and wave record.

## Scope

**Problem statement:** unfamiliar received hook names are silently considered non-edits, and Codex instruction-only edit control lacks actual patch/wrapper guidance.

**In scope:**

- Named-tool dispatch and bounded diagnostics in `render_platform_surfaces.py`; focused `tests/test_render_platform_surfaces.py` fixtures.
- The existing managed `_implement_doc` prose entry in `review_policy.py`, its profile-resolved implementation prompt and focused carrier integration fixtures. Canonical prose is updated before refreshing the owned region; the existing skill pointer remains unchanged.
- Existing generated `.claude/hooks/pre-edit.py`, `.github/hooks/pre-tool-use.py`, `.github/hooks/post-tool-use.py` when their canonical bodies change; regenerate through the existing owner after readiness.
- Existing platform mapping, threat model and one local changelog entry; current primary-source name/schema evidence and repository/local-tool controls.

**Out of scope:**

- New Codex native hooks/trust enrollment/plugins, `.codex/config.toml` changes or operator permission-rule edits; root AGENTS/bootstrap seed changes and universal entry or single-change instruction-delivery claims.
- Evaluator algorithms/version, digest normalizers, carrier registry, new root-entry writers or extra upgrade passes.
- Global host interception, shell parsing, arbitrary MCP mutation classification, authority enforcement outside current gates or file-write races.
- Seed 020 retrieval policy, seed 160 upgrade execution, approval semantics, eligibility reaping and unrelated host adapters.
- Claims of live-host/native Windows qualification or agent adherence from repository fixtures.

## Acceptance Criteria

- [ ] AC-1: A source-derived census covers every named-tool renderer pre/post dispatcher and distinguishes name-free adapters; identified handlers implement applicable edit/non-edit/unknown contracts. Oracle: bounded census and handler fixtures.
- [ ] AC-2: Unknown named pre-hook payloads with supported explicit paths respect every recovered seed/framework guard; ordinary paths/open guards preserve path verdicts. Oracle: generated-hook exit/diagnostic observations, including multi-path adapters.
- [ ] AC-3: Unknown no-path calls report bounded escaped uncertainty without payload disclosure or new shell/MCP blocking; known edits with unreadable paths/patch headers and missing/malformed identities retain fail-closed behavior. Oracle: hostile-label/no-path and known-edit negative fixtures.
- [ ] AC-4: Known read/shell calls and text-editor `view` preserve non-edit verdicts and cause no edit-specific lint/index work; unsupported text-editor commands stay edits. Oracle: generated pre/post fixtures and subprocess/refresh observations.
- [ ] AC-5: Unknown post calls start no lint/index work solely from an unfamiliar name, while recognized edits retain refresh/docs-lint behavior. Oracle: received-payload side effects, including recognized edit with failing lint.
- [ ] AC-6: Claude subscriptions retain the supported four-built-in matcher and no new native Codex hook/config or host subscription appears. Oracle: renderer outputs and config ownership comparisons.
- [ ] AC-7: Canonical `_implement_doc` prose and the actual managed Implement wave consumer prompt contain Codex destination/move, approval/stage-gate and wrapper/canonical-name instructions. The existing skill points to that prompt. Oracle: shipped-carrier assertions and realistic patch examples, with explicit workflow-only/instruction-only limits and no universal root-entry, single-change or agent-adherence claim.
- [ ] AC-8: Existing reconciliation delivers the policy into default and profile-resolved existing implementation prompts, retains surrounding customization and makes zero second-pass writes. Platform/threat-model prose accurately states handler/matcher and workflow-instruction limits; algorithms, registry and upgrade-pass count stay unchanged. Oracle: real carrier integration, preservation/idempotence controls and changed-doc review; no new evidence directory.
- [ ] AC-9: The change's own suites and every test it adds pass; documents it authors/edits validate; no failure elsewhere is attributable to this change. Oracle: changed-owner suites/document validation, with broader qualification recorded as gate evidence.

## Tasks

- [ ] Reconfirm the dispatcher census and evidenced non-edit identities on the implementation checkout; document qualified names in existing comments/fixtures, not a new host registry.
- [ ] Implement classifications and received-unknown behavior within existing renderer/path ownership.
- [ ] Add generated-hook controls for recognized edits, known reads/shell, unknown paths/no-paths, multi-path adapters, escaped labels and post side effects.
- [ ] Add Codex patch policy to the managed `_implement_doc` prose entry and refresh its actual consumer prompt through existing reconciliation; add shipped-carrier, profile, preservation/idempotence and absent-native-hook-output checks.
- [ ] Align platform mapping, threat model and changelog with owned behavior/remaining limits.
- [ ] Run changed-owner verification and independent reviews at existing gates; retain compact results in wave.md and temporary probes outside the repository.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Hook dispatch repair | implementer | readiness | Sole renderer owner; actual generated hooks in scratch repositories. |
| Codex policy/contracts | implementer | hook dispatch repair | Same owner integrates canonical managed prose, actual workflow carrier and shared docs. |
| Independent review | code, QA, architecture, security, docs-contract reviewers | frozen implementation | Read-only reviewers; Council readiness precedes edits, delivery remains separate. |

Planning uses the inherited capable workhorse for bounded source/schema diagnosis; actual runtime identity/effort are not exposed. Workers verify their own MCP retrieval tools before fallback.

## Serialization Points

One writer owns renderer, managed policy prose and generated carriers. Wave 20bw2 also owns `review_policy.py`, its focused tests and the implementation prompt: serialize those exact shared regions through the coordinator, with 20bw2 integrated first. Preserve its phase-routing guidance; do not change either wave's approval algorithms. Serialize shared changelog writes. This wave is prepared/reviewed only, not activated or implemented.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `docs/prompts/implement-wave.prompt.md`
- `.claude/hooks/pre-edit.py`
- `.github/hooks/pre-tool-use.py`
- `.github/hooks/post-tool-use.py`
- `docs/agents/platform-mapping.md`
- `docs/architecture/threat-model.md`

CHANGELOG.md is the changelog target described above; its name is prose because root-level files are not review-target path tokens. Root AGENTS and seed050 remain unchanged. Read `render_agent_surfaces.reconcile_review_policy_surfaces` and the existing `wf-implement-wave` skill to verify the carrier path; no mechanism or pointer edit is admitted. Explicitly request architecture, security and docs-contract lanes alongside code/QA.

## Affected Architecture Docs

Update `docs/agents/platform-mapping.md` for received-name handling, matcher coverage and Codex instruction-only control. Update `docs/architecture/threat-model.md` for the same bounded control/bypass distinctions. No new module, ADR or architecture child is needed; preserve the renderer-to-host/instruction boundary.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Source ownership governs affected handlers. |
| AC-2 | required | Repairs the reproduced unknown protected-path verdict. |
| AC-3 | required | Honest compatibility without leaks/invented authority. |
| AC-4 | required | Known-tool compatibility and routine overhead. |
| AC-5 | required | Avoid speculative post-read lint/index work. |
| AC-6 | required | Existing host/trust boundaries. |
| AC-7 | required | Requested Codex workflow instructions through an actual owned carrier. |
| AC-8 | required | Existing-consumer delivery, customization, profile paths and bounded upgrade cost. |
| AC-9 | required | Change-local implementation/document quality. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-10 | Current source and scratch handler probe; no repository source changes. | `RenderedEditHookPathTests` scratch fixture: Edit/edit=2, unfamiliar same-path tool=0 without diagnostic, Read/view=0. Source dispatch at980–983/1372–1384. |
| 2026-10-10 | Codex capability/schema checked; no live interception qualified. | Local0.162.1 hooks enabled; official documentation linked above; exposed `tools.apply_patch` wrapper. |
| 2026-10-10 | Readiness repair DC-20C-CARRIER: root independently replayed the full-render and managed-carrier scratch controls, then revised requirements/ACs/owner targets. No source edit or delivery claim. | Current render writes Codex config/skills but never transfers seed050 sentinel to existing AGENTS. Managed `_implement_doc` route transfers sentinel, preserves customization and writes nothing on second pass; readiness ledger cycle1. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-10 | Select explicit unknown classification, existing-path pre-gating/uncertainty and Codex instruction policy. | Repairs concrete silent handler allowance while preserving subscriptions and upgrade cost. | More guessed aliases: cannot identify future names and risks incorrect semantics. Match/block all tools and add native Codex interception: broadens shell/MCP/trust policy and requires owner/live-host qualification absent here. |
| 2026-10-10 | Unknown no-path calls advisory; unknown post calls do no lint/index work. | Copilot receives all calls; unsupported schema is not proof of a write. Blanket blocking breaks unrelated calls and speculative post work adds cost without evidence. | Unknown-as-read silently retains defect; every unknown-as-edit with required path blocks legitimate unsupported non-edits. |
| 2026-10-10 | Optional Review plan branches self-answered; no operator question remains. | Existing adapter fields decide path coverage; source census decides handlers; Codex carrier/schema fixtures establish policy presence, not enforcement. | Native Codex interception is separate owner/trust qualification, not readiness expansion. |
| 2026-10-10 | Replace the unowned seed050-to-existing-root-entry promise with the verified existing managed Implement wave instruction route. | Full current rendering refuted the root-entry transfer assumption; real managed reconciliation proved consumer delivery, customization retention and idempotence. Requirements7/8 and AC7/8 now own the narrower delivery scope. | A new universal root-entry writer or native hooks would expand ownership/trust and upgrade work. Editing bootstrap prose alone would leave existing consumers unchanged. Single-change delivery is unqualified and outside this repair. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Unknown read supplying a protected path conservatively blocks with closed guard. | Explicit compatibility uncertainty; only evidenced exact host identities exempt, never substrings/namespaces. |
| Future Claude name never matches subscription. | Document handler-versus-matcher limit; do not claim expanded host coverage. |
| Unknown successful edits miss automatic feedback. | Explicit uncertainty and existing integrity-boundary checks; no automatic unknown indexing claim. |
| Codex policy mistaken for native enforcement. | No native writer; separate host API availability, shipped support and agent adherence. |
| Workflow instruction presence mistaken for universal entry coverage. | Name the managed Implement wave carrier and skill route; existing root AGENTS and single-change routes are unqualified, not automatically refreshed. |
| Shared managed implementation prose overwrites 20bw2 work. | Coordinator serializes 20bw2 first, then this wave's distinct patch guidance; real integration preserves both and existing evaluator semantics. |
| Tool label carries controls or excessive output. | Bounded escaped label only, no arguments or patch content. |

## Session Handoff

See `docs/agents/session-handoff.md`. Planned, awaiting admission and independent readiness/prepare; all implementation tasks and ACs remain unchecked.
