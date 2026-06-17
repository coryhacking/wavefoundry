# Seed instruction: populate repo-profile.json vendored_paths (makes 1p64t usable)

Change ID: `1p651-enh seed-vendored-paths-instruction`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p61u graph-layer-map-quality`

## Rationale

`1p64t` added the codebase-map vendored axis: the generator reads `docs/repo-profile.json` `vendored_paths` (and `.gitattributes linguist-vendored`) to exclude vendored/third-party trees from the area tier. But **no seed tells an agent to populate `vendored_paths`**, so the signal is inert on a fresh install — the operator has to know the key exists and set it by hand.

Note the asymmetry this closes: the **generated** axis (`1a`) is automatic (`graph_indexer` tags `generated` from `.gitattributes linguist-generated`, header signatures, and generated dir/suffix names — no agent action). The **vendored** axis is deliberately explicit-signal-only (`1p64t` decision log: no name heuristics, to avoid misclassifying a first-party file that merely looks library-ish). "Explicit signal" is correct — but it *requires* an agent instruction to produce the signal. This change supplies it.

`seed-030` (inventory-and-map) is the producer of `repo-profile.json` and already has an extensibility clause for new profile keys, so the instruction belongs there; `seed-050`/`seed-020` describe the codebase-map orientation surface, so a one-line discoverability note belongs there.

## Requirements

1. `seed-030` instructs the agent, during inventory, to detect **bundled / vendored / third-party** trees (a judgment call — a checked-in copy of an external library/dependency, NOT first-party product code) and record them as a glob list under `vendored_paths` in `docs/repo-profile.json`. The agent should also recognize `.gitattributes linguist-vendored` as the ecosystem-standard marker the map honors, and should NOT guess from names alone (a product file with a library-ish name stays in).
2. The instruction names the consumer (the codebase-map generator excludes vendored-dominated areas into a collapsed footer; the trees stay `code_*`-searchable) so the agent understands why it's recording the key.
3. A short discoverability note where the codebase map is described (`seed-050`, and/or the `seed-020` run-contract orientation line) that the map excludes vendored/generated trees and consumes `vendored_paths` / `linguist-vendored`.
4. Seed-first (these are framework seeds; per-project rendered surfaces pick it up on install/upgrade). Generic; vendor-neutral; docs-lint clean.

## Scope

**In scope:**

- `seed-030-inventory-and-map.prompt.md`: a new task — vendored/third-party detection → `vendored_paths` in `repo-profile.json` (+ `.gitattributes linguist-vendored` recognition; explicit-signal, no name guessing).
- `seed-050-agent-entry-surface-bootstrap.prompt.md` (and/or `seed-020-run-contract`): one-line note that the codebase map excludes vendored/generated trees and consumes `vendored_paths`.

**Out of scope:**

- Automatic vendored detection in `graph_indexer` (rejected by `1p64t` — would reintroduce the name-heuristic / lookalike risk the explicit-signal design avoids).
- Changing the generator (the consumer already shipped in `1p64t`).

## Acceptance Criteria

- [x] AC-1: `seed-030` carries an explicit task to detect bundled/vendored/third-party trees and record them under `vendored_paths` in `docs/repo-profile.json`, recognizing `.gitattributes linguist-vendored`, with an explicit-signal / no-name-guessing caution and a note that the codebase map consumes it.
- [x] AC-2: The codebase-map orientation surface (`seed-050` and/or `seed-020`) gains a discoverability note that the map excludes vendored/generated trees and reads `vendored_paths` / `linguist-vendored`. Seed-first; docs-lint clean; full suite green.

## Tasks

- [x] Add the vendored-detection task to `seed-030` (record `vendored_paths`; recognize `linguist-vendored`; explicit-signal caution; name the map consumer).
- [x] Add the discoverability note to `seed-050` (+ `seed-020` if it fits the orientation line).
- [x] docs-lint + full suite (seed prose; no code path, but keep the gate green).

## Affected Architecture Docs

`N/A` — seed-prose guidance; no code/boundary/flow change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Without the producer-side instruction, `1p64t`'s vendored axis is inert on a fresh install. |
| AC-2 | important | Discoverability — agents/operators learn the map consumes the key. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Operator asked whether any instruction tells agents to add `vendored_paths`; there was none — `1p64t` shipped the consumer without the producer-side seed instruction. | `seed-030` (repo-profile producer); `gen_codebase_map.py:318` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Instruct the agent to populate `vendored_paths` (seed-030) rather than auto-detect vendor dirs in code. | Preserves `1p64t`'s explicit-signal design (no name heuristics / lookalike risk); the agent has the judgment to tell a bundled dependency from product code. | Auto-detect common vendor dir names in `graph_indexer` (rejected — reintroduces the heuristic risk). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Agent over-tags first-party code as vendored. | The instruction is explicit-signal + judgment ("a checked-in copy of an external library, not product code"); the map keeps vendored trees searchable (collapsed footer, not deletion), so a mistag is recoverable, not destructive. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
