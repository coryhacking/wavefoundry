# TechDocs Validation Must Stay Python-Only and Accept Spaced Nav Paths

Change ID: `1vrzu-bug techdocs-python-only-validation-and-spaced-nav`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-21
Wave: 1vvei techdocs-python-only-validation

## Rationale

Downstream dogfood exposed two defects in the same **Refresh TechDocs** validation boundary.

First, the canonical workflow conditionally asks agents to run `npx @techdocs/cli` and `techdocs-cli generate --no-docker`. The condition checks only whether the Node CLI is available, but `--no-docker` delegates to a separately installed `mkdocs` executable and `mkdocs-techdocs-core` plugin. A downstream project therefore reached an external build step that could not run even though the Wavefoundry publication audit was clean. Wavefoundry does not require Docker, Node, or an undeclared documentation renderer in target repositories; its required validation must remain within the framework's declared Python tool environment.

Second, `techdocs_audit_lib.parse_mkdocs` recognizes a nav target only when its path is a single non-whitespace token. Valid YAML nav paths containing spaces—including Wavefoundry's own `<lifecycle-id>-adr <slug>.md` convention—set `shape_ok=false`, erase the entire parsed nav, and degrade the audit. The downstream project had to omit direct ADR nav entries and route readers through `decisions/README.md` instead.

The change removes external rendering from the Wavefoundry workflow and repairs the Python audit so valid spaced nav paths participate in the same publication, existence, link, and containment checks as other targets.

## Requirements

1. **Python-only required validation.** **Refresh TechDocs** must require only Wavefoundry's declared validation paths: full docs validation, explicit nav-target existence, `wf_techdocs_audit` / `wf techdocs-audit`, citation re-resolution, and supplier reporting. It must not invoke, probe for, install, recommend as a workflow step, or condition success on Docker, Node/`npx`, `@techdocs/cli`, `mkdocs`, or `mkdocs-techdocs-core`.
2. **Rendering remains outside Wavefoundry.** The canonical operator checklist may state that rendering and publication are owned by the operator's Backstage/CI environment, but it must not prescribe a local preview/build command. An unavailable external renderer is neither a finding nor a degraded lane and must not appear in the workflow report.
3. **Spaced-nav fidelity.** `parse_mkdocs` must recognize valid root leaves and leaves beneath exactly one section header when their docs-relative paths contain spaces in plain, single-quoted, or double-quoted YAML scalar form. After structural indentation and mapping whitespace are removed, the admitted scalar subset is closed: (a) a nonempty plain tail with internal spaces allowed and no separation-whitespace `#` comment suffix, or (b) a nonempty payload enclosed by exactly one matching `'` or `"` wrapper with only whitespace after the closing quote. Doubled single quotes and every double-quoted backslash escape are explicitly unsupported. The parser must preserve the logical path without surrounding quotes and must not clear sibling nav entries.
4. **Parser honesty and containment.** Current code incorrectly flattens at least one two-section-deep leaf while claiming `shape_ok=true`; the repair must close that adjacent honesty gap rather than describe it as already preserved. A root leaf and a leaf beneath exactly one section header are supported; a second nested section, unmatched or mixed quote wrappers, any non-whitespace token after a quoted closer, separation-whitespace inline comments, doubled single quotes, and double-quoted backslash escapes must degrade the whole modeled nav boundary. Existing lexical and realpath containment must still run before `is_file`, open, or content access for every newly accepted target; absolute paths and root escapes remain refused/degraded with logical-only reporting.
5. **Public-path behavior.** Through both the raw audit and `run_techdocs_audit`, an existing spaced nav target must remain in `publication.nav` without `mkdocs_shape`; a missing spaced target must produce the normal missing-nav-target finding rather than erase the nav; quoted and unquoted spellings must converge on the same logical path.
6. **Canonical carrier ownership.** Edit seed sources first, then manually synchronize the corresponding self-hosted authored prompt twins; the current renderer does not own or overwrite these lifecycle prompts. Do not treat the local twin as the source of truth. Install/upgrade pointers, seed/twin parity tests, and package checks must agree that Wavefoundry does not render downstream sites.
7. **No dependency expansion.** No runtime, setup, package, lock, or dependency manifest may add Docker, Node, MkDocs, TechDocs CLI, or `mkdocs-techdocs-core` for this change. The parser repair uses the existing Python implementation and dependency boundary.

## Scope

**Problem statement:** The TechDocs workflow leaks an optional Backstage renderer into downstream validation, while the internal audit rejects valid nav paths containing spaces.

**In scope:**

- Remove the external build-smoke and local-preview instructions from canonical Refresh TechDocs and install-summary carriers.
- Replace them with an explicit operator-owned rendering/publication boundary and a statement that Wavefoundry performs no downstream render.
- Repair `parse_mkdocs` nav leaf parsing for the closed plain/matched-quote scalar subset and track indentation deeply enough to distinguish root leaves, one-section leaves, and unsupported deeper sections.
- Close the current false-computed deeper-section case while preserving path containment, read-only audit behavior, and existing state/report schemas.
- Add focused parser, raw-audit, isolated-worker, carrier-parity, and known-bad regression coverage.
- Synchronize the self-hosted authored prompt twins from the canonical seed changes and update the unreleased changelog entry.

**Out of scope:**

- Adding Docker, Node, `@techdocs/cli`, MkDocs, or `mkdocs-techdocs-core` to Wavefoundry dependencies.
- Building, serving, publishing, or visually comparing a TechDocs site in Wavefoundry or a downstream repository.
- Generating CI YAML, Backstage `app-config.yaml`, storage configuration, or credentials.
- Replacing the bounded recognized-shape parser with a general YAML implementation.
- Supporting nav nesting beyond the explicitly modeled root/one-section structure, YAML anchors/tags, block/folded scalars, inline flow collections, comment-bearing path scalars, doubled single quotes, or double-quoted backslash escapes.
- Changing `exclude_docs`, link-scoring, survivor enumeration, MCP response caps, or the ten-second worker deadline except where a regression test proves preservation.

## Acceptance Criteria

- [x] AC-1: An exhaustive live-carrier census finds no workflow instruction to run or probe `npx @techdocs/cli`, `techdocs-cli`, Docker, `mkdocs`, or `mkdocs-techdocs-core`; the canonical checklist states that rendering is not performed by Wavefoundry and belongs to the operator's chosen Backstage/CI environment.
- [x] AC-2: The required Step 3 contract remains explicit and complete—docs validation, nav existence, publication audit, citation re-resolution, and supplier/report reconciliation—and a semantic mutant that reintroduces external rendering or makes its absence a degradation is rejected.
- [x] AC-3: `parse_mkdocs` returns `shape_ok=true` and the identical logical nav target `decisions/1abc-adr architecture choice.md` for plain, single-quoted, and double-quoted root/one-section leaf scalars, while preserving ordinary no-space entries and sibling order; a table-driven scalar grammar pins matching wrappers and whitespace-only after a closer, and rejects separation-whitespace comments, non-whitespace trailing tokens, doubled single quotes, and double-quoted backslash escapes.
- [x] AC-4: End-to-end raw and isolated-worker audits retain an existing spaced target in `publication.nav` with no `mkdocs_shape`; when the file is absent, the audit emits the ordinary missing-target finding and does not return an empty nav.
- [x] AC-5: An exact depth matrix proves root leaf accepted, one-section leaf accepted, and a two-section leaf degraded with `mkdocs_shape`; unmatched/mixed wrappers, non-whitespace trailing tokens, separation-whitespace comment suffixes, doubled single quotes, and double-quoted backslash escapes also degrade. Exact containment probes prove that newly accepted absolute or escaping spaced targets trigger the existing refusal before any external `is_file`, open, or content read; in-root spaced targets remain readable.
- [x] AC-6: Canonical seed 178, the seed-012 install Phase-2 carrier, their self-hosted authored prompt twins, prompt-surface tests, and `CHANGELOG.md` agree on the no-render boundary; exact seed/twin and package parity checks pass without claiming renderer ownership.
- [x] AC-7: No Wavefoundry dependency or package surface gains Docker, Node, TechDocs CLI, MkDocs, or `mkdocs-techdocs-core`; warning-strict focused TechDocs audit/CLI/MCP and carrier tests pass, followed by the full framework suite and full docs validation.

## Tasks

- [x] Open only the required `seed_edit_allowed` and `framework_edit_allowed` gates after the wave is ready; record gate scope before mutation.
- [x] Update canonical seed 178 and the Phase-2 install carrier so required validation is Python-only and rendering/publication is operator-owned without a prescribed local command.
- [x] After editing the canonical seeds, manually synchronize `docs/prompts/refresh-techdocs.prompt.md` and `docs/prompts/install-wavefoundry.prompt.md` as self-hosted authored twins; do not use either local twin as the source fix or claim the current renderer owns it.
- [x] Replace the nav leaf tokenizer in `techdocs_audit_lib.parse_mkdocs` with a small tagged/indentation-aware helper that classifies section, leaf(target), or unsupported; accept root leaves and exactly one section level plus the closed plain/matched-quote scalar subset.
- [x] Add parser polarity tests for no-space, unquoted-space, single-quoted-space, double-quoted-space, siblings, root leaves, one-section leaves, two-section leaves, unmatched/mixed wrappers, trailing tokens, comment suffixes, doubled single quotes, and double-quoted backslash escapes.
- [x] Add raw/public audit tests for existing and missing spaced targets plus in-root/escaping containment operation spies.
- [x] Update carrier literal/parity tests and add known-bad mutants for the removed renderer instruction, the old `\\S+` nav-path behavior, and a naïve permissive `.+` tail matcher that still flattens unsupported depth or syntax.
- [x] Update `CHANGELOG.md` under `[Unreleased]`, run seed/twin/package parity checks, warning-strict focused tests, full framework suite, `wf_validate_docs`, and `git diff --check`.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Canonical workflow contract | implementer | — | Write-owning: seed 178 and Phase-2 install seed first; self-hosted authored twins are synchronized afterward and are not renderer-owned. |
| Spaced-nav parser and tests | implementer | — | Write-owning: `techdocs_audit_lib.py` and focused tests; preserve audit/read containment. |
| Authored-twin synchronization and parity | implementer | Canonical workflow contract | Synchronize self-hosted prompt twins, then update literal/seed-twin/package tests and changelog. |
| Independent review | code-reviewer, qa-reviewer, docs-contract-reviewer | All implementation workstreams | Read-only lanes; reviewers do not mutate source, tests, seeds, generated prompts, or lifecycle state. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/test_techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `docs/prompts/refresh-techdocs.prompt.md`
- `docs/prompts/install-wavefoundry.prompt.md`
- `CHANGELOG.md`

## Affected Architecture Docs

N/A. The existing `docs/architecture/layering-rules.md` TechDocs row already confines the audit to the standard library plus existing framework modules, preserves the recognized-shape stdlib parser, and forbids filesystem access before containment. This change does not alter tool ownership, response schema, mutation authority, runtime flow, module dependencies, test tiers, or CI gates; its seed wording and focused regressions preserve that existing architecture contract without editing an architecture document.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The operator explicitly rejected downstream rendering and undeclared external tooling. |
| AC-2 | required | Removing the command must not accidentally remove the actual validation contract. |
| AC-3 | required | This is the directly reproduced parser defect against the project's own ADR naming convention. |
| AC-4 | required | Parser-only success is insufficient; the public audit must preserve the boundary and finding polarity. |
| AC-5 | required | Accepting a broader scalar form must not weaken path containment or shape honesty. |
| AC-6 | required | Seeds are canonical and generated/install carriers must not ship conflicting instructions. |
| AC-7 | required | The change's core constraint is zero dependency expansion, with full regression verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-20 | Planned from downstream Solaris dogfood: audit became clean, but optional `@techdocs/cli --no-docker` could not run without undeclared MkDocs dependencies; direct `parse_mkdocs` probes showed every spaced nav spelling returned `shape_ok=false`, `nav=[]`. | Canonical prompt lines 58-65/94-103; `_NAV_ENTRY_RE` and `parse_mkdocs`; direct four-form parser probe. |
| 2026-08-20 | Readiness red-team found an adjacent current defect in the same parser seam: a two-section-deep leaf is flattened and reported as computed instead of degrading. The plan now defines an exact root/one-section depth matrix, a closed scalar subset, and a naïve-`.+` known-bad control. | Public `audit_techdocs` two-section fixture omitted `mkdocs_shape`; current one-section test could not detect the counterexample; `RT-READ-1` readiness challenge. |
| 2026-08-21 | **Thought:** activate the readied wave, open only the seed/framework gates, then run two non-overlapping implementation workstreams: canonical workflow carriers and the parser/tests. Synchronize authored twins only after seed edits, merge the evidence, and keep AC/task bookkeeping current before the full suite. | `wf_implement_wave(mode='create')` transitioned `1vvei` to implementing; pre-implementation memory brief reviewed the audit-only branch, install-row stability, matcher provenance, and carrier-drift advisories. |
| 2026-08-21 | **Observe:** the two implementation workstreams merged cleanly. The parser now models root leaves and one section level with the closed scalar grammar, and live TechDocs carriers now keep validation Python-only while assigning rendering/publication to the operator environment. | Warning-strict focused runs passed 83 parser/audit tests, 104 carrier tests, 53 install-log tests, 112 package tests, and 16 shipped-reference tests. The carrier polarity oracle killed both reintroduced-rendering and renderer-absence-degradation mutants. |
| 2026-08-21 | **Observe:** integrated verification completed and both temporary edit gates were closed. All required ACs and tasks now have executable evidence; delivery review is the remaining lifecycle step. | Full framework suite: 7,463 tests across 64 files, OK. Full `wf_validate_docs`: clean with zero warnings. `git diff --check`: clean. Live carrier census found no `npx`, TechDocs CLI, `--no-docker`, or `mkdocs-techdocs-core` workflow command; no dependency manifest changed for this wave. |
| 2026-08-21 | **Observe:** delivery QA found that the first closed-scalar implementation still interpreted leading YAML anchors, tags, and flow collections as filenames; code review then found the adjacent terminal-colon form. Repair cycle 1 now refuses reserved leading indicators and plain-scalar colon ambiguity while preserving `target:slug.md`, with parser and raw/worker polarity tests. | `QA-DEL-1`; warning-strict `test_techdocs_audit_lib.py` passes 84 tests, the current full suite passes 7,464 tests across 64 files, and fresh QA replay killed a terminal-colon acceptance mutant. The framework gate was reopened only for this repair and closed immediately afterward. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-20 | Select Python-only Wavefoundry validation plus a bounded spaced-nav parser repair. | It removes an unnecessary external toolchain while fixing the actual Python audit used in every downstream project. | Keep conditional `npx` smoke after probing all transitive dependencies (rejected: still advertises Node/Docker-era tooling and adds no required Wavefoundry signal); add MkDocs/TechDocs core to base dependencies and render locally (rejected: expands the dependency/product boundary for an operator-owned concern); remove rendering only and defer the nav defect (rejected: leaves a reproduced failure against Wavefoundry's own ADR convention). |
| 2026-08-20 | Preserve the recognized-shape parser rather than adopt a general YAML library. | The defect is a bounded nav-scalar tokenizer gap; existing fail-closed semantics and dependency isolation remain valuable. | Add PyYAML or reuse Backstage/MkDocs parsing (rejected: new runtime dependency and broader semantic surface). |
| 2026-08-20 | Make the recognized nav subset explicit and indentation-aware. | Merely replacing `\\S+` with a permissive tail matcher would fix spaced happy paths while preserving false-computed deeper shapes and guessing at YAML syntax. | Accept arbitrary scalar tails and retain flattening (rejected: fails shape honesty); implement general YAML scalar/nesting semantics (rejected: exceeds the bounded repair and dependency boundary). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A permissive spaced-path matcher could misparse section headers, comments, malformed quotes, or deeper nesting. | Use an explicit leaf-scalar parser with a closed polarity matrix; preserve `shape_ok=false` for unmodelled forms. |
| Newly accepted target strings could reach filesystem operations before containment. | Exercise raw audit operation spies for absolute/root-escaping spaced targets and retain lexical plus realpath refusal before `is_file`/open. |
| Removing the external smoke could be misread as claiming the audit is a full MkDocs renderer. | State the exact boundary: Wavefoundry validates its modeled publication contract; rendering and publication remain operator/Backstage-owned and are not performed. |
| Canonical seeds and self-hosted authored prompt twins could drift. | Edit seeds first, synchronize the authored twins explicitly, and enforce literal/seed-twin/package parity in tests; do not imply the current renderer owns them. |
| Review-policy inputs will change when the admitted plan or requested lanes change. | Finalize AC priority, targets, and lanes before recording the readiness receipt; re-Prepare after any later packet edit. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
