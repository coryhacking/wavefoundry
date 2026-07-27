# Code-Grounded Verification As A Core Tenet Of Creating, Reviewing, And Implementing

Change ID: `1tmb4-enh code-grounded-verification-as-core-tenet`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-26
Wave: `1tmb1 review-loop-readiness-clearing-path`

## Rationale

The framework tells **reviewers** to verify a plan's claims against the code. It never tells
**authors** or **implementers** the same thing. That asymmetry is **undocumented and unexamined**, not
a recorded choice: wave `1p9pk` deliberately excluded two things, the delivery council (already
expected to verify against code) and programmatic enforcement, and authoring was simply never in its
frame. Nothing needs overturning to close it. The gap has already failed once and has now failed again
in the same shape.

Two sites carry the review-side rule, in **different wording**, which matters for the pin in AC-6.
Anchor by **symbol and quoted string** — the literal line numbers below have already drifted twice
during this wave's own review window and are advisory only:

- `_build_prepare_council_brief` (`server_impl.py`, symbol at `:12504`, string at `:12519` as of the
  prepare council's read):
  *"Verification must be code-grounded: verify each **plan's** load-bearing claims against the actual
  tree, not against the **plan's** own prose…"*
- Seed `237-council-review.prompt.md:49`: *"**Verify code-grounded:** check the **artifact's**
  load-bearing claims against the actual tree, not against the **artifact's** own prose…"*

Both continue: cited `file:line` sites and symbols must resolve, "X already does Y" claims must hold in
the code, and "no other caller/site" censuses must be complete.

Seed 237 adds the reason: *"A readiness review answerable purely from plan prose is how nonexistent
symbols, wrong caller censuses, and no-op mechanisms pass review."*

That text exists because of wave `1p9pk`, which hardened it after a plan carrying a **no-op
mechanism, a nonexistent cited helper, and a wrong caller census** passed a thin prepare-council
review. `1p9pk`'s Scope confined the fix to the prepare/readiness phase, and its Decision Log recorded
the choice to keep code-grounded verification a review-side contract rather than a programmatic gate,
on the ground that "a validator cannot verify a human/agent actually read the code."

**The same three defect shapes recurred on 2026-07-26**, in a wave whose four change documents were
authored by one agent and then reviewed by a two-seat prepare council:

| `1p9pk`'s original shapes | Recurrence, 2026-07-26 |
| --- | --- |
| no-op mechanism | `1tjjj` routed Codex MCP registration through `detect_platforms`, which keys on `.codex/` existing. Executed against a Guru-absent repo: nothing under `.codex/` is created, so detection never fires and the defect the change exists to fix survives it. |
| nonexistent cited target | `1tjjj` scoped "the Codex row of the seed `050` capability matrix insofar as it concerns MCP registration ownership". A census of every `codex` occurrence in that seed found no MCP column and no `.codex/config.toml` reference; the target does not exist. |
| wrong census / wrong object | `1tmaz` scoped its fix to the published `required`/`properties`. Applying exactly that to a live tool and re-calling dispatch still raised `kwargs \| Field required`, because dispatch validates `fn_metadata.arg_model`, not `tool.parameters`. |

A fourth shape appeared that `1p9pk` did not name: **a decision justified by a benefit that does not
exist.** `1tmaz`'s Decision Log kept `**kwargs` on tool signatures because the typed
`unknown_arguments` envelope was "behavior worth keeping". Three argument shapes executed through
dispatch returned `ok`, `ok`, and a raw pydantic error. The envelope never fires. The design choice
was made against a benefit the code does not deliver, and no reviewer would have caught it from the
plan's own text because the plan read as coherent.

Every one of these was killed by **executing** the claim. None was killed by reading or reasoning.
The plans were internally consistent and plausible throughout.

### Why review-only is structurally insufficient

The review-side rule works. It caught all four. But it can only catch them **after** a full plan is
written on a false premise, which costs a complete authoring pass plus a council round per defect, and
it leaves two phases uncovered:

- **Authoring** has no rule at all (verified: seed `170-plan-feature.prompt.md` contains eight
  occurrences of "execut" — `:41`, `:47`, `:53`, `:60`, `:67`, `:127`, `:168`, `:186` — and **none of
  them states a code-grounded verification rule**. They are the diverge/critique/select pass, the
  Agent Execution Graph, and wave-execution timing. The claim is that no occurrence states the rule,
  not that the occurrences fall into two categories).
- **Implementing** has no rule either (verified: all fifteen "execut" occurrences in seed
  `180-implement-feature.prompt.md` — `:7`, `:19`, `:21`, `:24`, `:37`, `:78`, `:81`, `:187`, `:189`,
  `:190`, `:201`, `:219`, `:230`, `:231`, `:232` — refer to *wave* execution, never to executing a
  premise). An
  implementer who builds on a plan's stated premise without exercising it produces a working-looking
  change resting on a false foundation, and only the delivery review can catch it.

### The framework already owns the vocabulary; it is fenced off from planning

Seed `209-agent-harness-core.prompt.md`'s Executable Review Evidence Protocol already distinguishes
exactly what is needed:

- `execution_status` (`209:81`): `executed`, `inferred`, `unverified`, `not_applicable`
- `known_bad_detected` (`209:92`): "true only when the pre-fix/focused-mutation/injected-old behavior
  failed as intended"

Both are review/repair-cycle fields, never invoked from the planning or implementation seeds. Nothing
new needs inventing; the distinction needs to become available where plans are written and where code
is changed. Reusing the existing vocabulary is also what keeps three phase statements from drifting
into three different rules, which is a failure mode this repository has repeatedly produced.

Relatedly, the MCP-first exploration order in seeds `180` and `211` is entirely about **reading**
tools (`code_ask`, `code_search`, `code_definition`, `code_references`). It answers "MCP tools versus
grep" and never "reading versus executing". An agent can follow that order perfectly and still assert
a false mechanism, which is what happened.

## Requirements

1. Code-grounded verification is stated once, canonically, as a tenet applying to **creating,
   reviewing, and implementing**, using the `execution_status` vocabulary that already exists in seed
   `209` rather than new terms.
2. The existing review-side rule in seed `237` and `_build_prepare_council_brief` is **retained
   unchanged in force**. This change adds obligations at two more phases; it does not relocate or
   weaken the one that works.
3. **Authoring:** before a claim about existing code becomes a Requirement, an Acceptance Criterion,
   a Scope item, or a Decision Log rationale, it is verified against the tree, and preferentially
   *executed* where executable. Claims that cannot be executed are marked as `inferred` or
   `unverified` in the plan rather than asserted flatly.
4. Two claim shapes are named as requiring the strongest evidence, because they are the ones that
   have now failed twice: **"X already does Y"** mechanism claims, and **"no other caller/site"**
   censuses. A third is added from this recurrence: **a Decision Log rationale asserting a benefit**
   must have that benefit observed, not assumed.
5. **Implementing:** a premise the plan states is exercised before code is built on it. A plan is
   evidence, not proof. Where the plan's premise proves false, the implementer stops and reports
   rather than adapting the implementation to preserve the plan's conclusion.
6. The reading-versus-executing distinction is stated where the exploration order lives, so following
   the MCP-first order is not mistaken for having verified a mechanism.
7. **Authoring counterpart to the known-bad rule:** seed `209:126` already requires a *reviewer* to
   confirm a claimed test would fail against the known-bad behavior. Authors get the corresponding
   obligation: write each Acceptance Criterion so that an implementation with the fix absent cannot
   satisfy it, and state the failing condition where it is not obvious.
8. No seed states the tenet in its own words where a cross-reference would do. Phase seeds carry the
   phase-specific application and point at the canonical statement.

## Scope

**Problem statement:** code-grounded verification is a review-phase contract only. Authors and
implementers are never told to verify their load-bearing claims against the code, so plans are written
on unexecuted premises and implementations are built on unexercised ones, with the prepare council as
the sole backstop. The identical defect class was hardened review-only in wave `1p9pk` and has
recurred.

**In scope:**

- Canonical statement of the tenet in `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`,
  adjacent to the Executable Review Evidence Protocol whose vocabulary it reuses.
- Authoring application in `170-plan-feature.prompt.md`, attached to the existing pre-plan
  diverge/critique/select pass at `:41` and to the AC-quality guidance at `:73`.
- Implementing application in `180-implement-feature.prompt.md`, attached to the existing
  pre-implementation orientation step at `:219` that already treats recorded past mistakes as
  constraints.
- The reading-versus-executing distinction in the MCP-first exploration order (`180`, and `211-guru`
  where it is restated).
- Cross-references from `237-council-review.prompt.md` and `215-wave-council.prompt.md` to the
  canonical statement, **without** altering the review-side rule's force or wording.
- `docs/contributing/review-and-evals.md:101`, which **already restates the tenet in its own words**
  ("Seat verification must be code-grounded…"). Requirement 8 forbids exactly that going forward, so
  this is an existing instance to reconcile, not merely a doc that "should reference" the tenet.
- **Two further live restatement sites the render pipeline cannot reach** (prepare-council census):
  `docs/prompts/council-review.prompt.md:46`, a full verbatim copy of seed `237:49` sitting OUTSIDE
  the renderer-owned marker region (`:105-130`), and `docs/agents/guru.md`'s retrieval-loop body,
  which mirrors seed `211` verbatim outside its marker region (`:701-726`) and is the surface this
  repository's routing actually sends agents to. Both are reconciled by hand and covered by the
  AC-1/AC-5 sweeps.
- `docs/contributing/agent-team-workflow.md:106`, a stale pointer claiming the exploration order
  lives in `docs/prompts/implement-feature.prompt.md` (it contains none). Pre-existing drift, named
  here because it would misdirect the AC-5 census; reconcile in the same pass.
- `175-interrogate-plan.prompt.md`: assess whether plan interrogation should surface unexecuted
  load-bearing claims. Its contract currently resolves unresolved decision branches and explicitly
  treats the Decision Log as out of scope (`175:42`), which is where the false-benefit rationale
  lived. Audit and act, or record why not.
- Rendered project surfaces regenerated from the changed seeds (marker regions only; the named
  out-of-region sites are hand-reconciled per AC-8).

**Out of scope:**

- **Mechanical enforcement of cross-section contract consistency** within a change document (the
  "repair applied where the finding points, not everywhere the concept lives" failure mode). It is a
  genuine gap on both authoring and review sides, it is mechanically detectable unlike this tenet, and
  it belongs in its own change. Held by operator direction.
- Changing the review-side rule, its wording, or the council brief's generation.
- Any programmatic gate attempting to verify that an agent executed something. `1p9pk`'s reasoning
  stands: a validator cannot confirm code was read or run. This change is prose, and its honest limit
  is stated below.
- The `execution_status` field semantics or the review evidence ledger schema.

## Acceptance Criteria

- [x] AC-1: Seed `209` states the tenet once, naming all three phases, and reuses `execution_status`
  vocabulary rather than introducing parallel terms. A test asserts the canonical statement exists and
  that no phase seed duplicates **the canonical definition sentence**. It must NOT forbid phase seeds
  from carrying their own phase obligations, which Requirement 8 requires and AC-2 mandates for seed
  `170`; the anti-duplication target is the definition, not the obligation. A test written against the
  looser reading would fail AC-2 by construction.
- [x] AC-2: Seed `170` requires load-bearing claims about existing code to be verified before entering
  Requirements, Scope, Acceptance Criteria, or the Decision Log, names the three high-risk shapes
  ("X already does Y", "no other caller/site", and a rationale asserting a benefit), and requires
  unexecutable claims to be marked rather than asserted flatly.
- [x] AC-3: Seed `170` requires each AC to be written so an implementation with the fix absent cannot
  satisfy it, as the authoring counterpart to `209:126`. A test pins that the authoring and review
  statements of this rule remain consistent with each other. **That test is contract-presence evidence
  only**, in `209:126`'s own terms: it proves the obligation is stated, not that any author honored it.
  The obligation is enforced by review, not by the test, and the AC must not be read as verifying it.
- [x] AC-4: Seed `180` requires a plan premise to be exercised before code is built on it, and defines
  the stop-and-report path when a premise proves false, rather than leaving an implementer to adapt
  the implementation to preserve the plan's conclusion.
- [x] AC-5: The reading-versus-executing distinction appears wherever the MCP-first exploration order
  is stated. A test asserts every location carrying the exploration order also carries the
  distinction, so a future copy cannot omit it. The census domain is seeds `180` and `211` (the ~25
  role seeds, `020:88`, `050:162` and `AGENTS.md` all carry explicit point-do-not-restate pointers)
  **plus the live `docs/agents/guru.md` copy**, which mirrors seed `211` outside any renderer-owned
  region. Detection keys on the ordered tool-list signature (`180:116ff` / `211:116ff`) rather than a
  prose phrase, so a paraphrased copy is still caught.
- [x] AC-6: The review-side rule is **unchanged in force** at **both** sites, which carry different
  wording and therefore need two pins: `_build_prepare_council_brief` ("each plan's"; anchor by
  symbol and quoted string — the line number drifts) and seed `237:49` ("the artifact's"). One pin
  cannot cover both.
  **Tests already exist at both sites and assert substring presence only:**
  `test_docs_lint.py:2283` (`test_seed_237_requires_code_grounded_verification`, asserting "Verify
  code-grounded", "sites and symbols must resolve", "censuses must be complete") and the
  corresponding `_build_prepare_council_brief` coverage in `test_server_tools.py`, both shipped by
  wave `1p9pk` AC-5. Exact-value pinning is a genuine delta over substring presence, but the delta
  must be stated rather than the existing tests rediscovered.
  **The guard is proven by mutation, not by passing.** Demonstrate each pin **fails** against a
  deliberately mutated string, and the mutation must be one **the pre-existing substring tests
  survive** (for example, changing "each plan's" to "each artifact's" in the
  `_build_prepare_council_brief` string, which preserves every substring the `1p9pk` tests assert —
  grep-verified by the prepare council across the full test tree). A whole-string deletion also fails the
  substring tests and therefore proves nothing about the exact-value delta this AC exists to create.
  A pin that merely passes proves only that the string exists. An implementation that runs the
  existing tests and writes nothing does **not** satisfy this AC.
- [x] AC-7: `175-interrogate-plan.prompt.md` is audited for whether unexecuted load-bearing claims
  belong in its interrogation contract, with the outcome recorded either way. Audit-and-skip is an
  acceptable result; a silent skip is not.
- [x] AC-8: The self-hosted surfaces are reconciled by the mechanism that actually governs each.
  **The render pipeline does NOT propagate seed body edits**: `render_agent_surfaces.py` upserts only
  the hardcoded `REVIEW_PROTOCOL_CARRIER_BLOCK` marker region (`reconcile_review_protocol_surfaces`,
  `:1076`) and fresh-only lifecycle baselines (`reconcile_lifecycle_prompt_baselines`, `:1115`, which
  skips every existing file). So: (a) marker-fenced regions are regenerated, never hand-edited;
  (b) the two live restatement sites OUTSIDE marker regions — `docs/prompts/council-review.prompt.md:46`
  (verbatim copy of seed `237:49`'s "Verify code-grounded" bullet) and `docs/agents/guru.md`'s
  retrieval-loop body (mirroring seed `211`, e.g. `guru.md:669` == `211:680`) — are reconciled **by
  hand**, since no renderer reaches them; and (c) the AC-1/AC-5 anti-drift tests sweep these named
  live copies as well as `seeds/`, so a future seed edit cannot silently strand the operative Guru
  surface again. An implementation that re-renders and declares the prompts "matching" without
  touching (b) does not satisfy this AC.
- [x] AC-9: Docs gate and full framework suite green.

## Tasks

- [x] Draft the canonical statement for seed `209`, reusing `execution_status` and cross-referencing
  the existing `known_bad_detected` rule rather than restating it.
- [x] Write the AC-1 and AC-5 anti-drift tests first, and confirm they fail before the seed edits.
- [x] Read the existing `1p9pk` AC-5 tests at both AC-6 sites first, state the delta from substring
  presence to exact-value pinning, then write both pins and **demonstrate each fails against a mutated
  string**. Do not treat a passing run of the pre-existing tests as satisfying AC-6.
- [x] Open `seed_edit_allowed`; edit `209`, `170`, `180`, `211`, `237`, `215`; close the gate
  immediately after.
- [x] Audit `175-interrogate-plan.prompt.md` per AC-7 and record the outcome.
- [x] Re-render platform and agent surfaces for the marker-owned regions, then hand-reconcile the
  three named out-of-region restatement sites (`council-review.prompt.md:46`, `guru.md`
  retrieval-loop body, `review-and-evals.md:101`) and the stale `agent-team-workflow.md:106` pointer.
  Re-rendering alone does not reach them.
- [x] Full suite and docs gate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| guard-tests | implementer | — | AC-6: two pins, each proven by mutation the substring tests survive; AC-1/AC-5 must fail before edits |
| canonical-209 | implementer | guard-tests | One statement, existing vocabulary |
| phase-seeds | implementer | canonical-209 | `170`, `180`, `211`; cross-refs only in `237`, `215` |
| interrogate-audit | implementer | canonical-209 | AC-7; audit-and-skip permitted, silent skip not |
| render | implementer | phase-seeds | Regenerate marker regions; hand-reconcile the three named out-of-region sites per AC-8 |

## Serialization Points

- Seed edits require `seed_edit_allowed`, opened and closed around the seed task.
- **`1tmb0` is not in this wave.** It declares `Wave: 1tj0l cwd-independent-host-surface-launchers`
  and `Change Status: implemented`, and its seed `209` edit is already in the working tree, at the
  *Repair re-verification* and *Lane-clearing recipe* paragraphs (`~:157-162`) — a different section
  from this change's target (`~:75-126`). There is no concurrent-edit hazard to sequence.
- **The constraint that actually binds:** `1tj0l` is `implementing` and holds the single OPEN slot.
  `1tmb1` may be readied in parallel, but implementation cannot begin until `1tj0l` closes.
- Marker-fenced regions under `docs/prompts/` are renderer-owned; regenerate rather than editing.
  Content OUTSIDE marker regions in `council-review.prompt.md` and `guru.md` is project-authored and
  is reconciled by hand per AC-8; the render pipeline never reaches it.

## Affected Architecture Docs

`docs/contributing/review-and-evals.md` **already restates the tenet in its own words at `:101`**
("Seat verification must be code-grounded…"), which Requirement 8 forbids going forward; it is
reconciled to reference the canonical statement, per Scope, not merely pointed at it. No ADR: this extends an existing documented practice to two further phases rather than
choosing a new architecture. `1p9pk`'s decision to keep this prose rather than programmatic is
preserved, not revisited.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The tenet stated once is what prevents three phase copies drifting into three different rules, which this repository has repeatedly produced. |
| AC-2 | required | The authoring gap is the one with two recorded recurrences; without it the change does not address its own rationale. |
| AC-3 | required | An AC an absent fix can satisfy is the defect that let a laundering escape hatch into a required AC during the motivating incident. |
| AC-4 | required | Implementing is the phase where a false premise becomes shipped code rather than a rejected plan. |
| AC-5 | required | An agent can follow the MCP-first order perfectly and still assert a false mechanism; that is exactly what happened. |
| AC-6 | required | This change must not weaken the only phase that currently works. Pinning it is cheap and the failure mode is severe. |
| AC-7 | important | The false-benefit rationale lived in a Decision Log, which plan interrogation explicitly excludes today. Worth deciding deliberately. |
| AC-8 | required | Seeds ship to every target repository; a stale rendered surface distributes the old guidance. |
| AC-9 | required | Standard gates. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-26 | **Delivery cycle 3 repairs (operator-commissioned independent closure review).** The reviewer landed a third-round falsification: AC-8(c) claimed the anti-drift tests sweep the named live copies, but no test read `docs/prompts/council-review.prompt.md:46`; mutating its rule line left all guards green (reproduction re-executed by the implementer before recording). Also: the AC-5 signature missed Markdown-equivalent markers (`*`/`+` bullets, `N)` numbering), proven by evading plants. Repairs: the seed 237 pin test now also pins the live copy (guarded by existence for target repos), and the signature regexes accept the marker classes. Both proven red by the exact reproductions, reverts sha256-verified, full module green. Accepted limits recorded: a fully prose-paraphrased order with no list structure evades the structural signature (F3-adjacent); AC-1's anti-duplication is exact-string and phase-seed-scoped, weaker than Requirement 8's "no seed" (F3); repo-root `AGENTS.md` carries a project-authored Quick chooser tripping the bullet signature without the distinction, outside AC-5's domain (F4) — flagged for the deferred mechanical-consistency change rather than silently absorbed. | Findings `1tmb4-ac8-live-copy-sweep-claim-unexecuted`, `1tmb4-ac5-signature-misses-markdown-equivalent-markers` (cycle 3, repair_start before mutation); independent review report; probe transcripts |
| 2026-07-26 | **Delivery cycle 2 repairs.** The delivery council raised two blocking findings against the guards themselves, one falsified by execution: it planted a paraphrased exploration-order copy in seed 215 and the AC-5 test passed with it present (hardcoded file list keyed on the prose phrase, violating AC-5's own signature-keyed contract); and the AC-3 pairing pin asserted only the 170 side, so deleting 209's Reviewing statement left the suite green. Repairs: AC-5 test rewritten as a structural-signature scan (numbered `code_*` list, Quick Rules heading, or `- Use `code_` bullet run) over all seeds plus live guru.md, with a non-vacuity guard requiring the known carriers to trip the signature; a mention-count signature was measured and REJECTED because it trips 26 point-do-not-restate posture leads. AC-3 pin extended to 209's Reviewing bullet. Both repaired guards proven by known-bad probes: planted copy in 215 makes AC-5 FAIL (sha256-identical revert), deleting the Reviewing bullet makes AC-3 FAIL (restore verified in original bullet order). Full suite 6248 OK after repairs. | Council findings `1tmb4-ac5-test-not-signature-keyed`, `1tmb4-ac3-consistency-pin-one-sided` (cycle 2, `repair_start` recorded BEFORE mutation); probe transcripts; signature census output |
| 2026-07-26 | **Implemented.** Guard phase first: exact-value pins added at both sites; each demonstrated failing against a mutation the pre-existing substring tests survive ("each plan's" to "each artifact's" at the server string: substring test OK, pin FAILED, reverted, pin OK; "the artifact's" to "the plan's" in seed 237: same shape), then the four anti-drift tests confirmed red before any seed edit. Canonical tenet statement added to seed 209 ("Code-Grounded Verification (All Phases)") reusing `execution_status`; authoring obligation with the three claim shapes and the fix-absent AC rule added to 170; premise-exercise with stop-and-report added to 180; reading-vs-executing distinction added to 180, 211 and the live `guru.md` copy; cross-refs added to 237 (below the pinned rule, which stayed byte-identical) and 215; `review-and-evals.md:101` reconciled to reference; `agent-team-workflow.md:106` stale pointer corrected. Render confirmed byte-stable (diff-stat identical before/after). All six anti-drift tests green; full suite 6248 tests OK; both gates opened and closed around their tasks. | Mutation demo transcripts (substring OK / pin FAILED / revert OK at both sites); `run_tests.py` 6248 OK; render diff-stat comparison |
| 2026-07-26 | AC-7 audit outcome: **audit-and-skip, recorded.** Seed 175's interrogation contract resolves operator-judgment branches (`175:40-42`) and explicitly excludes the Decision Log. Surfacing unexecuted load-bearing claims there would duplicate the author's new obligation (170) upstream and the prepare council's contract (237) downstream, blurring 175's bounded scope. The false-benefit shape that motivated the question is addressed at authoring time by the third named claim shape. No 175 edit. | `175:30-55` read directly; Decision Log row below |
| 2026-07-26 | Prepare-council repairs. Docs-contract seat falsified AC-8's render-model premise by reading the pipeline: `render_agent_surfaces.py` upserts only the hardcoded `REVIEW_PROTOCOL_CARRIER_BLOCK` (`:1076`) and fresh-only baselines (`:1115`); seed body edits never flow to `docs/prompts/`. AC-8 rewritten to split marker-region regeneration from hand-reconciliation; two unreachable live restatement sites added to Scope (`council-review.prompt.md:46`, `guru.md` retrieval-loop body) plus the stale `agent-team-workflow.md:106` pointer; AC-5's census extended to the live Guru copy with a tool-list-signature detection key. Red-team seat PASSed after quoting both current pin strings and grep-proving the mutation survives every pre-existing test assertion; its two staleness notes are folded (symbol `:12504`, string `:12519`, cited as advisory with symbol+string as the anchor) and its unrecorded alternative is now a Decision Log row. | Prepare-council docs-contract seat F1/F2/F3 and red-team seat F1/F2; `render_agent_surfaces.py:1076,:1115` read directly |
| 2026-07-26 | Reverification raised R5 and R6; repair cycle 1 opened for all six findings (`repair_start` recorded, with the R1-R4 out-of-order edits disclosed in their records rather than implied ordered). R5: "fourteen" corrected to "fifteen" against an enumeration of fifteen and a grep count of fifteen. R6: four sections still asserted refuted claims after the AC-level repairs (Risks x2, Agent Execution Graph, Affected Architecture Docs); all four reconciled, then a whole-document sweep run for superseded formulations rather than trusting the four named sites to be the extent. AC-6 additionally tightened per the council's residual: the mutation demonstrated must be one the pre-existing substring tests survive, e.g. "each plan's" to "each artifact's", since a whole-string deletion proves nothing about the exact-value delta. R6 is the "repair applied where the finding points, not everywhere the concept lives" failure mode occurring inside the document that names it; recorded in the ledger as evidence for the deferred mechanical check. | Council reverification report; ledger records at cycle 1; grep sweeps over 1tmb4 |
| 2026-07-26 | Readiness council returned NOT READY with four blocking findings, all text repairs, all applied. R1: cited `server_impl.py:12451-12457` resolved in neither the working tree nor HEAD (symbol is at `:12503`, string at `:12518`) and the seed `170` census named two categories while omitting four occurrences; both corrected, and the brief-generator is now cited by symbol so it is line-stable. R2: AC-6 was written without knowing `1p9pk` AC-5 already shipped substring tests at both sites, and its "confirm it passes before any edit" task was satisfiable by a no-op, which this change's own AC-3 forbids; rewritten to require mutation-proven pins at two sites carrying different wording. R3: Serialization Points named `1tmb0` as a co-change, but it is in `1tj0l` and implemented; replaced with the constraint that actually binds. R4: `wave.md` sections were template placeholders. Also corrected the "deliberate and documented" overstatement: `1p9pk` excluded the delivery council and programmatic enforcement, never authoring, so this is an unexamined gap and no prior reasoning needs overturning. | Readiness council, findings R1-R4; `review_evidence.py:1199`; `server_impl.py:12503,12518`; `237:49`; `test_docs_lint.py:2283` |
| 2026-07-26 | Filed after a prepare council raised fifteen findings against four change documents, four of which were load-bearing claims falsified by execution. Root-caused to an asymmetry: the review side carries a code-grounded verification rule, the authoring and implementing sides carry none. Claims verified directly rather than inherited from the survey: seed `170` contains no code-grounded rule (its "execut" hits are the diverge/critique pass and the Execution Graph); seed `180`'s "execut" hits all refer to wave execution, never to executing a premise; seed `209` carries `execution_status` at `:81` and `known_bad_detected` at `:92`. | `server_impl.py:12451-12457`; `237:49`; `170:41,73`; `180:219`; `209:81,92,126,222`; wave `1p9pk` Scope and Decision Log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-26 | AC-7: do not extend seed 175's interrogation contract to unexecuted load-bearing claims. | Interrogation is bounded to resolving operator-judgment branches in Requirements/ACs/Scope; verification duties there would duplicate seed 170's new authoring obligation and seed 237's council contract while blurring a deliberately narrow surface. The Decision Log exclusion at `175:42` stands because the false-benefit rationale shape is now caught at authoring time. | Add an interrogation item for `inferred`/`unverified`-marked claims (rejected: those markers already route to the prepare council, which is the verification venue); silently skip the audit (forbidden by AC-7). |
| 2026-07-26 | Keep the two review-side sites' divergent wording ("each plan's" / "the artifact's") rather than unifying them into one shared constant rendered into both. | Requirement 2 retains the working rule unchanged in force; rewording the one phase that already works, in order to simplify its guard, inverts the risk ordering. Two pins cost little. Recorded because the prepare council correctly noted this alternative was implied but never written down. | Shared canonical constant rendered into brief and seed (rejected: touches the protected strings this change exists to leave alone); leave undocumented (rejected: an unrecorded rejection reads as an oversight). |
| 2026-07-26 | Add the tenet at authoring and implementing; do **not** move it from review. | Operator direction, and correct: relocating it would trade one gap for another, and the review-side rule demonstrably caught all four defects in the motivating incident. It is a tenet of creating, reviewing, and implementing, not a review procedure. | Move the rule upstream to authoring (rejected: removes the only phase currently working); leave review-only (rejected: that is the state that just failed for the second time). |
| 2026-07-26 | State it once in seed `209` and cross-reference from phase seeds, rather than writing it into each. | Three independently-worded copies of "verify your claims" is the drift class this repository keeps producing, and `209` already owns the `execution_status` vocabulary the tenet needs. | Write phase-specific statements in each seed (rejected: guarantees drift); put it in `AGENTS.md` only (rejected: `AGENTS.md` is rendered per project, seeds are the framework source of truth). |
| 2026-07-26 | Keep this change prose-only, and hold mechanical enforcement of cross-section consistency for a separate change. | `1p9pk`'s reasoning holds for this tenet: no validator can confirm an agent executed something. It does **not** hold for cross-section contract consistency, which is mechanically detectable, so that belongs in its own change with its own argument rather than riding along. Held by operator direction. | Fold both together (rejected: conflates an unenforceable tenet with an enforceable check); add a validator here (rejected: cannot verify execution, and would create false confidence). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The change weakens the review-side rule while adding the others | AC-6 requires two exact-value pins, one per site (the two sites carry different wording), each demonstrated to FAIL against a mutated string the pre-existing substring tests survive. A pin that merely passes proves only that the string exists. |
| Three phase statements drift apart over time | AC-1 requires one canonical statement, with a test forbidding duplication of the canonical definition sentence only; phase seeds keep their own phase obligations, which AC-2 mandates. |
| The tenet reads as "read the code more", which agents already believe they do | The statement is anchored on `execution_status` and names the three claim shapes that actually failed, so it is a specific obligation rather than a disposition. |
| Prose alone does not change behavior, and this change cannot prove it did | Acknowledged and unmitigated by design. `1p9pk` established that execution cannot be validated programmatically. The honest test is recurrence: if these shapes appear again after this lands, the conclusion is that prose is insufficient and the enforceable subset must be found. Recorded here so a future reader can judge it on that basis rather than assuming it worked. |
| The change ships prose while holding back the mechanical half of its own precedent's pattern | Acknowledged explicitly. `1p9pk` paired its unenforceable prose contract with a mechanical backstop (the roster-to-evidence validator) and recorded that pairing as what gives it teeth. This change ships the prose half only, by operator direction, with cross-section consistency held for a separate change. That is a knowing choice, not an oversight, and it raises the weight of the recurrence test above. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
