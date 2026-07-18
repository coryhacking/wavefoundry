# Commit-to-reasoning provenance (reverse wave lookup)

Change ID: `1sufp-feat commit-to-reasoning-provenance`
Change Status: `planned`
Owner: framework
Status: planned
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

- [ ] AC-1: Given a commit SHA, the tool resolves the producing wave(s)/change(s) via commit-message `Land wave` parse and via reverse-search of wave records/review evidence; conflicting/absent resolution is reported honestly, never guessed. (required)
- [ ] AC-2: Given a file + line range, a contained `git blame` yields the producing commit(s), then AC-1 resolution applies, and the wave's Decision Log entries + change-doc rationale relevant to that file are surfaced. (required)
- [ ] AC-3: The response returns wave/change IDs, relevant Decision Log rows, and change-doc pointers — the reasoning, not just a mapping. (required)
- [ ] AC-4: Local-only and read-only — only local git + on-disk wave records; no network; no git/wave-state mutation. (required)
- [ ] AC-5: A commit with no wave association returns a clear no-provenance result. (required)
- [ ] AC-6: `code_commit_provenance` emits the existing 1stwj measured `context_avoided` envelope field via the `_CONTEXT_RETRIEVAL_TOOLS` roster + `_context_source_paths` (cited sources = resolved `wave.md` + change docs; avoided = whole-file bytes − response), per-phase-deduped and zero-clamped like the other retrieval tools — no new gauge, and no per-wave token-savings target. (required)
- [ ] AC-7: The tool reports a `resolution_hit_rate` / `honest_absence_rate` non-token activity signal. (important)
- [ ] AC-8: Full framework suite green; docs-lint clean. (required)

## Tasks

- [ ] Resolver: commit-message `Land wave` parse + reverse-search of wave records/review evidence for a cited commit SHA.
- [ ] `code_commit_provenance` tool (SHA or file+line); contained `git blame`; surface Decision Log + change-doc rationale; honest absence.
- [ ] Reuse existing wave-record/change-doc parsers + contained git wrappers.
- [ ] Docs (tool-surface + reference); tests (both resolution paths, blame, absence, local-only, no mutation).
- [ ] Full suite + docs-lint.

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
