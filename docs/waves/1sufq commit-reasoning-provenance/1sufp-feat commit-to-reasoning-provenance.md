# Commit-to-reasoning provenance (reverse wave lookup)

Change ID: `1sufp-feat commit-to-reasoning-provenance`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-17

Wave: `1sufq commit-reasoning-provenance`

## Rationale

Wavefoundry tracks wave/change to commit going forward (waves cite landing commits in their review evidence; landing commits follow the `Land wave(s) <id>: …` convention), but there is no reverse lookup: from a commit, or a blamed line, back to the wave that produced it and its reasoning. "Why is this line here, what decided it" currently means an agent re-deriving context that already exists in the closed wave record and its Decision Log.

A field user running wavefoundry alongside other memory tools named this gap directly. It is buildable entirely locally over data we already have, with no new infra and no network: git blame/log plus the on-disk wave records. It also has a token-efficiency payoff (surfacing the recorded decision instead of re-deriving it).

## Requirements

1. **Commit to wave resolution.** Given a commit SHA, resolve the wave(s)/change(s) that produced it by two local paths: (a) parse the commit message for the `Land wave(s) <id>` convention, and (b) reverse-search the on-disk wave records / review evidence for the commit SHA cited in their evidence. When both disagree or neither resolves, report that honestly rather than guessing.
2. **Line to reasoning.** Given a file path and line (or line range), run a contained `git blame` to get the producing commit(s), then apply requirement 1, and surface the resolved wave's Decision Log entries and change-doc rationale relevant to that file.
3. **Surface the reasoning, not just the ID.** The response returns the wave/change IDs, the relevant Decision Log rows, and pointers into the change doc(s), so the caller gets the recorded reasoning, not just a mapping.
4. **Local-only and read-only.** Uses only local git and on-disk wave records. No network, no new persistent store required (an optional derived cache may be added but must be rebuildable and non-authoritative). It never mutates git or wave state.
5. **Honest absence.** A commit with no wave association (for example a pre-framework or hand commit) returns a clear "no wave provenance found" result, not a fabricated one.
6. **Measured token savings (council: the cleanest fit).** `code_commit_provenance` is a read-and-surface retrieval tool — it returns the recorded Decision Log rows + change-doc rationale *instead of* the agent reading the whole `wave.md` + change doc(s) to re-derive. So it joins the existing 1stwj measured context-avoided harness: add it to `_CONTEXT_RETRIEVAL_TOOLS` (`server_impl.py`) + `_context_source_paths` so its cited sources (the resolved `wave.md` + change docs) are credited as whole-file bytes − response, per-phase-deduped and zero-clamped. This is the measured metric, not an estimate; no new gauge.
7. **Non-token signal.** Report a `resolution_hit_rate` / `honest_absence_rate` as the wave's activity signal (not a token target); there is no per-wave token-savings AC.

## Scope

**Problem statement:** provenance is one-directional (wave to commit); there is no way to go from a commit or a blamed line back to the wave and decisions that produced it, so agents re-derive context that already exists.

**In scope (edited under `framework_edit_allowed`):**
- `.wavefoundry/framework/scripts/server_impl.py` — a `code_commit_provenance` tool (input: commit SHA, or file + line range): resolve wave(s), surface Decision Log + change-doc rationale, honest-absence result.
- A resolver helper: commit-message `Land wave` parse + reverse-search of wave records/review evidence for a cited commit SHA; contained `git blame` for the line path (reuse the existing contained-git discipline).
- Reuse the existing wave-record / change-doc parsers and `git log`/`git blame` wrappers already used by the freshness/drift subsystem.
- Docs — MCP tool-surface note + a short reference.
- Tests — commit-message resolution, evidence-reverse-search resolution, blame-to-wave, honest absence, local-only/no-network, no state mutation.

**Out of scope:**
- **Forward tracking** (wave to commit) — already exists.
- **Per-line reasoning storage** — resolution is computed on demand from git + wave records, not stored per line.
- **Team-shared or hosted provenance** — local-only.
- **A full git history browser / UI.**

## Acceptance Criteria

- [x] AC-1: Given a commit SHA, the tool resolves the producing wave(s)/change(s) via commit-message `Land wave` parse and via reverse-search of wave records/review evidence; conflicting/absent resolution is reported honestly, never guessed. (required) — `resolve_via_message` + `resolve_via_evidence` combined in `resolve_commit_to_waves`; `conflict`/`method`/`resolved` fields; tests `test_message_path_resolves_landed_wave`, `test_evidence_path_resolves_non_conventional_commit`, `test_conflict_reports_both_never_reconciles`.
- [x] AC-2: Given a file + line range, a contained `git blame` yields the producing commit(s), then AC-1 resolution applies, and the wave's Decision Log entries + change-doc rationale relevant to that file are surfaced. (required) — `blame_line_commits` (bounded `-L`, path-traversal guard) → `provenance_for_line`; tests `test_blame_line_to_commit`, `test_provenance_surfaces_decision_log`.
- [x] AC-3: The response returns wave/change IDs, relevant Decision Log rows, and change-doc pointers — the reasoning, not just a mapping. (required) — `_decision_log_rows` + `_provenance_rows_for_wave` (path + decisions + excerpt); verified: SHA `79d779e6` → waves `[1shv4,1sq4a,1sq9i]`, 7 provenance rows.
- [x] AC-4: Local-only and read-only — only local git + on-disk wave records; no network; no git/wave-state mutation. (required) — routed through argv-based `_run_git`; blame/log/rev-parse only; test `test_resolver_never_mutates_repo`.
- [x] AC-5: A commit with no wave association returns a clear no-provenance result. (required) — `no_wave_provenance` diagnostic + `resolution: "honest_absence"`; tests `test_honest_absence_never_fabricates`, `test_honest_absence_signal`.
- [x] AC-6: `code_commit_provenance` emits the existing 1stwj measured `context_avoided` envelope field via the `_CONTEXT_RETRIEVAL_TOOLS` roster + `_context_source_paths` (cited sources = resolved `wave.md` + change docs; avoided = whole-file bytes − response), per-phase-deduped and zero-clamped like the other retrieval tools — no new gauge, and no per-wave token-savings target. (required) — added to roster + `_context_source_paths` (`add_rows("provenance","path",("excerpt",))`); exact-census test `test_registered_envelope_census_is_exact` updated; verified 4 content-bearing sources credited.
- [x] AC-7: The tool reports a `resolution_hit_rate` / `honest_absence_rate` non-token activity signal. (important) — per-call `data["resolution"]` ∈ {`resolved`, `honest_absence`, `conflict`}, the atom a hit-rate/absence-rate aggregates; tests `ResolutionSignalTests`.
- [x] AC-8: Full framework suite green; docs-lint clean. (required) — `run_tests.py --no-cache`: 5760 tests OK; `wf docs-lint`: ok.

## Tasks

- [x] Resolver: commit-message `Land wave` parse + reverse-search of wave records/review evidence for a cited commit SHA.
- [x] `code_commit_provenance` tool (SHA or file+line); contained `git blame`; surface Decision Log + change-doc rationale; honest absence.
- [x] Reuse existing wave-record/change-doc parsers + contained git wrappers. — reuses sanctioned `_run_git`/`_sanitized_git_env`; Decision Log extraction is a small addition over the on-disk change docs, per the prepare-council note.
- [x] Docs (tool-surface + reference); tests (both resolution paths, blame, absence, local-only, no mutation). — `docs/specs/mcp-tool-surface.md` tool entry + chooser row; `test_commit_provenance.py` (16 tests).
- [x] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| resolver | framework | — | commit→wave via message parse + evidence reverse-search |
| tool | framework | resolver | `code_commit_provenance` (SHA / file+line); blame; surface reasoning |
| verify | framework | tool | tests + docs |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — edited under `framework_edit_allowed`. Reuses the existing contained-git wrappers.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` gets the new tool. No boundary change — a read-only resolver over local git + existing wave records.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Commit→wave resolution, two paths, honest on conflict/absence |
| AC-2 | required | Line→reasoning via contained blame |
| AC-3 | required | Surface the recorded reasoning, not just an ID |
| AC-4 | required | Local-only, read-only, no mutation (core principle) |
| AC-5 | required | Honest absence, never fabricated |
| AC-6 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-17 | Change doc authored; gap surfaced by a field user, buildable over existing local associations | Enhancement plan; `Land wave …` commit convention; waves cite landing commits in review evidence |
| 2026-07-17 | Implementation begun: core resolver module `commit_provenance.py` (message-parse + evidence reverse-search resolution; bounded `git blame` with path-traversal guard, SHA validation, uncommitted-sentinel filter) reusing sanctioned `_run_git`. Smoke-tested on real commits (4f0c8d4e→1stwj; 79d779e6→1shv4/1sq4a/1sq9i; invalid→fail-closed; traversal blocked). REMAINING: the `code_commit_provenance` MCP tool (registration + Decision Log extraction + honest-absence response), the `context_avoided` emission (AC-6), the test file, and docs. | `commit_provenance.py`; smoke test |
| 2026-07-18 | Implementation complete. `code_commit_provenance` tool registered (`@mcp.tool`, SHA or file+line), `code_commit_provenance_response` builder (honest-absence + conflict diagnostics, per-call `resolution` signal), wired into `_CONTEXT_RETRIEVAL_TOOLS` + `_context_source_paths` for measured `context_avoided`. Docs added (tool-surface entry + chooser row). Tests: `test_commit_provenance.py` (16, incl. server-layer resolution signal); exact-census test updated for the new roster member. Full suite 5760 OK; docs-lint ok. Hermetic tests caught + fixed a real evidence-path bug (returned wave dir-name, not the id token) the real-repo smoke test had masked. All ACs [x]. | `run_tests.py --no-cache`: 5760 OK; `wf docs-lint`: ok |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-17 | On-demand resolution from git + wave records | No new persistent state; local-only; reuses existing data | Per-line reasoning store (rejected — heavy, redundant with git+records) |
| 2026-07-17 | Two resolution paths (message parse + evidence reverse-search) | Robust to commits that do/don't name the wave | Message parse only (rejected — misses non-conventional commits) |
| 2026-07-17 | Local-only, read-only | Core no-network principle; provenance must not mutate | Hosted/team provenance (rejected — conflicts with local-only) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Commit-message convention not followed | Second path: reverse-search wave records/evidence for the commit SHA |
| Squashed/rebased history breaks blame→commit | Report the resolvable provenance + honest gap; never fabricate |
| `git blame` cost on large files/ranges | Contained blame on the requested range only; reuse the bounded-git discipline |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
