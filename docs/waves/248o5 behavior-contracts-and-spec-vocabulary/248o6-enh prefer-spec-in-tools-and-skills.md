# Use spec names in lifecycle tools and skills

Change ID: `248o6-enh prefer-spec-in-tools-and-skills`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: 248o5 behavior-contracts-and-spec-vocabulary

## Rationale

The shortcut catalog already offers Plan spec and Close spec. Following the skill instructions takes agents back to commands such as `wf_add_change`. Meanwhile the tool reference lives under a path that calls a standing contract a spec. Readers encounter two names for one artifact and one name for two artifacts.

## Product Intent

An engineer can plan, admit, inspect and close a spec using one vocabulary across skills, MCP discovery and tool responses. An engineer can also discover how to author a standing behavior contract for an implemented feature. Maintainers can migrate existing scripts to the replacement calls and preserve the permissions attached to each operation.

## Requirements

1. Replace the five stock tools: `wf_new_change` → `wf_new_spec`, `wf_get_change` → `wf_get_spec`, `wf_add_change` → `wf_add_spec`, `wf_remove_change` → `wf_remove_spec`, and `wf_close_change` → `wf_close_spec`. Remove the old names from stock registration in the same release. Keep kind-specific creation tools such as `wf_new_bug` and `wf_new_enhancement`. Document the generic scaffold's kind.
2. Accept `spec_id` on replacement tools wherever their predecessors accepted `change_id`. Expose spec_id in stock spec operation results. Preserve identifier values, kind tokens, event schemas and explicitly declared legacy alias contracts. Resolve existing downstream declarations targeting an old core operation to its successor without exposing a stock legacy endpoint. Preserve explicit downstream bindings, schemas, wrappers and hidden operations. On collision, the downstream binding wins. Suppress only the conflicting stock spelling and report the actual authorized route or the configuration edit required. Preserve exact-name host ask/deny restrictions and grant scope. Withhold a new route when the framework cannot establish equivalent restrictions.
3. Make the preferred names discoverable through the tool index, help, recovery and next-tool hints, rendered skill instructions and prompt examples. Use “spec” for the lifecycle document and “behavior contract” for an enduring project promise. Keep ordinary uses such as “review the code changes” and external standard names such as OpenAPI Specification. Retain old shortcut phrases. Update source registries, seeds and generated host surfaces. Reconcile project-owned role documents and edited prompts through the existing upgrade process, preserving local guidance and reporting unresolved references.
4. Carry forward operation semantics, permission tiers, annotations, dry-run behavior and operator ownership. Announce the breaking MCP rename in release notes and upgrade guidance, with the five mappings and an argument migration example. Reconcile framework-owned callers and surface affected project-owned references for their owner. A fork may explicitly serve a legacy alias through its extension declaration.

5. Add the skill `/wf-contract` with the description “Write or update a behavior contract using the implementation and its tests.” Keep **Author behavior contract** as the natural-language shortcut. Both route to one installed project prompt grounded in seed 230. Register the shortcut in the prompt catalog and render the skill on enabled skill hosts when the prompt exists. Use the existing install and upgrade reconciliation paths and preserve project-authored prompt edits. This workflow needs no new MCP tool.
6. The author checks the implementation and supporting tests, then consults the contract index. Update an existing authoritative page when one covers the behavior, including a page linked from outside the collection. Otherwise create a page in the contract home established by 248o4 and link it from the index. Identify missing verification explicitly. Route proposed behavior to Plan spec. Authoring a contract does not change its publication scope.

7. Write `Spec ID:` and `Spec Status:` in new stock spec documents and admission entries. Read both generations in the same wave. Preserve existing labels when updating an old entry, honor custom profiles, and refuse conflicting declarations before a mutation. Keep existing approval currency for unchanged records.
8. Inventory public ID consumers across marking, kind-specific creation, bulk lookup, listings, resources, CLI, dashboard, examples and recovery hints. Supply spec_id for stock callers of spec-facing operations. Preserve existing clients of established operations through compatible input/output aliases and reject disagreeing IDs. Preserve exact downstream schemas and opaque evidence payloads.

## Scope

Cover the shipped operator and agent vocabulary across lifecycle entry points. Sibling 248o4 owns contract discovery, migration and publication. The amendment covers human-authored labels and public spec identifiers. Historical ledgers, approval digests, persisted JSON and private implementation identifiers retain their existing contracts.

## Acceptance Criteria

- [x] AC-1: Using only shipped discovery and skill guidance, a fresh caller creates, admits, retrieves, removes, re-admits and dry-runs closing a spec in a fixture without guessing a change-named command or argument. A refused operation points to a usable preferred recovery call.
- [x] AC-2: Query the stock MCP registry and invoke each retired name directly. All five must be absent and return unknown-tool without a write. Compare the replacement operations against pre-upgrade fixtures for state, refusal, response and dry-run behavior. Start a customized server whose existing wf_get_spec alias targets wf_get_change and accepts change_id. Verify its schema and dispatch, a usable recovery hint or configuration remedy, and an unrelated operation. Test explicit host ask, deny and allow rules, hidden tools and a renamed profile.
- [x] AC-3: Check the rendered host skills, quick start, CLI help, MCP schemas and examples against the actual registry. A reader following a contract link reaches the durable behavior documentation. Record intentional legacy labels and relevant external vocabulary in the final inventory.

- [x] AC-4: On both the newly installed and upgraded fixtures from 248o4, inspect the installed MCP registry and each enabled host’s generated skills and prompts. Follow their instructions to create and retrieve a spec. Verify links resolve at their installed locations, an existing downstream override survives upgrade, and a second render introduces no drift.

- [x] AC-5: On the fresh-install and upgrade fixtures, verify that each enabled skill host lists `/wf-contract` with the specified description and that invoking it or the natural-language shortcut resolves to the same installed prompt. Follow it on a tested behavior, check the resulting contract references its source and test, and follow the index link. Repeat with an existing authoritative page outside the collection and verify it is updated without duplication. With a proposed behavior absent from source, the workflow directs the author to Plan spec and creates no standing promise. Verify that a project edit to the backing prompt survives reconciliation.

- [x] AC-6: Exercise one legacy and one new spec together through admission, lookup, marking, review and close. Check byte preservation of historical evidence and refusal of conflicting IDs or statuses without writes.
- [x] AC-7: Exercise each affected public schema and returned identifier on stock and downstream fixtures. Follow generated hints and verify that input, result and guidance agree, including direct and bulk reads and kind-specific creation.

## Tasks

- [x] Inventory exposed names, parameters, annotations, alias resolution and downstream overrides.
- [x] Implement the compatibility mappings and exercise a complete fixture workflow through the replacement interface and a customized distribution.
- [x] Reconcile seeds, rendering, skill bodies, discovery, recovery, tool reference and migration guidance with the served names.

- [x] Verify release and upgrade guidance names all five breaking calls. Run the vocabulary checks on installed pack contents and reconciled target surfaces in both fixtures.

- [x] Deliver the seed-230-backed prompt through install and upgrade, register the skill and shortcut, and exercise the create, update and proposed-behavior cases in AC-5.

- [x] Update the record readers and writers and exercise mixed-generation lifecycle records.
- [x] Reconcile stock public identifiers and exercise existing clients and downstream declarations.

## Agent Execution Graph

Inventory the registry, implement shared dispatch and compatibility, then render and exercise both caller journeys.

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/mcp_tool_roster.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/seeds/`

## Affected Architecture Docs

Update the MCP tool surface contract in its migrated location and the architecture hub's reference to it.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Demonstrates the new user journey. |
| AC-2 | required | Protects downstream callers and authority. |
| AC-3 | required | Keeps guidance executable. |
| AC-4 | required | Proves the vocabulary reaches downstream installations. |
| AC-5 | required | Demonstrates contract authoring from either entry point in an installed project. |
| AC-6 | required | Protects existing records and approvals during adoption. |
| AC-7 | required | Establishes a usable public identifier across entry points. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Inventoried five change-named operations in the tool reference and the existing plan-spec and close-spec skill directories. | Tool index and generated Codex skill tree. |
| 2026-11-24 | Operator superseded the compatibility-alias default after readiness. Remove the five stock names in the adopting release. | Updated requirements and AC-2 require a new readiness receipt. |
| 2026-11-24 | Operator requested the contract-authoring skill in this wave. | Requirements 5–6 and AC-5. |
| 2026-11-24 | Readback: expose the five spec-named MCP operations and preserve stored records, kind-specific calls, downstream wrappers and host restrictions. Deliver the Author behavior contract shortcut and /wf-contract with the same installed prompt. | Test stock registry and direct calls, custom aliases and hidden operations, install and upgrade skills and references. A fresh caller should admit with wf_add_spec and spec_id. |
| 2026-11-24 | Implemented the five spec operations and the contract authoring skill. Verified new and upgraded installations using the candidate pack, including a downstream alias with the old input schema. Legacy installations require operator confirmation of host permission rules before exposing replacement operations. | Fresh-process MCP calls, install and upgrade fixtures, and generated skill checks. Full framework qualification is separate. |
| 2026-11-24 | Reopened implementation after the operator approved AC-6 and AC-7. The red-team primer exercised stock record recognition and confirmed that Spec ID and Spec Status currently fail. Keep admission row boundaries distinct, retain each row’s previous-status spelling on close/reopen, and check approval currency in addition to historical bytes. | wave_lint_lib.constants and the close/reopen writers. |
| 2026-11-24 | Public inventory includes the two checklist marking tools, kind-specific creation results, bulk reads and the parameterized MCP resource. Add a spec URI and keep existing change bookmarks. Review listings, dashboard adapters and guidance for exposed identifiers. Keep stored review evidence, downstream schemas and implementation-only fields stable. | server_impl.register_mcp_surface, resource_change, dashboard.js. |
| 2026-11-24 | Implemented the amended records and public ID contracts. The mixed fixture admitted, marked and reviewed a new spec beside a legacy spec, preserved the old approval digest, and exercised close and reopen. Both MCP resource URIs returned the same document. Focused stock MCP checks exercised identifier input aliases, returned IDs, and refusal on disagreement. | test_close_change, test_spec_tool_surface, McpResourceTemplateReadTests and DashboardSnapshotTests. Broader verification remains separate. |
| 2026-11-24 | Replaced the earlier install evidence with a disposable package from the repaired source. On fresh and upgraded stock targets, the registered tools returned spec_id and wrote Spec ID and Spec Status. The upgraded downstream fixture kept its declared change_id lookup schema. | [Pack hashes, MCP results and recorded headings](evidence/installed-spec-verification.json). The earlier install checks predated the field amendment. |
| 2026-11-24 | Repaired checklist tool schemas and their reference entries. Upgrade previews now tell operators to run the permission confirmation from the target checkout without disclosing its absolute path. | Stock MCP registration and reload tests, upgrade dry-run checks and host-permission tests. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Superseded initial plan to retain stock compatibility aliases. | Operator requested minimal change terminology. Compatibility aliases are the planner default given the downstream usage. | Prose alone leaves tool calls inconsistent. A hard rename breaks callers and forks. |
| 2026-11-24 | Remove all five legacy stock names when the spec tools ship. | Operator chose one discoverable vocabulary now. | A deprecation window would preserve existing calls but expose both names. |

## Risks

| Risk | Mitigation |
| --- | --- |
| An alias exposes a hidden operation or bypasses a downstream wrapper. | Compare discovery and execution under explicit overrides and permission profiles. |
| Rewriting identifiers invalidates old evidence. | Verify existing records and keep their serialized fields stable. |

## Session Handoff

Prepare should review the compatibility matrix against the served registry and the legacy profile before implementation.
