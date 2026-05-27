# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-26

wave-id: `12wsj framework-cleanup`
Title: Framework Cleanup

## Changes

Change ID: `12vrb-enh suppress-empty-gardener-reports`
Change Status: `complete`

Change ID: `12wsd-debt remove-pre-v1-legacy-compat`
Change Status: `complete`

Change ID: `1p0qw-doc seed-prompt-review-and-simplification`
Change Status: `complete`

Change ID: `1p0r6-maint wave-template-validation-conformance`
Change Status: `complete`

Change ID: `12ww2-ops codex-project-local-mcp-config`
Change Status: `complete`

Change ID: `12wxj-maint bin-directory-naming-cleanup`
Change Status: `complete`

Change ID: `12xa1-bug setup-reranker-cache-recovery`
Change Status: `complete`

Change ID: `12xcg-enh artifact-query-formulation-guru`
Change Status: `complete`

Change ID: `12xcg-bug artifact-anchored-retrieval-routing`
Change Status: `complete`


## Objective

Remove pre-v1.0.0 legacy compatibility shims, suppress empty gardener reports, review seed-prompt simplification opportunities, keep wave/template scaffolds aligned with the live validator contract, and tighten search/retrieval guidance for artifact-anchored explanatory questions. The wave combines implementation cleanup with the documentation/template work needed to reduce prompt and workflow drift.

Completed At: 2026-05-26

## Wave Summary

Wave `12wsj` (Framework Cleanup) delivered 9 changes: Suppress Empty Gardener Reindex Reports, Remove pre-v1.0.0 legacy compatibility code, Seed Prompt Review And Simplification, Wave Template Validation Conformance, Codex Project-Local MCP Configuration, Bin Directory Naming Cleanup, Setup Model Cache Recovery, Artifact Query Formulation for Guru, and Artifact-Anchored Retrieval Routing. Notable adjustments during implementation: Suppress Empty Gardener Reindex Reports: Implemented empty-run suppression in `docs_gardener.py`; added regression coverage for no-op and existing-report cases.; Remove pre-v1.0.0 legacy compatibility code: Removed pre-v1 packaging/upgrade compatibility from runtime code, tests, seeds, and active operator docs. `build_pack.py` now blocks `<1.0.0`, `check_version.py` rejects non-semver strings, and semver-only zip discovery is enforced in `upgrade_wavefoundry.py`.; Codex Project-Local MCP Configuration: AC-1/2/3 complete: `.codex/config.toml` created at project root; user-level `wavefoundry-b1c145a9` entry removed from `~/.codex/config.toml`

**Changes delivered:**

- **Suppress Empty Gardener Reindex Reports** (`12vrb-enh suppress-empty-gardener-reports`) — 4 ACs completed. Key decisions: Suppress on empty, don't delete existing
- **Remove pre-v1.0.0 legacy compatibility code** (`12wsd-debt remove-pre-v1-legacy-compat`) — 5 ACs completed. Key decisions: Remove all pre-v1.0.0 compat
- **Seed Prompt Review And Simplification** (`1p0qw-doc seed-prompt-review-and-simplification`) — 3 ACs completed. Key decisions: Record findings before editing the seed corpus; Journal-memory contract should remember anything that improves outcomes, not only failures
- **Wave Template Validation Conformance** (`1p0r6-maint wave-template-validation-conformance`) — 4 ACs completed. Key decisions: Keep the scope focused on template and planning surfaces that directly define or restate the wave/change scaffold contract
- **Codex Project-Local MCP Configuration** (`12ww2-ops codex-project-local-mcp-config`) — 5 ACs completed. Key decisions: Use venv Python rather than system `python3`; Use relative paths in project-local config
- **Bin Directory Naming Cleanup** (`12wxj-maint bin-directory-naming-cleanup`) — 6 ACs completed. Key decisions: Combine both items in one change; Exclude closed wave history docs from AC-2/4 grep
- **Setup Model Cache Recovery** (`12xa1-bug setup-reranker-cache-recovery`) — 6 ACs completed. Key decisions: --------; Treat this as a bug in the setup/bootstrap contract, not a one-off local env issue.
- **Artifact Query Formulation for Guru** (`12xcg-enh artifact-query-formulation-guru`) — 3 ACs completed. Key decisions: --------; Keep the scope docs-side only.
- **Artifact-Anchored Retrieval Routing** (`12xcg-bug artifact-anchored-retrieval-routing`) — 3 ACs completed. Key decisions: --------; Keep routing changes separate from agent guidance.
## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| planner | plan | all admitted changes |
| wave-coordinator | coordinate | full wave lifecycle routing and readiness gate |
| code-reviewer | review | `12vrb`, `12wsd`, `1p0r6` — framework scripts and validator/scaffold behavior changes |
| qa-reviewer | review | all admitted changes — AC coverage, validator conformance, regression proof |
| docs-contract-reviewer | review | `1p0qw`, `1p0r6`, `12wsd` — seed/prompt/contract language and cleanup drift |
| release-reviewer | review | `12wsd` — packaging/versioning contract cleanup and upgrade-surface compatibility |
| council-moderator | council | full admitted set — Wave Council readiness synthesis |
| red-team | council | full admitted set — strongest challenge, alternative path, and implementation-sequencing pressure test |
| architecture-reviewer | council | full admitted set — lifecycle/tooling contract coherence |
| security-reviewer | council | full admitted set — path, packaging, and mutation-surface challenge |
| reality-checker | council | full admitted set — practical implementation sequencing and blast-radius review |

## Journal Watchpoints

- **Watchpoint (`12wsd`):** Legacy-compat removal must not touch closed wave records or the `Last verified:` date field — those are explicitly out of scope.
- **Blocking (`12wsd`):** Run the full test suite (`run_tests.py`) only after both Scripts and Tests workstreams are complete — do not chase a moving target by running tests mid-removal.
- **Blocking (`12vrb`):** Requires `seed_edit_allowed` gate open before editing any seed file; close the gate immediately after the edit.
- **Watchpoint (`1p0qw`):** Keep the review findings distinct from implementation work; do not collapse recommendation capture into ad hoc prompt edits without explicit follow-on scoping.
- **Watchpoint (`1p0r6`):** Template and prompt-surface conformance changes must stay tied to the live validator contract, not example wave docs or historical scaffolds.
- **Follow-up:** Both changes require the docs gate (`wave_validate`, `wave_garden`) to pass before closure is requested.

## Review Evidence

- wave-council-readiness: approved 2026-05-25 — Four cleanup changes admitted: empty gardener-report suppression, pre-v1 legacy-compat removal, seed-prompt simplification review, and wave-template validation conformance. Scope is coherent: one implementation cleanup pair (`12vrb`, `12wsd`) and one documentation/template pair (`1p0qw`, `1p0r6`) that together reduce framework drift and maintenance noise. Required reviewer lanes: code-reviewer for script and scaffold-surface changes; qa-reviewer for all admitted changes; docs-contract-reviewer for seed/prompt/template contract work; release-reviewer for packaging/versioning cleanup in `12wsd`. Product-owner: N/A — framework/process cleanup only. Wave is ready for implementation.
- wave-council-delivery: approved 2026-05-26 — All 9 admitted changes are complete with checked ACs, verified tests (1638 passing), and a clean docs gate. `12xcg-enh`/`12xcg-bug` ACs were corrected at review time (implementation was done, status fields lagged). `1p0qw`/`1p0r6` are pre-validator-contract docs and show `unknown` parser status — not introduced by this wave, not blocking. `_partition_tests()` heuristic surface noted for future maintenance if test-naming conventions expand. No blocking contradictions. Wave is ready for operator close.
- operator-signoff: approved 2026-05-26

## Prepare Review Evidence

- code-reviewer: approved — change docs for `12vrb`, `12wsd`, `1p0r6`, and `12ww2-ops` reviewed; framework script and validator/scaffold scope confirmed sound
- qa-reviewer: approved — AC coverage and priority recorded on all five admitted changes; test plan for Track B runtime changes reviewed
- docs-contract-reviewer: approved — seed/prompt/template language for `1p0qw`, `1p0r6`, and `12wsd` reviewed; contract surfaces internally consistent
- release-reviewer: approved — packaging and versioning cleanup scope for `12wsd` reviewed; semver and upgrade-surface impact confirmed contained

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-25: PASS** (red-team fixed seat; docs-contract-reviewer rotating seat)
  - Strongest challenge: bundling dead-code removal with prompt/template cleanup risks a half-cleaned contract where scripts stop mentioning legacy behavior before all seeded/operator docs and scaffold surfaces are consistent.
  - Best alternative considered: split the wave into two sub-waves, one for runtime cleanup and one for template/prompt cleanup.
  - Council verdict: keep the current wave because the admitted scope is still cohesive, but implement in two tracks: `1p0qw`/`1p0r6` contract cleanup and `12vrb`/`12wsd` runtime cleanup, with a docs-gate checkpoint between them.
  - No blocking contradictions remain after relocation repair and lane assignment.
- **Prepare wave — readiness verdict [prepare-readiness] — 2026-05-25: PASS**
  - All four admitted change docs are wave-owned under `docs/waves/12wsj framework-cleanup/`.
  - Required sections are present on all change docs.
  - AC priority is recorded on each admitted change.
  - Wave Council readiness signoff is recorded in `## Review Evidence`.
  - Product-owner acknowledgment is not required because this wave is framework/process cleanup only.
- **Track A checkpoint — 2026-05-25: PASS**
  - `1p0qw` contract decisions are now canonicalized in the shared seed set and matching local operator surfaces.
  - `1p0r6` template and wave-record contract surfaces are aligned with the live validator.
  - `python3 .wavefoundry/framework/scripts/docs_lint.py` passed after the Track A edits.
  - `git diff --check` passed.
  - Track B may begin next; the remaining work is runtime cleanup only (`12vrb`, `12wsd`).
- **Track B status — 2026-05-25: PASS**
  - `12vrb` implementation is complete: empty gardener runs no longer create report noise, targeted gardener tests pass, and manual no-op smoke output is correct.
  - `12wsd` implementation is complete: pre-v1 packaging/upgrade compatibility was removed from runtime code, tests, seeds, and active operator docs; targeted build-pack, check-version, upgrade, and design-system backfill suites pass; docs lint passes; `.wavefoundry/framework/` is clean against the legacy bridge/date-style grep.
  - Full-suite proof: `python3 .wavefoundry/framework/scripts/run_tests.py` — 1620 tests, 0 failures (2026-05-25). Prior `test_server_tools.RerankerTests` failures did not recur; baseline is clean.
- **`12ww2-ops` implementation — 2026-05-25: IN PROGRESS**
  - AC-1/2/3 complete: `.codex/config.toml` created at project root using venv Python and relative paths; user-level `wavefoundry-b1c145a9` MCP entry removed from `~/.codex/config.toml`.
  - AC-4 pending: requires Codex session restart to verify project-local config loads.

## Dependencies

- No external wave dependencies.

## Execution Plan

1. Implement **Track A — contract and scaffold cleanup**
   - `1p0qw-doc seed-prompt-review-and-simplification`
   - `1p0r6-maint wave-template-validation-conformance`
2. Run a **checkpoint** before any runtime cleanup:
   - confirm docs gate passes
   - confirm active seed/prompt/template surfaces are internally consistent
   - confirm no copied-in or stale wording remains in active surfaces
   - confirm the runtime-cleanup plan still matches the cleaned contract
   - explicitly verify no active prompt or seed still describes bridge/date-style behavior as supported before starting legacy-compat removal
3. Implement **Track B — runtime and dead-code cleanup**
   - `12vrb-enh suppress-empty-gardener-reports`
   - `12wsd-debt remove-pre-v1-legacy-compat`
4. Implement **Track C — search and retrieval refinements**
   - `12xcg-enh artifact-query-formulation-guru`
   - `12xcg-bug artifact-anchored-retrieval-routing`
5. Within `12wsd`, serialize the work further:
   - remove runtime behavior first
   - update tests second
   - remove prompt/seed/doc references third
   - run full validation last
