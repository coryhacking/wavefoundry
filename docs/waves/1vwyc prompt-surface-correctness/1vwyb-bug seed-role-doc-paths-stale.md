# Six seed citations name role docs at paths that do not resolve

Change ID: `1vwyb-bug seed-role-doc-paths-stale`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-21
Wave: 1vwyc prompt-surface-correctness

## Rationale

Six citations across two seeds name role documents at `docs/agents/<name>.md` when the file lives at
`docs/agents/specialists/<name>.md`. A repository materializing a prompt doc from those seeds gets a
broken path, and the agent told to read that role doc cannot open it.

The census was re-derived independently by two prepare-council seats across two rounds and is exact:
20 distinct `docs/agents/*.md` paths cited across the seed corpus, 15 resolve, 5 do not.

| Seed | Line | Cited | Actual |
| --- | ---: | --- | --- |
| `160-upgrade-wavefoundry.prompt.md` | 178 | `docs/agents/wave-council.md` | `docs/agents/specialists/wave-council.md` |
| `160-upgrade-wavefoundry.prompt.md` | 179 | `docs/agents/archetype-council.md` | `docs/agents/specialists/archetype-council.md` |
| `160-upgrade-wavefoundry.prompt.md` | 490 | `docs/agents/wave-council.md` | `docs/agents/specialists/wave-council.md` |
| `160-upgrade-wavefoundry.prompt.md` | 491 | `docs/agents/archetype-council.md` | `docs/agents/specialists/archetype-council.md` |
| `160-upgrade-wavefoundry.prompt.md` | 517 | `docs/agents/wave-council.md` | `docs/agents/specialists/wave-council.md` |
| `237-council-review.prompt.md` | 71 | `docs/agents/wave-council.md` | `docs/agents/specialists/wave-council.md` |

Two roles are repaired: `wave-council` (4 occurrences) and `archetype-council` (2).

**Two further occurrences are NOT stale and must not be repointed.** Seed-160 lines 191 and 489 read
`` `docs/agents/specialists/red-team.md` (or `docs/agents/red-team.md`) ``: a deliberate both-layouts
accommodation. Blind repointing produces the nonsense "(or `docs/agents/specialists/red-team.md`)",
and it would silently retire the framework's existing answer to whether a target may keep the flat
layout. That accommodation is either kept or retired by explicit decision, not by a typo fix.

**Two references resolve to no file here and are correct as written.** `docs/agents/product-owner.md`
(seeds `170`, `190`) exists in product repositories at the core tier and is absent here because this
repository has no product implementation source. `docs/agents/data-engineer.md` (seed `160`) is
declared conditional by seed-160 lines 188 and 488, with `seed-224` backing it.

### Scope discipline: this change repoints citations and nothing else

Three larger designs were attached to this defect across two council rounds and all three were
blocked on evidence. They are recorded here so they are not re-attempted casually:

- **A role-doc tier model in `docs_lint.py`** duplicated `agent_surface_integrity.canonical_role_paths()`,
  which already derives that map from `REVIEW_POLICY_CARRIER_REGISTRY` and shipped in wave `1vgep`.
  `test_audit_follows_a_registry_destination_change` exists to forbid a parallel role-path list.
- **A `_RETIRED_CONTENT_PATTERNS` tombstone** was the wrong mechanism: that table matches strings
  inside scanned file contents and cannot express a predicate about which files exist on disk.
- **A seed role-doc resolver check** was blocked as underdetermined. The plan simultaneously required
  every cited path to resolve and required the flat-layout accommodation to keep citing a path that
  does not resolve. A both-layouts-tolerant resolver satisfies every acceptance criterion while
  catching none of the six defects it exists to prevent. The recurrence guard is real and wanted, but
  it needs its own design pass with the accommodation question settled first. Deferred, not dropped.

## Requirements

1. Repoint the 6 stale citations to the paths where the files actually live.
2. Leave seed-160 lines 191 and 489 unchanged, or change them with the flat-layout decision recorded.
   Silent modification is not acceptable either way.
3. Do not modify any file under `docs/prompts/` or `docs/waves/`. The materialized twins already carry
   correct paths; the seeds are the stale side.

## Scope

**Problem statement:** six seed citations name role docs at paths that do not resolve, so freshly
materialized prompt docs carry broken references.

**In scope:**

- The 6 stale citations in seeds `160` and `237`.
- The flat-layout accommodation decision for seed-160 lines 191 and 489.

**Out of scope:**

- Any recurrence-prevention check. Deferred with its reasons recorded above.
- Any change to `agent_surface_integrity`, its advisory status, or its upgrade wiring.
- The cross-tier `docs/agents/frontend-developer.md` pair (146 lines, `Category: build`) versus
  `docs/agents/specialists/frontend-developer.md` (64 lines, `Category: specialist`). Both exist with
  different content, and `frontend-developer` has no `REVIEW_POLICY_CARRIER_REGISTRY` entry so the
  shipped audit cannot see it. Recorded as an observation for a future change; the sibling
  cross-references in the `specialists/` copy point to `accessibility-auditor` and `backend-architect`,
  which both exist in that directory, so the likeliest reading is two distinct roles sharing a name
  rather than a duplicate. Not decided here.

## Acceptance Criteria

- [x] AC-1: The 6 cited paths in the Rationale table read `docs/agents/specialists/<name>.md`.
- [x] AC-2: Every `docs/agents/*.md` path cited anywhere in seeds `160` and `237` that names a role
      present in `agent_surface_integrity.canonical_role_paths()` equals that role's canonical
      destination, except the two accommodation sites, which are checked against AC-3.
- [x] AC-3: Seed-160 lines 191 and 489 are byte-identical to their pre-change state, or changed with
      the flat-layout decision recorded in the Decision Log.
- [x] AC-4: No file under `docs/prompts/` or `docs/waves/` is modified, verified by digesting all 41
      files under `docs/prompts/` and all 236 wave records before and after.
- [x] AC-5: `wf docs-lint` passes, and `agent_surface_integrity.audit_agent_surfaces()` reports the
      same `finding_count` before and after, confirming no agent-surface behavior moved.

## Tasks

- [x] Open the seed gate: `wf_open_gate(gate="seed_edit_allowed")`.
- [x] Repoint the 6 citations in seeds 160 and 237.
- [x] Decide the flat-layout accommodation for lines 191 and 489; record it in the Decision Log.
- [x] Close the seed gate immediately after: `wf_close_gate(gate="seed_edit_allowed")`.
- [x] Run the AC-4 digests and the AC-5 checks before and after.

## Agent Execution Graph


| Workstream        | Owner       | Depends On        | Notes |
| ----------------- | ----------- | ----------------- | ----- |
| repoint-citations | implementer | :                 | 6 occurrences, 2 seeds, behind the seed gate. |
| verification      | qa          | repoint-citations | Digests, docs-lint, and the audit finding-count comparison. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/237-council-review.prompt.md`

## Affected Architecture Docs

`N/A`. This change edits citation strings inside seed prose. No code, no mechanism, no boundary,
no ownership, no control flow, and no verification behavior changes.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The defect itself. |
| AC-2 | required  | Catches a repoint that lands on the wrong destination, using the shipped canonical map as the oracle rather than a hand-copied list. |
| AC-3 | required  | The accommodation is a policy answer, not a typo. Retiring it silently would be a policy change disguised as a fix. |
| AC-4 | required  | A seed edit must not touch rendered twins or wave records; both were sites of accidental damage earlier in this wave. |
| AC-5 | important | Confirms nothing in the agent-surface machinery shifted, since three earlier cuts of this change proposed touching it. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-21 | Census measured and independently re-derived twice. | 20 distinct paths, 15 resolve, 5 do not; 6 repointable occurrences at seed-160 lines 178, 179, 490, 491, 517 and seed-237 line 71. Both council rounds reproduced it exactly. |
| 2026-08-21 | Worklist corrected from 8 to 6. | Seed-160 lines 191 and 489 are both-layouts accommodations, not stale citations. |
| 2026-08-21 | Scope cut to citations only after a second prepare-council BLOCK. | The tier model duplicated shipped `1vgep` machinery; the tombstone used a mechanism that matches text rather than file existence; the resolver was underdetermined against its own accommodation requirement. |
| 2026-08-21 | Six citations repointed behind the seed gate; gate closed immediately after. | Seed-160 lines 178, 179, 490, 491, 517 and seed-237 line 71 now read `docs/agents/specialists/<name>.md`; accommodation lines 191 and 489 hash-identical pre/post (sha256 `b2917af0`). |
| 2026-08-21 | All five ACs verified. | AC-2: 26 citations naming canonical roles checked against `canonical_role_paths()`, 0 violations, 4 accommodation-site mentions excluded. AC-4: 41 prompt files and 1196 wave-tree files (all 236 wave records) digest-identical across the seed edit, compared before any bookkeeping write to this doc. AC-5: docs-lint ok; `audit_agent_surfaces()` finding_count 0 before and 0 after. Full suite 7464 tests across 64 files OK with `--no-cache`. |
| 2026-08-21 | Gapfill: shell used for the line-addressed seed edits, the digest sweeps, and the test-pin grep. | Bulk-mechanical docs-only edits; tests are excluded from the semantic index so `code_keyword` cannot see them. The only flat-path hits in scripts or tests are a synthetic temp-tree fixture in `test_review_policy.py` (lines 193 and 236) that writes its own file. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------- | ------------ |
| 2026-08-21 | Fix the seeds, not the rendered twins. | The twins already carry correct paths; the seeds are the stale side. Editing twins hides the defect and leaves fresh materializations broken. | Repoint twins (rejected: helps nobody downstream); move files back to flat (rejected: `specialists/` is the framework-emitted layout). |
| 2026-08-21 | `product-owner` and `data-engineer` citations do not change. | Both are conditional roles, correct as written. `product-owner` exists in product repositories; `data-engineer` is declared conditional by seed-160 lines 188 and 488. | Delete or repoint them (rejected: they are not misplaced). |
| 2026-08-21 | Defer the recurrence guard rather than cut it a fourth time. | Three designs were blocked in one session: a duplicate of shipped machinery, a mechanism that cannot express the predicate, and a resolver that satisfies its ACs while catching none of the defects. The guard is wanted; the evidence says it needs its own design pass with the accommodation question settled first. | Ship a resolver now (rejected: the blocked design would be blind to all six defects); drop the guard permanently (rejected: without it this recurs on the next role-doc move). |
| 2026-08-21 | Keep the flat-layout accommodation at seed-160 lines 191 and 489 unchanged. | The accommodation is the framework's stated support for targets keeping the flat `docs/agents/red-team.md` layout; retiring it is a policy change with its own blast radius, and it is the first input the deferred recurrence-guard design pass needs settled. | Retire it now (rejected: a silent policy change riding a typo fix, exactly what AC-3 forbids). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A target genuinely using the flat layout is broken by the repoint. | AC-3 forces the accommodation decision to be explicit rather than incidental. Seed-160 lines 191 and 489 remain the framework's stated support for that layout unless deliberately retired. |
| Without a recurrence guard, the next role-doc move reintroduces this drift. | Accepted and recorded. Two independent councils found the drift by hand, and the deferred guard carries the reasons the three rejected designs failed so a future pass does not repeat them. |
| Editing seed-160 damages a marker-fenced region. | Seeds 160 and 237 carry no marker fence at or near the edit sites; seed-160's only `<!--` is backticked prose describing fences. This is not a universal claim: seed-030 line 105 carries a real `wave:repo-index-modules` fence and is not touched here. |
| A repoint lands on a path that is itself wrong. | AC-2 checks each repointed citation against `canonical_role_paths()` rather than against a hand-copied destination. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
