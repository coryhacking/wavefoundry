# Make the prepare-council readiness review verifiable: de-dup the seat template, validate roster⇄evidence consistency, require code-grounded verification

Change ID: `1p9pk-enh prepare-council-verification-rigor`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-04
Wave: TBD

## Rationale

Wave `1p9pe`'s own recorded prepare-council review is the motivating evidence: it passed technical validation and recorded a `prepare-council: PASS`, yet an independent adversarial readiness review of the same four admitted plans immediately found a NOT-READY mechanism defect (a plan whose `os.environ` approach is a verified no-op because Hugging Face reads the timeout into a module constant at import), a wrong causal story, two factual errors (a cited helper `_lint_changed` that does not exist — the real name is `_run_incremental_checks`; a "five callers" census that is actually six), and four AC vacuity/coverage gaps. None were caught at readiness. Three failure modes in the prepare-council machinery let that happen, each independently fixable:

1. **The verdict template hands over a copy-pasteable seat roster that can be internally inconsistent.** `server_impl.py:8879` (post-1p9q3) `_prepare_council_verdict_template` builds `seat_list = ["red-team", "architecture-reviewer", "security-reviewer", "qa-reviewer", "reality-checker"]` then unconditionally appends the rotating seat (`:8882-8883`). When the rotating seat is itself a fixed seat (e.g. `security-reviewer`, selected for trust-boundary waves), the template emits `security-reviewer` **twice** — exactly the roster recorded verbatim in `1p9pe`'s wave record. The concrete, duplication-carrying seat list invites agents to paste it as the *actual* roster rather than record the seats they truly ran.

2. **No validator checks that the recorded roster matches the recorded evidence.** `wave_validators.py:1431` only asserts a `prepare-council` verdict line *exists* in `## Review Checkpoints` for active/implementing waves; `wave_prepare` reports `council_verdict_valid: true` on structural completeness alone. In `1p9pe` the prepare-council line names *red-team, architecture-reviewer, qa-reviewer, reality-checker* (plus the duplicated security-reviewer), while the `## Prepare Review Evidence` section records *code-reviewer, security-reviewer, performance-reviewer* — a near-total mismatch between claimed and evidenced seats that nothing flagged.

3. **The readiness review is not required to be code-grounded.** The brief's `instructions` (`server_impl.py` `_build_prepare_council_brief`) say "Run each council seat in isolation against the admitted change docs and wave record" but do not require reviewers to verify the plans' load-bearing claims against the actual tree. A readiness review answerable purely from plan prose is how a nonexistent function name, a wrong caller census, and a no-op mechanism passed — each is caught only by opening the code (the guru "Pass 3" verification discipline the delivery review already expects).

Fixing all three converts the prepare-council from a structurally-checkable formality into a review that must actually be done and actually names who did it.

## Requirements

1. `_prepare_council_verdict_template` must not emit a seat more than once: when the rotating seat is already among the fixed seats, the template must de-duplicate it (the roster reflects distinct seats). The emitted template must make clear the seat list is to be replaced with the seats actually run, not pasted verbatim.
2. A docs-lint validator must flag a prepare-council roster⇄evidence mismatch using the pinned matching rule in AC-3 (literal role-token match; corpus = `## Prepare Review Evidence` ∪ `## Review Evidence` ∪ `## Review Checkpoints`, **excluding the matched verdict line's own text and the `## Participants`/`## Changes` regions**; tolerance set `{red-team, wave-council}`). The loose "corroborated by checkpoint prose" reading is explicitly NOT the rule — it is vacuous because the roster and its `strongest-challenge` prose share one line. A named non-tolerance seat whose literal token appears nowhere in the scoped corpus (as `architecture-reviewer` does in the pre-corrective `1p9pe`) is a lint finding, not a silent pass.
3. The validator must be fail-safe and not over-rigid: it tolerates the `{red-team, wave-council}` set (moderator synthesis; adversarial primer) without false-positiving, corroborates a seat by its literal token appearing in any evidence/checkpoint bullet **other than** the verdict line, and degrades to a clear message naming the specific mismatched seats.
4. The prepare-council brief `instructions` (and the review seed) must require code-grounded verification: reviewers must confirm each plan's load-bearing claims — cited `file:line`/symbols resolve, "X already does Y" claims hold, "no other caller/site" censuses are complete — against the current tree, and must not approve a plan whose claims were checked only against its own prose. **Scope-honesty:** the roster⇄evidence validator is a mechanical backstop only against *unnamed/unevidenced* seats — it CANNOT verify that a seat's evidence is actually code-grounded (a seat can write a prose finding having read zero code and pass). Requirement 4 is therefore an unenforceable seed/brief contract; the validator gives it teeth against roster padding, not against shallow review.
5. No regression to the existing prepare-council gate: `wave_prepare` still requires a structurally valid `prepare-council` verdict; the new validator is additive; a well-formed review with a consistent roster⇄evidence and code-grounded verification still passes cleanly.
6. Seed-first: the brief/template/validator changes and the review-seed wording must be updated together so downstream target repos pick up the tightened contract on upgrade. **Editing seeds under `.wavefoundry/framework/seeds/` requires opening `seed_edit_allowed` before and closing it immediately after (CLAUDE.md guardrail).** The shipped seed text must not add an *actionable* dangling pointer to a wavefoundry-internal wave/ADR ID (state the rationale inline instead); note there is **no automated test** enforcing this today (the shipped-reference-docs test checks byte-identity + a specific link, not internal-ID absence — seed 237 already carries a bare `(wave 1304x / 1305d)` provenance note and the suite is green), so self-containment is a manual review discipline, not a gated check.

## Scope

**Problem statement:** The prepare-council readiness review can pass on structural completeness alone: the seat-roster template can emit a duplicated/verbatim-pasted roster, no validator checks that the recorded roster matches the recorded evidence, and reviewers are not required to verify plan claims against code — so a thin review (as recorded for `1p9pe`) sails through while real defects survive to implementation.

**In scope:**

- De-duplicate the rotating seat in `_prepare_council_verdict_template` (`server_impl.py:8879-8884`) and adjust the template wording so the seat list reads as "replace with seats actually run." (Note: the collision fires for **both** `security-reviewer` and `architecture-reviewer` rotating picks — both are in the hardcoded fixed-seat list `:8881`; `_select_prepare_council_rotating_seat` can return either.)
- Add a validator in `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py` (near the existing `check_prepare_council_verdict` at `:1430`, whose current check is a bare `"prepare-council" in checkpoints.casefold()` substring test) for roster⇄evidence consistency, with the fail-safe/tolerance behavior in Requirements 2–3.
- Tighten the brief `instructions` string in `_build_prepare_council_brief` (`server_impl.py:8892`) and the review seed to require code-grounded verification (mirror the delivery review's Pass-3 verification expectation). **Primary seed target: `.wavefoundry/framework/seeds/237-council-review.prompt.md`** — its per-seat "must:" contract (`:45-48`) is where the requirement belongs; `215-wave-council.prompt.md` is moderator orchestration and gets a cross-reference only. Also audit `007-review-system-overview.md` (the review-system hub, which carries the most prepare-council references) for a consistency pointer.
- Tests: template de-dup for a fixed-seat rotating pick; validator flags a roster/evidence mismatch and passes a consistent one and tolerates synthesis-only conventions; brief instructions carry the verification requirement.

**Out of scope:**

- The delivery-phase (implementation) council — this change targets the prepare/readiness phase; the delivery review already expects code-grounded verification.
- Re-running or rewriting `1p9pe`'s recorded prepare-council (handled separately by this session's independent readiness review and the plan corrections it produced).
- Adding new seats or changing the fixed-seat/rotating-seat selection policy (`_select_prepare_council_rotating_seat`) — only the template's de-dup and the validator/instructions change.
- Enforcing code-grounded verification programmatically (a validator cannot check that a human/agent actually read the code) — the requirement is a seed/brief contract plus the roster⇄evidence validator as the mechanical backstop.
- Blocking `wave_prepare` on the new validator's findings beyond the existing docs-lint gate behavior (the validator reports through the standard lint channel).

## Acceptance Criteria

- [ ] AC-1: `_prepare_council_verdict_template` emits each seat at most once; when the rotating seat equals a fixed seat, the template's `seats:` list contains it exactly once. Verified by unit tests covering **both** colliding rotating picks (`security-reviewer` AND `architecture-reviewer` — both are in the fixed-seat list) plus a non-colliding pick (e.g. `docs-contract-reviewer`) that still appends normally.
- [ ] AC-2: The verdict template's seat list is presented as a replace-me placeholder (e.g. a bracketed instruction or an explicit "seats actually run" note), so a verbatim copy is visibly a template rather than a real roster. Verified by asserting the template text carries the replace-me signal.
- [ ] AC-3: A docs-lint validator flags a wave whose `prepare-council` roster names a seat with no corresponding evidence, using this **pinned matching rule** (the loose "evidence in checkpoint prose" phrasing was vacuous — a seat named in the roster line is trivially "corroborated" by the same line's own `strongest-challenge` prose; the readiness re-review worked out the rule that is neither vacuous nor false-positive-prone): for each token in the parsed `seats:`/`rotating-seat:` roster, **excluding** the tolerance set `{red-team, wave-council}`, flag the seat when its **literal role token** (`architecture-reviewer`, `qa-reviewer`, `reality-checker`, `security-reviewer`, `performance-reviewer`, `code-reviewer`, `docs-contract-reviewer`, …) appears **nowhere** in the corpus = `## Prepare Review Evidence` ∪ `## Review Evidence` ∪ `## Review Checkpoints`, **with the matched verdict line's own text removed** and **the `## Participants` table and `## Changes` region excluded** (else the seat matches the Participants Role column and the defect is silently un-caught). The message names the specific mismatched seats. Verified by a unit test on a **frozen pre-corrective** `1p9pe`-shaped fixture (roster names architecture-reviewer/qa-reviewer/reality-checker; evidence has code/security/performance → all three flagged) — NOT the live `1p9pe/wave.md`, which now self-heals because the corrective checkpoint line names those seats in prose.
- [ ] AC-4: The validator passes a consistent wave record (every rostered non-tolerance seat has a literal-token corroboration outside its own verdict line) and does NOT false-positive on: the `wave-council` moderator (a `moderator:` meta field, never in `seats:`, so never checked), a `red-team` adversarial primer (in the tolerance set), or a seat that records in checkpoint prose in a bullet **other than** the verdict line. Verified by unit tests on a consistent fixture and each tolerance case.
- [ ] AC-5: The prepare-council brief `instructions` and the corresponding review seed require code-grounded verification of each plan's load-bearing claims (cited sites/symbols resolve; caller/site censuses are complete). Verified by asserting the brief instructions string and the seed text contain the verification requirement.
- [ ] AC-6: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` is clean; the seed edits added no *actionable* dangling pointer to a wavefoundry-internal wave/ADR ID (manual reviewer check — there is no automated test enforcing internal-ID absence in seed bodies; the shipped-reference-docs test verifies byte-identity + a specific scan-findings link only), and any seed edit was made under an opened-then-closed `seed_edit_allowed` gate.

## Tasks

- [ ] De-dup the rotating seat in `_prepare_council_verdict_template` (`server_impl.py:8879-8884`) and reword the emitted seat list as a replace-me placeholder.
- [ ] Add a roster⇄evidence consistency validator in `wave_lint_lib/wave_validators.py` near `check_prepare_council_verdict` (`:1430`); fail-safe and tolerant of synthesis conventions; message names mismatched seats.
- [ ] Open `wave_gate_open(gate="seed_edit_allowed")`; tighten the brief `instructions` in `_build_prepare_council_brief` (`server_impl.py:8892`) to require code-grounded verification; land the per-seat requirement in `237-council-review.prompt.md` (`:45-48`), cross-reference from `215-wave-council.prompt.md`, audit `007-review-system-overview.md` for a consistency pointer; close `wave_gate_close(gate="seed_edit_allowed")` immediately after.
- [ ] Add unit tests: template de-dup (both `security-reviewer` AND `architecture-reviewer` colliding picks + a non-colliding pick); validator against a **frozen pre-corrective `1p9pe`-shaped fixture** (mismatch → names architecture/qa/reality-checker), a consistent fixture, and each tolerance case (`red-team`, `wave-council`, prose-in-other-bullet); brief-instructions verification requirement.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`; clean any `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-template-dedup | implementer | — | De-dup + replace-me wording in `_prepare_council_verdict_template`; small `server_impl.py` edit. |
| ws2-roster-evidence-validator | implementer | — | New `wave_validators.py` validator + tolerance rules. |
| ws3-instructions-and-seed | implementer | — | Brief instructions + review-seed verification requirement (seed-first). |
| ws4-tests | implementer | ws1-template-dedup, ws2-roster-evidence-validator, ws3-instructions-and-seed | Template/validator/instructions/seed tests; run suite + `wave_validate`. |


## Serialization Points

- `server_impl.py` is edited by ws1 (template) and ws3 (brief instructions) at disjoint functions — coordinate to land as one sequential edit set. ws2's validator is an independent file. ws4 joins after all three.

## Affected Architecture Docs

Likely `docs/contributing/review-and-evals.md` (or the review-system doc) if it describes the prepare-council recording contract — the roster⇄evidence consistency requirement and the code-grounded-verification expectation are new review contracts worth documenting there. Otherwise N/A: no module boundary or data/control-flow change; the change tightens the readiness-review recording/validation contract, not the wave lifecycle's structure. Confirm at implementation whether the review doc characterizes the prepare-council recording rules.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The duplicated-seat template is the concrete defect observed in `1p9pe`'s roster; de-dup is the core fix. |
| AC-2 | important | The replace-me signal is what stops verbatim-paste rosters; the de-dup helps but the paste habit is the deeper cause. |
| AC-3 | required | The roster⇄evidence validator is the mechanical backstop that would have caught `1p9pe`'s thin review at lint time. |
| AC-4 | required | Not false-positiving on legitimate synthesis conventions is what makes the validator shippable rather than noise. |
| AC-5 | important | Code-grounded verification is the behavioral fix; it is a seed/brief contract (not machine-enforceable), so it is important-not-required, with AC-3 as the mechanical partner. |
| AC-6 | required | Suite + docs-lint + self-contained seeds are the standing merge gates for framework/seed changes. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from wave `1p9pe`'s own thin prepare-council vs. an independent adversarial readiness review of the same four plans (which found 1 NOT-READY mechanism defect, 1 wrong causal story, 2 factual errors, 4 AC gaps). Verified the three machinery gaps: `_prepare_council_verdict_template` (`server_impl.py:8864-8868`) appends the rotating seat without de-dup → duplicated `security-reviewer` in `1p9pe`'s recorded roster; the prepare-council validator (`wave_validators.py:1431`) only checks the verdict line EXISTS, not roster⇄evidence consistency; the brief `instructions` (`_build_prepare_council_brief`) require per-seat isolation but not code-grounded verification. | `server_impl.py:8864-8868,8877+`; `wave_validators.py:1431-1455`; `1p9pe/wave.md` recorded prepare-council roster vs. `## Prepare Review Evidence`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Fix all three prepare-council gaps (template de-dup, roster⇄evidence validator, code-grounded-verification contract) in one change. | They share one root cause and one motivating incident (`1p9pe`); each alone leaves a hole (a de-dup'd template still allows a mismatched roster; a validator without the verification contract still allows a prose-only review). | Three separate changes — rejected: they are one coherent "make readiness review verifiable" fix and share the same tests/fixtures. |
| 2026-07-03 | Make the roster⇄evidence check a fail-safe, tolerance-aware lint finding rather than a hard structural gate. | Review-recording conventions vary (moderator synthesis, adversarial primer without a numbered signoff); a rigid exact-match would false-positive on legitimate reviews. The `1p9pe` failure is a *clear* mismatch (named seats with zero evidence), which a tolerant check still catches. | Rigid roster==evidence exact match — rejected: over-rigid, false-positives on synthesis conventions. |
| 2026-07-03 | Keep code-grounded verification a seed/brief contract, not a programmatic gate, backstopped by the roster⇄evidence validator. | A validator cannot verify a human/agent actually read the code; the enforceable proxy is that the claimed seats produced real, evidenced findings. | Attempt to machine-check verification — rejected: not feasible; the contract + mechanical roster⇄evidence backstop is the honest mechanism. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The roster⇄evidence validator false-positives on legitimate synthesis-only reviews and blocks good waves. | AC-4 pins tolerance for wave-council synthesis and red-team-primer conventions; the check flags only a clear contradiction (named seat, zero evidence anywhere) and reports the specific seats, and is a lint finding through the standard channel. |
| De-duping the template changes the recorded-roster format enough to break the prepare-council parser. | The parser (`server_impl.py:8791` regex) matches the verdict line structure, not the exact seat list; de-dup only removes a duplicate token. AC-6's suite run covers the parse path. |
| Code-grounded-verification wording bloats the brief/seed without changing behavior. | Keep it a concise, specific requirement (verify cited sites/symbols resolve; complete caller/site censuses) mirroring the delivery review's existing Pass-3 expectation; the roster⇄evidence validator is the mechanical partner that gives it teeth. |
| Seed edit ships an internal wave/ADR ID downstream. | AC-6 + the existing shipped-reference-docs test enforce self-contained seed text; state the rationale inline instead of citing `1p9pe`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
