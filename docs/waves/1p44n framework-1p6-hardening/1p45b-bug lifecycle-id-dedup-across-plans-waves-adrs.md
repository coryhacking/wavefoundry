# Lifecycle ID Minting Must Dedup Across Plans, Waves, And ADRs

Change ID: `1p45b-bug lifecycle-id-dedup-across-plans-waves-adrs`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

Lifecycle ID minting can hand out an ID that already exists, producing duplicate stems and prefix-ambiguous lookups. Two independent defects combine:

1. **The MCP tool paths skip directory dedup entirely.** `next_available_prefix` (`lifecycle_id.py:192-229`) only consults existing on-disk prefixes when a `repo_root` is supplied: `existing = _existing_prefixes(repo_root) if repo_root is not None else set()` (`:210`). But the server's `create_wave` calls `build_id("wave", slug_s, legacy=False, commit=…)` (`server_impl.py:4306-4308`) and `new_change` calls `build_id(kind, slug, legacy=False)` (`server_impl.py:4734`, and again at `:4768`) — **none pass `repo_root`**. So `_existing_prefixes` is never scanned on the MCP path; the only guard is the in-process `_last_assigned_prefix`, which is empty on a fresh server and never reflects files already on disk. Result: `wave_new_*` / `wave_create_wave` happily mint a stem that already exists in a wave directory (observed this session: a `wave_new_enhancement` call returned `1p44w`, already used by `1p44w-enh secrets-jwt-expiry-awareness`).

2. **ADRs are never scanned, even with `repo_root`.** `_existing_prefixes` (`lifecycle_id.py:170-189`) scans only `docs/plans/*.md`, `docs/waves/<dir>` names, and `docs/waves/*/*.md`. It does **not** scan `docs/architecture/decisions/*.md`. Evidence this already happened: `docs/architecture/decisions/12tm5-adr semver-versioning-contract.md` and `docs/architecture/decisions/12tm5-adr python-tool-environment.md` share the stem `12tm5` — a pre-existing duplicate ADR ID.

The fix is both halves: pass `repo_root` at the MCP call sites so dedup actually runs, and extend `_existing_prefixes` to include ADRs so the dedup set covers plans + waves + ADRs.

## Requirements

1. `_existing_prefixes` (`lifecycle_id.py:170-189`) must also collect prefixes from ADR documents under `docs/architecture/decisions/*.md`, so minted IDs never collide with an existing ADR stem.
2. The MCP minting call sites must pass `repo_root` into `build_id` so directory dedup is actually consulted: `create_wave` (`server_impl.py:4306`) and both `new_change` `build_id` calls (`server_impl.py:4734`, `:4768`) must forward the `root` they already hold.
3. Dedup must hold across BOTH the `dry_run`/peek path (`commit=False`) and the `create` path (`commit=True`) so a previewed ID and the subsequently-created ID are the same next-available, collision-free stem.
4. Defense in depth: when `next_available_prefix` / `build_id` is invoked without an explicit `repo_root`, it should fall back to `discover_repo_root()` (already used by the CLI at `lifecycle_id.py:311`) rather than silently skipping dedup, so no caller accidentally mints without a dedup set.
5. The dedup set is the union of plans + waves (wave-dir names and in-wave change docs, as today) + ADRs; an ID equal to any existing stem in any of those locations must be skipped.
6. **MCP-first minting reminder (runtime):** when `lifecycle_id.py` is invoked directly as a CLI/script, it emits a brief reminder (to **stderr**, so the minted ID on stdout stays machine-parseable) steering the caller to prefer the MCP minting tools — `wave_new_<kind>` / `wave_create_wave` — whenever the MCP server is available. The CLI stays a supported fallback; the reminder reinforces that all agents should mint via MCP (which scaffolds the change/wave doc and, after this fix, applies the same dedup).
7. **MCP-first minting reminder (docs):** the documentation surfaces that present the `lifecycle_id.py` CLI as a fallback — primarily the Plan-feature guidance (`170-plan-feature` seed + its prompt) and any other surface naming the CLI mint command — explicitly state that the MCP tools (`wave_new_<kind>` / `wave_create_wave`) are the preferred path and the CLI is a fallback for when the MCP server is unavailable. The legitimate fallback is retained, not removed.

## Scope

**Problem statement:** Minting can return an already-used stem because (a) the MCP paths call `build_id` without `repo_root` so `_existing_prefixes` is never scanned (`server_impl.py:4306`/`:4734`/`:4768`), and (b) `_existing_prefixes` omits ADRs (`lifecycle_id.py:170-189`).

**In scope:**

- Extend `_existing_prefixes` to scan `docs/architecture/decisions/*.md` (ADRs) in addition to plans and waves.
- Pass `repo_root` (the server's `root`) into `build_id` at the three MCP call sites.
- A `discover_repo_root()` fallback in the lifecycle layer when `repo_root` is `None`, so dedup is never silently skipped.
- Unit tests for `_existing_prefixes`/`next_available_prefix` covering ADR collisions and the plans/waves/ADRs union; server-level tests that `new_change` and `create_wave` skip an existing stem.
- An MCP-first reminder printed (to stderr) by the `lifecycle_id.py` CLI entrypoint, steering direct callers to the MCP minting tools (`wave_new_*` / `wave_create_wave`); the CLI remains a fallback and its stdout (the bare ID) is unchanged.
- A doc-level MCP-first reinforcement at the surfaces presenting the `lifecycle_id.py` CLI as a fallback (the Plan-feature seed `170` + prompt, and any other CLI-mint mention) — preferring the MCP tools while keeping the CLI fallback.

**Out of scope:**

- Renumbering the existing duplicate `12tm5` ADRs (data migration with cross-references; tracked as a follow-up, not this fix) — this change prevents NEW collisions.
- Changing the time-bucket encoding scheme (`build_prefix` / `_packed_value`) — only the dedup set and call-site plumbing change.
- ID format, slug validation, or the legacy `00000` path.

## Acceptance Criteria

- [ ] AC-1: `_existing_prefixes(repo_root)` includes prefixes parsed from `docs/architecture/decisions/*.md`; an ID matching an existing ADR stem is skipped by `next_available_prefix`.
- [ ] AC-2: `create_wave` and `new_change` pass `repo_root` so that, given an existing on-disk stem at the current time bucket, the minted wave/change ID is the next available stem — NOT a duplicate. (Regression for the observed `1p44w` collision.)
- [ ] AC-3: A `dry_run`/peek mint and the subsequent `create` mint return the same next-available, collision-free stem (dedup applied on both paths).
- [ ] AC-4: When `repo_root` is not supplied, the lifecycle layer falls back to `discover_repo_root()` and still dedupes (no silent empty-set path) when a repo root is discoverable.
- [ ] AC-5: The dedup set is the union of plans + wave-dir names + in-wave change docs + ADRs; a collision against any one of those locations is avoided.
- [ ] AC-6: Unit + server tests cover AC-1..AC-5; `python3 .wavefoundry/framework/scripts/run_tests.py` is green.
- [ ] AC-7: Invoking `lifecycle_id.py` directly as a CLI prints a reminder on **stderr** to prefer the MCP minting tools (`wave_new_<kind>` / `wave_create_wave`) when the MCP server is available; **stdout** remains the bare minted ID (machine-parseable, no reminder text). A test asserts the reminder is on stderr and stdout is ID-only.
- [ ] AC-8: The Plan-feature guidance (`170-plan-feature` seed + prompt) and any other surface naming the `lifecycle_id.py` CLI mint command state that the MCP tools (`wave_new_<kind>` / `wave_create_wave`) are preferred and the CLI is a fallback when the MCP server is unavailable; the fallback instruction is retained (not removed). docs-lint passes.

## Tasks

- [ ] Extend `_existing_prefixes` (`lifecycle_id.py:170-189`) to glob `docs/architecture/decisions/*.md` and add matching prefixes.
- [ ] Add a `discover_repo_root()` fallback when `repo_root is None` in `next_available_prefix` (or `build_id`) so dedup is consulted by default (AC-4).
- [ ] Pass `repo_root=root` into `build_id` at `server_impl.py:4306` (create_wave), `:4734`, and `:4768` (new_change).
- [ ] Add unit tests: ADR-stem collision avoidance; plans/waves/ADRs union; dry_run↔create consistency.
- [ ] Add server-level tests: `new_change` / `create_wave` skip an existing stem at a fixed time bucket.
- [ ] Note the pre-existing `12tm5` duplicate ADR as a follow-up (renumber out of scope here).
- [ ] Print an MCP-first reminder to stderr from the `lifecycle_id.py` CLI entrypoint (the `__main__`/argparse path, ~`:311`) after minting; keep stdout the bare ID. Test the stderr reminder + clean stdout (AC-7).
- [ ] Reinforce MCP-first in the doc surfaces that present the CLI fallback — the Plan-feature seed (`170-plan-feature.prompt.md`) + its prompt, plus any other CLI-mint mention (grep `lifecycle_id.py` across `docs/` and seeds) — preferring `wave_new_*` / `wave_create_wave`, keeping the fallback (AC-8).
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py`; run `.wavefoundry/bin/docs-lint` on this plan.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| existing-prefixes-adrs | Engineering | — | Add ADR scan + repo-root fallback in `lifecycle_id.py`. |
| call-site-repo-root | Engineering | — | Pass `repo_root` at the three `server_impl.py` `build_id` sites. |
| tests | Engineering | existing-prefixes-adrs, call-site-repo-root | Unit (ADR/union/peek) + server (skip-existing-stem) tests. |


## Serialization Points

- `.wavefoundry/framework/scripts/lifecycle_id.py` — `_existing_prefixes` / `next_available_prefix`; single owner here, but the encoding scheme (`build_prefix`/`_packed_value`) must remain untouched (out of scope).
- `.wavefoundry/framework/scripts/server_impl.py` — `create_wave` (`:4306`) and `new_change` (`:4734`/`:4768`); shared with other 1p44n changes that edit `server_impl.py` (e.g. upgrade-flow changes) — coordinate to avoid clobbering.

## Affected Architecture Docs

N/A — a correctness fix to the lifecycle ID-minting dedup set and its call-site plumbing; no new module boundary, data flow, or verification surface. (The ADR directory it newly reads is an input source, not a new architectural boundary.)

## AC Priority

(Provisional — revisited at Prepare wave.)


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | ADR scanning is the explicit gap called out. |
| AC-2 | required   | The MCP path passing repo_root is the root cause of observed collisions. |
| AC-3 | required   | dry_run↔create consistency prevents preview/create divergence. |
| AC-4 | important  | Fallback hardens any future caller against silent no-dedup. |
| AC-5 | required   | The union semantics is the contract being fixed. |
| AC-6 | required   | Test coverage + green suite. |
| AC-7 | important  | MCP-first nudge (runtime) — steer direct CLI callers back to the governed MCP minting path. |
| AC-8 | important  | MCP-first nudge (docs) — the CLI-fallback surfaces name MCP as preferred; consistent with the runtime nudge. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Fix both halves: pass `repo_root` at MCP call sites AND scan ADRs in `_existing_prefixes`. | The collision has two independent causes; fixing only one still leaves duplicates possible (no-repo_root skips all dedup; missing-ADR misses ADR stems). | Pass repo_root only (still misses ADRs); add ADRs only (MCP path still skips dedup because repo_root is None). |
| 2026-06-08 | The `lifecycle_id.py` CLI emits an MCP-first reminder (stderr) when used directly. | Operator direction: all agents should mint via the MCP tools (`wave_new_*`/`wave_create_wave`), which scaffold the doc and dedup; the CLI is a fallback, so nudge direct callers back to the governed MCP path without breaking machine-parseable stdout. | Silent CLI (misses the chance to steer agents to MCP); make the CLI error/refuse (too aggressive — it's a legitimate offline fallback). |
| 2026-06-08 | Add a `discover_repo_root()` fallback when `repo_root` is None. | Defense in depth — no caller should silently mint without a dedup set; the CLI already discovers the root this way. | Require every caller to pass repo_root (fragile; this bug is exactly a missed call site). |
| 2026-06-08 | Do not renumber the existing duplicate `12tm5` ADRs in this change. | Renumbering an ADR means rewriting cross-references and is a data migration; this fix prevents NEW collisions. Track separately. | Renumber now (scope creep + reference-update risk). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `discover_repo_root()` fallback returns None in odd execution contexts, re-introducing the empty dedup set. | Treat None as "scan what you can"; the explicit-`repo_root` call sites (AC-2) are the primary fix, the fallback is secondary. |
| ADR glob picks up the `template.md` / `README.md` and mis-parses a prefix. | `_PREFIX_RE` only matches a 5-char base36 prefix followed by `-`/space; `template.md`/`README.md` stems don't match, so they're naturally excluded — covered by AC-1 tests. |
| Editing `server_impl.py` collides with other 1p44n changes touching the same file. | Serialization point; the call-site edits are tiny and localized to the two mint functions — sequence and re-verify. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
