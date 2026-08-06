# Marking a Task Done Should Not Cost a Review Cycle, but Deferring One Should

Change ID: `1ug66-enh checkbox-state-digest-split-and-mark-tool`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-05
Wave: `1ui1d review-loop-friction`

## Rationale

Wave 1uhcb excluded `## Progress Log` from the review-policy digest, so recording a repair no longer
supersedes the receipt. It deliberately deferred **checkbox state**, and that is the carrier that
fires most often: `AGENTS.md` **Change Doc Tracking (Real-Time)** requires marking AC and task boxes
as work completes, so a single implementation flips them many times, and every flip moves the digest
and lapses the readiness roster (the council approval plus every prepare lane, measured at seven
signoff keys in wave 1ugk8).

The cost is not hypothetical. During 1uhcb's own implementation the coordinator instructed two
implementer agents to **batch** their checkbox edits specifically to avoid receipt churn. That is a
workaround for a defect, and it degrades the real-time tracking the rule exists to produce.

**The operator's framing (2026-08-05), which sets this change's boundary:** recordkeeping exists to
confirm the work happened and to let the actions be reviewed later. It is not the work. The work
lives in code and other documents. Updating recordkeeping must not trigger reviews or other work.

**But checkbox state is not uniformly recordkeeping, and the operator wants the tracking kept.** The
two markers say different things:

- `[ ]` to `[x]` records that a committed item is done. Progress. Nothing about the plan changed.
- `[ ]` to `[~]` says a requirement was **intentionally not met**, and per `AGENTS.md` it must carry
  an inline rationale. That is a scope statement, and a reviewer must see it.

So the boundary runs between the markers, not around the section. An earlier draft of this idea
proposed excluding checkbox state wholesale; that was wrong and is recorded here so it is not
retried, because it would have made a `[~]` deferral invisible to review.

## Requirements

1. **All task marker changes and AC completion are normalized; an AC `[~]` and its rationale are not.**
   `canonical_review_policy_body` normalizes an AC `[x]` and every task checkbox marker toward the
   unchecked form before hashing, so progress tracking never changes `policy_input_digest`. An AC
   `[~]` is left byte-intact, including its inline rationale note, because it changes the delivery
   contract and must supersede the receipt. A task `[~]` stays visible in the document and satisfies
   the close gate exactly as `[x]` does: per `AGENTS.md` **Change Doc Tracking**, every AC and task
   must be `[x]` or `[~]` at close, so it is a silent `[ ]` that blocks close, never a `[~]`. A task
   `[~]` is tracking state rather than a new delivery contract and therefore does not reopen review
   by itself. Nothing in this change alters the close gate.
2. **The transitions behave as an operator would expect.** On an AC, `[ ]` to `[x]` is free while
   `[x]` to `[~]`, `[~]` to `[x]`, and an edit to a `[~]` rationale move the digest. On a task, every
   marker transition, including `[x]` to `[~]` and `[~]` to `[x]`, is free. State each direction as
   its own case.
3. **Only AC and task checkbox lines are in scope.** Do not normalize checkbox syntax appearing in
   Rationale prose, in fenced examples, or in any other section. Reuse the fence-tracking and
   anchored-matching discipline wave 1uhcb established rather than inventing a second approach.
4. **Two small MCP tools, `wf_mark_ac` and `wf_mark_task`, mark one unambiguous AC or task complete
   or deferred; `wf_mark_ac` refuses a reasonless AC `[~]` on exactly the population docs-lint
   enforces.** They are exact-item editors,
   not a generic document mutation surface: it rejects an absent or ambiguous target, changes only
   that marker and any required AC rationale, and does not collect evidence for `[x]`. Today the
   rationale requirement is enforced by docs-lint *after* the invalid state is written. The tool
   enforces it at the write, so a silent required-AC `[~]` never lands.
   **The enforced population is narrower than "every `[~]`", and the tool must mirror it rather than
   exceed it.** Read from `_check_tilde_required_ac_has_inline_note`
   (`wave_lint_lib/wave_validators.py:294-365`): the note is required only for ACs whose priority in
   the `## AC Priority` table is `required`; important and nice-to-have ACs may use `[~]` loosely,
   and **tasks never require a note at all** (Req-12). The check is satisfied by either an inline
   italic segment or at least `_INLINE_NOTE_MIN_CHARS` of prose after the AC label. A tool that
   refused every reasonless `[~]` would be stricter than the backstop, would block legal task
   deferrals, and would contradict this change's premise that tracking must not cost friction.
   Resolve priority by AC id with the positional fallback the validator already uses, so the two
   cannot disagree on the population. Scope it deliberately otherwise: it enforces the required-AC
   `[~]` rationale and nothing else.
5. **The existing docs-lint silent-`[~]` check stays exactly as it is**, as the backstop for an
   author who edits by hand rather than through the tool, and a test pins that it still fires. If
   Requirement 4's mirroring reveals a genuine gap in the lint population, that is a finding to
   record and raise, NOT licence to widen either surface inside this change.
6. **Red-first, and one case per transition in Requirement 2.** The digest-sensitivity guard wave
   1uhcb established applies here too: at least one sensitivity case per requirement-bearing surface
   must remain, so an over-broad normalization fails loudly instead of silently weakening the
   receipt.

## Scope

**Problem statement:** the mandated real-time marking of AC and task checkboxes supersedes the
review-policy receipt on every flip, so progress recording costs a re-Prepare and a readiness
re-record, and implementers are being told to batch their tracking to avoid it.

**In scope:** the checkbox normalization in `canonical_review_policy_body`'s module; its tests; the
new MCP tool and its registration and docs; the docs-lint backstop pin; `CHANGELOG.md`.

**Out of scope:** `## Progress Log` (already delivered by 1uhcb); Review Checkpoints narrative
verdicts (a separate recordkeeping surface, worth its own change); lane selection (see
`1ug67-bug`); ledger record ergonomics (see `1ug68-enh`); any change to what `[~]` MEANS or to the
close-time rule that every AC must be `[x]` or `[~]`.

## Acceptance Criteria

- [x] AC-1: Flipping an AC or task from unchecked to `[x]` leaves `policy_input_digest` and the
  derived receipt id unchanged, proven through the real digest function on a real change doc rather
  than by asserting on the canonicalizer alone.
- [x] AC-2: Each transition in Requirement 2 has its own case: every stated AC `[~]` transition and
  rationale edit moves the digest, while every stated task-marker transition leaves it unchanged.
- [x] AC-3: One digest-sensitivity case per requirement-bearing surface still moves the digest, so an
  over-broad normalization fails loudly.
- [x] AC-4: Checkbox syntax outside AC and task lines, including inside a fenced block, is not
  normalized.
- [x] AC-5: The MCP tool edits exactly one unambiguous item, marks `[x]`, marks an AC `[~]` with a
  reason, and REFUSES a reasonless `[~]` on a required-priority AC; the refusal and ambiguous-target
  rejection are pinned by tests.
- [x] AC-5a: The tool's refusal population matches the validator's exactly, pinned on both sides of
  each boundary: a reasonless `[~]` on an `important` AC is ALLOWED, a reasonless `[~]` on a task is
  ALLOWED and digest-neutral, and both forms the validator accepts as a note (inline italics, and
  prose at the `_INLINE_NOTE_MIN_CHARS` boundary) are accepted by the tool. A test asserts the tool
  and `_check_tilde_required_ac_has_inline_note` agree on the same document rather than asserting
  each separately.
- [x] AC-6: The docs-lint silent-`[~]` backstop still fires on a hand-edited doc, pinned by a test.
- [x] AC-7: Mutation-checked. At minimum: normalization removed; AC `[~]` normalization widened;
  task `[~]` is left digest-sensitive; normalization is applied outside AC and task lines; the tool's
  rationale refusal is removed; and the tool's refusal is widened to every `[~]` regardless of
  priority. Each mutant is killed by a named test.
- [x] AC-8: Full framework suite and docs-lint pass.

## Tasks

- [x] Census the carriers against the then-current tree at Prepare (see Affected Architecture Docs)
- [x] Red-first tests for AC-1 through AC-4, including AC-versus-task `[~]` transitions
- [x] Checkbox normalization
- [x] `wf_mark_ac` / `wf_mark_task`, their refusal and ambiguity paths, registration, and docs
- [x] Backstop pin for docs-lint
- [x] Mutation check; full suite; docs-lint; CHANGELOG bullet

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| digest     | implementer | —          | Normalization plus its tests |
| tool       | implementer | digest     | New MCP tool; needs the normalization semantics settled first |


## Serialization Points

- `.wavefoundry/framework/scripts/gardener_metadata.py`; `.wavefoundry/framework/scripts/tests/test_review_policy.py`; `.wavefoundry/framework/scripts/server_impl.py`; `.wavefoundry/framework/scripts/tests/test_server_tools.py`; `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`; `docs/specs/mcp-tool-surface.md`; `CHANGELOG.md`
- `wave_validators.py` is a READ coupling, not a write target: Requirement 5 keeps
  `_check_tilde_required_ac_has_inline_note` byte-unchanged, but AC-5a's agreement test exercises it
  directly, so it is a coordination surface. Listing it does not change this change's automatic lane
  roster, which already selects on `.py`.

## Affected Architecture Docs

**Census deliberately NOT pre-written, and this is a choice rather than an omission.** This change
extends the same function wave 1uhcb modified, and during 1uhcb several precise `file:line` carriers
went stale within hours as repairs landed. Run the carrier census at Prepare against the then-current
tree and record it then. Candidates to sweep: the MCP tool-surface spec, any seed or prompt describing
checkbox marking (`seeds/170` owns AC and task authoring and its `[~]`-marker sub-section is the
nearest neighbour), `AGENTS.md` **Change Doc Tracking**, and `docs/agents/memory/` records describing
what the receipt digests. Treat `N/A` as a finding until the sweep is actually run.

## AC Priority

Populated at plan time, before the prepare council runs, per the ordering rule wave 1uhcb shipped
(`seeds/170-plan-feature.prompt.md`; `docs/plans/plan-template.md`).


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The `[x]`-is-free property is the change's entire purpose; proven through the real digest function rather than the canonicalizer alone |
| AC-2 | required   | The per-transition cases are what keep the marker split honest in both directions |
| AC-3 | required   | The digest-sensitivity guard is the direct defence against an over-broad normalization silently weakening the receipt |
| AC-4 | required   | Fenced and prose checkbox syntax is the exact vacuity class wave 1uhcb shipped a defect in; see memory `1ufqs-mem` |
| AC-5 | required   | Write-time refusal of a reasonless required-AC `[~]` is the tool's reason to exist |
| AC-5a | required  | Mirroring the validator's population is what stops the tool becoming stricter than its own backstop and blocking legal task deferrals |
| AC-6 | required   | The hand-edit backstop must survive, or the tool becomes a bypass rather than an improvement |
| AC-7 | required   | Mutation checks make the rest non-vacuous |
| AC-8 | required   | Suite and docs gate are the standing release condition |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-05 | Filed as the agreed follow-up to wave 1uhcb, which excluded the Progress Log and deferred checkbox state. Operator refined the design during planning: keep the tracking, split on the marker rather than excluding the section, and add a tool that enforces the `[~]` rationale at write time. The wholesale-exclusion approach is recorded as rejected so it is not retried. | Operator direction 2026-08-05; wave 1uhcb Out of scope; two implementer agents instructed to batch checkbox edits during 1uhcb to avoid receipt churn |
| 2026-08-05 | Admitted into wave `1ui1d review-loop-friction` and corrected during a pre-Prepare discovery pass. The plan described the tool as enforcing "the `[~]` rationale" and the docs-lint check as the same rule enforced later, but reading `_check_tilde_required_ac_has_inline_note` shows the enforced population is much narrower: `required`-priority ACs only, tasks exempt by Req-12, satisfied by italics OR a prose-length threshold. As written the tool would have been STRICTER than its own declared backstop and would have blocked legal task deferrals. Requirement 4 now states the population and the id-with-positional-fallback resolution, AC-5a pins both sides of each boundary against the validator itself, and AC-7 mutation-kills the widened refusal. | `wave_lint_lib/wave_validators.py:294-365`; `canonical_review_policy_body` at `gardener_metadata.py:108-122` confirmed as the two-normalization insertion point this change extends |
| 2026-08-05 | **Operator-directed addition (2026-08-05): Context Efficiency attribution for `wf_mark_ac` and `wf_mark_task`, in the implement stage.** Scope beyond the admitted ACs, taken on explicit operator direction and recorded here rather than folded silently. Design landed in three corrections, each from operator challenge. (1) First attempt credited the implement-wave prompt once per wave via `LIFECYCLE_PROMPT_MAP` — wrong in KIND, because it models a recurring per-write saving as a one-time procedure lookup. (2) Second attempt credited per write but measured only the matched LINE — right shape, wrong magnitude. (3) Delivered: `workflow_instruction_proxy` gained `avoided_authoring_tokens`, the mark tools report the FULL item block (bullet plus continuation lines), and credit is 2x that block per successful write, because an equivalent hand edit must carry the item in context and reproduce it twice, as the string to find and as the replacement. Dry runs and no-op marks earn nothing; every write is credited because every write saves. The tools deliberately earn NO content-source credit: they return no change-doc content and `_context_source_paths` credits only content present in the envelope. | Measured over this wave's own 41 checkbox items: hand-editing 4,084 tokens versus 791 for tool calls, 5.2x overall, with acceptance criteria at 8.6x (121 tokens each) and short task lines at 1.7x (16 each). Live: 6-line AC-5a credits 266, 4-line AC-7 credits 180, 3-line AC-1 credits 130, dry run 0; three writes accumulate 576 under `stage implement`. Suite 6842 across 62 files OK; docs-lint ok |
| 2026-08-05 | **Delivery review, two repairs here.** AC-2 claimed each of the seven stated transitions as its own case but delivered one test with three assertions, leaving AC `[x]`-to-`[~]`, AC `[~]`-to-`[x]`, task `[x]`-to-`[~]` and task `[~]`-to-`[x]` unpinned; the behavior was probe-verified correct, so this was a pinning gap rather than a defect. `test_each_checkbox_transition_direction_is_pinned_independently` now covers every direction. Writing it caught a vacuity trap in the review's own first draft: comparing `[x]` against `[~]` while also varying the rationale text let the test pass on a canonicalizer that wrongly normalizes an AC `[~]`, because the note alone still moved the digest. The comparisons now hold the label byte-identical, and the mutant that normalizes AC `[~]` is killed. Separately, `canonical_review_policy_body`'s docstring still read "Two narrow normalizations, and no more" while the function performs three; corrected, and it now states that an AC `[~]` is deliberately preserved. | Mutation check: AC-`[~]`-normalizing mutant SURVIVED the first draft and is killed by the corrected test; `gardener_metadata.py` docstring versus its three normalization calls |
| 2026-08-05 | Prepare-review findings, both repaired. (1) Requirement 1 said a task `[~]` "still blocks close until it is `[x]` or `[~]`", which is tautological and reads as though a task `[~]` blocks close. Per `AGENTS.md` **Change Doc Tracking** the close gate requires every AC and task to be `[x]` or `[~]`, so a silent `[ ]` blocks and a `[~]` satisfies it; reworded, with an explicit statement that this change does not alter the close gate. (2) Serialization Points omitted `wave_lint_lib/wave_validators.py` even though AC-5a's agreement test exercises `_check_tilde_required_ac_has_inline_note` directly; added and labelled a READ coupling, since Requirement 5 keeps that validator byte-unchanged. Adding it leaves the automatic roster unchanged (already selected on `.py`). | `AGENTS.md` close-gate rule; `wave_lint_lib/wave_validators.py:294-365`; selector probe before and after the edit |
| 2026-08-05 | Review resolved the remaining task-tilde ambiguity: AC `[~]` changes the delivery contract and remains digest-sensitive; every task marker is tracking state and is digest-neutral. The planned tool is constrained to one unambiguous item, rather than becoming a generic document editor. | AGENTS Change Doc Tracking contract; docs-lint enforces a rationale only for required ACs, never tasks |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-05 | Split on the delivery contract: normalize AC `[x]` and every task marker; keep an AC `[~]` and its rationale digested | AC completion and task status record progress. Only an AC `[~]` changes what the wave promises to deliver, so it remains review-relevant. This removes task-deferral churn without hiding an acceptance-criterion deferral | Keep every `[~]` digested (rejected: reasonless task status would still trigger review); exclude all checkbox state (rejected: makes an AC `[~]` deferral invisible) |
| 2026-08-05 | The tool enforces the `[~]` rationale only, not evidence for `[x]` | Evidence belongs in the Progress Log and the ACs; demanding it inline at mark time would rebuild the friction this change exists to remove | Require evidence for `[x]` (rejected as overreach) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The normalization is drawn too wide and an AC `[~]` deferral stops lapsing approvals | AC-2 pins each AC-versus-task transition and AC-7 mutation-kills widened normalization |
| Checkbox syntax in prose or fenced examples gets normalized, corrupting the digest for unrelated docs | AC-4 pins it, reusing 1uhcb's fence-tracking discipline rather than a second approach |
| The new tool becomes the only supported path and hand edits silently lose the rationale check | AC-6 keeps the docs-lint backstop live and pinned |
| The tool is built stricter than the validator it mirrors, blocking legal task and important-AC deferrals and re-adding the friction this change removes | Requirement 4 states the enforced population from the validator's own source; AC-5a pins the allowed cases on both sides of each boundary and asserts tool-validator agreement on one document rather than testing each separately; AC-7 mutation-kills the widened refusal |
| This change's required lanes drift while its own target declaration is repaired | The historical pre-declaration fixture is retained in `1ug67-bug`; this amended plan now declares concrete paths and independently selects `code-reviewer`, `qa-reviewer`, and `docs-contract-reviewer`. The wave-level five-lane roster remains explicit rather than accidental |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
