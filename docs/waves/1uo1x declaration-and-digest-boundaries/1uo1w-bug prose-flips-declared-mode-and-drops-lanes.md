# Prose Flips Declared Mode And Drops Lanes

Change ID: `1uo1w-bug prose-flips-declared-mode-and-drops-lanes`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-07
Wave: 1uo1x declaration-and-digest-boundaries

## Rationale

Field report from a downstream repository, reproduced on this tree. One sentence of narrative prose inside `## Serialization Points` silently removes required review lanes.

```
prose only, NO slashed token
  extracted paths : ()
  lanes           : ['qa-reviewer', 'architecture-reviewer']

same prose + "Spec wording lands in docs/specs/ alongside the code."
  extracted paths : ('docs/specs/',)
  lanes           : ['docs-contract-reviewer']
```

The `-bug` and `state machine` risks did not go away. `select_required_review_lanes` treats **any** extracted path as proof the author adopted the declared-target contract and switches the whole wave off prose scoring (`review_policy.py:576-577`, `if paths: undeclared = []`).

**The measured worst case is not a reduced roster but an empty one.** Independent review found two of four realistic prose sentences collapse the roster to nothing:

| prose inside the section | extracted | lanes before, after |
| --- | --- | --- |
| "Shared with the wave that also touches the docs/ folder" | `('docs/',)` | `[qa, architecture]`, `[]` |
| "Blocked on `docs/waves/1uo1x .../wave.md`" | `('declaration-and-digest-boundaries/wave.md',)` | `[qa, architecture]`, `[]` |
| "the src/ layout is unchanged" | `('src/',)` | `[qa, architecture]`, `[code]` |

`_is_declared_target` (`:448`) was written to reject `runner/test`, and the pinned test at `tests/test_review_policy.py:1502` shows the authors anticipated this class. A trailing-slash token such as `docs/` passes the predicate anyway.

**A correct declaration triggers the same failure.** `_REPO_PATH_RE` has no space in its character class, so `docs/waves/<id> <slug>/wave.md` shreds into `['docs/waves/1uo1x', 'declaration-and-digest-boundaries/wave.md']`. The second fragment has a dot in its final segment, so it **is** accepted as a declared target: a phantom that matches no risk trigger, flips the wave into declared mode, and yields **zero** required lanes. Declaring a real, on-disk, wave-owned artifact is therefore actively harmful today.

**An earlier revision of this plan proposed a bullet floor that scanned bullet lines for path tokens. The readiness council disproved it.** Real prose in Serialization Points sections is mostly written as bullets, so a floor that scans bullets re-admits the reported defect for its most common carrier: `- Shared with the wave that also touches the docs/ folder` is a bullet, still extracts `docs/`, and still empties the roster. The pinned prose-rejection fixture at `test_review_policy.py:1512` is itself a bullet. The adopted floor is therefore **pure-path bullets**: a single-line `- ` or `* ` bullet declares targets only when, after removing backticks and separator punctuation, every remaining token is an accepted declared target. One residual English word makes the bullet prose, and prose contributes nothing. Continuation lines of a wrapped bullet are not scanned.

**Measured under the shipped floor at delivery** (815 change documents, 139 currently declared): 38 documents keep declared status, 101 revert to whole-document fallback, **zero documents lose a lane anywhere in the corpus**, and 95 documents gain lanes. The corpus grew by one unadmitted plan during the wave, which is why an earlier measurement in this document reads 814/138/37; the invariant AC-7 asserts is the zero, not the counts. The reverting set is dominated by prose-bullet misclassifications, 19 of which sit at an empty declared roster today, so reverting them is the defect being fixed, not migration damage. Live exposure is three documents: this wave's two plans, which keep declared status under the floor, and the unadmitted plan `docs/plans/1rolq-enh verify-docs-agentic-review.md`, which reverts and gains three lanes, landing on a four-lane fallback roster, if it is ever admitted. No document anywhere needs an edit to preserve coverage.

The plan-time figure was 40 keeps rather than 37. The prototype that produced it predated Requirement 4's continuation-line disambiguation and accepted a wrapped bullet's first line, so it counted three documents (`1t0u4`, `1sufn`, `1tr85`) as declared. All three are prose sentences that happen to begin with a path (`- \`x.py\`, \`y.py\`, and the module owning ... form one protocol and must land together`), so classifying them as prose is the correct outcome and each gains lanes.

**The shipped guarantee this violates lives in four places, and none is the spec.** The sentence "coverage is never silently lost" (or its variant) ships at `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md:39`, `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md:22-24`, the embedded change-doc template in `server_impl.py` (`:17211-17214`), and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md:199`. The seed 160 carrier is the worst of the four, because the readiness council found it also states the exact rule this change deletes, in present tense, in a seed every upgrading target repository reads: "Adoption is per WAVE: as soon as any admitted change in a wave declares real paths, that wave scores on paths alone and prose stops recruiting for all of its changes." Two sibling sites in the same seed go stale with it: `:198` instructs upgrades to inject the old lane-derivation guidance into target repos' `plan-template.md` with no two-tier form, and the `:481` audit checklist should gain the two-tier form. The `:481` sentence "an undeclared change doc keeps whole-document fallback scoring" stays true under per-document adoption and needs no correction. An earlier revision counted three carriers; the census missed seed 160 because it grepped for one exact phrasing.

**The migration is opt-out.** Seed 160 correctly states existing change docs need no re-authoring. Combined with this defect, an un-migrated document whose prose happens to name a directory is already in declared mode with a reduced or empty roster, without its author ever opting in.

## Requirements

1. Adoption must be decided **per document**, never per wave. A wave containing one adopting document and one non-adopting sibling must score each in its own mode and union the result. Wave-level suppression is the defect: measured on a mixed wave, it turns `[code, qa, docs-contract]` into `[docs-contract]`.
2. A document that has not adopted keeps whole-document prose scoring, and no document may lose a required lane as a result of this change.
3. Prose inside `## Serialization Points` must not confer adoption, **including prose written as a bullet**. Only an explicit declaration form does.
4. The declaration form must be **two-tier**. Tier 1 is the pure-path-bullet floor: a `- ` or `* ` bullet whose content, after removing backticks and separator punctuation (`;`, `,`), consists entirely of accepted declared targets. Any residual word rejects the whole bullet as prose. **A bullet whose text wraps onto a continuation line is not a single-line bullet and is therefore prose in its entirety**; the floor never scans a bullet's first line and discards the rest. That disambiguation is load-bearing and measured: the discarding reading keeps more documents declared and silently drops the continuation-line targets of `1uf68-bug summary-schema-token-unobservable-on-non-nominal-runs.md`, swapping its `[docs-contract]` roster for `[code, release]`, which is the only lane loss either reading produces corpus-wide. Tier 2 is the explicit `**Review targets (repo-relative paths):**` block, the strict opt-in that additionally unlocks space-tolerant extraction and is where a wrapped multi-target declaration belongs.
5. Extraction inside the explicit block must tolerate spaces, so this project's own `<id> <slug>` artifacts are declarable. Inside the block, a backtick-delimited span is one target, spaces included; extraction is span-bounded, never regex-shredded. Spans are **lowercased like every other extracted target** (`review_policy.py:441`), because the footprint consumer folds case on the git side only and deliberately not on the target side (`server_impl.py:16333-16343`, where a prior delivery bug silently dropped every PascalCase declaration). The block itself is bounded: it consists of the bullet lines following the marker and ends at the first line that is neither a bullet nor blank. Fenced regions inside `## Serialization Points` are **not** scanned by either tier, matching the sibling normalizer's fence rule (`gardener_metadata.py:86-106`); zero change documents have a fence in that section today, so this fixes the shape before it exists rather than after. Pure-path bullets outside the marker block **still count when a block is present**: the tiers union, so adding a block can never silently drop a declaration that the floor already accepted.
6. The `_wave_code_footprint` consumer must accept a spaced target against real `git status --porcelain` output, in **both** the plain and rename entry shapes. The rename shape is currently broken: `R  "src/1x y/old.py" -> "src/1x y/new.py"` parses to `'"src/1x y/new.py'` because the quote strip runs before the ` -> ` split (`server_impl.py:16364`, `:16369-16370`), so the target never matches. **An earlier revision of this plan claimed the defect was unreachable today because no spaced target can be declared; the delivery QA lane disproved that by probe.** The pre-repair parse also dropped the UNSPACED rename shape (`R  src/plain/old.py -> src/plain/new.py` parsed to the whole `old -> new` string), so any declared file renamed with `git mv` was already being dropped from the advisory. The repair is therefore a live fix, not a pre-emptive one, and Requirement 5 only widens the shapes it covers.
7. A shredded path fragment must never become a declared target. The floor's all-tokens-accepted rule is the mechanism: an unbackticked spaced path splits into fragments of which the first (`docs/waves/1uo1x`) fails the declared-target predicate, so the whole bullet is rejected as prose and the document keeps its fallback. Silent loss of one declarable path is acceptable pending the explicit form; a phantom that suppresses the fallback is not.
8. The change must report its transition cost against the state that can actually regress, not a corpus aggregate.

## Scope

**Problem statement:** The extractor conflates "the author adopted the declared-target contract" with "here are the targets", and applies that conflation per wave, so incidental prose silently reduces or empties review coverage while looking deliberate.

**In scope:**

- Per-document adoption, replacing the wave-level suppression.
- Two-tier declaration: pure-path-bullet floor plus the explicit `**Review targets**` block.
- Space-tolerant span extraction inside the explicit block, and phantom-fragment rejection at the floor.
- Both consumers of `serialization_point_paths`: lane selection in `review_policy.py` and the wave file-footprint advisory in `server_impl.py` (`_wave_code_footprint`, `:16311-16375`), whose bounded file universe follows the same extractor.
- `REVIEW_POLICY_EVALUATOR_VERSION` bump (5 to 6) and its one-time re-Prepare, disclosed. This bump also carries `1umsf`'s digest boundary change; the coupling is stated in both plans.
- Correcting the false guarantee in all four carriers, the two stale seed 160 siblings and its re-authoring advice, both stale statements in the spec line, the context-efficiency doc's account of what makes the bounded-footprint advisory available, seed 170's author guidance, and the two-tier guidance in `docs/plans/plan-template.md` and the embedded scaffold.
- Re-pinning `tests/test_review_policy.py:1361`, which asserts wave-level adoption today.

**Out of scope:**

- **Unique-basename resolution against tracked files.** Split to its own change. It is gated behind a marker that only this wave's plans currently carry, so it would deliver near-zero recall on day one, while putting a subprocess and a non-hermetic working-tree read behind a review gate in a module documented stdlib-only. It should follow once the marker has adoption to act on.
- **Root-level declared files.** Declined on measurement: four repositories, zero root-level source files, zero lane impact.
- The retired-token registry, the lane roster, and what each trigger means.
- A systematic audit of every path-parsing site for space handling, filed separately.

## Acceptance Criteria

- [x] AC-1: Prose that mentions a directory keeps the document's full prose-derived roster, pinned against the **empty-roster** case (`docs/` alone, measured `[qa, architecture]` to `[]`) in **both shapes**: a plain prose line and a prose bullet (`- Shared with the wave that also touches the docs/ folder`). Reproduced as red tests first.
- [x] AC-2: A document using either declaration tier scores as declared and gets exactly its declared roster, with requested and project lanes held empty in the fixture so the assertion is not satisfied by unioned inputs.
- [x] AC-3: **A mixed-wave fixture** with one adopting document beside one non-adopting sibling loses no lane. A corpus census cannot detect this failure and does not satisfy this criterion: under wave-level suppression the mixed wave measures `[code, qa, docs-contract]` collapsing to `[docs-contract]`, and a static count over a corpus where nearly all declared documents sit in closed waves returns zero losses under a correct and an incorrect design alike.
- [x] AC-4: `tests/test_review_policy.py:1361`, which asserts wave-level adoption, is re-pinned to per-document adoption rather than deleted, and its new expectation is stated in the test. Its multi-path backticked declaration bullet must still declare all three paths under the floor.
- [x] AC-5: A declared path containing spaces extracts intact inside the explicit block, proven with a real on-disk `<id> <slug>` artifact, and the span is lowercased like every other target. **The extraction side is the repair** (no spaced target can be produced at all today). The `_wave_code_footprint` half is pinned on a spaced target **outside** `_FOOTPRINT_EXCLUDE_PREFIXES` (a temp-repo fixture such as `src/1x y/mod.py`), because `docs/` is footprint-excluded (`server_impl.py:16308`) and a docs artifact would measure zero under correct and incorrect handling alike. The fixture must leave `_FOOTPRINT_PROVIDER` unset so the real body runs; every existing footprint test stubs it, so a stubbed fixture here would be vacuous. Plain porcelain quoting is a **coverage pin** (`:16364` already strips it); the **rename entry is a repair** (Requirement 6), and the mixed-case and rename cases are pinned separately so a fix satisfying one by breaking the other fails.
- [x] AC-6: A shredded fragment is **not** treated as a declared target and does not suppress the fallback: the unbackticked spaced-path bullet (`- docs/waves/1uo1x declaration-and-digest-boundaries/wave.md`) extracts nothing, measured, because its first fragment fails the declared-target predicate and the all-tokens rule rejects the bullet. Pinned separately from AC-5.
- [x] AC-7: The floor census is re-run at delivery and asserts **zero documents lose a lane corpus-wide**, reporting keeps, reverts, and gains (plan-time measurement: 40 keep, 98 revert, 0 losses, 92 gain over 138 declared).
- [x] AC-7a: A **wrapped pure-path bullet** is prose, pinned by unit fixture rather than left to AC-7's census, using the real four-line declaration from `1uf68-bug summary-schema-token-unobservable-on-non-nominal-runs.md`. Without this pin an implementation that scans the first line and discards continuations passes every other AC while losing that document's `docs-contract-reviewer` lane.
- [x] AC-7b: The two unspecified-behavior boundaries are pinned so they cannot be settled by accident: a fenced example inside `## Serialization Points` declares **nothing** under either tier (it declares `src/app/handler.py` today, measured), and a document carrying both a marker block and separate pure-path bullets keeps **both** sets of targets.
- [x] AC-8: Every doc surface this change falsifies or leaves incomplete is corrected. All four carriers of the false guarantee; seed 160's "Adoption is per WAVE" sentence rewritten for per-document adoption, its `:198` sibling and `:481` checklist gaining the two-tier form, and its "no re-authoring is required, and none should be attempted" clause amended, because re-authoring stays optional but an author wanting declared precision back after their prose bullets revert must re-declare with a pure-path bullet or the marker; `docs/specs/mcp-tool-surface.md:637` updated for **both** stale statements, its "evaluator version `5`" becoming 6 and its description of what the digest normalizes changing with `1umsf`'s allowlist boundary, not merely its per-path-reasons clause; `docs/references/context-efficiency.md:204-212`, which stays literally true but becomes incomplete once 98 documents revert to undeclared and lose the bounded-footprint advisory it describes, updated to say what now counts as declared; and seed 170's author guidance, `docs/plans/plan-template.md`, **and the embedded `_default_template()` scaffold** all documenting both tiers, so a repo scaffolding through `wf_new_*` gets the same guidance as one copying the template. A freshly scaffolded change document, from the template and from the embedded scaffold, must declare **zero** targets under both tiers, pinned by test that **reads the canonical producers** (`docs/plans/plan-template.md` and the `server_impl.py` scaffold constant) rather than a copied literal, since a literal goes vacuous the moment either drifts, which is the drift this pin exists to prevent.
- [x] AC-9: The evaluator bump converges in exactly one re-Prepare and is idempotent thereafter; closed waves remain byte-immutable. The existing pins **move rather than disappear**: the direct constant pin at `test_review_policy.py:478` and the convergence templates at `test_server_tools.py:28750`, `:28765`, `:28806`, plus a public v5-to-v6 transition case, so the bump cannot land half-pinned. The CHANGELOG entry states all four facts an operator needs: non-closed waves take exactly one re-Prepare, approvals lapse once at that re-Prepare, closed waves stay byte-immutable, and the single bump carries both this change's lane semantics and `1umsf`'s digest boundary.
- [x] AC-10: The full framework suite and docs-lint pass.

## Tasks

- [x] Write the red tests, **all five behaviors that are red on current code**, before any fix: empty-roster in both prose shapes, the mixed-wave fixture, the spaced-path phantom, and the embedded scaffold placeholder (which today puts every freshly created change doc into declared mode with a code-reviewer-only roster). The phantom and scaffold pins must not be deferred into the `spaces` and `carriers` workstreams, where they would first be authored after the fix already made them green.
- [x] Add the wrapped-pure-path-bullet fixture (AC-7a) from the real `1uf68` declaration.
- [x] Add the two-tier declaration form with an adoption predicate separate from target extraction; floor is pure-path bullets, single-line, all-tokens-accepted.
- [x] Key adoption per document and delete the wave-level suppression.
- [x] Add span-bounded space-tolerant extraction inside the explicit block (lowercased, fence-skipping, unioning with the floor); verify phantom rejection at the floor.
- [x] Repair the rename-entry parse in `_wave_code_footprint` (split on ` -> ` before stripping quotes) and pin the plain, rename, and mixed-case porcelain shapes with `_FOOTPRINT_PROVIDER` unset.
- [x] Re-pin the wave-level adoption test to per-document.
- [x] Re-run the floor census at delivery; record keeps, reverts, gains, and the zero-loss assertion in the Progress Log.
- [x] Bump the evaluator version and add the convergence test.
- [x] Correct the four guarantee carriers, the seed 160 siblings (`:198`, `:481`) and its re-authoring clause, both stale statements in the spec line, the context-efficiency footprint carrier, seed 170's author guidance, and the two-tier guidance in both the plan template and the embedded scaffold.
- [x] Write the CHANGELOG entry with the four operator-facing transition facts named in AC-9.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                                          |
| ---------- | ----------- | ---------- | --------------------------------------------------------------- |
| red-test   | implementer | none       | Empty-roster in both shapes and the mixed-wave fixture, before any fix |
| adoption   | implementer | red-test   | Per-document keying plus the pure-path floor; this is the P1 fix  |
| spaces     | implementer | adoption   | Span extraction in the explicit block; phantom rejection; footprint consumer |
| carriers   | implementer | adoption   | Four guarantee carriers, seed 160 siblings, spec line, seed 170, plan template |
| transition | implementer | adoption   | Evaluator bump, convergence test, re-pinned wave-level test       |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`
- `docs/plans/plan-template.md`
- `docs/references/context-efficiency.md`
- `docs/specs/mcp-tool-surface.md`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md:637` states that declaring `## Serialization Points` replaces the legacy fallback with exact per-path reasons. Under per-document adoption that becomes false for a wave whose documents differ, so the line changes with the code. The guarantee sentence itself lives in the seeds, the shipped lifecycle prompt, and the embedded template, all declared above. No boundary moves and no ownership changes.

## AC Priority


| AC    | Priority  | Rationale                                                                                       |
| ----- | --------- | ------------------------------------------------------------------------------------------------ |
| AC-1  | required  | The reported P1, pinned at its measured worst case and in the bullet shape the first floor missed. |
| AC-2  | required  | Without it the fix could score everything undeclared and still pass AC-1.                          |
| AC-3  | required  | The only criterion that can detect the wave-level regression an earlier revision of this plan proposed. |
| AC-4  | required  | An existing test asserts the behavior being replaced; leaving it would block the fix or be deleted silently. |
| AC-5  | required  | Our own artifact naming is currently undeclarable, and the footprint consumer breaks silently without the porcelain case. |
| AC-6  | required  | The phantom is worse than the silent drop: it suppresses the fallback and yields zero lanes.        |
| AC-7  | required  | The zero-loss assertion is the floor's safety contract; the earlier revision's preservation count hid an empty-roster misclassification as a keep. |
| AC-7a | required  | The one ambiguity in the floor rule, and the only lane loss either reading produces; a census alone lets the wrong reading ship. |
| AC-7b | important | Fence handling and tier interaction are otherwise decided implicitly by whoever writes the parser, in a wave about silent loss. |
| AC-8  | required  | A shipped guarantee that is false in four carriers, one of which states the deleted rule verbatim.   |
| AC-9  | required  | Lane semantics changing without a bump leaves receipts describing a stale roster.                   |
| AC-10 | required  | Standard gate.                                                                                      |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-07 | Defect reproduced: one prose sentence naming `docs/specs/` drops two lanes | `select_required_review_lanes` two-document probe |
| 2026-08-07 | First independent review: wave-level suppression keyed on adoption still reintroduces the defect on a mixed wave; Requirement 1 rewritten to per-document adoption. Census-shaped AC-3 shown vacuous; replaced with a mixed-wave fixture. Spaces shown to produce phantom targets. Carrier location corrected to seeds and shipped prompt | independent sandboxed review |
| 2026-08-07 | Readiness council (red-team seat) disproved the scanned-bullet floor: prose bullets are the dominant prose carrier in real Serialization Points sections, so `- Shared with the wave that also touches the docs/ folder` still emptied a roster under the floor, and the 134-of-138 preservation census was counting an empty-roster misclassification as a keep. Floor redefined to pure-path bullets | readiness council probe |
| 2026-08-07 | Pure-path floor measured: 817 change docs, 138 declared, 40 keep, 98 revert, zero lane losses corpus-wide, 92 reverting docs gain lanes. Live exposure three docs: this wave's two plans keep; `1rolq` reverts with gains. Phantom mechanism confirmed: the unbackticked spaced-path bullet extracts nothing because `docs/waves/1uo1x` fails the predicate and the all-tokens rule rejects the bullet. The embedded template's placeholder bullet is also rejected as prose under the floor, closing a pre-existing hazard | revision-3 census probe |
| 2026-08-07 | Readiness council (docs-contract seat) found a fourth guarantee carrier: seed 160:199 ships the "Adoption is per WAVE" sentence this change deletes, with stale siblings at :198 and :481; the :481 fallback sentence itself stays true under per-document adoption. Carriers, AC-8, Serialization Points, and the wave watchpoint extended. Seed 170's edit is now described, not just named | readiness council review |
| 2026-08-07 | Council P2s folded: `_wave_code_footprint` acknowledged as the second consumer of the extractor, with the porcelain double-quoting case added to AC-5; the Risks row citing a nonexistent "allowed-values affordance" rewritten to the floor's real mitigation | readiness council review |
| 2026-08-07 | IMPLEMENTED. All five red tests written first and confirmed failing on current code (prose bullet AND plain line emptying the roster, mixed wave collapsing, phantom `declaration-and-digest-boundaries/wave.md`, wrapped bullet declaring only its continuation-line target, scaffold placeholder declaring `src/app/handler.py`). Wave-level suppression deleted; two-tier extraction added | full suite 6941 tests OK, docs-lint ok |
| 2026-08-07 | AC-7 delivery census against the SHIPPED extractor: 814 change docs, 138 declared before and 37 after, 101 reverting, 95 gaining, **ZERO losing a lane**. The keep count is 37 rather than the plan-time 40 because the plan-time prototype predated the Requirement 4 disambiguation and accepted a wrapped bullet's first line. The three affected docs (`1t0u4`, `1sufn`, `1tr85`) are prose SENTENCES that begin with paths, so treating them as prose is correct and each gains lanes. Only one non-closed document changes roster: unadmitted plan `1rolq`, which gains three lanes | `ac7-census.py` against shipped code |
| 2026-08-07 | The AC-8 scaffold pin caught a defect introduced BY the AC-8 carrier edit itself: documenting the two declaration forms with indented example bullets made the embedded template declare `src/app/handler.py` and `docs/specs/` again, re-opening the exact hazard the AC exists to prevent. Examples moved inside fences, which declare nothing | `test_the_shipped_scaffolds_declare_nothing...` |
| 2026-08-07 | Evaluator bumped 5 to 6 with both pins MOVED not deleted: the tripwire at `test_review_policy.py:478` and a new public v5-to-v6 convergence test. The retired v4-to-v5 case needed its second prepare pinned inside the patch context, matching the retired v1-to-v2 pattern; leaving it unpinned would have silently retargeted it at the live version | 4 evaluator tests OK |
| 2026-08-07 | Delivery docs-contract lane WITHHELD on a real P1: the reported defect SURVIVED inside tier 2. Span extraction took every backticked token and ignored the words around it, so `- Shared with the wave that also touches the \`docs/\` folder` written INSIDE the marker block still went from two required lanes to zero, and a wrapped block bullet declared its first-line span. Seven shipped carriers asserted "prose declares nothing in any shape" while the code did not mean it in the block. Reproduced, then repaired: the all-or-nothing rule and the wrapped-bullet rule now apply in BOTH tiers, pinned by `test_prose_declares_nothing_inside_the_explicit_block_either` | reproduction probe, 73 tests OK |
| 2026-08-07 | Same lane found the seed examples taught a form the parser REJECTS: seeds 040 and 170 wrote the tier-1 example with escaped backticks, which render literally and extract nothing. Corrected to the nested double-backtick form, verified to extract both targets. Also folded: seed 160 now requires that any example injected into a target repo's template must not itself declare (the trap this wave already fell into once), the CHANGELOG evaluator arithmetic is stated as a single 4-to-6 transition from the last release, a sibling CHANGELOG bullet still describing wave-level adoption is corrected, and two stale `v5` labels are fixed | census re-run 37/101/0/95 unchanged, docs-lint ok |
| 2026-08-07 | Delivery code lane APPROVED (no P1) with three P2s, all real and all repaired. (1) `_serialization_points_body` was FENCE-BLIND, so a fenced EXAMPLE of a whole `## Serialization Points` section substituted for the real one and dropped a lane, and a fenced `## ` line truncated the real section. This change made it MORE reachable, because the scaffold it ships now teaches fenced examples in that exact section. (2) `index in block` contradicted the union invariant the module documents: a marker line above a mixed-notation bullet silently dropped a declaration the floor accepts. (3) The rename-parse fix had ZERO coverage; both deleting and inverting it left the suite green | lane's 27-mutation harness, reproductions confirmed locally |
| 2026-08-07 | Two P3s also repaired: a tier-2 span needed a separator rule (`- \`1.15.4\`` declared itself, matched no trigger, and zeroed the roster, because `_is_declared_target` accepts any dotted final segment and spans get no `_REPO_PATH_RE` check), and a fence marker after a bullet was read as a wrapped-bullet continuation, dropping a real declaration written directly above a fenced example. All seven repairs mutation-verified KILLED, including the two mutations the lane proved previously survivable | mutation harness, census unchanged at 0 losses / 95 gains |
| 2026-08-07 | Delivery QA lane WITHHELD on a P1 (AC-5's footprint half untested) that was ALREADY FIXED: its sandbox snapshot predated the footprint tests added in response to the code lane. Verified rather than assumed by re-running its exact mutations against the live tree, where the rename split and the quote-strip are both KILLED. Its P1 is not carried as an open finding; its underlying observation was correct against what it reviewed | mutation re-run on current tree |
| 2026-08-07 | The same lane's remaining findings were real and are now repaired: the tier-2 marker fence-skip was unpinned (and the shipped scaffolds carry a FENCED marker example, so the first author keeping it hits that shape), Requirement 5's block boundary was unpinned, the tier-1 path-shape check was unpinned (its deletion flips `README.md` into a declared root-level target, which the plan puts out of scope), marker case-insensitivity was accidental rather than contracted, the footprint dir-prefix arm was unpinned, and AC-4's byte-for-byte degrade clause could not be reached by the census at all. Six tests added; all six mutations now KILLED | mutation harness |
| 2026-08-07 | Corrected a false claim the lane disproved by probe: Requirement 6 said the rename defect was "unreachable today because no spaced target can be declared". The pre-repair parse ALSO dropped the unspaced rename shape, so any declared file renamed with `git mv` was already missing from the advisory. The repair is a live fix, not a pre-emptive one | lane probe against real porcelain |
| 2026-08-07 | Editorial item left for the operator, not silently reorganized: `## [Unreleased]` carries two `### Fixed` sections (CHANGELOG.md:11 and :115) straddling `### Changed`. The second holds other waves' entries, so merging them is a cross-wave release-notes decision rather than this wave's to make | docs-lint does not flag it |
| 2026-08-07 | Independent QA REVERIFICATION APPROVED: all seven prior findings resolved, nine mutations killed (including both halves of the AC-5 footprint P1 and a bonus `rsplit`-inversion probe), the rename fixture confirmed to stage real `git mv` renames with genuine quoting and to leave `_FOOTPRINT_PROVIDER` unset, and 18/18 behavior cases correct with no regression from the seven repairs | reverification lane |
| 2026-08-07 | The same lane isolated a census confound worth recording: a naive HEAD-to-working-tree comparison shows 42 documents losing lanes, which is NOT this wave. Holding the extractor as the only variable gives zero losses; swapping only the fallback-corpus canonicalization gives all 42, and that belongs to closed wave 1umst's `1ujtt-bug`. Extractor alone: 0 losses, 95 gains | isolated-variable census |
| 2026-08-07 | New P2 from reverification, FIXED in session: a tier-2 span carrying a path plus a trailing note (`` `…/upgrade_wavefoundry.py (extraction filter)` ``) or two paths in one span declared the whole string as a phantom, which named no file, suppressed the fallback, dropped `release-reviewer`, and zeroed the wave footprint for a file that really changed. Span predicate tightened: a directory segment may contain spaces, a basename may not, and an extension is never followed by more text. Legitimate `<id> <slug>` artifacts still declare | reproduction, 84 tests OK |
| 2026-08-07 | Final delivery census on the shipped tree: 815 change docs (corpus grew by one unadmitted plan during the wave), 139 declared before, 38 after, 101 revert, 95 gain, **zero lane losses**. Digest census unchanged: exactly one differing document, `1p7dg`, widening, closed wave | `ac7b-census.py` |
| 2026-08-07 | Gapfill: implement-stage instrumented retrieval was 0 against 9 changed non-docs files, and the advisory is correct rather than a false positive. Part of the work genuinely warranted harness fallback: executed probes (test runs, the mutation harness, censuses, `git status --porcelain` behavior) are shell work by the posture's own terms, and the carrier edits were bulk-mechanical single-file Edits. But the EXPLORATION was not: locating the guarantee carriers, reading `select_required_review_lanes` and `_wave_code_footprint`, and finding the trigger tables were done with `grep` and `sed` where `code_keyword`, `code_read`, and `code_definition` were the right instruments. Recorded as a deviation, not a justification | `wf_review_wave` implementation-phase telemetry |
| 2026-08-07 | Clean full framework suite on the current tree: 6943 tests across 62 files, OK, 197s. An earlier run reporting 7 file failures was environmental only: zero assertion failures, one hard per-file timeout and several p95 LATENCY-BUDGET tests, measured at load average 17 while three sandboxed review agents ran their own suites. `test_server_tools` alone passes 1602 tests with no per-file cap | `run_tests.py`, `uptime`, per-module reruns |
| 2026-08-07 | Coordinator-run delivery review after the code and QA lanes were stopped. Found and fixed a CRLF defect I introduced: the tier-2 marker was anchored `[ \t]*$`, so a Windows checkout matched no marker and silently lost every spaced declaration, degrading to the floor. The sibling `_PROGRESS_LOG_HEADING_RE` already carries `\s*$` for exactly this reason. Pinned by `test_declarations_survive_a_crlf_checkout` | CRLF probe, 74 tests OK |
| 2026-08-07 | Mutation harness over the new extractor found FOUR of my own tests vacuous with respect to the branch they claimed to pin: the `1uf68` wrapped-bullet fixture opens with BARE filenames that carry no separator and so declare nothing regardless of the rule; the tier-2 wrapped case was already rejected by the residue rule; the fenced fixture was saved by the wrapped-bullet rule rather than the fence skip; and no fixture covered a non-target span. Fixtures strengthened (slashed wrapped bullet, clean-first-line block bullet, blank line inside the fence, non-target span). All 8 mutations now KILLED, including reverting per-document adoption | mutation harness in isolated sandbox |
| 2026-08-07 | Readiness code lane APPROVED with no P1 or P2, prototyping BOTH designs against the tree and reproducing every figure exactly. Confirmed both edits are implementable at the named sites without collateral: `select_required_review_lanes` has one production caller (`server_impl.py:7092`) carrying no wave-level semantics, `normalize_review_tracking_status` has one caller and leaves the shared regex untouched, `_is_declared_target` needs no change, and closed-wave immutability is already enforced at `review_policy_upgrade.py:97`. Five P3 spec gaps folded as Requirements 5-6 and AC-7b: tier-2 spans must lowercase (the consumer folds case on the git side ONLY, by design after a prior PascalCase bug), fenced regions must not be scanned, the tiers must union, the rename-entry porcelain parse is broken and becomes REACHABLE the moment spaced targets are declarable, and AC-5's fixture must leave `_FOOTPRINT_PROVIDER` unset or it is vacuous | readiness code lane |
| 2026-08-07 | Readiness QA lane APPROVED and found the tier-1 rule ambiguous by IMPLEMENTING BOTH READINGS over the 138-doc declared corpus: "continuation lines are not scanned" also reads as scan-first-line-discard-rest, which keeps 45 instead of 40 and loses `docs-contract-reviewer` on `1uf68`, the only lane loss either reading produces. Requirement 4 disambiguated, AC-7a added with that document's real four-line bullet as the fixture. Same lane found two red-today behaviors scheduled into post-fix workstreams (spaced-path phantom, scaffold placeholder) and moved them into red-test; corrected AC-5's porcelain half from repair to coverage pin, since `server_impl.py:16364` already strips git's quoting; named the evaluator pins at `test_review_policy.py:478` and the three convergence templates | readiness QA lane |
| 2026-08-07 | Readiness docs-contract lane APPROVED and found two more unswept carriers of the surrounding declaration contract, using search terms the earlier phrase-grep could not reach: `context-efficiency.md:204-212`, which documents that declaring Serialization Points is what makes the bounded-footprint advisory available and goes incomplete when 98 docs revert, and the spec bullet's SECOND stale statement, `evaluator version 5`. Both added to AC-8 and the carrier declared. Also folded: the embedded scaffold must document both tiers (not just the template), seed 160's "none should be attempted" advice is amended, and AC-9 now names the four facts the CHANGELOG must state | readiness docs-contract lane |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-07 | Adoption is per document, not per wave | Wave-level suppression IS the defect. Measured on a mixed wave it reproduces the reported failure exactly; per-document scoring measured 149 waves unchanged, 57 gains, zero losses | Keep wave-level suppression, which an independent review proved reintroduces the bug |
| 2026-08-07 | Floor is pure-path bullets, all tokens accepted or the bullet is prose | A floor that scans bullets for tokens re-admits the reported defect for its most common carrier, measured; the readiness council's probe emptied a roster with a bullet-shaped sentence. The pure-path rule kills that class, mechanically rejects shredded phantoms, and rejects the template placeholder bullet | Scanned-bullet floor (previous revision, disproved); marker only, which costs every declared doc an edit for the same defect removal |
| 2026-08-07 | Accept 98 reverts for zero losses | The reverting set is prose-bullet misclassifications; 92 gain lanes and none lose any. Keeping them declared preserves precision that was never legitimately declared, including at least one empty-roster doc counted as preserved by the earlier floor | Preservation-maximizing floor, which preserves misclassifications along with declarations |
| 2026-08-07 | Split unique-basename resolution into its own change | It is gated behind a marker only this wave's plans carry, so it delivers near-zero recall on day one, and it puts a subprocess and a non-hermetic working-tree read behind a review gate in a module documented stdlib-only | Ship all three together, delaying a live correctness fix behind a recall feature with no day-one effect |
| 2026-08-07 | AC-3 is a mixed-wave fixture, not a corpus census | The census cannot distinguish a correct design from the incorrect one, measured. A fixture with one adopting and one non-adopting document in the same wave is the smallest thing that can | Corpus census, which passes while the plan ships the bug |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The new rule loses lanes for documents that never migrate | AC-7's delivery census asserts zero losses corpus-wide; AC-3's mixed-wave fixture detects the wave-level regression no census can |
| Reverting misclassified documents to prose scoring reintroduces false positives the contract removed | Real and accepted: 92 documents gain lanes that are partly false positives. Coverage ranks above precision deliberately, and a document that wants precision back re-declares with pure-path bullets or the marker |
| The explicit marker gets written slightly wrong and silently yields nothing | The floor stays active regardless, so a misspelled marker degrades to tier 1, not to nothing. The residual loss is bounded to spaced paths, which only the marker can declare, and phantom rejection (AC-6) prevents the harmful outcome of a shredded fallback suppression |
| The evaluator bump lapses approvals on in-flight waves | AC-9 pins one-time convergence; live exposure is three documents, all measured safe. Disclosed in the changelog |
| A contrived unbackticked spaced path whose fragments are all individually accepted declares phantoms | Possible in shapes like `docs/v1.0 beta/x.md` where every fragment passes the predicate. The floor cannot reject these without a tree read, which is out of scope; the explicit marker with backticks is the sanctioned form for spaced paths, and the real-world shapes (`<id> <slug>` wave artifacts) are covered because their first fragment always fails the predicate |
| The footprint consumer diverges from lane selection | Both consumers share `serialization_point_paths`; AC-5's porcelain case and the footprint task keep the advisory correct for spaced targets |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
