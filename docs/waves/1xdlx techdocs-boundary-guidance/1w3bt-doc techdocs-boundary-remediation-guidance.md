# Clarify TechDocs Publication-Boundary Repairs and Upgrade Propagation

Change ID: `1w3bt-doc techdocs-boundary-remediation-guidance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-22
Wave: `1xdlx techdocs-boundary-guidance`

## Rationale

Field use of **Refresh TechDocs** correctly preserved useful repository links and reported 48 `techdocs_link_outside_boundary` findings, but then proposed two ineffective repairs: adding `repo_url` without rewriting the relative links, and removing a page from `nav` even though every page surviving `exclude_docs` remains published. The audit is correct; the authoring guidance needs to state its remediation semantics plainly enough that an agent cannot confuse navigation with publication or repository metadata with link rewriting. The same correction must reach existing installations: packages replace seed 178, but upgrades preserve the project-owned Refresh TechDocs prompt unless the upgrade workflow explicitly reconciles it.

## Requirements

1. State that `repo_url` does not rewrite Markdown links. A published page may keep a cross-boundary reference only by replacing its relative link with an explicit repository URL derived from an operator-configured remote/branch, or by naming the repository path in prose.
2. State that removing a page from `nav` changes discoverability only; it remains published and audited while it survives `exclude_docs`.
3. Describe the net ordered `exclude_docs` result precisely: direct-file matches take precedence over ancestor-directory matches, and the last matching rule wins within each tier. A non-negated exclusion can reduce the publication set; a later matching `!` rule in the same tier can expand it. A directory negation does not necessarily override a direct-file exclusion.
4. Preserve the current audit algorithm, finding schema, publication boundary, and operator ownership of the boundary.
5. Correct the internal `techdocs_audit_lib.py` module overview so it describes the survivor set as the publication boundary and does not imply that `nav` adds pages to that set.
6. Require the read-only pre-apply seed-diff preview to retain whether `178-refresh-techdocs.prompt.md` changed. When it did, the same upgrade pass must merge the changed canonical clauses into the existing `docs/prompts/refresh-techdocs.prompt.md`, preserve project-only additions and metadata, never replace the whole project-owned prompt, and run `wf render-surfaces` again afterward. If the prior canonical clause cannot be identified uniquely or local wording conflicts with the new invariant, stop and present the conflict to the operator instead of guessing. The already-required post-extraction drift pass supplies the installing-run bridge by reconciling against the freshly extracted canonical seed.
7. Evaluate the finite set of 14 completed waves after the last shipped upgrade: annotated tag `v1.21.0` (commit `ca5e6a5f`) exclusive through pre-wave `HEAD` `ef100849`, using first-parent history and the closed-wave records rather than commit subjects alone. Record one row per wave with its closure commit, downstream target class, convergence class, exact mechanism, proof, and gap disposition. Allowed convergence classes are packaged replacement, version-triggered rebuild, safe state evolution, generated-surface refresh, explicit project-surface reconciliation, and justified not-applicable; a mixed wave may require several mechanisms. Exclude editorial-only commit `4ae3b383` explicitly. Repair every uncovered behavior-bearing gap in this wave.
8. Add two explicit source-to-destination reconciliation mappings. When seed 170 or the freshly extracted `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md` changes the Serialization Points grammar, merge only that project-authored prose into an existing `docs/prompts/prepare-wave.prompt.md`; preserve its metadata, project prose, and renderer-owned marker regions, which remain the final render's responsibility. When seeds 170 or 190 change the AC-locality or advisory-sensor contract, merge those clauses into `docs/contributing/change-workflow.md`. Preserve the existing no-whole-file-replacement and conflict-stop rules for both mappings. These carriers survive package extraction, so upgrade must not rely only on a final drift check.

## Scope

**Problem statement:** Ambiguous remediation prose led a downstream authoring agent to recommend changes that would not clear the findings it had just reported.

**In scope:**

- Canonical seed 178 wording and its self-hosted authored twin.
- Canonical seed 160 upgrade guidance and its self-hosted authored twin.
- The internal TechDocs audit module overview.
- Upgrade-convergence review of completed waves after `v1.21.0`.
- Focused carrier assertions and audit regressions pinning nav/repository-URL polarity.
- The current Unreleased changelog entry.

**Out of scope:**

- Changing the audit result schema or severity.
- Automatically rewriting links or guessing repository remotes/branches.
- Requiring nav coverage for every published page.
- Changing baseline generation, site rendering, or external dependencies.
- Adding migrations where packaged replacement or existing version gates already converge the target safely.

## Acceptance Criteria

- [x] AC-1: Seed 178 and `docs/prompts/refresh-techdocs.prompt.md` explicitly distinguish nav membership from publication and `repo_url` configuration from an explicit repository URL in page content.
- [x] AC-2: A public audit fixture proves that a page omitted from `nav` remains a survivor and its outside-boundary relative link remains a finding.
- [x] AC-3: The same fixture proves adding `repo_url` alone leaves the survivor set and outside-boundary finding unchanged, an exact source-page exclusion removes it from the publication set, and a later exact `!source-page.md` rule re-includes it under same-tier last-match semantics; the carrier guidance also states that direct-file matches take precedence over ancestor-directory matches.
- [x] AC-4: Existing TechDocs audit/carrier tests, docs validation, and diff check pass with no external renderer dependency.
- [x] AC-5: `techdocs_audit_lib.py` describes publication as the pages that survive `exclude_docs`, with `nav` treated only as discoverability metadata; a focused module-doc contract rejects the stale nav-plus-survivors model.
- [x] AC-6: Seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md` use the pre-apply seed diff to trigger a merge-safe Refresh TechDocs prompt reconciliation whenever seed 178 changes, preserve project additions and metadata, refuse non-unique or conflicting replacement, require reconciliation during the same installing run, and require the post-merge agent-surface render. A two-carrier mutation matrix kills omission or reversal of each rule, including loss of the retained pre-apply result and wholesale replacement of the project prompt.
- [x] AC-7: A 14-row audit of every completed wave after `v1.21.0` identifies closure commit, downstream target, convergence class, mechanism, proof, and gap disposition, and leaves no known project-owned carrier or persisted-state gap unaddressed.
- [x] AC-8: Seed 160 and the self-hosted upgrade prompt bind the changed seed/lifecycle-template source to each destination and clause family: Serialization Points grammar to the project-authored region of `docs/prompts/prepare-wave.prompt.md`, and AC-locality/advisory-sensor guidance to `docs/contributing/change-workflow.md`. The instructions preserve metadata, project prose, and renderer-owned markers, retain the conflict stop and no-whole-file replacement rules, and focused carrier tests independently fail when a source trigger, destination, clause family, ownership boundary, or preservation rule is removed or reversed.

## Tasks

- [x] Amend seed 178 first, then manually synchronize its self-hosted authored twin.
- [x] Add focused literal/semantic carrier assertions for nav, `repo_url`, and ordered exclude/re-include semantics.
- [x] Add one audit polarity test covering nav omission, `repo_url`, source-page exclusion, and a later matching `!` re-inclusion.
- [x] Update the Unreleased changelog and run focused/full verification.
- [x] Correct the stale internal audit-module overview without changing runtime behavior, and add a focused `techdocs_audit_lib.__doc__` assertion that rejects the old nav-plus-survivors wording.
- [x] Add the seed-178 upgrade reconciliation instruction in both upgrade carriers, then add a two-carrier mutation matrix for the change trigger, retained pre-apply result, same-run bridge, project-content and metadata preservation, no whole-file replacement, non-unique/conflicting-clause refusal, and final `wf render-surfaces` pass.
- [x] Audit post-`v1.21.0` completed waves for upgrade convergence and record the disposition in this change document.
- [x] Re-run focused tests, docs validation, diff check, and the full framework suite after the expanded implementation.
- [x] Add the two omitted carrier mappings to both upgrade instructions, pin their source triggers, destinations, clause families, and ownership boundaries in the carrier test, explicitly disposition source-only carrier deltas in the audit, and rerun verification.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guidance correction | technical-writer | — | Seed-first, then authored-twin parity |
| Boundary regression | qa-reviewer | Guidance correction | Exercise the public audit without changing its schema |
| Upgrade convergence | technical-writer, coordinator | Guidance correction | Reconcile project-owned prompt guidance and audit post-1.21.0 delivery paths; request an independent release review after implementation |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `docs/prompts/refresh-techdocs.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `CHANGELOG.md`

## Affected Architecture Docs

Reviewed against `docs/architecture/cross-cutting-concerns.md`. No architecture edit is required: this wave uses the existing instruction-class installing-run path (the old prompt's post-extraction drift pass reads the freshly extracted canonical seed) and does not add a behavior-class migration or change ownership of project-authored prompt text.

## Post-v1.21.0 Upgrade Convergence Audit

Boundary: annotated tag `v1.21.0` (`ca5e6a5f`) exclusive through pre-wave `HEAD` `ef100849` inclusive. `git log --first-parent` yields 12 commits; editorial-only `4ae3b383` is excluded, leaving 11 closure commits whose closed-wave records account for exactly 14 waves.

| Wave | Closure commit | Downstream target class | Convergence class | Exact mechanism and proof | Gap disposition |
| --- | --- | --- | --- | --- | --- |
| `1seaw` | `27ec5fe6` | Retrieval runtime, seed 211, Guru role doc | packaged replacement; explicit project-surface reconciliation | `build_pack.collect_files` plus upgrade extraction replace shipped scripts and seed 211; seed 160 already requires `docs/agents/guru.md` regeneration whenever seed 211 changes. | Covered. |
| `1wur7` | `17d6a166` | Evaluator/lint runtime, review seeds, project reviewer docs, source-repository verification docs | packaged replacement; explicit project-surface reconciliation; justified not-applicable | Shipped code and seeds are replaced from the pack; this wave's changed-project-owned-review-carriers rule merges relevant seed 209/214/221/239 clauses into reviewer and review-contract docs. Its `docs/contributing/build-and-verification.md` framework-test-receipt addition is source-repository-only: destination packs exclude `run_tests.py`, and their close receipt check is intentionally a no-op. | Gap repaired in this wave; source-only carrier is not applicable to destination upgrades. |
| `1wuju` | `17d6a166` | Review lifecycle runtime, seeds 170/180/190/209, project workflow docs, source-repository release prompt | packaged replacement; explicit project-surface reconciliation; justified not-applicable | Shipped code and seeds are replaced; this wave's review-carrier rule merges the AC-locality advisory, landing rule, external-blocker rule, frozen-tree briefing, and mutation-table contract into named project carriers, including `docs/contributing/change-workflow.md`. Its `docs/prompts/package-wavefoundry.prompt.md` advisory-sensor release checklist is for framework-source package operators and is not a destination lifecycle surface. | Gap repaired in this wave; source-only release carrier is not applicable to destination upgrades. |
| `1wybs` | `17d6a166` | Shipped plan and Prepare templates, lifecycle seeds, existing project plan and mixed-ownership Prepare carriers | packaged replacement; explicit project-surface reconciliation | Pack extraction replaces the shipped templates and seeds; seed 160 carries merge-safe `Serialization Points` repairs for the existing `docs/plans/plan-template.md` and maps changed seed-170/lifecycle-baseline grammar to the project-authored prose in the missing-only renderer's preserved `docs/prompts/prepare-wave.prompt.md`, while preserving renderer-owned markers for the final render. | Gap repaired in this wave. |
| `1wpif` | `f6790333` | Chunking/retrieval runtime and semantic index state | packaged replacement; version-triggered rebuild; safe state evolution | Shipped runtime is replaced; `CHUNKER_VERSION` mismatch routes `indexer.build_index` through re-chunking with vector reuse, while existing state-store reconciliation accepts and normalizes prior state. | Covered. |
| `1wpig` | `bcf7d121` | Graph extraction/query runtime and graph artifact | packaged replacement; version-triggered rebuild | Pack extraction replaces graph code; the graph builder-version change is detected by the upgrade graph phase and forces full re-extraction before serving the new edge contract. | Covered. |
| `1wpih` | `bcf7d121` | Retrieval/graph evaluators, seed 211, Guru role doc | packaged replacement; explicit project-surface reconciliation | Evaluators and seed 211 are shipped framework files; seed 160's existing seed-211 rule regenerates the project Guru role doc after a changed seed. | Covered. |
| `1x4ol` | `8a9fa245` | Scanner rules and scan/index runtime | packaged replacement; version-triggered rebuild | Pack extraction replaces `scan-rules.toml` and scanner code; scanner-version/rules-fingerprint mismatch invalidates cached rule assumptions and the normal upgrade/index path rebuilds derived coverage. | Covered. |
| `1x54z` | `83efb3d9` | Semantic/graph index runtime and eligibility-reap state | packaged replacement; safe state evolution | Shipped readers are replaced; absent new reap fields retain the old no-report meaning, and the next ordinary build writes current deferral/preservation state without rewriting authoritative rows during upgrade. | Covered. |
| `1x6ti` | `a317bdf6` | Graph/index runtime, public health response, persisted reap visibility | packaged replacement; version-triggered rebuild; safe state evolution | Shipped tools are replaced; graph builder identity forces re-extraction for the dangling-edge filter, while optional reap-state fields default safely and are populated by subsequent builds. | Covered. |
| `1x5tq` | `ed564b03` | Incremental graph fragments and deferred-link recovery state | packaged replacement; version-triggered rebuild; safe state evolution | Shipped graph/index code is replaced; graph builder staleness triggers re-extraction, and missing deferred-recovery state is accepted as empty until the next real build records work. | Covered. |
| `1x5tr` | `37311f29` | Scanner skip ledger, close response, coordinator/review contract | packaged replacement; safe state evolution; explicit project-surface reconciliation | Shipped scanner/close code and seed 209 are replaced; a missing guard-skip ledger is the supported empty prior state and later scans populate it; this wave's review-carrier rule merges Review Artifact Discipline into project coordinator/review docs. | Gap repaired in this wave. |
| `1xa00` | `1d9f7418` | Markdown table chunking and semantic index chunks | packaged replacement; version-triggered rebuild | Pack extraction replaces `chunker.py`; its compatibility-version bump is detected by `indexer.build_index`, which re-chunks affected layers with vector reuse so header-plus-row chunks replace stale header-only windows. | Covered. |
| `1vt2t` | `ef100849` | Codebase-map generator, map seeds, generated map | packaged replacement; generated-surface refresh | Pack extraction replaces the generator and seeds; `_regenerate_codebase_map_on_upgrade` rewrites `docs/references/codebase-map.md` through the current generator during upgrade. | Covered. |

Shared proof: `build_pack.collect_files` includes shipped framework source while upgrade extraction replaces allowlisted `.wavefoundry/` members; the upgrade index phase always runs after extraction; `indexer.build_index` escalates walker mismatches to rebuilds and chunker mismatches to re-chunking with embedding reuse; the graph-only upgrade phase applies graph builder-version invalidation; project-owned docs are preserved and therefore use the explicit reconciliation rules above. No entire wave is justified not-applicable because every one changed a shipped runtime, seed/template, derived-state contract, generated surface, or project-owned carrier; the source-repository-only subcarriers identified in `1wur7` and `1wuju` are individually not applicable to destination upgrades.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Prevents the observed incorrect `repo_url` and nav advice. |
| AC-2 | required | Pins the actual publication-set definition. |
| AC-3 | required | Proves all three remediation polarities without changing the audit. |
| AC-4 | required | Keeps the documented Python-only verification boundary intact. |
| AC-5 | required | Removes an internal description that contradicts the public and implemented publication boundary. |
| AC-6 | required | Makes the correction reach existing installations instead of only new installs and the self-hosted repository. |
| AC-7 | required | Prevents adjacent post-release changes from shipping without a valid upgrade convergence path. |
| AC-8 | required | Ensures existing destination workflow carriers receive the post-release behavior their freshly installed framework runtime expects. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-22 | Planned from two downstream Refresh TechDocs reports. | Direct public audit probe: nav contained only `index.md`, yet `prompts/index.md` remained a survivor; adding `repo_url` left its outside-boundary finding unchanged. |
| 2026-09-07 | Readiness red-team narrowed the ordered-rule claim to the audit's two-tier precedence semantics. | `techdocs_audit_lib.excluded`; existing direct-file versus ancestor-directory polarity tests; the new fixture will use exact-file rules in one tier. |
| 2026-09-07 | Thought: correct the canonical seed contract first, then synchronize its self-hosted authored twin before adding tests. | The stage gate is open; readiness approvals are current; seed-first order preserves the framework source-of-truth boundary. |
| 2026-09-07 | Observe: seed 178 now distinguishes the survivor set from nav, content links from `repo_url`, and the two `exclude_docs` precedence tiers. | Canonical seed edit completed under the seed gate; audit behavior and schema were untouched. |
| 2026-09-07 | Thought: synchronize the self-hosted authored prompt byte-for-byte for the amended clauses. | Self-hosting requires the project-local carrier to match the corrected canonical behavior without treating it as generated output. |
| 2026-09-07 | Observe: the seed and self-hosted prompt now carry identical remediation clauses. | Carrier task marked complete; both stale formulations were removed from the live surfaces. |
| 2026-09-07 | Thought: add non-vacuous carrier assertions before the public audit fixture. | Literal pins establish both-surface parity, while independent clause mutants prove each semantic distinction is load-bearing. |
| 2026-09-07 | Observe: the carrier contract test passes and kills five misleading-clause mutants on each surface. | `TechdocsCarrierLiteralPinTests.test_techdocs_carriers_pin_boundary_remediation_semantics`; deleting or reversing any nav, `repo_url`, or precedence clause fails the predicate. |
| 2026-09-07 | Thought: add one public audit fixture that exercises all four remediation states on the same source page. | Keeping one realistic page and exact finding identity across mutations proves the state transitions without changing production code. |
| 2026-09-07 | Observe: the four-state public audit regression passes. | `TechdocsAuditFindingMatrixTests.test_boundary_repairs_change_only_the_inputs_that_define_publication`; the assertions fail if survivors are intersected with nav, `repo_url` suppresses the finding, exact exclusion is ignored, or same-tier last-match order is reversed. |
| 2026-09-07 | Thought: add a concise Unreleased changelog note, then run focused and full verification. | The external benefit is accurate repair guidance; implementation details belong in the change record and tests rather than the changelog. |
| 2026-09-07 | Observe: the changelog is updated and both focused suites pass. | 85 TechDocs audit tests and 116 agent-surface tests passed; the framework and seed gates are closed. |
| 2026-09-07 | Thought: validate the complete docs surface, inspect the scoped diff, and run the full framework suite last. | These checks establish AC-4 and produce the current framework test receipt without an external renderer dependency. |
| 2026-09-07 | Observe: implementation verification is complete. | Full docs validation and `git diff --check` passed; the final framework run passed 8,526 tests across 75 files with three expected skips and wrote a current green receipt. |
| 2026-09-07 | Reflect: operator review exposed an upgrade propagation gap and brought the adjacent internal wording inconsistency into scope. | Package collection and extraction replace framework seed 178, while the project-owned Refresh TechDocs prompt survives; seed 160 only named the first-install backfill and did not explicitly cover later seed-178 changes. |
| 2026-09-07 | Thought: audit every completed wave after the `v1.21.0` release boundary before editing upgrade carriers. | Classify each change by packaged replacement, version-triggered rebuild, safe optional state, generated-surface refresh, or explicit merge-safe reconciliation; add instructions only for uncovered project-owned surfaces. |
| 2026-09-07 | Reflect: expanded-scope readiness review rejected an underspecified merge and an open-ended wave census. | The revised requirements bind the trigger to the pre-apply seed diff, preserve the whole-file ownership boundary, fail safe on ambiguity, and define the exact 14-wave evidence table from `v1.21.0` through `ef100849`; editorial commit `4ae3b383` is explicitly excluded. |
| 2026-09-07 | Reflect: QA readiness rejected generic test language for AC-5 and AC-6. | `QA-RDY-1` requires a module-doc negative control and an explicit two-carrier mutation matrix for all eight upgrade-reconciliation failure modes; the ACs and tasks now name those controls before implementation. |
| 2026-09-07 | Observe: the expanded implementation corrects the internal overview, teaches merge-safe seed-178 reconciliation, and records upgrade convergence for every post-`v1.21.0` wave. | The module-doc assertion and two-carrier mutation matrix pass; a mechanical audit verifies 14 wave rows against 12 first-parent commits, including the explicit editorial exclusion. |
| 2026-09-07 | Observe: expanded-scope validation is green. | Docs lint and `git diff --check` pass; the final framework run passed 8,528 tests across 75 files with three expected skips and wrote a current green receipt. |
| 2026-09-07 | Reflect: the AC-8 readiness council rejected a filename-only reconciliation rule because the Prepare carrier mixes project-authored prose with renderer-owned marker regions. | RED-RDY-AC8-1 through RED-RDY-AC8-4 and DOC-RDY-AC8-1 were repaired before implementation; receipt `review-policy-da40de9e6a7a16e53202` records the current approvals. |
| 2026-09-07 | Observe: destination upgrade guidance now maps each changed canonical source to its preserved carrier and clause family without changing ownership. | Seed 160 and the self-hosted upgrade prompt map seed 170/the extracted Prepare baseline to project-authored Serialization Points prose, and seeds 170/190 to the contribution workflow; conflict, metadata, project prose, whole-file, and renderer-marker rules are explicit. |
| 2026-09-07 | Observe: AC-8 verification is green. | The focused mutation test, all 117 agent-surface tests, all 483 upgrade tests, surface rendering, full docs validation, and `git diff --check` pass; the final framework run passed 8,528 tests across 75 files with three expected skips and wrote a current green receipt. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-22 | Correct guidance and add one polarity regression; do not alter the audit. | The implementation already matches MkDocs publication semantics and all 84 focused audit tests pass. | Teach the audit to interpret `repo_url` (wrong layer); add an autofix/suggestion schema (broader contract); require every survivor in nav (rejects legitimate link-only pages). |
| 2026-09-07 | Record the change under Unreleased rather than the stale `1.19.0` section named during planning. | The changelog now uses an Unreleased section for pending user-facing changes. | Rewrite a historical release entry, which would misstate when the change shipped. |
| 2026-09-07 | State direct-file precedence over ancestor-directory matches and test last-match behavior with exact-file rules. | The audit applies last-match semantics within two match tiers; a later directory negation cannot always rescue a direct-file exclusion. | Preserve the broader claim, which would teach another ineffective repair. |
| 2026-09-07 | Treat `v1.21.0` as the completed-wave upgrade audit boundary. | It is the latest shipped release tag; all later committed waves are pending the next packaged upgrade. | Use the most recent local commit, which is not a shipped consumer boundary. |
| 2026-09-07 | Keep seed-178 propagation instruction-driven and fail safe. | The existing upgrade prompt already requires a post-extraction canonical drift pass; retaining the pre-apply seed diff makes the changed seed observable during that installing run without changing prompt ownership. | Add a renderer-owned marker or versioned migration, which would change ownership and runtime behavior beyond the operator-requested upgrade instructions. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Wording could still imply that `repo_url` alone repairs links. | Require the literal distinction between configured metadata and an explicit absolute repository URL in page content. |
| A test could check only nav output and miss survivor behavior. | Assert survivor membership and exact finding polarity before/after `repo_url` and `exclude_docs` changes. |
| Generic upgrade wording could leave an existing project-owned TechDocs prompt stale. | Name seed 178 and its destination explicitly, require merge-safe reconciliation on every seed change, and pin both upgrade carriers. |
| A destination upgrade could overwrite renderer-owned Prepare content or leave project workflow guidance stale. | Map each source and clause family explicitly, limit the Prepare merge to project-authored prose, preserve marker regions for the final render, and mutation-test both mappings independently. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
