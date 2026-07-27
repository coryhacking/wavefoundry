# Repair And Reverification Independence Is Documented But Unenforced

Change ID: `1tmb2-bug repair-reverification-independence-unenforced`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-27
Wave: `1to7k lifecycle-evidence-and-focus-integrity`

## Rationale

The review ledger's credibility rests on one rule: the agent that repairs a finding is not the agent
that reverifies it. Seed prose states the rule. No code enforces any part of it.

A filesystem-wide `rg` census over framework Python, querying `repair_actor`,
`reverification_actor`, `repairer`, `same actor`, `actor ==`, and `actor !=`, found only
approval-actor name/boolean checks in `build_compact_review_event`, not a chain comparison:

```
if actor != expected_actor:                            # name match, not identity
if expected_actor != "operator" and (
    event.get("fresh_context") is not True
    or event.get("independent") is not True
```

The first is a *name* check: an approval for `wave-council-readiness` must carry the literal string
`wave-council`. The second checks that two booleans are `True`. Both booleans are supplied by the
caller. `fresh_context` means "the actor started without retained repair context" and `independent`
means "did not implement the repair and formed its own verdict", and the ledger's only evidence for
either is that the writer said so.

Nothing compares the `repair_start` actor to the `reverification` actor. The run-kind grammar is
strictly ordered: a readiness-origin finding may open its first repair cycle directly from readiness,
while a delivery-origin finding requires `initial_delivery` before `repair_start`; either path then
requires `reverification` after `repair_start`, and only reverification can set
`repair_execution_state="completed"`. The *shape* of a repair cycle is enforced rigorously while the
*independence* that gives the shape its meaning is not checked at all. One agent can repair a finding,
then immediately reverify its own repair under the same actor and the same `context_id`, declare
`fresh_context=true` and `independent=true`, and the ledger will accept it and mark the finding
resolved.

This matters more here than it would elsewhere. This repository uses the review system to verify the
review system, so a defect in the verifier is self-concealing: the evidence that would reveal it is
produced by the thing that is broken.

**What this change can and cannot achieve.** The validator sees strings, not callers. A determined
agent that writes a different actor name cannot be caught by any check inside this process, and this
change does not pretend otherwise. What is achievable, and currently absent, is twofold:

1. **Internal-contradiction detection.** A self-declared field can still be checked against *other*
   self-declared fields. Two records sharing a `context_id` are by definition the same context, so a
   reverification that shares its chain's `repair_start` `context_id` while declaring
   `fresh_context=true` is not untrustworthy, it is self-contradictory. That is decidable from the
   ledger alone, with no trust assumption.
2. **Catching the observed accidental class.** The field evidence is convenience rather than proven
   forgery: one acting role doing both halves because nothing objected. A same-actor check addresses
   the observed field shape represented by 35 historical chains, and would flag their latest chains
   if explicitly reopened, without claiming that census establishes caller identity or the prevalence
   of every possible failure mode.

The distinction between "cannot be forged" and "cannot happen by accident" should be stated in the
seed rather than left for a reader to assume the stronger of the two.

## Requirements

1. A `reverification` whose `context_id` equals the `context_id` of the `repair_start` it resolves is
   rejected when it declares `fresh_context=true`. This is a contradiction check, decidable from the
   ledger, and carries no trust assumption. Matching is by exact `finding_id` and cycle: another
   finding or an earlier cycle with the same context does not control the current reverification. The
   append diagnostic code is `reverification_context_not_fresh`.
2. A `reverification` whose `actor` equals the `actor` of the `repair_start` it resolves is surfaced
   immediately and rejected as protocol policy with code `reverification_actor_not_distinct`, but
   actor equality is not described as proof of shared caller identity. Recovery is a new
   reverification from a distinct acting role and context. This wave adds no waiver: the existing
   broad repair waiver has different semantics and must not become an independence bypass.
3. Both preview and append evaluate the exact finding/cycle chain before building terminal synthesis.
   Same-context and same-actor attempts append nothing and return their named diagnostics, so the
   prior synthesis remains the single current-state authority. If both match, the decidable
   same-context contradiction takes precedence and returns only
   `reverification_context_not_fresh`; actor policy is evaluated only after context differs.
4. The close gate independently surfaces affected current/latest older-code chains with
   `review_evidence_independence_invalid` only when the target wave's current lifecycle status is
   non-closed/reopened. Generic ledger parsing and `_repair_cycle_progress` remain backward-compatible;
   a closed/sealed archive remains readable and passing. If explicitly reopened, the forward close
   audit applies before it can close again. Recovery is a new legal repair cycle—`repair_start` at the
   next cycle, followed by a distinct-role and distinct-context reverification—which supersedes the
   invalid terminal chain and makes the close audit eligible to clear.
5. Sealed and closed waves are never retroactively invalidated merely by validation or upgrade.
   Frozen history stays readable and stays passing until an operator explicitly reopens it.
6. Seed prose distinguishes what is mechanically enforced from what remains an honor-system
   declaration, so no reader infers unforgeable guarantees from a self-declared field.
7. Canonical seed changes flow through the existing renderer and install/upgrade paths: seed 209 owns
   the protocol, seed 239 carries the QA obligation, and their rendered target surfaces are updated.
   Upgrade replaces the packaged server/seed surfaces and requires the normal MCP reload before the
   new enforcement is active. No ledger migration, compatibility alias, or fallback is added.

## Scope

**Problem statement:** the repairer-is-not-the-reverifier rule exists only in seed prose. No code
compares the two actors or contexts, so a single agent can repair and reverify its own finding while
self-declaring independence, and the ledger records it as verified.

**In scope:**

- Chain-aware validation in `review_evidence.py` comparing a `reverification` against the
  `repair_start` it resolves, on both `context_id` and `actor`.
- The public `wf_review_event` tool docstring/diagnostics in `server_impl.py`.
- Surfacing the condition at the `wf_review_event` append boundary and at the close gate.
- A corpus regression proving no existing valid ledger is newly rejected.
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` and
  `239-qa-reviewer.prompt.md`, rendered `docs/contributing/review-and-evals.md` and
  `docs/agents/qa-reviewer.md`, plus renderer/install/upgrade regressions.
- Applicable `wf_review_event` and close-lifecycle docstrings plus
  `docs/specs/mcp-tool-surface.md`, including diagnostic precedence, recovery, and reload behavior.

**Out of scope:**

- Any attempt to authenticate callers or make `actor` unforgeable. The validator cannot know who is
  calling, and a design that implies otherwise would be worse than the current honest gap.
- Changing the run-kind grammar or the ordering rules, which are correct.
- The readiness-phase documentation gap, which is `1tmb0`.

## Acceptance Criteria

- [x] AC-1: A committed test expects a same-finding/current-cycle reverification sharing its
  `repair_start` context and declaring `fresh_context=true` to be rejected with a named
  contradiction. It is observed RED against current code and GREEN after the fix. Controls prove a
  same context on another finding or earlier cycle does not block the current chain.
- [x] AC-2: Same-actor reverification is rejected with `reverification_actor_not_distinct` without
  claiming caller identity; a distinct-role/context reverification succeeds. Same-context evidence is
  rejected separately, and the existing repair waiver cannot clear either policy.
- [x] AC-3: Executed `wf_review_event` preview/create calls prove both rejection codes, append nothing,
  and leave the prior synthesis head byte-identical; neither attempt can silently clear the finding.
- [x] AC-4: The close gate surfaces an affected current/latest chain in an open/reopened wave even
  when records were appended by older code, while identical seeded closed archives containing both
  same-actor and same-context contradictions remain valid until reopened. An executed reopened-wave
  control proves detect → `repair_start` at the next cycle → distinct-role/context reverification →
  close-eligible, rather than stranding an already-terminal finding.
- [x] AC-5: Every existing wave ledger in `docs/waves/` still validates. Executed over the real
  corpus, not a fixture, because the fixtures were written by the same model that wrote the
  validator. No sealed wave changes state.
- [x] AC-6: Seed prose states which independence properties are enforced and which are declared, and
  a test pins that claim against the validator's actual behavior so the two cannot drift.
- [x] AC-7: Docs gate and full framework suite green.
- [x] AC-8: Renderer, fresh-install, and upgrade fixtures stage both canonical seeds and produce the
  updated review-and-evals and QA carriers in a disposable target; no deprecated wording survives.

## Tasks

- [x] Write the AC-1 desired-behavior test and record it failing against current code before the fix;
  keep it as the permanent green regression after repair.
- [x] Census the real corpus before implementation: 35 same-actor chains—nine in closed wave
  `1slep` and 26 in closed wave `1skt1`—plus two same-context contradictions in closed `1skt1`.
  Record the forward-only blocking decision and preserve both archive classes in regressions.
- [x] Implement the chain-aware comparison in `review_evidence.py`.
- [x] Wire detection into the `wf_review_event` append path and the close gate.
- [x] Run AC-5 over every ledger in `docs/waves/` and confirm no regression.
- [x] Update the seed and `docs/contributing/review-and-evals.md` with the enforced/declared split.
- [x] Regenerate both rendered carriers and extend renderer/install/upgrade contract tests.
- [x] Update public review-event/close tool docstrings and the MCP tool-surface spec; prove upgrade
  replaces the packaged implementation and the new contract becomes live after reload without ledger
  migration or fallback.
- [x] Full suite and docs gate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Desired-behavior test must fail against current code for the named reason, then pass after repair |
| corpus-census | implementer | — | Completed at prepare: 35 same-actor chains across closed `1slep`/`1skt1`, including two same-context contradictions in `1skt1` |
| validator | implementer | red-test, corpus-census | Chain-aware context and actor comparison |
| boundaries | implementer | validator | Append-time and close-time surfacing |
| docs | implementer | validator | Enforced versus declared, pinned by a test |

## Serialization Points

- `review_evidence.py` is the verification substrate for every wave. A defect introduced here is
  self-concealing, so 1tmb2 is implemented and independently reverified to a hard checkpoint before
  the related 1tmb3 change begins; no concurrent shared-test editor is permitted.
- AC-5 must run before the change is considered complete, since a false rejection would block every
  in-flight wave.

## Affected Architecture Docs

`docs/contributing/review-and-evals.md`, `docs/agents/qa-reviewer.md`, and the public review-evidence
tool contract in `docs/specs/mcp-tool-surface.md`. No ADR: this enforces an existing documented rule
rather than choosing a new one.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The defect itself, and the only AC that proves the gap was real before it was closed. |
| AC-2 | required | The same-actor case is the common real occurrence; leaving it unhandled would fix the rarer contradiction and miss the frequent one. |
| AC-3 | required | Detection at close is too late to be actionable; the repair context is gone by then. |
| AC-4 | required | Ledgers already written without the check must not pass close unexamined. |
| AC-5 | required | A false rejection would block every in-flight wave, and the corpus is the only oracle the fixtures cannot substitute for. |
| AC-6 | required | The load-bearing correction: a reader must not infer an unforgeable guarantee from a self-declared field. |
| AC-7 | required | Standard gates. |
| AC-8 | required | The framework behavior must reach installed and upgraded target projects, not only this self-hosted repository. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-26 | Filed. Gap established by an independent readiness council during wave `1tj0l`, then confirmed by a filesystem-wide `rg` census over every framework `*.py`: only two queried actor-comparison hits, both approval actor/boolean checks; no repair/reverification chain identity comparison. | `review_evidence.py` `build_compact_review_event`; `rg` over `.wavefoundry/framework --glob '*.py'`, 2/2 hits accounted for. |
| 2026-07-27 | Premise re-exercised before implementation: a same-actor, same-context repair_start + clearing reverification declaring fresh/independent was ACCEPTED end-to-end by `build_compact_review_event` + `validate_review_evidence_records` (head reached `completed` with cleared lanes). AC-1/AC-2 red tests then written and observed RED for exactly that reason (rows appended where `()` expected) before any fix. | scratchpad `probe_premise_1tmb2.py`; `RepairReverificationIndependenceTests` red run: 4 rejection tests FAILED on acceptance, 4 audit tests ERRORED on missing `repair_independence_violations`, 3 controls green |
| 2026-07-27 | Implemented: chain-aware `_reverification_independence_defect` + `_resolving_repair_start_context` + `repair_independence_violations` in `review_evidence.py`; append boundary emits `reverification_context_not_fresh` / `reverification_actor_not_distinct` as diagnostic codes; close gate emits `review_evidence_independence_invalid` only for non-closed status. Guard mutations killed: precedence swap, audit first-not-latest, append-guard removal, close-audit removal, closed-status-gate removal, code-mapping drop (6/6); finding-filter drop killed after control reorder; cycle-filter removal measured as an equivalent mutant (cycle monotonicity enforced elsewhere makes latest-wins resolution equivalent on valid ledgers) — filter retained as explicit intent. | `test_review_evidence.py` `RepairReverificationIndependenceTests`; `test_server_tools.py` `RepairIndependenceBoundaryTests`; mutation transcript in session |
| 2026-07-27 | AC-5 executed over the real corpus with the enforcement join (synthesis → evidence → verification_context): 37 ledgers, 0 invalid, no sealed wave changed state. Enforcement-visible affected chains: 34 same-actor (25 in closed `1skt1`, 9 in closed `1slep`) and 6 fresh-declared same-context contradictions (all cycle-1 `1skt1`); latest-chain audit would flag 24 (`1skt1`) + 9 (`1slep`) only if reopened. Delta vs the prepare census (35/2) explained: the prepare join used run-level identity with dedup-evidence fallback — it counted `reverification-freshness-misattribution` cycle 3 (not same-actor at the per-finding evidence the validator reads) and tagged the two cycle-4 chains same-context via the shared batch dedup context (per-finding reverification contexts are distinct and are what enforcement compares). Both joins agree: every affected chain lives in the two closed waves; zero open/reopened waves affected. | scratchpad `census_1tmb2_impl.py` + `census_1tmb2.py` cross-check; `RealCorpusRegressionTests` committed |
| 2026-07-26 | Repair (cycle 1) of finding `same-actor-nonfresh-rejection-untested`: added `RepairReverificationIndependenceTests.test_same_actor_nonfresh_nonclearing_reverification_is_rejected` pinning the council's P8 probe shape — a same-actor, fresh_context=false, non-clearing reverification (blocking_required_lanes unchanged) is rejected with `reverification_actor_not_distinct` and appends nothing. Passed on current code unmodified; M5 mutation kill proven: narrowing the actor rejection in `_reverification_independence_defect` to fire only when fresh_context is true made the test FAIL (rows appended), byte-identical revert verified by sha256 (`8bf5e380…d1157` before and after; mutated `94dad70c…4cf07`), test and full module green after revert. No production code changed. | `tests.test_review_evidence` 118 tests OK; docs-lint ok |
| 2026-07-26 | Prepare-time corpus census found 35 same-actor chains: nine in closed wave `1slep`, 26 in closed wave `1skt1`, and two of the `1skt1` chains also carry same-context contradictions (`architecture-state-contract-drift` cycle 4 and `carrier-symlink-root-escape` cycle 4). | Independent reality-check parse of every `docs/waves/*/events.jsonl`; both affected waves are closed, so frozen history remains exempt under Requirement 5 and becomes forward-audited only if reopened. |
| 2026-07-27 | Repair (cycle 2) of finding `same-actor-same-context-nonfresh-reverification-accepted`: the same-context/non-fresh early return in `_reverification_independence_defect` (review_evidence.py:1740-1743) bypassed the actor policy, so a same-actor, same-context, fresh_context=false reverification appended 3 rows. Red test `test_same_actor_same_context_nonfresh_reverification_is_rejected` observed RED on exactly that probe shape, then the precedence was fixed: actor equality is evaluated whenever the fresh-context contradiction did not fire. Quadrant controls added (same-actor/same-context/fresh=true returns only `reverification_context_not_fresh`; distinct-actor/same-context/non-fresh still passes policy and cannot clear). Mutation kill: restoring the early return made the red test FAIL (rows appended); byte-identical revert verified by sha256 (`83e2cd94…d69b4` before and after). No existing test modified. | `tests.test_review_evidence` 121 tests OK; `RepairIndependenceBoundaryTests` OK; full suite 6291 tests OK; repair_start recorded at cycle 2 (`run-repair-start-2-same-actor-same-context-nonfresh-`) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-26 | Scope the change to contradiction detection and same-actor detection, explicitly NOT to caller authentication. | The validator sees strings and cannot know who is calling. A mechanism implying it could would create false confidence, which is worse than a documented honest gap. The achievable wins are real: the context_id contradiction is decidable with no trust assumption, and the same-actor case covers the convenience failure that actually occurs. | Attempt caller identity or signing (rejected: not available to an in-process validator, and false confidence is worse than a known gap); leave it to prose (rejected: prose is what failed here). |
| 2026-07-26 | Reject same-context and same-actor attempts before append; audit only older non-closed/reopened ledgers at close; preserve closed history until reopened. | Context equality is a contradiction. Actor equality is a forward protocol policy rather than identity proof. Rejecting before synthesis preserves one current-state authority and follows the implementer-then-reviewer role model. | Retain-but-block was rejected because it would create a completed synthesis plus a separate nonterminal audit; warning-only and new waiver machinery were rejected as ineffective or needlessly complex. |
| 2026-07-26 | Evaluate close-time independence against the current/latest chain and clear an inherited violation only through a new legal repair cycle. | Existing grammar does not allow another reverification on an already-terminal cycle. A next-cycle `repair_start` plus independent reverification provides a real recovery path and leaves append-only history intact. | Reverify the terminal cycle in place (rejected: illegal grammar); permanently block reopened archives (rejected: no recovery path). |
| 2026-07-27 | Requirement 2 settled on measured corpus data: same-actor reverification is REJECTED at append (not a blocking diagnostic). | The census shows zero same-actor chains in any open or reopened wave — every affected chain lives in closed `1skt1`/`1slep`, which the status gate exempts — so forward rejection blocks no in-flight work while preventing the observed convenience failure from recurring. A blocking diagnostic would leave a completed synthesis plus a separate nonterminal audit, the dual-authority state the prior decision row already rejected. | Blocking diagnostic after append (rejected: creates a second current-state authority and still requires the same recovery); warn-only (rejected: the observed 34-chain corpus shows warnings without enforcement do not change behavior). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The new check falsely rejects valid in-flight or historical ledgers | AC-5 runs over every real ledger in `docs/waves/` before the change is complete, and AC-1 pins the intended rejection narrowly to the contradiction case. |
| Same-role equality rejects two genuinely independent agents sharing one lane name | The diagnostic is explicitly protocol policy, not identity proof. The canonical repair actor is `implementer` and reverification actor is the blocking reviewer lane; callers retry under those truthful acting roles. |
| The fix is written and verified by one agent, reproducing the very defect being fixed | This change is implemented and reverified by different agents, and that separation is stated here so a reviewer can check it was honored. |
| A reader concludes independence is now guaranteed | AC-6 requires the seed to state the enforced/declared split, pinned by a test. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
