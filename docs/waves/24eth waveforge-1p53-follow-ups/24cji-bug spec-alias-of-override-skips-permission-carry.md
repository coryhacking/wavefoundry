# A distribution alias for a renamed spec tool skips the permission carry-over

Spec ID: `24cji-bug spec-alias-of-override-skips-permission-carry`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-26
Wave: 24eth waveforge-1p53-follow-ups

## Rationale

This changes the host-permission promise for the renamed spec tools stated in the upgrade prompt's "MCP tool names for change specs" section (seed `160` and `docs/prompts/upgrade-wavefoundry.prompt.md`): each exact rule for a previous tool gets the same rule for its replacement, and setup readiness reports the withheld tools.

Waveforge reported, on v1.53.0, that a rule on `wf_close_change` is not carried to `wf_close_spec` when the distribution overrides the stock close handler, and nothing warns. Executing the declaration showed the gap is narrower than reported and real:

- With only an override of `wf_close_change`, the distribution's handler keeps the name `wf_close_change` and `wf_close_spec` is not served, so an existing deny or ask rule still restricts the served tool. Nothing is lost. (executed: `mcp_tool_roster.all_tool_tiers()` under a validated declaration returns `wf_close_change: write`, `wf_close_spec: None`.)
- When the distribution also declares `EXTENSION_TOOL_ALIASES = {"wf_close_spec": "wf_close_change"}` to follow the rename, which is what Waveforge did, both names are served with the write tier. `mcp_tool_extensions.stock_spec_routes()` (`.wavefoundry/framework/scripts/mcp_tool_extensions.py:336`) drops `wf_close_change` because it is an override target and `wf_close_spec` because it is occupied by an alias. Every permission caller receives that route set: the permissions render (`render_platform_surfaces.selected_permission_rules` and `migrate_spec_tool_permissions`), the upgrade summary (`upgrade_wavefoundry._spec_tool_permission_summary`, which also calls `mcp_tool_roster.spec_permission_holds(root)` whose `routes` default is `stock_spec_routes()`), setup readiness (`spec_tool_permissions.setup_pending` from `setup_readiness`), the acknowledgement command (`spec_tool_permissions.acknowledge`) and the server's hold check (`server_impl._spec_registration_routes`). A deny on `wf_close_change` therefore never reaches `wf_close_spec`, the name agents are now told to call, and no hold or diagnostic says so. (executed for the tiers; the per-caller effect is inferred from the shared route set.)

The same holds for any of the five renamed pairs whose new name a distribution aliases onto the old one, whether the old name is overridden, hidden or plain (executed by the red-team readiness seat). An alias onto a replaced core name is refused by the declaration validator, so that case cannot arise.

## Product Intent

A repository owner whose host denies or asks before a renamed lifecycle tool keeps that restriction after a distribution republishes the tool under its new spec name. Before: the restriction silently stops applying to the new name. After: the framework carries the restriction to the aliased new name, or withholds that name until setup has migrated and verified the rules, exactly as it does for a stock rename. AC-1 and AC-3 together test whether this is established. Distributions that do not alias a new spec name onto an old one see no change.

## Requirements

1. An **aliased spec pair** is an old name `old` from `SPEC_TOOL_NAMES` with new name `new` such that the declaration serves `new` as an `EXTENSION_TOOL_ALIASES` alias whose canonical name is `old`, and `old` is not in `stock_spec_routes()`. The set is derived from the validated declaration at call time; no list of pairs is hard-coded.
2. Every permission consumer that today receives `stock_spec_routes()` receives the stock routes plus every aliased spec pair through one accessor: the permissions render carry-over, `migrate_repository` and the upgrade summary in `upgrade_wavefoundry._spec_tool_permission_summary`, the `routes` default of `mcp_tool_roster.spec_permission_holds`, `setup_pending` in setup readiness, the acknowledgement command's `--tool` choices, and the server's hold check. A deny, ask or constrained rule on `old` is carried to `new` with its constraint kept verbatim, as for a stock route. Tier and serving consumers (`mcp_tool_roster.all_tool_tiers`, `_served_low_risk_write_tools`) keep using `stock_spec_routes()`.
3. While the aliased `new` is held (a review hold exists only when `spec_tool_permissions._requires_review(root)` is true, as for stock routes), the server removes the distribution alias after the `EXTENSION_TOOL_ALIASES` loop in `server_impl._install_served_names` and reports it unavailable with the hold's recovery text. The stock-route value returned by `_spec_registration_routes` stays stock-only, so no stock-schema tool is ever built over the distribution's handler. While the alias is withheld, response hints name the old name the distribution still serves, never the withheld `new`. Setup readiness lists the held `new` among `spec_tools_withheld`. Unlike a stock route, the old name stays served throughout.
4. `stock_spec_routes()` itself is unchanged, so which names are served, their schemas, tiers and hints for an aliased pair are unchanged once permissions are verified.
5. A declaration with no aliased spec pair produces byte-identical permission renders, migrations, readiness results and served tool lists.
6. Behaviour is identical on Windows, macOS, Linux and WSL2: the change is in name resolution only and touches no path or process handling.

## Scope

**Problem statement:** a distribution alias that republishes a renamed spec tool escapes the permission carry-over.

**In scope:**

- A derived aliased-spec-pair set in `mcp_tool_extensions.py` and its use by every permission consumer named in Requirement 2.
- Server withholding of an aliased `new` while its permissions are unverified.
- Tests under a real validated declaration.
- One sentence on aliased spec pairs in the upgrade prompt's "MCP tool names for change specs" section, in seed `160` (under `seed_edit_allowed`) and `docs/prompts/upgrade-wavefoundry.prompt.md`.

**Out of scope:**

- Carrying rules to aliases of tools that were never renamed. An alias of any other tool keeps today's behaviour: its own name needs its own rule.
- Changing what an override, replacement or alias serves once permissions are verified.
- A replacement that serves core behaviour under the new spec name through `alias_for_core` (for example `EXTENSION_REPLACEMENTS={"wf_close_change": {"alias_for_core": "wf_close_spec"}}`): it is a distribution-declared core alias, not an `EXTENSION_TOOL_ALIASES` pair, and keeps today's behaviour.
- Codex user-level or enterprise managed settings beyond what the stock route already handles.

## Acceptance Criteria

- [x] AC-1: Under a validated declaration that overrides `wf_close_change` and aliases `wf_close_spec` to it, a project Claude settings file denying `mcp__wavefoundry__wf_close_change` renders with the same deny on `mcp__wavefoundry__wf_close_spec`, and a constrained ask keeps its constraint verbatim; with the derived pair removed from the permission routes, the same test fails. Oracle: unit test in `test_spec_tool_permissions.py` driving the real render and `migrate_repository`.
- [x] AC-2: The same declaration without any rule produces no held tool after setup verification, and a declaration with no aliased pair produces byte-identical render output, migration result, `setup_pending` result and served tool list to today's. Oracle: before/after comparison tests.
- [x] AC-3: Under that declaration, in a fixture where `_requires_review(root)` is true and before setup verification, setup readiness reports `spec_tools_withheld` naming `wf_close_spec`, the upgrade summary's `spec_tool_permission_holds` names it, the server leaves `wf_close_spec` unserved with the hold's recovery text, and a hint that names close names `wf_close_change`. After `record_verification`, `wf_close_spec` is served with the distribution alias's own schema. A control with the old name only overridden (no alias) reports nothing withheld.
- [x] AC-4: The pair is derived, not listed: a test aliasing a different renamed pair (`wf_remove_spec` to an overridden `wf_remove_change`) is carried and held the same way without editing any list.
- [x] AC-5: Both upgrade prompt copies state the rule for aliased spec pairs in the "MCP tool names for change specs" section, and the change's own suites and every test it adds pass; the documents this change edits validate.

## Tasks

- [x] Add the derived aliased-spec-pair helper and a permission-routes accessor in `mcp_tool_extensions.py`.
- [x] Route every permission consumer in Requirement 2 through the accessor, including the `spec_permission_holds` default.
- [x] Withhold a held aliased `new` after the alias loop in `_install_served_names`, and keep hints on the served old name.
- [x] Tests for AC-1 to AC-4 under a real validated declaration.
- [x] Add the aliased-pair sentence to both upgrade prompt copies.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| helper | implementer | — | derived set and accessor |
| consumers | implementer | helper | render, migrate, readiness, acknowledge, server |
| tests-docs | implementer | consumers | AC-1 to AC-5 |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/spec_tool_permissions.py`
- `.wavefoundry/framework/scripts/mcp_tool_roster.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_spec_tool_permissions.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`

## Affected Architecture Docs

N/A for architecture docs: the promise lives in the upgrade prompt copies listed in Scope; no layering, flow or contract-doc change. `docs/architecture/contracts/mcp-tool-surface.md` does not state the carry-over rule.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The restriction reaching the new name is the fix. |
| AC-2 | required | Stock and unaliased distributions must not change. |
| AC-3 | required | Unmigrated layers must hold the name rather than serve it unrestricted. |
| AC-4 | important | Guards against a per-pair list. |
| AC-5 | required | The prompt must state the promise. |

## Progress Log

2026-11-26: The full suite caught stale permission-source hashes in the committed Claude pre-edit hook. The canonical surface renderer updated only those two hashes. The previously failing hook parity test then passed.

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-26 | Planned from the Waveforge v1.53.0 report, finding 1. | Executed tier check in Rationale. |
| 2026-11-26 | Readiness repair for RDY-2: added the `spec_permission_holds` default and `mcp_tool_roster.py`, moved the documented promise to the upgrade prompt copies, named the withholding site and hint behaviour, dropped "replaced", stated the `alias_for_core` case out of scope and the review-required fixture state. | Red-team and docs-contract readiness reports. |
| 2026-11-26 | Readback: carry permissions to explicitly re-aliased spec names, withhold them until verified, and keep hints on the served old name. Preserve stock registration and distribution schemas. | AC-1 to AC-5: declaration, permission consumers, server and upgrade prompts. |
| 2026-11-26 | The permission resolver includes exact old-to-new aliases. Registration withholds the alias until verification, directs hints to the served predecessor, and restores the distribution schema when verification succeeds. The grant and operation rosters retain their previous owners. | The focused permission, readiness and real MCP registration suites ran 46 tests with one runner-only skip. Both close and remove failed under the stock-only control. Work evidence: `impl/24cji-focused.log` and `impl/24cji-mutant.log`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-26 | Treat an aliased spec pair as a stock route for permissions only (carry, hold and withhold), leaving `stock_spec_routes()` and serving unchanged. Planner default; the operator asked for a single wave covering the DO items. | Replaying the Waveforge case: the deny on `wf_close_change` reaches `wf_close_spec` through the existing carry-over, and unmigrated outside layers hold the name through the existing hold machinery. The mechanism controls the outcome rather than advising. It could wrongly hold a distribution alias that was deliberately unrestricted; setup verification clears that, as for stock. Measured after release by the next Waveforge carry-over check. | (B) Carry only, no withholding: outside layers the framework cannot write would leave the new name unrestricted silently. (C) Report the pair in readiness only: advice that a distribution must act on, and the failure is silent until someone reads it. (D) Put override targets back into `stock_spec_routes()`: changes what is served and registers stock schemas over a distribution's own handler. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Server withholding of an alias is a new step in `_install_served_names`; the per-caller effect is inferred, not executed. | AC-3 drives the real registration path and checks the served schema and hints. |
| A distribution relying on its alias being served before setup sees it withheld until setup runs. | Same contract as the stock rename; the withheld text names the recovery. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
