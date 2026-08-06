# Documenting Evidence Recruits Reviewers, Because Lane Selection Scores Plan Prose

Change ID: `1ug67-bug lane-selection-scores-plan-prose-not-scope`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-05
Wave: `1ui1d review-loop-friction`

## Rationale

`select_required_review_lanes` (`review_policy.py:391-421`) derives the required delivery-lane roster
by substring-matching risk trigger tokens against the **change document's text**. Verified in the
tree: it lowercases every admitted change doc, joins them into one `corpus` (`:412`), and tests each
token with a bare `token in corpus` (`:414`). There is no diff input, no magnitude input, and no
restriction to the sections that declare what the change touches. The corpus it scores is the plan's
prose. The token table is `RISK_TRIGGER_LANES` at `:40-48`.

The consequence is a perverse incentive: **the more carefully a plan documents its evidence, the more
reviewers it draws.** Four specimens, all measured on real waves rather than constructed:

1. **A lane fired on a file the change never touched.** In wave 1ugk8 the release lane was required by
   `risk trigger: upgrade_wavefoundry.py, build_pack.py`. The change touched neither; the plan
   *discussed* `build_pack.py` while explaining a changelog gate.
2. **The same thing recurred immediately.** Wave 1uhcb's release lane fired the same way, on
   filenames its plan quoted purely as evidence for this very change.
3. **A JavaScript trigger fired on a JSONL ledger.** `.js` is a substring of `events.jsonl`, so a plan
   that names the review authority repeatedly recruits the code lane for JavaScript reasons.
4. **Reporting a surface as CLEAN recruits its reviewer.** Wave 1uhcb's roster went from three lanes
   to five when a census finding was folded in. The census had concluded that `docs/architecture/` and
   `docs/specs/` need NO correction, and writing that conclusion down is what required an
   architecture-reviewer and a docs-contract-reviewer.

5. **A change doc recruits a lane from its own ID kind, and from any sibling it cross-references.**
   The code-reviewer tokens include `-feat `, `-enh ` and `-refactor `; qa-reviewer includes `-bug `
   (`review_policy.py:41-42`). These match the change ID in the document's own header, so the kind
   suffix alone selects a lane. Worse, naming a sibling change in an Out-of-scope cross-reference
   imports that sibling's kind: an `-enh ` mention pulls the code lane into a docs-only `-bug`.

6. **The sharpest specimen was produced by this document's own prepare review, live.** The red-team
   seat found that path-only scoring makes `security-reviewer` and `performance-reviewer`
   unreachable, and wrote that finding into this plan as Requirement 5. Writing it down named
   `security boundary`, `trust boundary`, `privilege`, `latency`, `throughput` and `hot path` — so
   the very next `wf_prepare_wave` recruited **both of those lanes**, taking the wave roster from
   five to seven and flipping `delivery_council_required` from false to true. Documenting that two
   lanes lose coverage is what recruited those two lanes. Specimen 4 said reporting a surface CLEAN
   recruits its reviewer; specimen 6 is the same mechanism applied to a coverage regression, and it
   fired inside the review that discovered it. The text was NOT trimmed to shrink the roster: this
   repo's standing rule is that gaming the evaluator by deleting load-bearing evidence from a plan is
   the wrong fix, and the resulting security review of a lane-selection change is genuinely
   warranted, however absurdly it was arrived at.

**Before this review added explicit target paths, this document reproduced all of specimens 1 through
5 on itself.** The recorded pre-declaration bytes returned all five lanes:

| Lane | Reason string | What actually matched |
| --- | --- | --- |
| code-reviewer | `risk trigger: .py, .js` | `.js` inside `events.jsonl` — the sentence explaining specimen 3 |
| qa-reviewer | `risk trigger: -bug ` | this document's own change-ID kind |
| architecture-reviewer | `risk trigger: docs/architecture` | line 28, quoting the census that found that surface CLEAN |
| docs-contract-reviewer | `risk trigger: docs/specs/` | line 29, the same clean-census sentence |
| release-reviewer | `risk trigger: upgrade_wavefoundry.py, build_pack.py` | the Rationale quoting them as specimen 1's evidence |

The historical reason strings are defective even where a lane is independently warranted: code and QA
review belong on a change to `review_policy.py` and its tests, but `.js` and `-bug` do not establish
that scope. Architecture and release review were false positives; docs-contract review was a false
positive in the pre-declaration document because the cited clean census was not a target. The amended
live plan now declares its real paths and is expected to select code, QA, and docs-contract review.
The frozen pre-declaration bytes remain the false-positive fixture. Specimen 4 is the sharpest case:
recording that a surface is safe must not recruit its reviewer.

**The defect is bidirectional, and the under-recruitment half was missed when this was filed.** Before
this review added explicit paths, the two siblings each returned `code-reviewer` alone, matched on
`-enh ` from their own change IDs. `1ug66-enh` modifies the review-policy digest function and adds a
new MCP tool, yet originally drew no qa-reviewer or docs-contract-reviewer despite shipping tests and
a tool-surface spec. The historical pre-declaration bytes are retained as test fixtures. The amended
`1ug66-enh` now returns its desired `code-reviewer`, `qa-reviewer`, and `docs-contract-reviewer`
roster from concrete paths, proving the minimal declaration works even before the selector changes.
**Prose-level scoring rewards vagueness and punishes precision in the same stroke;** the repair must
therefore score explicit paths and preserve semantic review through Requested review lanes, never
infer scope prose.

**Why this is filed separately from its siblings.** Unlike `1ug66-enh` and `1ug68-enh`, this change
**reduces review coverage**. That is a genuine risk-posture change and deserves its own approval
rather than riding along with coverage-neutral work. Risk in this codebase is not proportional to
diff size, so the fix must narrow the *corpus* being scored, not weaken the triggers themselves.

## Requirements

1. **Score automatic triggers only from explicit repo-relative paths in `## Serialization Points`,
   never from narrative.** `## Scope` remains explanatory prose and is not machine-scored. A
   path-bearing Serialization Points entry is the minimal declared target contract; update the plan
   template and authoring seed to say so. A semantic risk that has no path representation is named
   through the existing wave-level `Requested review lanes` field, which remains authoritative.
   Rationale, Scope prose, Progress Log, Decision Log, Risks, cross-references, and any census or
   carrier enumeration are excluded from automatic scoring.
2. **Coverage is preserved in BOTH directions, and this is the requirement the change lives or dies
   on.** (a) Every lane the current evaluator requires for a genuinely-touched path must still be
   required. (b) The under-recruitment measured above must not survive: a path-bearing Serialization
   Points entry recruits its lane, and a non-path semantic risk recruits its lane only when the
   planner explicitly requests it. `1ug66-enh` is the worked example: its concrete Serialization
   Points must yield `code-reviewer`, `qa-reviewer`, and `docs-contract-reviewer`; it does not infer
   architecture or release review from prose. Demonstrate both, do not assert either.
3. **Substring matching on ambiguous tokens is fixed, not just re-scoped.** `.js` matching
   `events.jsonl` is a tokenisation defect that survives any corpus change. Match path and extension
   tokens at boundaries rather than as bare substrings. The change-ID kind tokens (`-feat `, `-enh `,
   `-refactor `, `-bug `) are a second tokenisation defect in the same table: they fire on a
   document's own header and on cross-referenced siblings. Remove kind tokens from automatic trigger
   selection; kind alone is not review scope, and a planner may request the appropriate lane.
4. **The evaluator version bumps from 3 to 4 and upgrades surface the changed roster.** Changing
   automatic selection changes `required_lanes`, a receipt semantic field. Pin the v3-to-v4
   transition with byte-level policy tests and a real public prepare convergence test, and extend the
   upgrade migration to compare each non-closed declared wave's current policy-receipt evaluator
   version with the current evaluator. Mark only a wave with a stale current receipt for re-Prepare,
   even when config and prompt carriers did not change; a newly planned wave with no receipt is not
   marked.
   The insertion point is exact: `review_policy_upgrade.py:81` computes
   `policy_unchanged = config_after == config_before and not carriers`, and `:98` then does
   `if policy_unchanged: continue`. An evaluator-only bump changes neither the migrated config bytes
   nor the reconciliation carriers, so today it marks **nothing at all** — that is the gap, and it is
   why the receipt-evaluator comparison has to be a third disjunct rather than a tweak to either
   existing term. Leaving the no-receipt case unmarked is deliberate and matches
   memory `1uejb-mem`: `_review_policy_receipt_diagnostics` already returns early for a declared wave
   with neither a receipt nor a marker, so marking one here would contradict the live gate.
   **This bump stales THIS wave's own receipt, and that is expected rather than a defect.**
   `evaluator_version` sits inside the hashed payload (`review_policy.py:434`), so the constant move
   changes `policy_input_digest` for every change doc including these three. Measured on this wave's
   own bytes: `dd1fb564…` at evaluator 3, `13e15b5c…` at evaluator 4, same input. The moment this
   change lands, wave `1ui1d`'s readiness receipt goes stale, its readiness approvals lapse, and a
   stale receipt gates guided signoff recording until one re-Prepare. Wave 1uhcb hit exactly this on
   its own 2-to-3 bump. Sequencing consequence, stated so no one reports it as a regression: land the
   constant move as the LAST step of this change, then re-Prepare once and re-affirm readiness under
   the fresh receipt before recording any delivery approval.
5. **Decide, explicitly and before implementation, what happens to the two lanes that path-only
   scoring makes unreachable.** Measured against `RISK_TRIGGER_LANES`: five lanes carry at least one
   path-shaped token, but **`security-reviewer` and `performance-reviewer` carry none.** Every
   trigger they have is a semantic phrase — `security boundary`, `secret handling`, `trust boundary`,
   `privilege`, and `performance budget`, `latency`, `throughput`, `hot path`. Scoring only
   Serialization Points paths therefore removes automatic selection for those two lanes **entirely
   and permanently**, converting them to request-only.
   This is the one coverage consequence AC-2's census cannot surface: if no wave in the corpus ever
   auto-selected them, the old/new diff shows zero delta and the reduction reads as free. A census
   that cannot see a regression is not evidence against it.
   Record the decision in the Decision Log with its alternatives. At least these three, and do not
   leave it to implementation:
   (a) accept request-only for both, using the existing wave-level `Requested review lanes` field
       and Prepare Council review when the change affects a trust boundary, permissions, secrets,
       latency, throughput, or resource use;
   (b) give both lanes path representation in `RISK_TRIGGER_LANES` (for example the secrets and
       permission carriers) so they stay automatically selectable;
   (c) keep a small explicit risk-declaration field alongside paths, scored for semantic-only lanes.
   Whichever is chosen, the seeds and plan template must tell an author that semantic risk is now
   theirs to declare, because the evaluator will no longer infer it.
   Replay specimen 6 as a test alongside the others: a document that DESCRIBES a lane's triggers
   while declaring no path for it must not recruit that lane. This is the same assertion specimen 4
   makes about a clean census, and this plan is its fixture.
6. **Replay all five specimens as tests, using this document and its two siblings as fixtures.**
   Each becomes a case proving the roster is now correct for a real document: no release lane for a
   merely-quoted `build_pack.py`, no JavaScript lane for `events.jsonl`, no architecture or
   docs-contract lane for a census that reports those surfaces clean, no lane from a cross-referenced
   sibling's kind — and, for `1ug66-enh`, its three explicit-path lanes. Freeze the pre-declaration
   sibling bytes for the historical under-recruitment fixture, and pin each before-roster so a
   fixture cannot silently stop demonstrating anything. The amended live values are five lanes for
   this document and three lanes for each sibling.
7. **A bounded coverage-comparison census reports both directions without turning history into a
   manual backlog.** Generate an old/new diff for the full corpus as diagnostic aggregate evidence,
   but adjudicate each delta only for non-closed declared waves that an upgrade can still mark for
   re-Prepare. Each current removal must be justified against an explicit path or requested lane;
   each current addition names that declaration. Closed history is reported as counts and samples,
   never as hundreds of hand-classified obligations.

## Scope

**Problem statement:** the required-lane roster is derived from change-doc prose, so documenting
evidence, quoting a filename, or recording that a surface needs no change all recruit reviewers who
have nothing to review — while an explicit target can escape review when the plan has no machine
readable target declaration. Precision is taxed and vagueness is rewarded, in the same mechanism.

**In scope:** `select_required_review_lanes` and its trigger tokenisation; parsing explicit
repo-relative Serialization Points paths; the plan template and authoring seed wording for that
existing section; the v3-to-v4 evaluator migration and transition pins; the five specimen tests; the
bounded coverage-comparison census; `CHANGELOG.md`.

**Out of scope:** which lanes exist and what each reviews; the `delivery_council_required` derivation;
requested-lane handling (a wave record may still request lanes explicitly, and that stays); checkbox
and Progress Log digest behaviour (see `1ug66-enh`); ledger ergonomics (see `1ug68-enh`).

## Acceptance Criteria

- [x] AC-1: Each of the five specimens produces the correct roster, one test per specimen. The four
  live false-positive specimens are red against the current evaluator; the historical
  under-recruitment fixture freezes the pre-declaration sibling bytes and its `code-reviewer`-only
  before-roster. Every before-value is pinned.
- [x] AC-2: A coverage-comparison census emits a full-corpus aggregate diff and individually
  adjudicates every delta only for non-closed declared waves. Each current removal is justified
  against an explicit path or requested lane and each current addition names its declaration. Closed
  history is not converted into a manual classification backlog.
- [x] AC-3: Boundary-aware token matching: `.js` does not match `events.jsonl`, and the equivalent
  false-substring cases for other extension and path tokens are pinned. Change-ID kind tokens no
  longer fire from a cross-referenced sibling's id, pinned with a doc that names one.
- [x] AC-4: A lane whose trigger appears in an explicit Serialization Points path is still required,
  pinned per automatic lane; a non-path lane is required only when explicitly requested.
- [x] AC-4a: Under-recruitment is closed: `1ug66-enh` recruits exactly `code-reviewer`,
  `qa-reviewer`, and `docs-contract-reviewer` from its explicit paths rather than `code-reviewer`
  alone, with the roster recorded in the Decision Log. This AC fails if the delivered evaluator
  returns a single lane for it.
- [x] AC-4b: The Requirement 5 decision on `security-reviewer` and `performance-reviewer` is recorded
  in the Decision Log with its alternatives. The adopted request-only branch is pinned: neither lane
  is selected by descriptive prose or paths alone, while either is selected when explicitly named in
  the existing wave-level `Requested review lanes` field. An undecided or untested outcome fails this AC.
- [x] AC-5: Evaluator version 4 is recorded with byte-level and public prepare convergence evidence,
  and upgrade marks a non-closed declared wave whose current receipt is v3 for one re-Prepare even
  when config and prompt carriers are byte-identical, while leaving a newly planned no-receipt wave
  unmarked.
- [x] AC-6: Mutation-checked. At minimum: corpus widened back to the whole document; Scope prose
  wrongly added to automatic scoring; an explicit path ignored; and boundary matching reverted to
  substring. Each is killed by a named test.
- [x] AC-7: Full framework suite and docs-lint pass.

## Tasks

- [x] Census carriers and update the existing Serialization Points authoring contract at Prepare
- [x] Red-first specimen tests (AC-1)
- [x] Explicit Serialization Points path selection, removal of kind triggers, and boundary-aware tokenisation
- [x] Full aggregate plus non-closed-wave coverage-comparison census (AC-2)
- [x] v3-to-v4 upgrade and public prepare transition pins
- [x] Mutation check; full suite; docs-lint; CHANGELOG bullet with any transition disclosure

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| evaluator  | implementer | —          | Explicit-path selection, tokenisation, and evaluator migration |
| census     | qa-reviewer | evaluator  | Bounded current-wave coverage evidence for AC-2 |


## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`; `.wavefoundry/framework/scripts/review_policy_upgrade.py`; `.wavefoundry/framework/scripts/tests/test_review_policy.py`; `.wavefoundry/framework/scripts/tests/test_server_tools.py`; `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`; `docs/plans/plan-template.md`; `CHANGELOG.md`

## Affected Architecture Docs

Census at Prepare against the then-current tree; do not pre-write it. Candidates: any doc or seed
stating how required lanes are derived, the review-system overview seed, the MCP tool-surface spec's
prepare/review sections, and `docs/agents/memory/` records about review policy. A surface asserting
that lanes are risk-selected from the change document becomes imprecise on delivery. Treat `N/A` as a
finding until the sweep is run.

## AC Priority

Populated at plan time, before the prepare council runs, per the ordering rule wave 1uhcb shipped
(`seeds/170-plan-feature.prompt.md`; `docs/plans/plan-template.md`).


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The five specimens, including the frozen pre-declaration under-recruitment fixture, are the change's evidential basis; without them the roster claim is an assertion |
| AC-2 | required   | The bidirectional census is the coverage gate for a risk-posture change and the named council item the superseded separate-wave decision was buying |
| AC-3 | required   | Boundary-aware tokenisation is a correctness fix that survives any corpus decision |
| AC-4 | required   | Retention pins are the direct guard against a silent coverage reduction |
| AC-4a | required  | Under-recruitment is measured and currently under-reviews a change to the digest function and the MCP tool surface; leaving it open would make the corpus narrowing net-negative |
| AC-4b | required  | Path-only scoring makes `security-reviewer` and `performance-reviewer` permanently unreachable automatically, and AC-2's census is structurally blind to that regression; an undecided outcome ships a silent security-review coverage loss |
| AC-5 | required   | A changed evaluator that leaves an existing open wave on its prior roster defeats the review-coverage guarantee this change is making |
| AC-6 | required   | Mutation checks are what make the coverage claims non-vacuous |
| AC-7 | required   | Suite and docs gate are the standing release condition |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-05 | Filed as the coverage-REDUCING follow-up to wave 1uhcb, deliberately separated from its two coverage-neutral siblings so it gets its own approval. All four specimens were measured live during waves 1ugk8 and 1uhcb rather than constructed; specimen 4 was produced by this plan's own predecessor when folding a census finding escalated its roster from three lanes to five. | Wave 1uhcb `wave.md` watchpoint recording all four specimens; receipt reason strings from both waves |
| 2026-08-05 | Admitted into wave `1ui1d review-loop-friction` alongside both siblings on operator direction, and strengthened during a pre-Prepare discovery pass. Added: specimen 5 (change-ID kind tokens firing from the document's own header and from cross-referenced siblings); the self-demonstration table showing this document recruits all five lanes purely by describing the defect; and the BIDIRECTIONAL finding, which the original filing missed entirely — `1ug66-enh` modifies the digest function and adds an MCP tool yet recruits `code-reviewer` alone, escaping qa, docs-contract and architecture because it names no literal path. Requirement 2 is now two-directional, Requirement 3 covers the kind tokens, Requirement 5 pins before-rosters, AC-4a targets under-recruitment, and the separate-wave decision is superseded with its obligation carried forward as a named council item. | Executed `select_required_review_lanes` over all three change docs in this wave via the tool venv; `review_policy.py:40-48` token table, `:412` corpus join, `:414` bare-substring test; matched lines 28-29 of this document for the architecture and docs-contract triggers |
| 2026-08-05 | **Delivery review: three blocking findings, all repaired.** (1) `architecture-reviewer` was UNREACHABLE: its only token `docs/architecture` neither started with `.` nor ended with `/`, so `_path_token_matches` fell to the equality/suffix branch and a plan declaring `docs/architecture/current-state.md` selected NOTHING; the bare-token branch now also matches a directory prefix, and `docs/architecture.md` was added for the hub doc. (2) `_REPO_PATH_RE` hardcoded a four-prefix allowlist, so any target repo laid out as `lib/`, `pkg/`, `cmd/`, `app/` or `internal/` extracted zero paths and got zero automatic lanes with no diagnostic, violating the AGENTS.md Product Boundary; the pattern is now shape-based. (3) The AC-2 census, never run before this review, showed path-only scoring was RETROACTIVE: 775 change docs lost lanes, ZERO gained any, and five of six non-closed change docs collapsed to an EMPTY roster because every plan authored before this contract describes targets in prose. Repaired by failing OPEN: a document that declares no machine-readable target keeps its previous whole-document coverage via `LEGACY_WHOLE_DOCUMENT_TRIGGER_LANES`, labelled distinctly in the reason string, and omitting the two retired lanes so the request-only decision still holds. A fourth defect was introduced and caught during that repair: the generalized path pattern read English prose (`the runner/test corpus`, `stop dashboard/index activity`) as declared targets, which misclassified a plan as DECLARED and suppressed its own fallback; `_is_declared_target` now requires an extension or an explicit trailing separator. | Census re-run after repair: 0 of 9 non-closed change docs at an empty roster, previously 5. New pins: `test_every_automatic_lane_is_selected_by_a_real_declared_path`, `test_path_extraction_is_layout_agnostic_across_target_repositories`, `test_an_undeclared_plan_keeps_its_coverage_instead_of_dropping_to_zero`, `test_slashed_prose_is_not_mistaken_for_a_declared_target`. Mutation-checked: reverting the token branch and restoring the prefix allowlist each kill their pin |
| 2026-08-05 | Specimen 6, produced live by this review and recorded rather than suppressed. Folding the Requirement 5 finding into this plan named the semantic triggers of the two lanes it concerns, so the next `wf_prepare_wave` recruited `security-reviewer` and `performance-reviewer`: the wave roster moved five to seven and `delivery_council_required` flipped false to true. Documenting that two lanes lose coverage is precisely what recruited them. The prose was deliberately NOT trimmed to shrink the roster, per the standing rule that deleting load-bearing evidence to game the evaluator is the wrong fix; the resulting security review of a lane-selection change is warranted on its merits. Requirement 5 now asks for specimen 6 to be replayed as a test: a document describing a lane's triggers while declaring no path for it must not recruit that lane. | `wf_prepare_wave` dry-run before and after the Requirement 5 edit: required_lanes 5 to 7, `delivery_council_required` false to true, receipt `review-policy-ca4f9d1750632279e913` to `review-policy-8b04e62a042efd73b80b` |
| 2026-08-05 | Prepare-council red-team finding, folded as Requirement 5 and AC-4b: path-only automatic scoring makes `security-reviewer` and `performance-reviewer` **permanently unreachable**. Measured over `RISK_TRIGGER_LANES`: five lanes carry at least one path-shaped token; those two carry none, holding only semantic phrases (`security boundary`, `secret handling`, `trust boundary`, `privilege`; `performance budget`, `latency`, `throughput`, `hot path`). The plan's philosophy of routing semantic risk through Requested review lanes may still be right, but retiring automatic security-review selection is a decision that must be made and recorded rather than discovered during implementation. The finding also exposes a gap in this change's own gate: AC-2's old/new census cannot detect it, because a lane that never fired historically shows a zero delta and the regression reads as free. Three alternatives named; AC-4b requires the chosen branch to be pinned by a test. | Executed enumeration of `RISK_TRIGGER_LANES` path-shaped versus semantic tokens per lane; `review_policy.py:40-48` |
| 2026-08-05 | Prepare-review verification and one blocking finding, repaired. VERIFIED against the tree: all 20 Serialization Points paths across the three change docs resolve on disk; `review_policy_upgrade.py:74-119` is the region claimed, with the `policy_unchanged` guard at `:81` and its `continue` at `:98`; the selector probe reproduces the recorded live rosters exactly (this doc five lanes, each sibling code+qa+docs-contract); and a simulation scoring ONLY Serialization Points paths returns code+qa+docs-contract for all three, so AC-4a's target roster is achievable. FINDING (blocking, folded): nothing anywhere anticipated that the 3-to-4 bump stales THIS wave's own receipt. Measured on this wave's own change-doc bytes, identical input: `dd1fb564…` at evaluator 3, `13e15b5c…` at evaluator 4. Because a stale receipt gates guided signoff recording, delivery approvals become unrecordable the moment the constant moves. Requirement 4 now discloses it with both digests and the exact insertion points, a Risk row carries the sequencing remedy, and the wave record carries a blocking sequencing watchpoint: land the constant move last, re-Prepare once, re-affirm readiness before any delivery approval. | Executed `policy_input_digest` over this wave's three change docs at evaluator 3 and a patched 4; path-existence sweep over all three Serialization Points blocks; `review_policy.py:434`; `review_policy_upgrade.py:81`, `:98`; memory `1uejb-mem` for the deliberate no-receipt exemption |
| 2026-08-05 | Review replaced the unimplementable "declared scope prose" source with the smallest explicit contract: only repo-relative paths in the existing Serialization Points section are automatically scored, while non-path risks use the existing Requested review lanes field. The evaluator must move 3 to 4, and the census is bounded to upgrade-affected non-closed waves rather than creating a historical classification backlog. Adding paths corrected the live sibling rosters immediately, so the original under-recruitment is now a frozen pre-declaration fixture rather than a false claim about the amended files. | `docs/plans/plan-template.md:19-52`; `review_policy.py:391-421`; `review_policy_upgrade.py:74-119`; current selector probe: `1ug66`/`1ug68` = code+qa+docs-contract; 999 Markdown records currently under `docs/waves/` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-05 | Score explicit Serialization Points paths rather than the whole corpus or Scope prose | Risk in this codebase is not proportional to diff size, so triggers remain intact. Paths are the minimal machine-readable declaration already near the plan's coordination surface; semantic risks use Requested review lanes instead of inferred prose | Score Scope prose (rejected: the template provides no machine-readable scope grammar); score the diff (rejected: no prepare-phase input); reduce lanes by change size (rejected: size is not the risk signal here) |
| 2026-08-05 | ~~File separately from `1ug66-enh` and `1ug68-enh`~~ **SUPERSEDED — operator admitted all three into wave `1ui1d review-loop-friction`** | The original reasoning stands and is retained: this is the only one of the three that changes risk posture, so it must not ride along invisibly behind coverage-neutral work. What changes is the remedy. Sharing a wave does not merge the approvals: each change carries its own ACs, and AC-2's bidirectional coverage census is this change's own gate. The obligation the separate-wave plan was buying is preserved by making it explicit instead: the coverage census must be adjudicated as a named item at the delivery council rather than folded into a wave-level verdict, and the council record must state the roster deltas it accepted | Keep it in its own wave (superseded by operator direction 2026-08-05); bundle silently and rely on the wave-level approval (rejected: that is exactly the risk the original entry identified) |
| 2026-08-05 | Treat under-recruitment as in scope rather than as a follow-up | It is the same mechanism and the same line of code. A fix that narrowed the corpus without addressing it would ship a measurable coverage REDUCTION while claiming coverage neutrality, and the plan's own sibling `1ug66-enh` is the counterexample sitting in the same wave | File under-recruitment separately (rejected: a corpus-narrowing change cannot be safely reviewed without it, since narrowing is what makes it worse); ignore it (rejected: measured, and it under-reviews a change to the digest function and the MCP tool surface) |
| 2026-08-05 | Security and performance are request-only risk-tiered exceptions | Their triggers are semantic rather than path-shaped. The existing `Requested review lanes` field is the smallest explicit declaration, and Prepare Council validates the choice; adding inference or another metadata field would recreate prose scoring complexity | Add path-shaped triggers (rejected: carrier lists are not a reliable semantic-risk proxy); add a new risk-declaration schema (rejected: duplicates the existing requested-lanes contract) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Narrowing automatic selection silently drops a lane that was genuinely warranted | AC-2 adjudicates every upgrade-affected non-closed wave, while AC-4 pins explicit paths and Requested review lanes separately |
| Authors omit a path to avoid reviewers | Explicit paths and Requested review lanes are reviewed at Prepare; AC-4a proves a sibling's concrete paths recruit the exact needed lanes rather than relying on prose inference |
| Path-only scoring silently retires automatic `security-reviewer` and `performance-reviewer` selection, and the coverage census cannot see it because those lanes may never have fired in the corpus | Requirement 5 forces an explicit recorded decision among three named alternatives before implementation, and AC-4b requires the chosen branch to be pinned by a test. The finding is measured from `RISK_TRIGGER_LANES` rather than inferred: those two lanes hold zero path-shaped tokens |
| The fix addresses over-recruitment only and ships a net coverage reduction while claiming neutrality | Requirement 2 is explicitly two-directional; AC-4a fails the change if `1ug66-enh` still draws one lane; AC-2 requires additions to be attributed as well as removals justified |
| The evaluator bump leaves an already-readied open wave on a stale roster | Requirement 4 requires v3-to-v4 upgrade migration to mark the affected non-closed declared wave for one re-Prepare, then pins public convergence |
| The bump stales this wave's OWN receipt mid-implementation, lapsing its readiness approvals and gating further signoff recording, and is misread as a defect | Measured and disclosed in Requirement 4 with both digests. Land the constant move last, take exactly one re-Prepare, re-affirm readiness under the fresh receipt before any delivery approval. The wave record carries the same sequencing watchpoint |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
