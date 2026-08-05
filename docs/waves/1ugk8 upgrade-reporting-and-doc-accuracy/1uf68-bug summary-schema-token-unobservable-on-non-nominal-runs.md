# The Summary Schema Token Is Unobservable on Exactly the Runs That Deviate

Change ID: `1uf68-bug summary-schema-token-unobservable-on-non-nominal-runs`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-04
Wave: `1ugk8 upgrade-reporting-and-doc-accuracy`

## Rationale

Target-repo field report (2026-08-04): the delegation's field proof is positively closed (four
consecutive post-transition runs reported `summary_schema_version: 1` unmarked, zero degradation
markers), with one structural caveat the reporter isolated: the token is phase-scoped. The
pgt9 run showed `schema=<ABSENT>, degraded=<absent>` because its primary phase paused at the
memory checkpoint and emitted no summary at all, and the cleanup summary omits the token.

Absent and degraded are different states and only degraded is marked. The drift tripwire is
therefore unobservable precisely on the runs that deviated, which are the runs most worth having
a tripwire for.

Council census (2026-08-04, code-grounded) corrected and widened the mechanism:

- The sole production caller of `_emit_primary_summary_via_delegate_or_fallback` is
  `upgrade_wavefoundry.py:4984` (the plan originally cited a drifted :4924).
- The cleanup summary is emitted by `_print_operator_summary` (`:3280`, sentinel at `:3403`),
  which the original plan never named; `_build_upgrade_summary` is a SHARED builder also used by
  the primary-phase degradation fallback at `:3024`.
- There are THREE windows in which a summary is emitted without the token today: the checkpoint
  pause (two exit paths, a plain `return memory_backfill.ACTION_REQUIRED_EXIT` at `:4907` being
  the common one and the `SystemExit` route via `:4941` the other), `--resume-after-memory`
  (returns 0 at `:4162`), and every ordinary cleanup summary.
- The only token writer today is `_emit_delegated_summary` (`:3191`, `:3272-3273`).

Prepare-phase lanes (2026-08-04, executed) corrected the reachability model and closed the census:

- `_print_operator_summary` has exactly two production callers, both inside `phase_cleanup`
  (`:2489` failure branch, `:2558` success). `phase_cleanup` has exactly ONE production caller,
  `main`'s `if args.cleanup:` branch at `:4350`. The default run terminates at `:4984`/`:5002`
  and prints `upgrade-wavefoundry --cleanup` as the operator's next step (`:4996`). This is
  already pinned independently at `test_reconcile_scan.py:848` (`callers == {"phase_cleanup"}`)
  and `test_upgrade_wavefoundry.py:8953`.
- Therefore the pause run and the resume run emit NO sentinel at all, in their own process, and
  this change does not alter that. Each window reaches a tokened summary at its subsequent
  `--cleanup` invocation, which is the recovery step every documented path takes.
- The documented recovery from a checkpoint pause (`--resume-after-memory`, then `--cleanup`) takes
  the SUCCESS branch, because `:4154-4157` clears `failed_phase`. A pause lock taken straight to
  `--cleanup` without resuming does NOT reach `phase_cleanup` at all: the pre-cleanup memory gate
  (`:4189-4219`) refuses it with exit 4 and zero sentinels, because memory is not yet marked
  indexed. The FAILURE branch (`:2489`) is still reachable and still needs a pin, but from any
  other `failed_phase` value the lock can carry, and `--cleanup` reads it at `:4326`. The test
  fixture reaches that branch carrying the pause's own
  `failed_phase="awaiting_memory_validation"` (stamped at `:4890`) only because it force-marks
  memory indexed to clear the gate, which is a synthetic lock combination rather than a real
  pause-without-resume run. There are only two distinct paths through `phase_cleanup`,
  discriminated by the lock shape it reads, not three windows with three code paths.
- Census closed on the remaining no-summary exits: `main` also refuses before `phase_cleanup` at
  `_unrecovered_review_or_docs_gate` (`:4180-4182`, `return 1`) and at the memory gate
  (`:4189-4219`, `return ACTION_REQUIRED_EXIT`), executed and reproduced (exit 4 with an explicit
  ordered-recovery diagnostic). These do NOT need the token: a loud stderr diagnostic plus a
  distinct exit code already disambiguates them, and no summary is emitted to be misread. The
  claim this change makes is therefore scoped to every window in which a summary IS emitted.

## Requirements

1. **The cleanup emit site carries the token; the shared builder never does.** Add
   `summary[SUMMARY_SCHEMA_KEY] = SUMMARY_SCHEMA_VERSION` inside `_print_operator_summary`
   immediately before the sentinel emit at `:3403`, unconditionally (the existing `:5019` pin
   calls this function with `root=None`, so the insertion must not depend on `root`). It must NOT
   go into `_build_upgrade_summary`: that builder also produces the primary-phase degradation
   fallback, whose documented invariant (`:3019`) is that it never carries the token, pinned at
   `test_upgrade_wavefoundry.py:5680` and stated in ADR 1u49j:35-36 and
   `data-and-control-flow.md:515-516`. It must also NOT go into the shared `_emit_summary_line`
   helper, which the degradation fallback calls at `:3047`. One insertion covers all three
   token-less emitting windows because every one of them reaches `_print_operator_summary` at its
   subsequent `--cleanup` invocation, the sole production route into `phase_cleanup` (`:4350`).
2. **Mechanism DECIDED at Prepare (2026-08-04): cleanup carries the token; the paused primary
   phase does NOT emit before pausing.** Rationale in the Decision Log. The rejected option would
   emit from pre-extraction code (making the fix class (b), ineffective on its own installing
   upgrade), would falsify the `failed_phase=None` justification audited at `:3032-3035` and
   `:3253` by making that site reachable on a run whose lock carries a `failed_phase`, and would
   permanently claim an index state that Phase 4 has not yet determined.
3. **The token is a SELF-WITNESSING freshness claim, and that is what the carriers must say.**
   Only code that contains the emit line can emit the token, so the token's meaning is exactly
   "the framework code that rendered this summary is post-extraction code that carries the
   contract". That statement is true at both emit sites and needs no producer-identity field.
   Two consequences are ratified rather than acquired silently:
   - Failure-path cleanup summaries also gain the token (`:2489` is reached with a `failed_phase`
     in the lock). Correct under this reading: the claim is about the code that built the summary,
     not whether the upgrade succeeded. `failed_phase` remains the success discriminator.
   - The token stops identifying WHICH emitter produced a summary. Accepted: no consumer needs
     producer identity, and the pre-existing `summary_source_degraded` marker remains the sole
     degradation discriminator, unchanged and still exclusive to the in-process fallback (whose
     one caller at `:3179` always passes a marker, so an unmarked fallback is unreachable). No new
     flat scalar is added; the ADR's Alternatives row that rejected a fresh-phase emitter must be
     amended in the same edit (Requirement 7) so the record does not ship a rejection of what was
     built.
4. **The one existing pin that this breaks is NARROWED, not deleted.**
   `test_upgrade_wavefoundry.py:5019-5039` (`test_primary_and_prose_render_from_same_builder`)
   asserts the primary and prose key sets are EQUAL, encoding wave 1p8kz AC-2. Executed today's
   key sets are 18 == 18 and become 19 vs 18. Re-point it to a superset assertion (cleanup keys
   equal primary keys plus exactly the schema token) with the rationale recorded inline, so the
   one-builder property it protects survives.
5. **The bounder cannot make a present token look absent.** Add `summary_schema_version` to
   `UPGRADE_SUMMARY_TERMINAL_KEYS` (`server_impl.py:2345-2361`). That set today registers TEN
   keys (`review_sidecar_cleanup`, `from_version`, `to_version`, `zip_applied`, `pruned_count`,
   `docs_gate`, `index_update`, `failed_phase`, `is_major_or_minor`, `summary_source_degraded`):
   EXTEND it, never replace it. Without the registration the token competes in the unknown-scalar
   budget and a drop yields `None`, which reads as absent to any consumer not also checking the
   truncation flag, reintroducing the exact ambiguity this change removes. Two facts to state and
   not rediscover: the per-value cap at `:12178` still applies (irrelevant for a 1-char value),
   and this registration lives in the MCP server's in-process module, so unlike the emit-site fix
   it takes effect only after a full host restart (the documented class (c) boundary). Emission is
   class (a) and unaffected. This is a registration of an existing key, not a new schema key.
6. **Red-first, structured by what actually varies.** The discriminator is the lock shape
   `--cleanup` reads at `:4310-4330`, not the window, so the honest test set is:
   - (a) **Pause to cleanup, driven through `main`.** Write a lock with
     `failed_phase="awaiting_memory_validation"` plus `action_required`, exactly the shape
     `:4878-4892` writes; run `main(["--cleanup"])`; assert `SystemExit(1)` AND that the sentinel
     parsed out of captured stdout carries the token. This doubles as Requirement 3's failure-path
     pin. Must drive `main`/`phase_cleanup`, not call `_print_operator_summary` directly, because
     Requirement 1's whole reachability claim is what needs pinning.
   - (b) **Nominal cleanup** on a clean lock through the success branch (`:2558`), parsing the real
     sentinel line out of captured stdout as `:5030-5034` does. Patching `_emit_summary_line` or
     asserting on `_build_upgrade_summary`'s return value bypasses the emit seam and is vacuous.
     The post-resume lock shape (`failed_phase` cleared per `:4154-4157`, `index_rebuilt_at` set at
     `:4150` surfacing as `ran_index_rebuild=True` at `:4320`) is a `subTest` lock-shape
     parameterization of THIS case, not a separate window: with `failed_phase=None` it is
     path-identical. Do not count it as independent coverage.
   - (c) **Builder-level non-leak pin:** assert `SUMMARY_SCHEMA_KEY not in` the dict
     `_build_upgrade_summary` returns, proving the token lives at the emit site. The four existing
     degradation pins already cover the fallback path; a fifth adds nothing, this assertion is the
     one that is missing.
   - (d) **Bounded response under budget pressure.** Feed a cleanup-shaped sentinel (token present,
     `failed_phase: null`) through `wf_upgrade_response(root, phase="cleanup")` with enough
     oversized unknown scalars to exhaust `unknown_scalar_budget`, mirroring
     `test_server_tools.py:25118-25139`, and assert both the token survives and
     `summary_truncated is True`. Without budget pressure the token survives even unregistered and
     the test proves nothing; it must be shown red against a key set with the token removed (the
     `:25146` filtering idiom).

   Four cases, not five: the resume shape folds into (b) as a `subTest` because it exercises no
   distinct path. Extend the existing `DelegatedSummaryContractTests` family (`:5259`) and, for
   (d), the existing `test_server_tools.py` upgrade-summary tests; no new test module.

## Scope

**Problem statement:** the token is emitted only by the delegated primary-phase producer, so
deviating runs produce summaries where drift and absence are indistinguishable.

**In scope:** `_print_operator_summary`'s emit site in `upgrade_wavefoundry.py`;
`UPGRADE_SUMMARY_TERMINAL_KEYS` in `server_impl.py`; `test_upgrade_wavefoundry.py` and
`test_server_tools.py` (new pins plus the one narrowed assertion); the Requirement 7 doc carriers,
which include `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` and its rendered
mirror and therefore require the `seed_edit_allowed` gate.

**Out of scope:** the token VALUE and recognized set; the delegation and degradation mechanics
(field-proven); `_build_upgrade_summary` and `_emit_summary_line` MUTATION (explicitly forbidden by
Requirement 1); adding any new summary field (explicitly decided against in Requirement 3); the
pre-`phase_cleanup` refusal exits at `:4180-4182` and `:4189-4219` (no summary is emitted and the
exit code plus diagnostic already disambiguate them).

## Requirement 7 doc carriers

The token stops being delegation-exclusive, so these say so. Both the provenance claims and the
one-builder claims are affected, and the seed pair ships to every target repository.

Required:

- `docs/specs/mcp-tool-surface.md:970` both passages: the provenance sentence (a cleanup summary
  now carries the token while being neither delegated nor degraded) and the phase-semantics
  one-builder parenthetical.
- `docs/specs/mcp-tool-surface.md:966`: "`cleanup` ... Also re-emits `data.summary` (same builder
  as the primary phase)" now needs the token difference named.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md:49` (gated) and its rendered
  mirror `docs/prompts/upgrade-wavefoundry.prompt.md:50`: "both emissions are rendered from one
  builder, so their structured fields agree" becomes false in exactly one key and must say so.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md:85` (gated) and its mirror
  `docs/prompts/upgrade-wavefoundry.prompt.md:58`: the token-interpretation disclosure is the
  target-facing guidance for reading token presence, which is what this change alters. It must
  state the three causes of token ABSENCE so a target agent does not report the wrong one: the
  in-process degradation fallback (always accompanied by `summary_source_degraded`), a runner
  predating this contract (distinguished by `to_version`), and no summary emitted at all
  (pause/resume, before the recovery `--cleanup`).
- `docs/architecture/decisions/1u49j-adr fresh-code-summary-producer-contract.md:36`: carrier set
  widens; the fallback-carries-no-token invariant is restated, not weakened. **And `:100`**, the
  Alternatives row rejecting "authoritative emission from an already-fresh spawned phase", must be
  amended in the same edit per Requirement 3, or the ADR ships a rejection of what was built. The
  amendment's grounding, verified by execution rather than left for the implementer to invent: the
  row's collision limb does not apply because `_parse_upgrade_summary` (`server_impl.py:12099`) is
  the SOLE sentinel consumer and is called once per subprocess invocation on that invocation's
  stdout (`:12879`), never on the accumulated `log_path`, so the primary and cleanup sentinels
  never share a parsed stream. The only other token reader,
  `upgrade_wavefoundry.py:3139`, parses the `--emit-summary` child alone, which routes to
  `_emit_delegated_summary` and never to `_print_operator_summary`.
- `docs/architecture/data-and-control-flow.md:517`: the sentence claiming the cleanup summary is
  unchanged becomes false and must be corrected; `:515-516` stays true and is the tripwire proving
  Requirement 1 was honored.
- `docs/agents/session-handoff.md` standing field-report hook (`:20`, `:25`, `:275-284`,
  `:357-360`): name WHICH summary satisfies the field proof now that cleanup also carries the
  token, and require future reports to distinguish "no sentinel was emitted" from "a sentinel was
  emitted without the token". The pgt9 report collapsed both into one `<ABSENT>` string, which is
  the reporting half of this defect. `:20` ("the schema token is phase-scoped; checkpoint-paused
  runs emit no token-bearing summary") becomes false at the cleanup site and is the sentence most
  directly superseded. While in that paragraph, correct two stale adjacent facts: `:19` files
  1uf68/1uf69 under `docs/plans/` though 1uf68 now lives in this wave directory, and `:37-38`
  claims the CHANGELOG heading reads `## [1.15.2] - unreleased` when `CHANGELOG.md:9` reads
  `## [1.15.2] - 2026-08-04`.
- `CHANGELOG.md`: see the shared-section note below.

Recommended:

- `docs/architecture/layering-rules.md:29`: the boundary row ties the token to the pinned
  `--emit-summary` producer boundary and carries the "never a second sentinel" clause. On
  inspection it does not claim the token is EXCLUSIVE to that boundary, so nothing in it becomes
  false; a clarifying note that cleanup also carries the token is welcome but is not a correction,
  and the ADR plus `mcp-tool-surface.md:970` already carry the widened set.

## Acceptance Criteria

- [x] AC-1: Every summary emitted from the cleanup emit site carries `summary_schema_version`,
  red-first, on both `phase_cleanup` branches; and the pause and resume paths, which by ratified
  design emit no summary in their own process, reach a tokened summary at their recovery
  `--cleanup`, pinned by driving `main(["--cleanup"])` rather than calling the emitter directly.
- [x] AC-2: The primary-phase fallback still carries NO token, `_build_upgrade_summary` and
  `_emit_summary_line` are unmutated, and the existing `:5680` pins pass unchanged.
- [x] AC-3: The `:5019-5039` equality assertion is narrowed to a superset assertion with inline
  rationale (narrowed, never deleted), and the failure-path token is pinned per Requirement 3.
- [x] AC-4: `summary_schema_version` is ADDED to the ten existing terminal keys and a test proves
  the bounded MCP response carries it from a cleanup summary under budget pressure, shown red
  against a key set without it.
- [x] AC-5: Every Requirement 7 carrier states the widened carrier set; the seed pair and the
  session-handoff reporting hook additionally state the three causes of token absence; the ADR's
  Alternatives row is amended; docs-lint passes.
- [x] AC-6: The delegation clusters, the `test_server_tools` upgrade-summary tests, and the full
  framework suite pass; the contract tests were extended, not forked.

## Tasks

- [x] Red-first tests: (a) pause-to-cleanup through `main`, (b) nominal cleanup with the
  post-resume lock shape as a subTest, (c) builder-level non-leak, (d) bounded response under
  budget pressure
- [x] Token at the cleanup emit site; terminal-key registration; narrow the `:5019` assertion
- [x] Requirement 7 carrier edits (seed pair under `seed_edit_allowed`)
- [x] Delegation clusters + `test_server_tools` + full suite; CHANGELOG bullet (see note)

## Shared serialization note

`CHANGELOG.md` has NO open unreleased section (`:9` is the released `## [1.15.2] - 2026-08-04`),
and `build_pack.py` hard-fails without a section matching `--version` (`:1263-1268` on the release
preflight, `:1276-1291` otherwise, both before the docs gate, no bypass flag). **1uf68 implements
first and CREATES `## [Unreleased]` with a `### Fixed` subsection; 1ug7o appends to it.** Both
changes declare `CHANGELOG.md` as a shared serialization point.

`## [Unreleased]` is a new heading pattern for this repository (zero prior occurrences in
`CHANGELOG.md`, the seeds, `docs/contributing/`, or `build_pack.py`), and
`_extract_changelog_section` (`:368-394`) matches `^## \[{version}\]`. So the next
`build_pack --version 1.15.3` or `--release` will hard-fail until the heading is renamed to
`## [1.15.3] - <date>`. That is the safe failure direction (loud abort, which is what the
changelog-first gate exists for) but it is a manual step: the release runner must rename the
heading, and this note is the record of it.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          | Implements first; creates the CHANGELOG Unreleased section; needs `seed_edit_allowed` for the seed-160 carriers |


## Serialization Points

- `upgrade_wavefoundry.py`, `server_impl.py`, `test_upgrade_wavefoundry.py`,
  `test_server_tools.py`; `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` and
  `docs/prompts/upgrade-wavefoundry.prompt.md` (shared with 1ug7o, which edits `:518` of the same
  seed); `CHANGELOG.md` (shared with 1ug7o, this change creates the section)

## Affected Architecture Docs

See **Requirement 7 doc carriers** above. Required: `mcp-tool-surface.md` (`:966` and `:970`), the
seed-160 `:49`/`:85` pair with its rendered mirror, ADR 1u49j (`:36` and the `:100` Alternatives
row), `data-and-control-flow.md:517`, `session-handoff.md`, CHANGELOG. Recommended:
`layering-rules.md:29` (nothing in it becomes false).

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The emitting windows are the defect, and the reachability claim is the mechanism; pinning it through `main` is what makes the fix real rather than asserted |
| AC-2 | required | Token on the in-process fallback would be a false freshness claim, the opposite of the fix |
| AC-3 | required | Deleting the one-builder pin would trade an observability fix for a drift hole |
| AC-4 | required | A bounder-dropped token reads as absent, reintroducing the exact ambiguity being removed |
| AC-5 | required | Living surfaces including two shipped seeds assert the token is delegation-exclusive and that both emissions agree in every field; they become false on delivery |
| AC-6 | required | The emit path runs on every upgrade; the suite is the regression guard |


## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-04 | Filed from the field report that positively closed the rename's second-half proof and isolated this gap. | Field report 2026-08-04 (pgt9: schema absent, degraded absent) |
| 2026-08-04 | Readiness council FAILED the first draft and the findings were folded whole: the call-site citation had drifted to :4984, the actual cleanup carrier is `_print_operator_summary` (never named), `_build_upgrade_summary` is shared with the fallback so mutating it would break three pins and falsify the ADR, a THIRD token-less window exists (`--resume-after-memory`), the pause has two exit paths with the plain `return` the common one, option (a) breaks the `:5019` equality pin (narrow, not delete), failure summaries also gain the token and needed ratification, and the bounder can make a present token read as absent without terminal-key registration. The docs seat added the four-surface required carrier set and the CHANGELOG no-open-section problem. | Council seat reports 2026-08-04 |
| 2026-08-04 | Prepare-phase lanes: release APPROVED (class (a) verified by executed AST reachability probe plus both invocation paths; no transition-run disclosure needed; ship path and rollback confirmed). Five lanes withheld and every finding is folded: `_print_operator_summary` is reachable ONLY via `--cleanup` so AC-1 and R6(a)/(b) were unsatisfiable as written and are now two-invocation shapes; the token's semantic is restated as self-witnessing so no producer-identity field is added and ADR `:100`'s Alternatives row is amended instead; R5 misstated the terminal-key set as one key when it holds ten, and the registration is class (c); the R7 census missed `mcp-tool-surface.md:966` and the seed-160 `:49`/`:85` pair with its rendered mirror, so the seed gate is now declared; R6(b) was structurally identical to R6(c) and R6(e) was vacuous without budget pressure; the pre-cleanup refusal exits are censused and ruled out; the `## [Unreleased]` rename step is recorded. | Prepare lane reports 2026-08-04 (executed: AST call-graph probe, defect reproduction, 150-test baseline green, key-set 18 == 18) |
| 2026-08-04 | IMPLEMENTED red-first. Four new pins written and confirmed failing for the right reason BEFORE the fix: (a) `test_checkpoint_pause_recovery_cleanup_carries_the_schema_token` and (b) `test_nominal_cleanup_carries_the_schema_token_on_both_lock_shapes` both failed on `None != 1` after their exit-code and single-sentinel assertions had already passed (so the harness genuinely reached the emit site through `main(["--cleanup"])`); (c) `test_shared_builder_never_carries_the_schema_token` is a non-leak pin, green by construction and proven non-decorative by mutant 3; (d) `test_schema_token_is_terminal_and_survives_cleanup_budget_pressure` failed on the missing registration, and an executed probe first falsified the plan's assumed fixture: with a few OVERSIZED unknown scalars the 25-char token survives even unregistered, because the budget is decremented only for ADMITTED fields, so the fixture was rebuilt from 1,200 same-size (25-char) fillers, which drives the residual budget strictly below the token's own entry cost. GREEN: `summary[SUMMARY_SCHEMA_KEY] = SUMMARY_SCHEMA_VERSION` at `upgrade_wavefoundry.py:3400`, immediately before the `_emit_summary_line(summary)` sentinel; `_build_upgrade_summary` and `_emit_summary_line` byte-unchanged; `summary_schema_version` appended to the ten existing keys at `server_impl.py:2367`. The `:5019` equality pin is narrowed (not deleted) to a two-way superset assertion naming the token as the only permitted difference, rationale inline. All Requirement 7 carriers edited plus the recommended `layering-rules.md:29` clarifier. `CHANGELOG.md` gained a fresh `## [Unreleased]` / `### Fixed` section left open for 1ug7o. Gapfill: Bash was used for read-only greps and `awk`/`sed` reads of the two test modules and for a fixture probe, because the tests tree is outside the semantic code index; all repository source reading and navigation went through `code_read`. | Full suite 6813 OK across 62 files in 366.6s and again 6813 OK in 341.9s exit 0 (baseline 6809, plus the four new tests); delegation clusters 38 OK; `WaveUpgradeMcpToolTests` 55 OK; `test_server_tools` alone 1575 OK; `wf docs-lint: ok`. One intermediate full-suite run reported a single failure attributed to `test_context_efficiency.py`, which passes in isolation (53 OK) and did not recur on the next full run; unrelated to this change, which touches no context-efficiency path |
| 2026-08-04 | Mutation check on a byte-copy of the framework tree under the scratchpad (repository files byte-identical afterwards, verified with `cmp`). Mutant 1 (cleanup token assignment removed) was caught by (a), both subTests of (b), and the narrowed `test_primary_and_prose_render_from_same_builder`: 4 failures. Mutant 2 (terminal-key registration removed) was caught by (d) alone: 1 failure, which is the correct blast radius for a server-resident registration. Mutant 3 (token moved INTO the shared builder, the wrong fix) was caught by (c), by the narrowed one-builder pin, and by 9 pre-existing degradation pins including the `:5680` fallback assertions: 11 failures. No survivors. | Mutant runs 2026-08-04: 4 / 1 / 11 named failures; `cmp` clean on both changed sources |
| 2026-08-04 | Delivery-review findings REPAIRED by an independent repairer (not the implementer; a separate agent reverifies). R1 (BLOCKING, docs-contract): `mcp-tool-surface.md:966` claimed the token is "the one field in which the two emissions differ", which is FALSE on every nominal run because the delegated primary producer sets the same key at `upgrade_wavefoundry.py:3272` (verified by reading both emit sites); the sentence now says the token is the only field in which the two emissions CAN differ and that the primary carries it only when its summary came from the delegated producer, importing the qualifier already correct at seed-160:49 and `docs/prompts/upgrade-wavefoundry.prompt.md:50`. The second passage on the long `:970` line was re-read and stays true and consistent (it already scopes the exception and states the in-process fallback never carries the token). R2 (docs-contract): the ADR 1u49j Alternatives row had DELETED the original rejection's collision limb; the original text is restored verbatim from HEAD and the wave-1uf68 amendment now follows it as a separate marked clause in the `1tsbu-adr:15` convention, plus an explicit note that the no-such-phase limb still stands. R3: the same row's `_parse_upgrade_summary` citations were seven lines stale after this change's insertion and are corrected to `server_impl.py:12099` and `:12879` (both verified); the same two citations in this doc's Requirement 7 carrier list were corrected with them. R4 (qa, narrative): the Rationale's claim that the pause-without-resume case reaches the FAILURE branch is corrected, and so are the `_cleanup_ready_root` fixture docstring and the failure-branch test's docstring, which asserted the same thing. R7: three blank lines before `class DelegatedSummarySchemaDivergentTests` reduced to two. Also recorded in 1ug7o: R5 and R6 delete the zero-count delivery-mode allowance table and the dead `_census_files(root=...)` parameter as deliberate deviations from that change's Requirement 4. No production code changed; all ACs stay `[x]`. | R4 verified by execution, not inspection: a real pause lock (memory unmarked, `failed_phase="awaiting_memory_validation"`) driven through `main(["--cleanup"])` returns exit 4 with ZERO sentinels and the ordered-recovery stderr diagnostic, refused at the pre-cleanup memory gate (`:4189-4219`) and never reaching `phase_cleanup`; the same lock with memory force-marked indexed (the fixture's shape) exits 1 with one sentinel carrying `failed_phase=awaiting_memory_validation` and the token; an unrelated `failed_phase="docs_gate_backfill"` reaches the same failure branch with the token, proving it independently reachable. `test_upgrade_wavefoundry.py` 445 OK. Full suite 6817 OK across 62 files in 361.3s exit 0 (6818 before, minus the one vacuous test R5 deleted; no other test changed status). `wf docs-lint: ok`. Gapfill: Bash used for read-only `grep -n` line-number verification in `server_impl.py`, `git show HEAD:<adr>` to recover the verbatim rejection text, and to execute the R4 probe and the test suites; all repository source navigation went through `code_read` |
| 2026-08-04 | Independent reverifier (not the author, not the repairer) confirmed all seven 1uf68 lane findings folded and every load-bearing citation resolving against the tree, then landed three corrections: the R7 census still missed `session-handoff.md:20` (plus two stale adjacent facts at `:19` and `:37-38`), the mandated ADR `:100` amendment had no supplied grounding so the sole-consumer fact is now stated, and two simplifications were taken (the resume red-first case folds into the nominal case as a subTest since it exercises no distinct path, and `layering-rules.md:29` drops to recommended because nothing in it becomes false). | Reverification report 2026-08-04 (executed: exhaustive caller enumeration, sentinel-consumer census, live `_print_operator_summary` key count = 18 with the token absent) |
| 2026-08-04 | Final coordinator pass, closing the reverifier's two open items and trimming self-inflicted cost. The R1 repair was only PARTIAL: "the only field in which the two emissions CAN differ" is still false on a degraded run, where the primary additionally carries `summary_source_degraded`. All four carriers (`mcp-tool-surface.md` `:966` and `:970`, seed-160 and its rendered mirror) now name BOTH provenance keys, and seed/mirror parity is byte-verified. The 10-line comment written for a one-line assignment is trimmed to the three lines that state the actual constraint, which also shrank the insertion from +10 to +4 lines; every drifted `upgrade_wavefoundry.py` citation in this doc and in the new test docstrings was then swept to its true current line, along with the fallback-pin citation (`:5680`), the contract-test class (`:5259`), the reconcile backstop (`:8953`), and `session-handoff.md`'s `CHANGELOG.md:41`. Progress Log rows were re-joined to their table header (orphaned rows below blank lines do not render). Gapfill: two throwaway scripts under the scratchpad did the citation sweep and the four-carrier wording replacement, because both are bulk-mechanical text passes across five files where per-file Edit calls would have been slower and more error-prone; each asserted an exact match count before writing. | Seed/mirror clause parity True and 1uf69 qualifier count 1 (executed); `wf docs-lint: ok`; targeted modules re-run after the edits |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-04 | Cleanup carries the token at the emit site; the paused primary does not emit | Cleanup runs in a separate post-extraction process, so its token is an honest fresh-code claim and the fix is class (a), effective on its own installing upgrade; one insertion covers all three emitting windows via their recovery `--cleanup` | Paused primary emits before pausing (rejected: runs pre-extraction code so it is class (b) and ineffective on its installing upgrade, falsifies the audited `failed_phase=None` justification by making that site reachable with a failed_phase in the lock, and claims an index state Phase 4 has not determined) |
| 2026-08-04 | Register the token as a terminal key rather than only pinning current bounder behavior | A dropped token yields None, which reads as absent, recreating the ambiguity this change exists to remove; registration fixes the failure mode at its root | Pin the current behavior only (rejected: pins a latent hole); raise the scalar budget (rejected: unbounded and unrelated) |
| 2026-08-04 | Do NOT add a producer or phase field; restate the token as a self-witnessing freshness claim and amend the ADR's Alternatives row | Only code carrying the emit line can emit the token, so "post-extraction code rendered this summary" is true at both sites and is the property an operator acts on; producer identity is not a question any consumer asks, and `summary_source_degraded` remains the degradation discriminator, unchanged | Add a flat `summary_phase`/`summary_producer` scalar (rejected: a new field for a distinction nothing consumes, against the standing simplicity constraint, when the ADR amendment records the same fact for free); leave the ADR's rejection row standing (rejected: the record would contradict the delivery) |
| 2026-08-04 | Bring the seed-160 `:49`/`:85` pair and its rendered mirror INTO this change and declare the gate | Both are shipped target-facing surfaces whose one-builder and token-interpretation claims become false on delivery, and both changes share one implementer with an explicitly serialized order, so the gate can be opened once | Defer them to 1ug7o (rejected: 1ug7o's Scope and AC-3 are about the delivery-mode clause, and splitting one seed's corrections across two changes is how the first census rotted); leave them uncorrected (rejected: AC-5 would pass while false claims keep shipping) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The token leaks into the fallback via the shared builder or the shared emit helper | Requirement 1 forbids both explicitly, AC-2 pins the fallback and the builder, and the existing `:5680` assertions fail loudly if it happens |
| Narrowing the one-builder pin weakens drift detection | AC-3 requires a superset assertion naming exactly the schema token as the only permitted difference, with inline rationale |
| The reachability claim is asserted rather than pinned, so a later refactor that adds a second `phase_cleanup` caller goes unnoticed | AC-1 requires the pause and resume pins to drive `main(["--cleanup"])`; `test_reconcile_scan.py:848` independently pins the caller set |
| The terminal-key registration appears not to work on the installing upgrade | Requirement 5 states it is class (c) and takes effect after a host restart; emission is class (a) and unaffected |
| Both changes edit seed-160 in interleaved windows | Serialization Points name the shared seed, the AEG puts both in one `fix` workstream, and the wave watchpoint fixes the order (1uf68 first) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
