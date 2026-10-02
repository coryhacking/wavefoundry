# Retire the Feat Change Kind for New Change Docs

Change ID: `1zlhx-change retire-feat-change-kind`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zli8 retire-feat-change-kind

## Rationale

A change doc is the smallest planning unit in the framework: one scoped change whose acceptance criteria a single wave can close. A product feature usually spans several changes and often several waves, so the `feat` kind names something larger than the record it labels. In practice it invites oversized plans that get split mid-wave, it has no structural boundary with `enh` (this repository holds about 41 `-feat` change docs against about 537 `-enh`), and "feature" already means "any change doc" in the **Plan feature** command name. A distribution that needs a feature-level grouping above waves builds its own construct, as the Waveforge distribution has.

This change stops minting new `feat` change docs while every existing `-feat` id, live or archived, keeps linting unchanged.

## Requirements

1. **Retired kinds are declared once.** `vocabulary_profile` gains, in the fixed and derived section beside `CORE_CHANGE_KINDS` (not the distribution-editable block, so the profile snapshot and assets are unchanged), `RETIRED_CHANGE_KINDS = ("feat",)`, a derived `MINTABLE_CHANGE_KINDS` (`CHANGE_KINDS` minus the retired kinds, same order), and `retired_kind_message(kind)`, the one refusal sentence every surface uses: it names the kind as retired for new change docs, says existing ids stay valid, and names `enh` / `wf_new_enhancement` as the replacement. `CORE_CHANGE_KINDS`, `CHANGE_KINDS`, `CHANGE_KIND_RE`, `VALID_CHANGE_KINDS` and every docs-lint change-id pattern are unchanged, so existing `-feat` ids in plans, change docs, wave records and archives lint exactly as before.
2. **No MCP or CLI creation path mints a retired kind.** The check sits inside `_change_create_response`, which every MCP and extension-helper creation path reaches (`_new_change_response` for each `wf_new_*` tool, and `change_doc_response`). It compares the normalized kind (`kind_s`, stripped and lowercased), runs before the slug check and before `change_create`, so no lifecycle id slot is consumed and no file or mint record is written, and returns `status: "error"` with data `{kind, slug, mode}`, exactly one diagnostic `change_kind_retired` carrying `retired_kind_message(kind)` with recovery tools `["wf_new_enhancement"]`, `next_tools=["wf_new_enhancement"]` and `usage="wf_new_enhancement(slug=...)"`. `wf_new_feature` stays registered and returns this refusal. The lifecycle-id CLI keeps `feat` in `--kind` choices (so `parse_args` and `--help` are unchanged) and refuses a retired kind in `main` with `retired_kind_message` on stderr and exit code 2. `change_doc_response` keeps its case-sensitive pre-check, so `"FEAT"` still returns `invalid_arguments` and `"feat"` returns `change_kind_retired`. The module functions `new_change` and `change_create` are internal scaffolding helpers, not creation surfaces: they are unchanged and test fixtures that build existing `-feat` docs through them stay valid. Every other kind, and a distribution's declared extra kinds, mint exactly as before.
3. **No silent remap.** A request for `feat` is refused, never converted to `enh`: the person planning decides whether the work is one change or several.
4. **Guidance points at the right tool.** The `wf_help` `plan_feature` workflow recommends `wf_new_enhancement` (chain, next step and usage) with fallback tools `wf_new_bug`, `wf_new_maintenance` and `wf_new_change`; `wf_list_plans` `next_tools` recommends `wf_new_enhancement` instead of `wf_new_feature`; the `wf_new_change` docstring stops listing `feat` among preferred kinds; the `wf_new_feature` docstring says the kind is retired and names the replacement.
5. **Docs and seeds.** The kind lists in seeds `001-feature-wave-framework-overview`, `110-wave-memory-bootstrap` and `170-plan-feature` (tool enumeration and both kind lists) say `feat` is retired for new change docs and stays valid for existing ids, and seed 170 says a large feature is planned as several changes, possibly across waves. The Plan feature prompts `docs/prompts/plan-feature.prompt.md` and `docs/prompts/agents/plan-feature.prompt.md` are not rendered from seed 170, so they are edited directly: drop the `feat` to `wf_new_feature` mapping and add the same guidance. The kind lists in `docs/PLANS.md`, `docs/contributing/feature-wave-lifecycle-overview.md` and `docs/references/enterprise-delivery-model.md` are updated the same way. `docs/specs/mcp-tool-surface.md` updates the `wf_new_<kind>` row and the `change_doc_response` contract (a retired kind is refused). The `AGENTS.md` tool notes describe `wf_new_feature` as retired. The **Plan feature** command name is unchanged. CHANGELOG gets a `### Changed` bullet that names the `change_doc_response` behaviour change and tells consuming repositories to drop the `feat` row from their own Plan feature prompts, which an upgrade does not rewrite.
6. **Distributions.** `EXTRA_CHANGE_KINDS` still refuses every core kind, so a distribution cannot re-enable `feat` through it. This is intentional and stated in `docs/architecture/layering-rules.md`.

## Scope

**Problem statement:** the `feat` kind labels a single change doc with a word that means a larger unit of work, which encourages oversized plans and blurs the line with `enh`.

**In scope:**

- `RETIRED_CHANGE_KINDS` and `MINTABLE_CHANGE_KINDS` in `vocabulary_profile`.
- The refusal in `_change_create_response` (reached by `wf_new_feature` and `change_doc_response`) and the CLI refusal in `lifecycle_id.main`.
- `wf_help`, `wf_list_plans` `next_tools`, tool docstrings, seeds 001, 110 and 170, both Plan feature prompts, `docs/PLANS.md`, the lifecycle overview, the enterprise delivery model, the tool-surface spec, `AGENTS.md`, layering-rules and the CHANGELOG.
- Tests and the register-surface handler digests that the refusal and docstrings change.

**Out of scope:**

- Removing the `wf_new_feature` tool or the `feat` grammar; existing `-feat` ids stay valid everywhere.
- Renaming the **Plan feature** command or its skill.
- Any feature-level grouping construct above waves.
- The internal scaffolding helpers `new_change` and `change_create`, which stay unchanged (a fork that edits source can still call them).
- The `-feat ` code-reviewer trigger token in `review_policy`, which keeps scoring existing documents.
- Rewriting existing `-feat` documents.

## Acceptance Criteria

- [x] AC-1: Through `call_tool`, `wf_new_feature(slug=...)` returns `status: "error"` with exactly one diagnostic, code `change_kind_retired`, whose message is `retired_kind_message("feat")` and whose recovery tools are `["wf_new_enhancement"]`, with the specified `next_tools` and `usage`; no file is created under `docs/plans/` and no lifecycle mint record is written.
- [x] AC-2: `change_doc_response(root, "feat", slug)` returns the same refusal and writes nothing, while `"FEAT"` still returns `invalid_arguments`; `lifecycle_id --kind feat --slug x` exits 2 with `retired_kind_message("feat")` on stderr, while `--kind enh` and a declared extra kind still mint.
- [x] AC-3: Existing `-feat` change docs, plans and wave records lint clean (a fixture plan, change doc and wave record using `-feat`), and `CHANGE_KIND_RE`, `VALID_CHANGE_KINDS` and the docs-lint change-id patterns are byte-identical to before.
- [x] AC-4: A test pins that the `wf_help` `plan_feature` workflow recommends `wf_new_enhancement` (chain, next step, usage, fallbacks without it) and that `wf_list_plans` `next_tools` names `wf_new_enhancement` and not `wf_new_feature`; the `wf_new_change` docstring no longer lists `feat`; the `wf_new_feature` docstring names the retirement and the replacement.
- [x] AC-5: Seeds 001, 110 and 170, both Plan feature prompts, `docs/PLANS.md`, `docs/contributing/feature-wave-lifecycle-overview.md`, `docs/references/enterprise-delivery-model.md`, the tool-surface spec (`wf_new_<kind>` row and `change_doc_response` contract), `AGENTS.md`, layering-rules and the CHANGELOG describe `feat` as retired for new docs and valid for existing ids, and contain no remaining `feat` to `wf_new_feature` creation mapping.
- [x] AC-6: `RETIRED_CHANGE_KINDS` is the single source: in a scratch tree with `RETIRED_CHANGE_KINDS = ("bug",)`, `wf_new_bug` and `change_doc_response(root, "bug", ...)` refuse with `change_kind_retired` and `lifecycle_id --kind bug` exits 2, while `wf_new_feature` mints again; and the kind census still finds no hardcoded kind list outside `vocabulary_profile`.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add `RETIRED_CHANGE_KINDS` and `MINTABLE_CHANGE_KINDS` to `vocabulary_profile`.
- [x] Refuse retired kinds in `_change_create_response` (so every `wf_new_*` tool and `change_doc_response` share it) and in `lifecycle_id.main`, both through `retired_kind_message`.
- [x] Update `wf_help` (chain and fallbacks), `wf_list_plans` `next_tools`, the two docstrings, and `tests/fixtures/register-surface-handler-digests.json` for the changed docstrings.
- [x] Update `test_change_kinds.py`: `DeclaredKindTests.test_change_doc_response_creates_the_doc_with_the_wf_new_envelope` uses `enh` for the core case and adds a `feat` refusal case; `DefaultGrammarTests` adds a frozen `RETIRED_CHANGE_KINDS` assertion (CLI choices stay unchanged).
- [x] Update seeds 001, 110 and 170 under `seed_edit_allowed`; edit both Plan feature prompts directly; update `docs/PLANS.md`, the lifecycle overview, the enterprise delivery model, the spec, `AGENTS.md`, layering-rules and CHANGELOG.
- [x] Tests for AC-1 to AC-6.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| retire-kind | implementer | none | vocabulary_profile, server_impl, lifecycle_id, tests |
| guidance | implementer | retire-kind | seeds, rendered prompts, spec, AGENTS.md, CHANGELOG |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/lifecycle_id.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`
- `.wavefoundry/framework/seeds/110-wave-memory-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `docs/prompts/plan-feature.prompt.md`
- `docs/prompts/agents/plan-feature.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/layering-rules.md`
- `docs/contributing/feature-wave-lifecycle-overview.md`
- `docs/references/enterprise-delivery-model.md`

## Affected Architecture Docs

`docs/architecture/layering-rules.md`: the vocabulary-profile paragraph gains the retired-kind rule and states that `EXTRA_CHANGE_KINDS` cannot re-enable a core kind. No boundary, flow or verification change otherwise.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The refusal is the behaviour this change exists to add. |
| AC-2 | required | Every creation path must refuse, or the retirement leaks. |
| AC-3 | required | Existing `-feat` ids must keep linting in every repository. |
| AC-4 | important | Guidance that still recommends the retired tool misroutes agents. |
| AC-5 | important | Seeds and prompts are how agents learn the rule. |
| AC-6 | important | Keeps one source for the retired set. |
| AC-7 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Operator review: `SkillGuidanceTests` sat after the `unittest.main()` guard, so running the file directly exited before defining it. Moved the guard to the end of the file. | Direct run (`python -B test_retired_change_kinds.py` with the scripts directory on the path) and the runner both report 17 tests OK |
| 2026-10-01 | Reverification follow-up. New `SkillGuidanceTests.test_the_plan_feature_skill_lists_no_retired_scaffold` pins the wf-plan-feature skill's scaffold list (no `feature`, no retired kind); the reviewer's surviving mutation R8 (restore `feature`) now fails it. | `test_retired_change_kinds` OK; R8 killed in a scratch copy |
| 2026-10-01 | Delivery review repair. The shipped wf-plan-feature skill body (`render_agent_surfaces.SKILL_REGISTRY`) no longer lists "feature" among the `wf_new_<kind>` scaffolds; the three rendered skill files are re-rendered. `change_doc_response`'s `invalid_arguments` message now lists `MINTABLE_CHANGE_KINDS` (the kinds that can be created), so it no longer offers `feat`; the lint message keeps listing every declared kind because existing `-feat` ids stay valid. New test `CliRefusalTests.test_the_refusal_comes_before_slug_validation` pins the CLI refusal before `build_id` (the reviewer's surviving mutation R2 now fails it); the uppercase test also pins the message. Spec sentence on the case-sensitive check reworded. | `test_retired_change_kinds`, `test_change_kinds`, `test_render_agent_surfaces`, `test_extension_public_helpers` OK; R2 killed in a scratch copy |
| 2026-10-01 | Implemented. `vocabulary_profile` gains `RETIRED_CHANGE_KINDS = ("feat",)`, derived `MINTABLE_CHANGE_KINDS` and `retired_kind_message` in the fixed section; `_change_create_response` refuses a retired normalized kind before the slug check and before `change_create` (`change_kind_retired`, recovery and `next_tools` `wf_new_enhancement`); `lifecycle_id.main` raises the same message inside its existing try (exit 2), `KIND_CHOICES` unchanged; `wf_help` `plan_feature`, `wf_list_plans` `next_tools` and the `wf_new_feature` / `wf_new_change` docstrings updated, with the two handler digests refreshed. Seeds 001, 110 and 170 (under `seed_edit_allowed`), both Plan feature prompts, `docs/PLANS.md`, the lifecycle overview, the enterprise delivery model, the tool-surface spec, `AGENTS.md` (note placed after the Tool Detail pointer, outside the census-parsed Available tools block), layering-rules and the CHANGELOG updated. Tests: new `test_retired_change_kinds.py` (AC-1, AC-2, AC-4) and `test_change_kinds.py` additions (`ExistingFeatIdsTests` AC-3, `RetiredKindsSingleSourceTests` AC-6 with `RETIRED_CHANGE_KINDS = ("bug",)`, frozen retired assertion, `DeclaredKindTests` core case now `enh` plus a `feat` refusal). Failing first: 14 of 15 new tests and 3 `test_change_kinds` cases failed before implementation. Full suite in a scratch copy 10590 tests OK (34 skipped); `--profile second` 10587 OK (44 skipped); `--profile declared` 10590 OK (34 skipped). Mutations (drop the server check, drop the CLI refusal, hardcode `feat` instead of `RETIRED_CHANGE_KINDS`, revert `wf_list_plans` `next_tools`, revert the `wf_help` chain) each failed named tests. Gapfill: the docs `feat` census used shell grep because the MCP `code_keyword` index does not cover the prose kind-list forms across seeds and `docs/` in one pass. | scratchpad `1zli8-failing-first.txt`, `1zli8-mutations.log`, `1zli8-default.log`, `1zli8-second.log`, `1zli8-declared.log`; `wf_validate_docs` ok |
| 2026-10-01 | Planned. Census of `feat` creation surfaces: `wf_new_feature` (`server_impl`), `_change_create_response`, `change_doc_response`, `lifecycle_id.main` (the `--kind` choices stay unchanged), the `wf_help` `plan_feature` workflow, the `wf_new_change` docstring, seeds 001, 110 and 170, `docs/prompts/plan-feature.prompt.md` and `docs/prompts/agents/plan-feature.prompt.md`, `docs/specs/mcp-tool-surface.md`, `AGENTS.md`, the register-surface handler digests. Non-creation references (`review_policy` trigger token, `mcp_tool_roster` tier, `publication_control` writer, `render_platform_surfaces` rename map) stay because the tool stays registered. | `grep` census of framework scripts, seeds, dashboard and docs outside wave records |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-01 | Retire `feat` for creation only; keep it in the grammar | Existing `-feat` ids in this and every downstream repository, including archives, must keep linting | Remove the kind from the grammar (breaks existing records); lint-warn on new `-feat` docs (no reliable way to tell new from old) |
| 2026-10-01 | Keep `wf_new_feature` registered as a refusing tool | A removed tool gives callers an unknown-tool error with no pointer to the replacement; the refusal names it, and the tool surface stays stable | Remove the tool (breaking change for MCP clients and rendered surfaces); remove it in a later major release once callers have moved |
| 2026-10-01 | Refuse rather than remap `feat` to `enh` | The planner should decide whether the work is one change or several; a silent remap hides that decision | Silently create an `enh` doc |
| 2026-10-01 | One refusal sentence (`retired_kind_message`) on every surface; the CLI keeps `feat` in `--kind` choices and refuses in `main` | Readiness red-team: narrowing argparse choices gives an unexplained invalid-choice error while MCP names the replacement; one helper gives one wording and keeps `parse_args` stable | Narrow `KIND_CHOICES` to the mintable kinds (argparse error with no pointer) |
| 2026-10-01 | `new_change` and `change_create` stay internal and unchanged | They are scaffolding helpers with about 25 test fixtures building existing `-feat` docs; every served creation path goes through `_change_create_response` | Guard `change_create` and migrate the fixtures |
| 2026-10-01 | No re-enable path for distributions | The operator confirmed the downstream distribution has its own feature-level construct; simplest rule | Let `EXTRA_CHANGE_KINDS` list a retired core kind to re-enable minting |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An agent or script that calls `wf_new_feature` now gets an error | The refusal names `wf_new_enhancement` as the recovery tool; seeds and `wf_help` stop recommending the retired tool |
| A downstream repository has planned, unimplemented `-feat` plans | They stay valid; only new creation is refused |
| Platform behaviour | No path or process handling changes; behaviour is identical on Windows, macOS, Linux and WSL2 |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
