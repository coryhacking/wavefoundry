# Generalize review verification protocol to any implementation change

Change ID: `1sq49-enh generalize-review-verification-protocol`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-16

Wave: `1sq4a review-verification-generalization`

## Rationale

Change `1sr0t` (shipped unreleased in 1.13.0) introduced an independent-reference verification rule, but gated it on a **mechanism-type enumeration** — "deterministic transformation, parser, serializer, migration, normalizer, compatibility adapter, or fallback." The intent was a **generic protocol for validating implementation work**, not a parser-specific one. As written, an agent reviewing a feature, an API-surface change, a config-driven change, or a plain bug fix does not see its work in the enumeration and skips the protocol entirely — the opposite of the intent.

The motivating failure (the `1sbfl` review) was correlated verification: the implementation was checked against its own fixtures, and a "second" reviewer inherited the author's briefed hypotheses. That failure mode is universal to verification; it is not a property of parsers. The fix is to lift the trigger from "these mechanism types" to "any implementation change," keeping the deterministic-mechanism cases as the *sharpest-reference examples* rather than the eligibility gate.

Separately, the protocol name "Oracle-diverse verification" collides with the database vendor "Oracle" in a framework/indexing repository. Rename to **"Independent-reference verification,"** which names the mechanism directly with no vendor collision.

Timing: 1.13.0 is built (`pcmr`) but **not released**. This change folds into 1.13.0 before ship so the narrow framing never reaches a release, superseding the wording `1sr0t` introduced in the same version.

## Requirements

1. Rename the protocol from "Oracle-diverse verification" to **"Independent-reference verification"** across seed `209`, carrier seeds `221` (code-reviewer) and `239` (qa-reviewer), the renderer carrier block, and all rendered agent surfaces. No residual use of "oracle-diverse" / "oracle diversity" / `ORACLE_DIVERSITY` as the protocol name.
2. Generalize the seed `209` trigger from the mechanism-type enumeration to **any implementation change** — explicitly covering features, API/tool-surface changes, config-driven changes, and bug fixes, not only deterministic mechanisms.
3. Retain the deterministic-mechanism list (transformation/parser/serializer/migration/normalizer/compatibility-adapter/fallback) as a **"sharpest-reference" sub-clause** (differential against a materially independent implementation, or a spec-derived / metamorphic invariant), not as the eligibility gate.
4. Preserve every load-bearing invariant from `1sr0t`: a same-hypothesis helper or briefed subagent is **not** independent; implementer-authored evidence remains `independent: false` and cannot restore a withdrawn approval; name the reference, the exact promised property, and the plausible common-mode limitation; keep the probe bounded and reproducible; record the narrow limitation when no credible independent reference exists; carrier-presence tests prove propagation, not reviewer adherence.
5. Re-render agent surfaces so the rendered code-reviewer and qa-reviewer carriers match the updated seeds; docs-lint clean.

## Scope

**Problem statement:** A generic implementation-validation protocol shipped gated on a parser/transformation-flavored mechanism enumeration, so most implementation review (features, APIs, config, bug fixes) falls outside its stated trigger. The name also collides with a database vendor.

**In scope (full census, verified against the tree):**

Seeds (edited under `seed_edit_allowed`):
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` — the protocol section (heading, trigger, generalized reference list, retained sharpest-reference sub-clause, invariants).
- `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md` and `.wavefoundry/framework/seeds/239-qa-reviewer.prompt.md` — carrier bullet/section.

Framework scripts + tests (edited under `framework_edit_allowed`):
- `.wavefoundry/framework/scripts/render_agent_surfaces.py` — `ORACLE_DIVERSITY_CARRIER_BLOCK` constant name and body (rename → `INDEPENDENT_REFERENCE_CARRIER_BLOCK`) + the append-site reference.
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py` — assertions on the carrier constant name, the "not oracle diversity" wording, the `Oracle-diverse verification` heading, and the negative security-surface assertion.
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` and `test_setup_wavefoundry.py` — assertions on the rendered `Oracle-diverse verification` heading / trigger string.
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py` — comment + test-method name using the protocol phrasing (behavioral independence logic unchanged).

Hand-authored project docs (direct edit):
- `docs/contributing/review-and-evals.md` — the "Oracle-Diverse Verification" section.
- `docs/architecture/testing-architecture.md` — the contract-table row and the "Oracle-Diverse Review Evidence" section.

Regenerated (NOT hand-edited — re-rendered from the updated seeds/renderer):
- `docs/agents/code-reviewer.md`, `docs/agents/qa-reviewer.md` — rendered carriers; regenerated by `render_agent_surfaces`, verified to match seeds (AC-6).

**Out of scope:**

- The generic "test oracle" testing term of art and the SQL **"Oracle" dialect** references (graph indexer, `test_graph_incremental_merge.py`, SQL-dialect waves, `scan-rules.toml`, chunker) — these are not the protocol name and must not be touched. AC-7's gate targets only the protocol-name forms (`oracle-diver`, `oracle diversity`, `ORACLE_DIVERSITY`).
- The closed `1shv4` wave archive, including `1sr0t-enh oracle-diverse-review-verification.md` — historical closed-wave record; not rewritten. The new name supersedes going forward.
- `CHANGELOG.md` — its only "oracle" is the 1.12.0 SQL dialect; the 1.13.0 section is a release-time deliverable, not this wave.
- Adding a validator/docs-lint check that asserts the protocol was *followed* — capability-/protocol-adherence is reviewer-owned semantics, not a literal-heading validator check (consistent with the `1snq3` and stage-gate precedents). Carrier-presence proves propagation only.
- The `1sbfl` chunker code and its differential generator (already landed; unaffected).
- Severity/classification, credible-threat gate, or any other seed `209` section.

## Acceptance Criteria

- [x] AC-1: The protocol is titled **"Independent-reference verification"** in seed `209`; no occurrence of "Oracle-diverse" / "oracle diversity" / `ORACLE_DIVERSITY` remains as the protocol name in seeds `209`/`221`/`239` or the renderer. (required) — evidence: AC-7 residue gate CLEAN.
- [x] AC-2: Seed `209`'s trigger reads as *any implementation change* and names features, API/tool-surface changes, config-driven changes, and bug fixes as in scope — not only deterministic mechanisms. (required) — evidence: seed 209 lead sentence enumerates "a feature, an API or tool-surface change, a config-driven change, a bug fix, or a deterministic transformation".
- [x] AC-3: The deterministic-mechanism enumeration is retained as a "sharpest-reference" sub-clause (differential / metamorphic / spec), clearly subordinate to the general trigger, not the eligibility gate. (required) — evidence: seed 209 second paragraph "the sharpest reference is a differential … or a … metamorphic invariant".
- [x] AC-4: All `1sr0t` invariants are preserved in intent: same-hypothesis helper/subagent ≠ independent; implementer-authored evidence `independent: false` and cannot restore withdrawn approval; name reference + promised property + common-mode limitation; bounded/reproducible probe; record-limitation-when-none; carrier-presence ≠ adherence. (required) — evidence: all six invariants present in seed 209; `test_review_evidence.py` independence checks green.
- [x] AC-5: Carrier seeds `221` and `239` and the renderer carrier block (renamed `INDEPENDENT_REFERENCE_CARRIER_BLOCK`) are generalized and renamed consistently with seed `209`. (required) — evidence: renderer constant renamed + append-site updated; `test_render_agent_surfaces` green.
- [x] AC-6: Agent surfaces are re-rendered; rendered code-reviewer/qa-reviewer carriers match the updated seeds; the framework test suite is green (the four affected test files updated to the new name/wording, asserting the generalized trigger — not merely deleting coverage); `wave_validate` docs-lint is clean. (required) — evidence: `wf render-surfaces` regenerated both carriers (new name present, zero old); full suite 5,643 OK; docs-lint clean.
- [x] AC-7: A case-insensitive search of live/shipped operational surfaces for the protocol-name forms (`oracle-diver`, `oracle diversity`, `ORACLE_DIVERSITY`) returns no hits. Lifecycle records under `docs/waves/`, `docs/plans/`, and `docs/agents/journals/` are excluded because they retain honest rename history; the SQL "Oracle" dialect and the generic "test oracle" term are excluded because they are not the protocol name. (important) — evidence: bounded live-surface gate returned "CLEAN" over `.wavefoundry/framework/` and `docs/` with those lifecycle-record exclusions.
- [x] AC-8: The hand-authored `docs/contributing/review-and-evals.md` and `docs/architecture/testing-architecture.md` sections are renamed and generalized to match seed `209` (generic trigger, sharpest-reference sub-clause, invariants preserved). (required) — evidence: both sections rewritten; docs-lint clean.

## Tasks

- [x] Rewrite the seed `209` protocol section: rename heading, generalize the trigger, add the generic independent-reference list, demote the mechanism enumeration to a sharpest-reference sub-clause, keep the invariants.
- [x] Update seed `221` code-reviewer bullet and seed `239` qa-reviewer section to match (rename + generalized trigger).
- [x] Rename `ORACLE_DIVERSITY_CARRIER_BLOCK` → `INDEPENDENT_REFERENCE_CARRIER_BLOCK` and rewrite its body; update the reference at the append site.
- [x] Update the four affected test files (`test_render_agent_surfaces.py`, `test_upgrade_wavefoundry.py`, `test_setup_wavefoundry.py`, `test_review_evidence.py`) to the new name/wording and assert the generalized trigger.
- [x] Rename + generalize the hand-authored `docs/contributing/review-and-evals.md` and `docs/architecture/testing-architecture.md` sections.
- [x] Re-render agent surfaces; confirm rendered carriers match seeds.
- [x] Grep live/shipped operational surfaces case-insensitively for protocol-name residue (`oracle-diver`/`oracle diversity`/`ORACLE_DIVERSITY`), excluding lifecycle records that preserve rename history.
- [x] `wave_validate` clean; framework test suite green.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seed-rewrite | framework | — | Seeds 209/221/239 under `seed_edit_allowed`; serialize on each seed file |
| renderer-and-surfaces | framework | seed-rewrite | Rename carrier constant + re-render; depends on final seed wording |
| verify | framework | renderer-and-surfaces | Grep residue, docs-lint, test suite |


## Serialization Points

- Seed files under `.wavefoundry/framework/seeds/` — edited only under the `seed_edit_allowed` gate.
- `render_agent_surfaces.py` — the carrier constant must match the seed wording before re-render.

## Affected Architecture Docs

`N/A` — this is review-protocol prose carried in seeds and rendered agent surfaces. No architecture boundary, layering, data/control-flow, or verification-topology change. (Any `docs/architecture/*` that merely *names* the protocol is updated as an in-scope doc reference, not an architecture change.)

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Vendor-collision rename is the operator's explicit ask |
| AC-2 | required | The core intent correction — generic trigger |
| AC-3 | required | Preserves the concrete deterministic tooling without re-narrowing the gate |
| AC-4 | required | Load-bearing anti-correlation invariants must not regress |
| AC-5 | required | Carriers must not drift from seed 209 |
| AC-6 | required | Rendered surfaces are the operating contract; tests must track the rename, not drop coverage |
| AC-7 | important | Case-insensitive rename hygiene per framework rename gate (protocol-name forms only) |
| AC-8 | required | Hand-authored contributing/architecture docs must not drift from seed 209 |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-16 | Change doc authored; intent-correction of `1sr0t` scope + rename | This doc |
| 2026-07-16 | Code-grounded census expanded scope: added `docs/contributing/review-and-evals.md`, `docs/architecture/testing-architecture.md`, and four test files (render/upgrade/setup/review_evidence); added AC-8; refined AC-7 to protocol-name forms; confirmed CHANGELOG + SQL-dialect + test-oracle jargon out of scope | `grep -rniE "oracle[- ]diver\|ORACLE_DIVERSITY"` census |
| 2026-07-16 | Implemented all 8 ACs: seed 209 rewritten (generic trigger + sharpest-reference sub-clause + invariants), seeds 221/239 + renderer constant renamed, four test files updated, two hand-authored docs generalized, surfaces re-rendered. One render-test assertion normalized for the new line-wrap (phrase-presence intent preserved, matching the sibling `" ".join(...)` pattern) | Full suite 5,643 OK; AC-7 residue gate CLEAN; docs-lint clean; rendered carriers carry new name, zero old |
| 2026-07-16 | Delivery review corrected AC-7's impossible census boundary: the current change record legitimately names the retired protocol while explaining the rename, so lifecycle/history records are now explicitly outside the live/shipped-surface residue proposition. No product surface was changed by this correction. | Direct case-insensitive census of `.wavefoundry/framework/` and `docs/` excluding `docs/waves/**`, `docs/plans/**`, and `docs/agents/journals/**`: zero protocol-name hits |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-16 | Fold into unreleased 1.13.0, superseding `1sr0t` wording | Avoid shipping the narrow framing in a release | Ship narrow, broaden in 1.13.1 (rejected — ships known-narrow intent) |
| 2026-07-16 | Rename to "Independent-reference verification" | "Oracle" collides with the DB vendor in an index-heavy repo | Keep "oracle" (testing term of art) — rejected per operator |
| 2026-07-16 | No validator adherence check | Protocol adherence is reviewer semantics, not a literal-heading check | Add lint check (rejected — bypassable + over-strict, per `1snq3` precedent) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Rename leaves stale references in rendered operational surfaces or current framework docs | AC-7 case-insensitive live/shipped-surface grep gate; lifecycle records remain honest history |
| Generalizing dilutes the concrete deterministic guidance | AC-3 retains the mechanism enumeration as a sharpest-reference sub-clause |
| Carrier drift from seed 209 | Re-render from seeds; AC-6 compares rendered vs seed |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
