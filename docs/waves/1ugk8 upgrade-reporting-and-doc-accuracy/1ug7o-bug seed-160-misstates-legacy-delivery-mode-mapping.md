# Four Doc Surfaces Tell Downstream Projects the Upgrade Sets universal Review When It Sets targeted

Change ID: `1ug7o-bug seed-160-misstates-legacy-delivery-mode-mapping`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-04
Wave: `1ugk8 upgrade-reporting-and-doc-accuracy`

## Rationale

Surfaced by the docs-contract lane during wave 1uf65 (it read the whole seed-160 sentence that
1uf69 appended to) and verified by executing the mapping:

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md:518` states the upgrade "maps
  legacy enabled review to `universal` and disabled review to `disabled`".
- `docs/contributing/build-and-verification.md:181` states "legacy enabled projects become
  `wave_review.delivery_mode=universal`".

The readiness council found TWO more living carriers of the same false `universal` claim that
the original census missed:

- `docs/references/project-overview.md:102` states "The framework ships `wave_review.enabled:
  true` and `delivery_mode: universal` by default." This is the fresh-install default rather
  than the legacy mapping, but it is the same wrong mode on the same axis, and it sits in the
  Tier-1 startup doc that `AGENTS.md` lists as read-first. Its two sibling carriers were already
  corrected (`feature-wave-lifecycle-overview.md:66` and `review-and-evals.md:90` both say
  `targeted`), so this one is straggler drift.
- `docs/architecture/decisions/1tsbu-adr review-policy-and-upgrade-protocol.md:13` states
  "Fresh and legacy-enabled installs remain `universal`; legacy-disabled installs become
  `disabled`" with `Status: accepted` and no superseded-by marker. It was accurate when written;
  wave 1u7dq's `1u8jb-enh risk-tiered-delivery-review` later flipped the default and the ADR was
  never amended.

Executed against the current tree, `migrate_wave_review_policy({'enabled': True})` returns
`{'enabled': True, 'delivery_mode': 'targeted'}` and `{'enabled': False}` returns
`{'enabled': False, 'delivery_mode': 'disabled'}` (`review_policy.py:21`,
`FRESH_INSTALL_DELIVERY_MODE = "targeted"`). The disabled half is correct in every surface; only
the enabled half and the fresh-install default are wrong.

The claim is load-bearing for downstream operators: `universal` means every wave takes a full
Council review, `targeted` means full Council only for upgrade/release, trust-boundary, and
cross-platform work. A target-repo agent reading any of these surfaces would tell its operator the
upgrade configured heavier review than it did. The canonical statement is already correct
(`review_policy.py:100-102` `UPGRADE_POLICY_BLOCK` and its rendered mirror
`docs/prompts/upgrade-wavefoundry.prompt.md:252-253` both say `delivery_mode=targeted`), so this
is drift in secondary carriers, not a contract question.

Two prepare lanes independently re-ran the census and confirmed there is NO fifth living carrier
of the false claim, and both flagged that `universal` is a live legal enum value whose legitimate
occurrences must NOT be "corrected". An independent reverifier then MEASURED them over
Requirement 4's exact scope: **64 occurrences across 28 files**, comprising correct mode
enumerations (`docs/references/dashboard-adapter-model.md:75`, `docs/prompts/index.md:76`,
`seeds/007-review-system-overview.md:17`, `docs/contributing/review-and-evals.md:90`,
`docs/contributing/feature-wave-lifecycle-overview.md:66`) and unrelated English uses of the word
("universal specialist", "universal_claim", "universal fallback", "universal meta-review") spread
across the seeds and several framework scripts. The reverifier executed Requirement 4's patterns
over that corpus: they hit exactly the three in-scope carriers with **zero** false positives.

The one genuine trap, and the only in-scope occurrence a slightly looser pattern would catch, is
`server_impl.py:2536`'s `"delivery_mode": "universal"` fail-closed default on malformed policy.
That is the negative control worth naming; the other 63 are safe by construction under
claim-keying.

Pre-existing; not introduced by any change in wave 1uf65.

## Requirements

1. **Every carrier states the delivered mapping:** legacy enabled becomes
   `delivery_mode=targeted`, legacy disabled becomes `delivery_mode=disabled`, and the
   fresh-install default is `targeted`. Prefer wording that agrees with the canonical
   `UPGRADE_POLICY_BLOCK` sentence rather than inventing a third phrasing.
2. **The canonical block and its rendered mirror stay untouched** (already correct; verified
   `review_policy.py:100-102` and `docs/prompts/upgrade-wavefoundry.prompt.md:252-253`).
3. **All four living carriers are corrected, and the ADR is AMENDED rather than rewritten:**
   seed-160:518, `build-and-verification.md:181`, and `project-overview.md:102` state the
   delivered modes; `1tsbu-adr:13` gains an inline amendment note in this repository's
   established convention, verified at
   `docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md:27`
   (`> **Amendment (wave 1tj0l):** ...`), preserving the original decision text as history.
   Closed-wave archives keep their text untouched.
4. **The census becomes a durable pin, not a one-time grep, and it keys on the CLAIM rather than
   the word.** A bare `universal` token sweep is unsatisfiable (see the negative-control set in
   the Rationale). Add the pin to `test_events_only_residue_census.py`, which is the
   purpose-built precedent: its `_census_files()` (`:322-352`) already builds exactly the needed
   scope (shipped `scripts/*.py` excluding tests, `framework/{seeds,install,dashboard}`,
   `docs/{prompts,specs,contributing}/**.md`, top-level-only `docs/architecture/*.md` and
   `docs/agents/*.md`), with `docs/waves/` and `docs/plans/` excluded by construction, and its
   `PREIMPLEMENTATION_GATE_ALLOWANCES` (consumed at `:300-319`) is the allowance-table shape this
   needs. Two scope corrections are required: ADD `docs/references/` (where
   `project-overview.md:102` lives, not currently in scope) and KEEP
   `docs/architecture/decisions/` excluded (Requirement 3 deliberately preserves the ADR's
   original `universal` text under an amendment note). Forbid THREE claim-shaped forms
   (`delivery_mode=universal`, `delivery_mode: universal`, ``enabled review to `universal` ``)
   with expected counts of zero after the fix, each allowance carrying a non-empty justification,
   so a NEW occurrence trips while legitimate uses stay untouched. A fourth candidate,
   ``remain `universal` ``, is deliberately EXCLUDED: its only occurrence in the repository is
   `1tsbu-adr:13`, which Requirement 3 keeps outside census scope, so the pattern could never fire
   before or after the fix. `test_review_policy.py:349` is NOT the home: that module reads
   `review_policy.UPGRADE_POLICY_BLOCK` constants only and never touches the filesystem, and it
   has no census scaffolding.
5. **Seed-160's edit is gated** (`seed_edit_allowed`) and leaves the rest of that bullet,
   including 1uf69's no-op qualifier, byte-identical apart from the corrected clause. The clause
   that must survive verbatim is `(a no-op migration marks nothing and rewrites no wave)`. Note
   the canonical block carries a SHORTER variant, `(a no-op migration marks nothing)`, so
   converging on the canonical wording must not overwrite the seed's longer clause.

## Scope

**Problem statement:** four living doc surfaces name the wrong delivery mode, promising downstream
operators a heavier review posture than the upgrade configures.

**In scope:** seed-160:518 (gated), `docs/contributing/build-and-verification.md:181`,
`docs/references/project-overview.md:102`, an amendment note on `1tsbu-adr:13`, and the new
census pin in `test_events_only_residue_census.py`. `CHANGELOG.md` is a shared serialization
point: 1uf68 implements first and creates the `## [Unreleased]` section; this change APPENDS to it.
Seed-160 is also shared: 1uf68 edits `:49` and `:85` of the same file and runs first.

**Out of scope:** the mapping behavior itself (correct); the canonical block and rendered mirror
(already correct, and actively guarded by `test_review_policy.py:349`); closed-wave archives;
`docs/architecture/decisions/` as census scope (Requirement 3 preserves the ADR text
deliberately); the legitimate mode enumerations and English uses listed in the Rationale; whether
`targeted` is the right default (settled by wave 1u7dq); rewriting the ADR's original decision
text (amended inline instead).

## Acceptance Criteria

- [x] AC-1: `build-and-verification.md:181` and seed-160:518 state `targeted` for legacy enabled
  and `disabled` for legacy disabled, and `project-overview.md:102`'s first clause ("ships
  `wave_review.enabled: true` and `delivery_mode: universal` by default") states `targeted`. The
  clause "every wave in `universal`, risk/receipt-selected waves in `targeted`" later on that same
  line legitimately uses `universal` as a mode name and must not be touched. All three converge on
  the canonical block's wording.
- [x] AC-2: `1tsbu-adr:13` carries an inline amendment note in the convention at
  `1p7pb-adr native-windows-distribution-model.md:27`, with its original decision text preserved.
- [x] AC-3: A census shows no living surface claiming the `universal` mapping or default; the
  canonical block, its rendered mirror, and 1uf69's `(a no-op migration marks nothing and rewrites
  no wave)` qualifier in the same seed-160 bullet are byte-unchanged apart from the corrected
  clause.
- [x] AC-4: The census pin lives in `test_events_only_residue_census.py` with
  `docs/references/` added to scope and `docs/architecture/decisions/` still excluded, keys on the
  three claim-shaped patterns rather than the bare word, and is shown red against a planted
  reintroduction while staying green across the whole in-scope corpus, `server_impl.py:2536`'s
  fail-closed default included.
- [x] AC-5: Docs-lint passes and the full framework suite passes.

## Tasks

- [x] Correct seed-160:518 under the gate; correct build-and-verification.md:181 and
  project-overview.md:102's first clause; add the ADR amendment note
- [x] Add the three-pattern census pin to test_events_only_residue_census.py, extending
  `_census_files()` scope with `docs/references/`; prove it red against a planted reintroduction
  and green across the in-scope corpus
- [x] Verify the untouched surfaces (canonical block, rendered mirror, 1uf69 qualifier,
  project-overview.md:102's mode-name clause)
- [x] Docs-lint + full suite; append the CHANGELOG bullet to the section 1uf68 created

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | 1uf68      | Seed edit requires the `seed_edit_allowed` gate; 1uf68 runs first (shared seed-160 and the CHANGELOG section) |


## Serialization Points

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` (shared with 1uf68, which edits
  `:49`/`:85` and runs first); `docs/contributing/build-and-verification.md`;
  `docs/references/project-overview.md`;
  `docs/architecture/decisions/1tsbu-adr review-policy-and-upgrade-protocol.md`;
  `test_events_only_residue_census.py`; `CHANGELOG.md` (shared with 1uf68, which creates the
  section)

## Affected Architecture Docs

`1tsbu-adr:13` (inline amendment note) and CHANGELOG. No contract or behavior change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The wrong mode is the defect; a downstream agent acts on these sentences |
| AC-2 | required | Silently rewriting an accepted ADR destroys the decision record it exists to be |
| AC-3 | required | A surviving carrier keeps shipping the false claim, which is how two survived the first pass |
| AC-4 | required | Two lanes verified seed-160:518 has NO contract pin today, so without a durable pin the drift recurs; and a bare-word pin would be loosened on contact, rotting the same way |
| AC-5 | required | Seed and doc edits ripple into lint and render pins; the suite is the guard |


## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-04 | Implemented. Pin written FIRST and shown red against the unmodified tree: exactly the three in-scope carriers, zero false positives, `server_impl.py`'s fail-closed `"delivery_mode": "universal"` default untripped. All four carriers then corrected (seed-160:526 under the open gate, `build-and-verification.md:181`, `project-overview.md:102` first clause, ADR amendment note at `1tsbu-adr:15` preserving the original text at `:13`) and the pin went green. `project-overview.md:102` now matches its two already-correct sibling carriers verbatim. Untouched-surface verification passed on all four: canonical `UPGRADE_POLICY_BLOCK` (`review_policy.py:101`), rendered mirror (`docs/prompts/upgrade-wavefoundry.prompt.md:261`), 1uf69's `(a no-op migration marks nothing and rewrites no wave)` clause byte-identical in the edited bullet, and `project-overview.md:102`'s `universal`/`targeted` mode-name enumeration. Four mutation checks on byte-copies under a temp root (the repository tree never mutated): each of the three reintroductions caught individually with the expected pattern and count, and the project-overview reintroduction went UNDETECTED once `docs/references/` was dropped from the scope, proving the scope extension load-bearing. CHANGELOG bullet appended to 1uf68's `## [Unreleased]` / `### Fixed`. Gapfill: Bash used only to execute tests, the byte-copy mutation driver, and one read-only `git status --porcelain` to confirm which repository files carry the edits (working-tree state is not an MCP-served surface). | Census red: 3 violations (`test_no_live_surface_claims_the_universal_delivery_mode`, `test_universal_delivery_mode_claim_count_is_zero_across_scope`). Green after fix: census 25 tests OK, `test_review_policy` 36 tests OK. Full suite 6818 tests across 62 files OK (baseline 6813 + 5 new pin tests). `wf docs-lint: ok`. Mutation driver: 3/3 CAUGHT, unmutated byte-copies GREEN, scope extension LOAD-BEARING |
| 2026-08-04 | Readiness council FAILED the first draft: the census was incomplete (project-overview.md:102 in the Tier-1 startup doc and 1tsbu-adr:13 with accepted status both carry the same false `universal` claim), AC-2 was unsatisfiable within the declared Scope, and AC-3's rationale was FALSE because seed-160:518 carries no contract pin at all, meaning the census would rot exactly as it already had. All folded: four carriers, ADR amendment convention, and a durable census pin. | Council seat reports 2026-08-04 |
| 2026-08-04 | Prepare-phase lanes independently re-verified all four carriers verbatim and swept for a fifth: none exists. Three findings folded: the census pin's home was wrong (`test_review_policy.py` reads constants only and has no census scaffolding; `test_events_only_residue_census.py` is the purpose-built precedent, needing `docs/references/` added and `decisions/` kept excluded), the pin must key on claim-shaped patterns because `universal` is a live legal enum with roughly twenty legitimate occurrences now enumerated as the negative-control set, and the ADR-convention citation named a nonexistent file (`1p7pb-adr wave-gate-retirement.md`; the real path is `1p7pb-adr native-windows-distribution-model.md:27`). Also corrected: requirement numbering ran 1,2,3,5,4; the Risks row mis-cited AC-2 for the byte-identical pin, which is AC-3; AC-1 now names the exact clause so the implementer does not over-edit `project-overview.md:102`'s correct second sentence. | Prepare lane reports 2026-08-04 (executed `migrate_wave_review_policy`; independent censuses by two lanes) |
| 2026-08-04 | Filed after wave 1uf65 closed; the claim was disproven by executing migrate_wave_review_policy (enabled -> targeted), and a census found a SECOND carrier the original observation missed (build-and-verification.md:181) plus confirmed the canonical block and rendered mirror are already correct. | Executed mapping 2026-08-04; grep census across living surfaces |
| 2026-08-04 | Delivery-review findings REPAIRED by an independent repairer (not the implementer; a separate agent reverifies). Two architecture-lane simplifications, both recorded as DELIBERATE DEVIATIONS from Requirement 4's allowance-table instruction rather than taken silently. **R5:** `DELIVERY_MODE_CLAIM_ALLOWANCES` shipped EMPTY, its lookup branch in `_scan_delivery_mode_claim` could never fire, and `test_every_delivery_mode_claim_allowance_is_load_bearing` asserted `[] == []` over an empty dict. The table, the lookup branch, and that vacuous test are deleted. Reason for the deviation: a zero-count allowance exempts nothing, and any entry that WOULD exempt an occurrence immediately fails the sibling `test_universal_delivery_mode_claim_count_is_zero_across_scope`, which is strictly stronger, so the table was decoration that could only ever be wrong. The claim scan itself is KEPT (its failure messages name file, pattern, and count) and so is the corpus-total pin; a comment at the token tuple records why there is deliberately no table and what shape to use if a genuine exemption is ever needed. The pre-existing `PREIMPLEMENTATION_GATE_ALLOWANCES` machinery and `_dead_preimplementation_allowances` are untouched. **R6:** the `root` parameter added to `_census_files` was dead (all six in-repo callers use the default) and was scaffolding for a throwaway mutation driver; the function is restored to the module-level `REPO_ROOT`/`FRAMEWORK` constants, KEEPING the load-bearing `docs/references/` scope addition. All six callers verified still on the default and passing. **R8:** `server_impl.py:2529` corrected to `:2536` in the Rationale, AC-4, and the Risks row, and that row's now-false "the allowance table pins expected counts" mitigation is restated as the claim-shaped patterns plus the corpus-total pin. **AC-4's mechanism is now the claim scan plus the corpus-total pin** rather than the claim scan plus an allowance table; AC-4 stays `[x]` because the scope extension and the red-against-planted-reintroduction property both still hold, re-proved below. | Census module 24 OK (25 before; R5 removes exactly the one vacuous test). `test_upgrade_wavefoundry.py` 445 OK. Full suite 6817 OK across 62 files in 361.3s exit 0 (6818 before; no other test changed status). `wf docs-lint: ok`. Census pin RE-PROVED load-bearing after R5+R6 on a byte-copy under the scratchpad (repository tree never mutated; `git diff` on `docs/references/project-overview.md` shows only the implementer's `targeted` correction and zero planted lines): baseline on the unmutated copy 24 OK; with `delivery_mode: universal` planted into `docs/references/project-overview.md` and scope INTACT, BOTH `test_no_live_surface_claims_the_universal_delivery_mode` and `test_universal_delivery_mode_claim_count_is_zero_across_scope` FAIL, the first naming `docs/references/project-overview.md: delivery_mode: universal (1 occurrence(s))`; with the same plant still present and `docs/references/` DROPPED from `_census_files`, both claim tests go GREEN and the reintroduction is UNDETECTED, leaving only `test_census_scope_is_non_vacuous` failing, which is the independent guard on the scope itself. Gapfill: Bash used for read-only `grep -n` caller enumeration, the byte-copy probe driver, and test execution |
| 2026-08-04 | Independent reverifier confirmed all four 1ug7o lane findings folded and every citation resolving, and landed four corrections: AC-1 said "SECOND sentence" when the mode-name clause is the third, so it now quotes the clause instead of counting; the "roughly twenty legitimate occurrences" figure was understated about threefold and is now the measured 64-across-28-files; the negative-control enumeration was both incomplete for the declared scope and padded with `docs/architecture/decisions/` entries the census never reads, so it is replaced by the measured result plus the one genuine trap (`server_impl.py:2529`); and the fourth forbidden pattern ``remain `universal` `` was cut because its only occurrence sits outside census scope and it could never fire. | Reverification report 2026-08-04 (executed: `_census_files()` scope reimplemented, all four candidate patterns run over the corpus, three in-scope carriers hit, zero false positives) |
| 2026-08-04 | Final coordinator pass: corrected this doc's remaining drifted citations and re-joined the Progress Log rows to their table header. The delivery-review verdict for this change was APPROVE on all six lanes; its only findings were the two simplifications already recorded above (R5 and R6) and the `server_impl.py:2536` citation. | `wf docs-lint: ok`; census module green after R5/R6 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-04 | Amend `1tsbu-adr:13` inline rather than correcting or deleting its text | An accepted ADR is a point-in-time decision record; the repository's convention (`1p7pb-adr native-windows-distribution-model.md:27`) is an inline amendment note naming the wave that superseded the decision | Rewrite the ADR sentence (rejected: destroys the record); leave it silent (rejected: it states the exact false mapping with accepted status and no pointer) |
| 2026-08-04 | Correct the carriers to match the canonical block; do not restate the mapping a third way | The canonical `UPGRADE_POLICY_BLOCK` sentence is already accurate and is the surface targets read at upgrade time; convergent wording prevents this drift from recurring | Rewrite all carriers in fresh wording (rejected: churns correct text and risks new drift); delete the claim from the secondary surfaces (rejected: the mapping is genuinely useful context where it appears) |
| 2026-08-04 | Home the census pin in `test_events_only_residue_census.py` with a claim-keyed allowance table, not in `test_review_policy.py` with a token sweep | The census module already owns the exact scope and archive-immunity this needs and already has the allowance-table idiom; `test_review_policy.py` reads module constants and would acquire a whole-repo filesystem dependency. Claim-keying is forced by `universal` being a live legal enum with roughly twenty legitimate occurrences | Bare-token sweep next to `test_review_policy.py:349` (rejected: red on contact against correct prose, then loosened, then rotted, which is the failure this AC exists to prevent) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The seed edit disturbs 1uf69's no-op qualifier in the same bullet | AC-3 pins that clause byte-identical, Requirement 5 quotes it verbatim and warns that the canonical block's shorter variant must not overwrite it, and the correction touches only the mapping phrase |
| Closed-wave archives still assert the `universal` mapping and are indexed, so `docs_search`/`code_ask` can surface them | Excluding archives is deliberate: they are point-in-time records. The residual is bounded because `code_ask` citations on wave archives carry `{historical, waves_behind}` freshness, and the `doc_code_drift` partition exists. Named here so it is a known residual rather than an unexamined gap. Live carriers: `docs/waves/1tuoc review-policy-and-delivery-evaluator/1tsbu-enh ...:32,41,44` and `.../review-policy-adoption-baseline.md:50` |
| The census pin false-trips on legitimate `universal` uses | An independent reverifier executed the three patterns over the full in-scope corpus (64 occurrences, 28 files) and measured zero false positives; AC-4 requires green across that corpus including `server_impl.py:2536`, and the pin keys on the three claim-shaped patterns rather than banning the word (delivery repair R5 dropped the zero-count allowance table, which could exempt nothing; the corpus-total pin is the stronger guard) |
| Both changes edit seed-160 | Serialization Points and the AEG put 1uf68 first with a single `fix` workstream and one gate window |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
