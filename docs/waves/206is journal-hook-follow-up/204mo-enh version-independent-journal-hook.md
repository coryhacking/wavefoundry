# Allow journal relocation beyond the legacy version gate

Change ID: `204mo-enh version-independent-journal-hook`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: `206is journal-hook-follow-up`

## Rationale

The declared pre-migration hook is currently called only before the 1.15.0 cutover. A distribution that owns journal relocation needs an explicit path on later upgrades without silently broadening the built-in destructive migration or executing hooks during preview. Addresses Waveforge public request C6 against `d11da852`, received 2026-10-08. Deliverable: framework fixes, focused regression evidence and documented compatibility behavior. This document authorizes planning only; implementation follows admission and readiness.

## Requirements

1. Introduce EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER for the existing hook, with the shipped legacy_cutover default and journals_present opt-in. An absent constant means legacy_cutover. A present constant must have exactly one direct module-level literal string assignment, plain or annotated. Only these two strings are supported; empty/non-string/invalid literals, nonliteral expressions, conditional or duplicate bindings are refused clearly before declaration execution or dependent migration.
2. Call the opted-in hook during upgrade apply when supported source journals exist, independent of from-version. The source is the standard docs/agents/journals directory, confirmed by the operator; retain direct regular *.md journal files excluding README.md, without following linked paths or scanning recursively. No configurable source-root declaration is needed. Schedule at the existing pre_docs_gate journal boundary, at most once per invocation; repeated upgrade attempts require an idempotent hook. No exactly-once-across-crashes promise.
3. Keep the existing built-in pre-1.15 migration gate and existing declarations’ default semantics. A hook failure prevents dependent migration and yields a clear diagnostic.
4. Keep dry-run and public migrate_journals preview free of declaration, hook and distribution-helper execution. Trusted shipped read-only framework helpers may supply bounded source reads. Report the proposed trigger and eligibility statically, distinguishing invalid declarations from unknown source. Unreadable or unparseable source is unknown, not an absent declaration: later-version apply skips the hook with a path-free uncertainty diagnostic and no declaration execution; the original pre-1.15 path retains its validated apply-time load/refusal. Absent or literal legacy_cutover remains dormant on later upgrades.
5. Resolve hook code and dependencies from the extracted pack, including calls made by an older runner. Use a journal-only incoming import context spanning selected declaration validation and hook loading/call, shadowing incoming top-level module/package names and their descendant keys. Restore prior sys.modules identities, remove newly introduced affected modules, and restore sys.path on success and failure. Give the incoming directory precedence even if it was already later on sys.path; do not change the generic _scripts_on_sys_path helper. Update the shipped journal seed and all named project contracts together.
6. Register EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER = legacy_cutover in tests/record_layout_support.py's SHIPPED_DECLARATION so base declarations and profile overlays include the new constant. Preserve the journal validator's existing third positional helper_modules argument and keep journal declarations outside declared() MCP-extension activation.

### Static trigger decisions

| Declaration source / binding | Upgrade apply | Dry-run / public preview |
| --- | --- | --- |
| Missing module or absent trigger constant | Existing legacy_cutover behavior; later versions import no declaration or hook | Report legacy_cutover without executing extensions |
| One direct literal legacy_cutover | Existing cutover behavior, including the legacy hook with no journal source | Report the legacy gate; no hook execution |
| One direct literal journals_present | Call at pre_docs_gate only when contained direct regular singly linked *.md journals excluding README.md exist; builtin migration independently remains pre-1.15 | Report policy and bounded presence; public migration preview never executes the hook |
| Explicit invalid value, nonliteral, conditional or duplicate binding | Refuse before declaration execution or dependent migration | Report static invalid/unsupported declaration without executing it |
| Unreadable/refused or unparseable source | Later versions skip with uncertainty diagnostic; original pre-1.15 validated apply-time load/refusal is preserved | Report unknown, never silently substitute a default or execute the declaration |

## Scope

In scope: the public request C6 and the declared review targets below. Delivery qualification discovered a bounded adjacent declaration-reset fixture in tests/test_extension_tool_modules.py; include its new shipped trigger default without changing the existing census. Retained migration-input references use the existing exact v2 historical-record judgments in docs/reconcile-dispositions.json; preserve source documentation, raw audit findings and detection of changed or new live instructions.

Out of scope: other requests, native host hook classification, packaging skip-parity policy, publishing, release creation, and unrelated refactors.

## Acceptance Criteria

- [x] AC-1: An opted-in hook runs once with qualifying direct regular singly linked *.md journals in docs/agents/journals, excluding README.md, on upgrades from before, at and after 1.15.0; missing/empty/README-only/nested-only/symlink/hardlink sources produce no invocation. Presence is inspected without reading journal content and is not inferred from migration preview's left entries.
- [x] AC-2: Absent opt-in retains the existing cutover behavior; later-version hook invocation alone does not authorize the built-in journal migration.
- [x] AC-3: Dry-run and public preview execute no declaration/hook/distribution helper and make no target changes. Exercise every static-decision row, including empty/non-string/invalid literal, nonliteral/conditional/duplicate bindings and unknown source. Malformed policies and failing hooks are reported without dependent migration; diagnostics do not promise rollback of hook-owned partial effects.
- [x] AC-4: An actual older-runner upgrade fixture loads the new hook and incoming sibling dependencies from the pack at both import and call time despite cached old modules, and restores prior module/path state on success and failure. Retry behavior matches once per invocation and hook-owned idempotence, without an exactly-once-across-crashes promise. The production declaration census, base declaration and profile-overlay controls include the new default; the existing third positional validator API and stock MCP declared() remain compatible.

## Tasks

- [x] Resolve the journal-presence scope and declaration name before readiness.
- [x] Implement validated opt-in scheduling, ordering and extracted-pack loading.
- [x] Cover the static-decision/source/version matrix, dry run, hook failure/partial effects, actual old-runner cached dependencies and retries; verify declaration fixture/profile compatibility and module/path restoration.
- [x] Update canonical seed, local contract, dataflow and layering invariant; collect all five required lane approvals and closure-readiness evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Contract and fixtures | Implementer | Readiness | Own declared source/test edits only |
| Documentation | Technical writer | Contract | Own named documentation; coordinate shared files |
| Independent review | Code reviewer and QA reviewer | Implementation | Read-only review and evidence; additional lanes selected at Prepare |

## Serialization Points

One writer per shared file. Complete test-oracle repairs before consumers extend those tests; serialize `upgrade_extensions.py`, shared profile modules and the MCP surface specification across changes. Reviewers do not edit implementation files. Generated local surfaces are regenerated from canonical sources, never patched in lieu of seeds.

- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/reconcile-dispositions.json`
- `.wavefoundry/framework/seeds/210-migrate-journals.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/layering-rules.md`

## Affected Architecture Docs

docs/specs/mcp-tool-surface.md, docs/architecture/data-and-control-flow.md and docs/architecture/layering-rules.md: static selection, selected apply-time loading, independent builtin permission, ordering, preview, import restoration and failure/retry contract. Canonical seed: .wavefoundry/framework/seeds/210-migrate-journals.prompt.md; regenerate any existing applicable local surface (the command catalog currently points directly to this seed; do not invent a new local prompt).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Direct evidence for the requested compatibility behavior |
| AC-2 | required | Direct evidence for the requested compatibility behavior |
| AC-3 | required | Direct evidence for the requested compatibility behavior |
| AC-4 | required | Direct evidence for the requested compatibility behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Final whole-checkout quiet canonical qualification passes11995 tests across177files with20 existing skips; fresh green receipt 83a742059996ef0eedc2fd3c637d5ef8864dedfbdacbf8c8c88f29d226f86092 recorded 2026-10-09T16:44:30.287213+00:00. Final11 reviewed paths remain unchanged; all five delivery approvals are current and six finding heads are terminal. All required ACs/tasks are complete. Technical dry close and pause are next; wave closure remains operator-owned; no closure, commit, push or new pack. | [consolidated evidence](wave.md#evidence-retention); events.jsonl |
| 2026-10-09 | All11995 tests across177files completed green with20 existing skips in523.213s, but root published review events and documentation/evidence while the runner was active. The whole-repository quiet-tree guard therefore correctly rejected the run and wrote no green receipt. The final11 source paths were unchanged; there is no test failure or source repair. Finish bookkeeping and rerun the complete suite with no checkout writes until it exits; never waive the guard or reuse the stale receipt. | evidence/delivery/wf-206is-canonical-concurrent-bookkeeping.log names only the coordinator bookkeeping deltas; quiet full-suite qualification remains pending |
| 2026-10-09 | All three delivery qualification findings are terminal after five actual cycle2 lane reverifications: docs clears the exact historical-reference repair; QA and code independently clear both fixture repairs. The last clearance atomically records the convergence checkpoint. All five required specialist delivery approvals are current; no council-delivery is required by this receipt. New code/QA/docs contexts did not implement repairs. They execute the current journal/older-runner controls and own paired reverse-fixture or changed/omitted/new-instruction counterexamples; original scoped architecture/security review remains unaffected by these qualification-only repairs. All final11 paths are unchanged. Canonical full suite is still running; final task remains open. | evidence/delivery/wf-206is-reverify-code.json; wf-206is-reverify-qa.json; wf-206is-reverify-docs.json; wf-206is-delivery-architecture.json; wf-206is-delivery-security.json; typed events.jsonl |
| 2026-10-09 | Re-Prepare for the two named qualification fixtures and existing exact historical store passed with five fresh specialist approvals and actual standard council: isolated three-stance/two-question primer, four fixed seats, rotating docs alternative weighed by all fixed seats, then masked merits and authority reattachment. Applied only two literal fixture corrections and three exact historical judgments after recorded cycle-2 repair starts; runtime, seed, contracts and census/scanner logic are unchanged. All four required ACs now have passing implementation controls; fresh affected-lane reverification and canonical suite remain pending. | evidence/readiness/wf-206is-qualification-chair-final.json; evidence/delivery/wf-206is-qualification-repair-applied.log; [consolidated evidence](wave.md#evidence-retention):22 tests,zero skips,OK; final11 fingerprint baf1cf4c3c0df2a99582886d78366a79675e6f0e12338e0d2322c4cd2a1e4d21 |
| 2026-10-09 | Named runtime consistency pins: deleting the loaded/static equality branch fails test_loaded_trigger_must_match_static_selection_before_dependents; deleting the loaded type/allowlist branch fails test_loaded_invalid_trigger_is_refused_by_framework_policy_guard; deleting the other-binding AST clause fails test_function_class_exception_and_pattern_trigger_bindings_are_invalid_before_execution. The first two mutants reach a deliberately forbidden hook load; the third changes invalid to valid. All unmutated controls pass. | evidence/delivery/wf-206is-guard-pins.json and guard-logs preserve all 25 exact mutants, paired commands, named tests and causal assertions; evidence/delivery/wf-206is-guard-final-replay.py with its two sibling replay/annotation scripts reproduces them after copying those scripts and wf-206is-guard-pins-initial.json to /tmp |
| 2026-10-09 | Guard landing proof completed on the frozen implementation: 25 bounded deletions/loosenings, 24 causal named-test failures with paired green baselines and no skips. Static preexecution/type/allowlist/conditional/duplicate/shadow-binding refusal, loaded trigger consistency/validity, default dormancy, independent builtin permission, README/regular/single-link/ancestor eligibility, preview nonexecution, incoming cache/descendant/path precedence and identity/path cleanup are pinned. A partial ancestor deletion survives because remaining containment still refuses it; deleting the full no-follow family is detected. Added named tests for runtime equality/invalid policy and unsupported function/class/exception/pattern bindings. | /tmp/wf-206is-guard-pins.json maps each mutant to its named failing test and actual assertion; replay /tmp/wf-206is-guard-final-replay.py; [consolidated evidence](wave.md#evidence-retention): 18 tests, no skips, OK; frozen fingerprint a1033368f0c48a884fe0c5c38fc0f48d1201eb994d07feef57731d6bb579c600 |
| 2026-10-09 | Implemented literal trigger validation, bounded source scheduling, preview metadata, independent builtin gate and temporary incoming module/path restoration. New public-path policy and real older-runner fixtures pass; the broader upgrade/protocol/profile owners pass. Mutation verification found additional runtime-trigger and shadow-binding test gaps; tests are being extended before requesting delivery review. | [consolidated evidence](wave.md#evidence-retention): 15 tests, no skips; /tmp/wf-206is-runtime-baseline.log: 27 tests, one native-Windows skip; /tmp/wf-206is-owner-integration.log: 834 tests, two platform skips, OK |
| 2026-10-09 | Readback: implement the reviewed static trigger table at pre_docs_gate, standard contained direct singly linked Markdown eligibility, once-per-invocation idempotent hook and separate legacy builtin permission. A qualifying 1.29 journals_present upgrade changes from no hook to one hook call with zero builtin migrations; default and preview stay non-executing on later upgrades. Root owns upgrade_extensions.py, mcp_tool_extensions.py and the shipped fixture registry; separate implementers own the two named test files and canonical seed/spec/dataflow/layering docs. Memory advisories about stale dependencies and exception/state identity inform a journal-only temporary import context, leaving generic reload/lock/publication mechanisms untouched. | Successful Prepare ready and Implement create at current receipt review-policy-0461c07cde4e57b46259; [consolidated evidence](wave.md#evidence-retention) and wf-206is-focused-chair.json |
| 2026-10-09 | Gapfill: attached live code_outline, targeted code_read and exhaustive code_keyword were used for affected symbols/callers. Root semantic docs and graph retrieval refused stale producer runtime; workers had mixed successful but explicitly stale/setup-input warnings, so indexed results served only navigation. Fresh scratch execution, live source and bounded mechanical patches supply authority; no setup or rebuild. | Independent readiness reports record actual tool status per context; current source snapshots at /tmp/wf-206is-source-before |
| 2026-10-09 | Operator confirmed Waveforge uses the standard journal folder. Source-location blocker resolved; retain existing direct Markdown scope with README exclusion and no recursive scan or additional roots seam. Declaration name and pre_docs_gate boundary remain selected. Preparation, independent readiness and implementation have not run. | Operator: "they use the standard folder"; Requirements 1–2 and AC-1 |
| 2026-10-08 | Planned from public report and current source inspection; not implemented or readied | Declared source targets and request C6 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-09 | Use docs/agents/journals as the source; retain direct regular *.md files excluding README.md and existing path containment. | Operator confirmed the standard folder; the existing bounded scope satisfies the stated location without new configuration. | Configurable source roots and recursive discovery add unrequested scope. |
| 2026-10-08 | Add an explicit opt-in trigger while retaining the legacy default and built-in migration gate. | Preserve the requested behavior and existing compatibility boundaries | Removing the gate globally silently reruns existing distribution hooks; a second callable seam duplicates loading and validation without resolving trigger semantics. |

| 2026-10-08 | Select EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER and retain pre_docs_gate as the scheduling boundary. | The actual current hook executes there, not in post_extract; preserving the boundary keeps old-runner behavior and pre-lint ordering coherent. | Moving hook execution to post_extract creates a second lifecycle boundary unnecessarily. The source-location question remains pending operator input. |

| 2026-10-08 | Move unchanged C6 scope from 204mp to planned 206is while its source-location decision is pending. | Allows independent C1–C5 implementation to proceed without guessing at journal scope; this change remains admitted and retained under the same ID. | Holding all public fixes would unnecessarily serialize independent work. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A presence check that diverges from the selected migration scope may invoke or skip the hook incorrectly. | Use the confirmed standard directory with direct regular *.md files excluding README.md. Test absent, README-only, nested-only and linked sources alongside qualifying journals; no broader scan or roots seam. |

## Session Handoff

See `docs/agents/session-handoff.md`. Source location is resolved; independent preparation and readiness approval still precede implementation.
