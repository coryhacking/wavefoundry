# Reconstruct the CHANGELOG so 1.6.0 is the complete official release record

Change ID: `1p5dl-doc changelog-1-6-official-release-record`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p5dk 1-6-release-hardening`

## Rationale

The `## [1.6.0] - 2026-06-09` CHANGELOG section was cut at commit `e30586a` and never shipped (no 1.6 build was distributed). Four substantial waves landed and were committed *after* that date but are almost entirely undocumented:

- **1p4wz** (commit `16f45b2`) — the single-index fold (removed the two-layer search path), the docs/code embedding-model split (`snowflake-arctic-embed-xs` for docs, `bge-small-en-v1.5` for code), FP16/CoreML acceleration, and the `ms-marco-MiniLM` reranker wired into `code_ask`. The largest functional change in the release — **zero CHANGELOG entries.**
- **1p5cg** (commit `0bf1585`) — streaming bounded-buffer index build, offline-first model load, lazy per-layer embedder load. No entries.
- **1p4hi** (`81bae0c`/`7af573c`) — all-language constant chunking + `code_ask` rerank. No entries.
- **1p58z** (`a147eac`) — only the canonical-names removal made it in (under `[Unreleased]`); the oversized-file guard (1p5c4), project-relative tracked surfaces (1p590), and install-asset consolidation (1p591) are undocumented.

Most critically, **both forced-rebuild version bumps are absent**: `GRAPH_BUILDER_VERSION` and `CHUNKER_VERSION` both went **25 → 30** after the cut (verified: `git show e30586a` shows `25`; HEAD shows `30`). Combined with the 1p4wz model swap, upgrading to this build forces a **full graph re-extract + full re-chunk + full re-embed** — a complete index rebuild — and the CHANGELOG signals none of it. The content is also split incoherently (one 1p4wz line inside `[1.6.0]`, canonical-names in `[Unreleased]`, everything else nowhere) while `VERSION` already reads `1.6.0+p4uw`.

Operator decision (recorded): no 1.6 build was ever distributed, so **this is the official 1.6.0** — fold everything into one `## [1.6.0]` section rather than cutting 1.6.1/1.7.0.

## Requirements

1. `## [1.6.0]` becomes the single, complete official-release record: absorb the `## [Unreleased]` content and add entries for every landed wave not yet represented (1p4wz, 1p5cg, 1p4hi, the 1p58z sub-changes), in the existing Keep-a-Changelog `Added`/`Changed`/`Removed` structure.
2. Add an explicit, operator-facing **upgrade-impact note** stating that moving to 1.6.0 forces a full index rebuild (graph re-extract + re-chunk + re-embed with the new docs/code models), naming `GRAPH_BUILDER_VERSION`/`CHUNKER_VERSION` 25→30 as the cause and the new model pair.
3. The canonical-names removal bullet cites its governing ADR (`1p5be`).
4. The `## [Unreleased]` section is emptied (or removed) once its content is folded in; the `## [1.6.0]` date advances to the actual assembly/ship date.
5. Style follows the repo convention: git-commit-message-style bullets, no build numbers, no wave IDs, no internal version constants in prose — except the forced-rebuild note, where `GRAPH_BUILDER_VERSION`/`CHUNKER_VERSION` is the operator-relevant fact.

## Scope

**Problem statement:** the CHANGELOG omits ~4 landed waves and both forced-rebuild bumps, and splits one release period across `[1.6.0]`/`[Unreleased]`/nothing — so a consumer cannot see what 1.6 contains or that it forces a full rebuild.

**In scope:**

- `CHANGELOG.md` only: reconstruct `## [1.6.0]`, fold in `## [Unreleased]`, add the upgrade-impact note + ADR citation.

**Out of scope:**

- Code, version constants, the upgrade flow (covered by `1p5dn`/`1p5do`), and the operator prompt docs (`1p5dm`).
- Re-cutting a different version number (operator chose single 1.6.0).

## Acceptance Criteria

- [x] AC-1: every landed-but-undocumented wave (1p4wz, 1p5cg, 1p4hi, 1p58z sub-changes) has a CHANGELOG entry under `## [1.6.0]`; cross-checked against `git log` since the 1.6.0 cut. Added: single-index/model-split/reranker (1p4wz), streaming/offline/lazy (1p5cg), constant retrieval (1p4hi), oversized-file guard (1p5c4), portable surfaces + install consolidation (1p590/1p591).
- [x] AC-2: a prominent upgrade-impact note under `## [1.6.0]` states the move forces a full index rebuild (graph re-extract + re-chunk + re-embed), naming the `GRAPH_BUILDER_VERSION`/`CHUNKER_VERSION` bumps and the new `snowflake-arctic-embed-xs` / `bge-small-en-v1.5` model pair.
- [x] AC-3: `## [Unreleased]` content folded into `## [1.6.0]` and the section removed; the canonical-names bullet cites ADR `1p5be`.
- [x] AC-4: docs-lint clean; no wave IDs / build numbers in `[1.6.0]` prose (stripped `Wave 1p4u0 / 1p4u1` from the provider entry); date advanced to 2026-06-13.

## Tasks

- [x] Enumerate landed-but-undocumented changes from `git log e30586a..HEAD` + the wave records; draft entries per wave.
- [x] Fold `## [Unreleased]` into `## [1.6.0]`; add the upgrade-impact note + ADR `1p5be` citation; advance the date.
- [x] docs-lint; verify style + completeness against the wave list.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- None — `CHANGELOG.md` only; independent of the other changes in this wave.

## Affected Architecture Docs

`N/A` — release-history documentation only; no architecture/boundary/flow impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The release record must reflect what actually shipped. |
| AC-2 | required  | The forced full rebuild is the single most important operator-facing upgrade fact. |
| AC-3 | required  | One coherent release section; the pulled-forward removal needs its ADR. |
| AC-4 | important | Style consistency keeps the changelog usable and lint-clean. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Reconstructed `## [1.6.0]` (date → 2026-06-13): added a forced-rebuild upgrade note (blockquote) and `### Changed`/`### Added` entries for the model-split + reranker + index-fold, streaming/offline/lazy, oversized-file guard, constant retrieval, and portable surfaces. Moved the canonical-names removal from `[Unreleased]` into `### Removed` with an ADR `1p5be` citation; removed `[Unreleased]`. Stripped the `Wave 1p4u0 / 1p4u1` wave-ID from the provider entry. docs-lint clean; no wave IDs in `[1.6.0]` prose. | `CHANGELOG.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-13 | Single official `## [1.6.0]`, not 1.6.1/1.7.0 | Operator confirmed no 1.6 build was ever distributed, so 1.6.0 is the first real release | Cut 1.7.0 (model split is feature-tier) — rejected because nothing shipped under 1.6.0 yet |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Missing a landed change in the reconstruction | Cross-check `git log e30586a..HEAD` against the closed-wave list as the AC-1 gate |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
