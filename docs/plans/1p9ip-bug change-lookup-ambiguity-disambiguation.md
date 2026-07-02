# Change and wave lookups silently collapse colliding IDs; both must return all matches and stay namespace-separate

Change ID: `1p9ip-bug change-lookup-ambiguity-disambiguation`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-02
Wave: TBD

## Rationale

Lifecycle IDs can collide in real life: two agents on parallel branches mint from the same time-ordered counter and can produce the same short ID before either lands. That is exactly what happened landing wave `1p9hn` — its `1p9hh-bug windows-stdout-purity` change reused the short ID of the already-merged `1p9hh-bug python3-prereq-stop` change. The filename slug disambiguates the two on disk, but the bare-ID lookups do not.

Both the change and wave resolvers mishandle a bare ID that matches more than one record, in opposite but equally wrong ways:

- **Change lookup — silently returns the first match.** `get_change(root, change_id_prefix)` (`server_impl.py:2448`) substring-matches the prefix against every `*.md` stem under `docs/plans/` and `docs/waves/` and **returns the first hit, then stops**. When two change docs share an ID prefix it returns whichever the walk reaches first and hides the other. Before the `1p9hh` collision was renumbered, `wave_get_change(change_id="1p9hh")` returned *windows-stdout-purity* and shadowed *python3-prereq-stop* — a caller asking for a known ID got a confidently wrong answer with no signal a second match existed.
- **Wave lookup — silently returns nothing.** `_find_wave_md(root, wave_id_or_prefix)` (`server_impl.py:4490`) collects every `*/wave.md` whose parsed `wave_id` contains the token, then returns `None` when the count is not exactly 1. An ambiguous wave query therefore reads as "not found" — the ambiguity is hidden just as thoroughly, only in the other direction.

Both must instead surface every match and let the caller disambiguate by slug/path. The list primitive already exists on the change side — `_resolve_change_doc_matches` (`server_impl.py:4515`) returns all matching change docs (path, canonical ID, content) — it simply is not used by the single-lookup path. The wave side has no list-returning variant yet.

Two invariants across both resolvers:

1. **No silent collapse** — a bare-ID lookup matching more than one record returns *all* matches, never one arbitrary pick and never a bare "not found".
2. **Namespace separation** — a change lookup returns only changes; a wave lookup returns only waves. A token shared between a wave ID and a change ID (e.g. wave `1p9hi` vs. change `1p9hi-bug windows-oskill-liveness-regression`) must never cross-resolve.

## Requirements

1. **Change lookup** (`wave_get_change(change_id=X)` single mode) resolves through the list-returning matcher: **0** matches → `not_found` (as today); **exactly 1** → the single change in `data.change` (unchanged, backward compatible); **>1** → every match in `data.changes` (canonical change ID, repo-relative path, content each), `data.change` set to `null`, plus an `ambiguous_change_id` diagnostic naming the candidate IDs and paths. Never return the first match as if it were unique.
2. **Wave lookup** (the resolver behind `wave_get_change(wave_id=X)` bulk mode, the `wavefoundry://wave/{wave_id}` resource template, and any other wave-by-id consumer) resolves symmetrically: **0** → `not_found`; **exactly 1** → the single wave (unchanged); **>1** → every matching wave (wave ID, repo-relative `wave.md` path, and its admitted-change summary) plus an `ambiguous_wave_id` diagnostic. It must stop returning `None`/"not found" when multiple waves match.
3. **Namespace separation.** Change resolution searches change docs only — `wave.md` files are excluded so a change lookup can never return a wave record. Wave resolution searches `wave.md` records only and never begins matching change docs.
4. **Token-anchored matching.** Matching is anchored to the leading ID segment (the `id[-kind]` token) of the filename/canonical ID, not a loose substring anywhere in the stem, so a query equal to a full ID does not spuriously match a doc whose slug merely contains the token. Partial-ID prefix lookups remain supported and, when they fan out to multiple records, follow requirements 1–2.
5. **Caller migration.** Every caller of `get_change` and `_find_wave_md` is audited and migrated to the list-aware resolvers (or a single-result wrapper that annotates/raises on ambiguity rather than silently dropping matches), so no other tool, resource, or prompt path re-introduces silent collapse.

## Scope

**Problem statement:** The single-record lookups collapse multiple ID matches — the change resolver to the first hit, the wave resolver to `None` — hiding real collisions; and change matching walks the whole `docs/waves/` tree without excluding `wave.md`, blurring the wave/change namespace boundary.

**In scope:**

- Change single-lookup routed through `_resolve_change_doc_matches` with the 0/1/many contract.
- A symmetric list-returning wave resolver with the same 0/1/many contract, wired into the wave-by-id consumers.
- Exclude `wave.md` from change matching; keep wave matching to `wave.md` only.
- Token-anchored matching on both sides.
- Audit and migrate all `get_change` and `_find_wave_md` callers.
- Regression tests for every case.

**Out of scope:**

- Changing the ID minting scheme or preventing cross-branch collisions at mint time (slugs + these lookups make collisions safe to observe and resolve).
- Renumbering existing colliding changes (handled per-instance during landing; the `1p9hh`→`1p9io` renumber for wave `1p9hn` is already done).

## Acceptance Criteria

- [ ] AC-1: `wave_get_change(change_id=X)` with two change docs matching X returns both in `data.changes` (canonical ID + path + content each), `data.change` is `null`, and an `ambiguous_change_id` diagnostic lists the candidates.
- [ ] AC-2: `wave_get_change(change_id=X)` with exactly one match returns that change in `data.change` unchanged; zero matches returns the existing `not_found` diagnostic.
- [ ] AC-3: A wave-by-id lookup with two waves matching the token returns both (wave ID + `wave.md` path + admitted-change summary each) plus an `ambiguous_wave_id` diagnostic; exactly one match returns the single wave unchanged; zero returns `not_found` (never a silent `None`).
- [ ] AC-4: A change lookup for a token that is also a wave ID returns only the change doc(s); the wave lookup for that token returns only the wave(s). Neither cross-resolves.
- [ ] AC-5: `wave.md` files are excluded from change matching (fixture: a wave record whose body contains the queried change-ID token is not returned by the change lookup).
- [ ] AC-6: Matching is anchored to the ID token — a query equal to a full ID does not match an unrelated doc whose slug merely contains that token; partial-prefix lookups still match and, when multiple, return the list.
- [ ] AC-7: Every remaining caller of `get_change` and `_find_wave_md` is migrated (verified by a guard test or grep assertion that the first-match-wins / None-on-ambiguity forms are no longer reachable from a tool/resource handler).
- [ ] AC-8: Full framework suite passes; docs-lint clean.

## Tasks

- [ ] Add a change single-result-with-ambiguity resolver over `_resolve_change_doc_matches` — excludes `wave.md`, token-anchored.
- [ ] Add a symmetric list-returning wave resolver (matching-waves list) alongside `_find_wave_md`; token-anchored, `wave.md`-only.
- [ ] Wire `wave_get_change` (both modes), the `wavefoundry://wave/{wave_id}` resource, and other wave/change-by-id consumers to the new resolvers; shape `data.changes` / matching-waves + the two `ambiguous_*` diagnostics.
- [ ] Audit and migrate all `get_change` and `_find_wave_md` callers; remove or quarantine the first-match-wins / None-on-ambiguity forms.
- [ ] Add regression tests: colliding change IDs → list; colliding wave IDs → list; wave-ID/change-ID shared token → correct namespace both directions; single match → unchanged both sides; `wave.md`-excluded fixture; token-anchoring fixture.
- [ ] Run the full framework suite and docs-lint.

## Agent Execution Graph


| Workstream        | Owner       | Depends On          | Notes |
| ----------------- | ----------- | ------------------- | ----- |
| change-resolver   | implementer | —                   | List-aware, namespace-scoped, token-anchored change resolver. |
| wave-resolver     | implementer | —                   | Symmetric list-returning wave resolver. |
| tool-wiring       | implementer | change-resolver, wave-resolver | `wave_get_change` (both modes) + `wave/{id}` resource response shapes + `ambiguous_*` diagnostics. |
| caller-migration  | implementer | change-resolver, wave-resolver | Audit and migrate all `get_change` / `_find_wave_md` callers. |
| tests             | implementer | tool-wiring, caller-migration | Regression coverage for AC-1..AC-7. |


## Serialization Points

- `server_impl.py` resolver functions (`get_change`, `_resolve_change_doc_matches`, `_find_wave_md`, new wave list resolver) and the `wave_get_change` handler + `wave/{id}` resource are the shared surface; resolvers land before tool-wiring and caller-migration.

## Affected Architecture Docs

N/A — confined to the change/wave lookup functions in `server_impl.py`, their tool/resource handlers, and tests. No module boundary, data-flow, or verification-architecture change; the MCP contracts gain an additive `data.changes` / matching-waves list on the ambiguous path without altering the single-match shapes.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Core fix: no silent shadowing of colliding change IDs. |
| AC-2 | required | Backward compatibility for the common single-change path. |
| AC-3 | required | Symmetric fix for the wave resolver's silent None-on-ambiguity. |
| AC-4 | required | Namespace separation is the operator-stated invariant. |
| AC-5 | required | Enforces the change/wave namespace boundary concretely. |
| AC-6 | important | Prevents loose-substring false matches. |
| AC-7 | required | Ensures no other path re-introduces silent collapse. |
| AC-8 | required | Behavior locked by the suite. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-02 | Change scoped from the `1p9hh` collision observed landing wave `1p9hn`. Change resolver first-match-wins at `server_impl.py:2448` (`get_change`); list primitive `_resolve_change_doc_matches` at `:4515` unused on that path; wave resolver `_find_wave_md` at `:4490` returns `None` on multiple matches (needs a symmetric list variant). | Operator request; code read. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-02 | Both resolvers return all matches on ambiguity rather than one-pick (change) or None (wave). | Slugs already disambiguate on disk; non-silent, symmetric lookups are the durable, minting-scheme-agnostic fix. Per-instance renumbering still handles a specific landing. | Guarantee global ID uniqueness at mint across branches (heavier; does not help already-merged history). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A caller assumes a single return and breaks on the new list shape. | AC-7 audits and migrates all callers; single-match paths keep the existing shapes. |
| Token-anchoring changes which docs a partial-prefix query matches. | Preserve prefix lookups explicitly; fixtures assert both full-ID and partial-prefix behavior. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
