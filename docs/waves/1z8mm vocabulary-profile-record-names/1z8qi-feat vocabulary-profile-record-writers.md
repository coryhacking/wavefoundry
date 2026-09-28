# Vocabulary Profile for Record Names: Writers and End-to-End Proof

Change ID: `1z8qi-feat vocabulary-profile-record-writers`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-27
Wave: 1z8mm vocabulary-profile-record-names

## Rationale

Change `1z826` adds `vocabulary_profile.py` and routes every reader of record vocabulary. The writers still emit the default names, so a fork running a second profile gets records that its own readers cannot find. The writers are:

- the wave scaffold, a code string in `server_impl.create_wave`;
- the change block in `_insert_change_block_into_changes_section`;
- the summary rewrite in `_replace_wave_summary_section`;
- the close-time `Completed At:` insertion in `wf_close_wave_response`;
- the back-reference rewrite in `wf_add_change_response`;
- `new_change`;
- `install/plan-template.md`;
- the rendered Claude Stop hook: `render_platform_surfaces.claude_stop_source` hard-codes `"wave.md"` and `wave-id:` in the hook body it emits, although that body already imports `record_paths` at runtime.

This change routes them and proves a second profile end to end.

## Requirements

1. **Writers use the profile.** Every production site that creates or renders a vocabulary token (per the in/out table in `1z826`) writes the profile's value:
   - the wave scaffold, including title, id key, member-list heading and summary heading;
   - the change block;
   - the summary rewrite and its `Completed At:` anchor;
   - the back-reference rewrite;
   - `new_change`.
2. **Template.** `install/plan-template.md` keeps its default labels, and `vocabulary_profile.localize_template` rewrites them to the profile's labels wherever the shipped template is rendered (the scaffold baseline and `new_change`): the line-leading member id, status and back-reference labels in one pass, and the record filename in the template's example path. The rendered `docs/plans/plan-template.md` stays byte-identical under the default profile, because it is the review-policy scaffold baseline (`review_policy.SCAFFOLD_DOC_NAMES`).
3. **Stop hook reads the profile at runtime.** The emitted Stop-hook body imports `vocabulary_profile` at runtime beside its existing `record_paths` import, with the same guard. It uses the profile for the record filename and the id key, including the `_ac_progress` skip of the record file.
4. **The census class closes.** The "pending 1z8qi" allow-list class from `1z826` is removed, so any unrouted writer fails the census.

## Scope

**Problem statement:** with a second profile, Wavefoundry would still write records under the default names.

**In scope:**

- the writers, the template localization and the Stop-hook body;
- closing the census class;
- the end-to-end test.

**Out of scope:**

- readers (`1z826`);
- the events-path leak (`1z8qj`);
- tool aliases and the parent tier.

## Acceptance Criteria

- [x] AC-1: under the default profile, the wave scaffold, change block, summary rewrite, the rendered `docs/plans/plan-template.md` and every rendered surface except the Stop-hook body are byte-identical to the pre-change output. The Stop-hook body differs only by the added profile import and the routed name references, and a golden pins that diff.
- [x] AC-2: in a fresh interpreter over a copied scripts tree with a second profile, a scratch repository runs create wave, admit change, prepare, record review evidence, advance a status after an approval, and close. Discovery, parsing and docs-lint find the records with non-zero counts. No default vocabulary marker appears anywhere in the written tree, checked with the same case-sensitive marker matcher as the census (so the fixed `<!-- wave:* -->` fences and `wave-council-*` lane names are not markers), which requires routing the scaffold prose that names the member-list heading. The approval survives the status advance.
- [x] AC-3: the census has no pending-writer class and passes on the tree.
- [x] AC-4: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Route the `server_impl` writers.
- [x] Localize the shipped template's labels at render; pin the default render.
- [x] Stop-hook runtime profile import and routed references; re-render this repository's hooks.
- [x] Remove the census pending class.
- [x] End-to-end second-profile test (subprocess, copied scripts tree; framework-test receipt stubbed or the no-runner path).
- [x] Docs and CHANGELOG `[Unreleased]`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Writers | implementer | `1z826` implemented | |
| Review | combined reviewer | Writers | Code, QA, architecture, docs-contract |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/vocabulary_profile.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/`, `.claude/hooks/`
- `CHANGELOG.md` (shared by the changes in this wave)

## Affected Architecture Docs

`docs/architecture/current-state.md`: record writers follow the vocabulary profile.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Existing users must see no change |
| AC-2 | required | The feature's purpose, proven end to end |
| AC-3 | required | No unrouted writer remains |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Implemented. Writers routed in `server_impl` (scaffold title, id line, member heading, summary heading and the scaffold's Dependencies prose; the change block and its missing-section path; the back-reference rewrite; `new_change`; the summary rewrite and the close-time `Completed At:` anchor). The legacy back-reference placeholders stay fixed text as `_LEGACY_BACKREF_PLACEHOLDERS` (census `retired_name`). The shipped template is localized at render (see Decision Log). The Stop hook imports the profile at runtime; this repository's hooks were re-rendered and only `.claude/hooks/session-capture.py` changed. The census pending-writer class is removed | Before and after capture of the scaffold, change block (both paths), summary rewrite, `new_change`, rendered template and every platform's rendered surfaces: byte-identical except the Stop-hook body, whose delta is pinned by `test_vocabulary_writers.DefaultProfileWriterTests.test_stop_hook_reads_the_profile_at_runtime`. The rendered hook run against this repository reports the active wave. `test_vocabulary_writers`: a second profile runs create, admit, prepare, readiness and delivery evidence, a member-status advance after the approvals, and close; lint clean, no default marker under the waves or plans root; the default-tree control closes and its markers are found. Mutation: reverting the digest's status-line exclusion to the literal label in the copied second-profile tree makes close fail with `review_policy_receipt_stale` |
| 2026-09-27 | Split from `1z826` per the readiness review (N7); carries B3 (the Stop hook imports the profile at runtime, so AC-1 names the expected hook-body diff) | readiness review |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Localize the shipped template's labels at render instead of adding placeholders to it (Requirement 2 revised during implementation) | Seed 040's no-MCP fallback copies the shipped template verbatim and substitutes only `{{generated_at}}`, so new placeholders would reach those copies unfilled. The template body also names the record filename in an example path, which placeholders for the labels would not have covered. Known limit: under a second profile, that no-MCP fallback still produces a template with the default labels, which a fork corrects in its template copy or seed | Placeholders plus a seed 040 edit |
| 2026-09-27 | The generated close summary prose ("Wave ... delivered one change") stays as written | It uses the bare tier names in prose, which the vocabulary rule and the census do not treat as markers; routing prose through `CONTAINER_NAME` is a separate decision | Route summary prose through the tier names now |
| 2026-09-27 | Stop hook imports the profile at runtime | The hook already imports `record_paths` at runtime; baking names at render time would leave the active-wave read on a stale name after a fork edit | Bake names at render time |

## Risks

| Risk | Mitigation |
| --- | --- |
| The scaffold baseline drifts and lapses approvals | Default render pinned byte-identical |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
