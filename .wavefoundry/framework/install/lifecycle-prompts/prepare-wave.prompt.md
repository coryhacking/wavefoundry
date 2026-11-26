# Prepare Wave

Owner: Engineering
Status: active
Last verified: {{generated_at}}

Shortcut: **`Prepare wave`** | Alias: **`Ready wave`**

## Operator-selected small changes

Check the effective lane returned by Prepare. If the operator selected the small-change lane at admission and the change qualifies, obtain an independent code-reviewer readiness approval on the current receipt. The reviewer must inspect the intended effect, including whether an internal helper changes public behavior. Request ordinary review if that effect is public or uncertain. Follow the council steps below for ordinary review.

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-spec.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort for readiness analysis by task fit, and record the bounded work allocation in the existing wave record. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

In existing readiness and delivery reviews, ask whether meeting Requirements and ACs would establish Product Intent and the wave Objective, and whether added complexity, runtime cost or operator burden undermines that outcome. At delivery, distinguish evidenced outcomes from intended benefits; checked implementation steps alone prove neither benefit nor approval. Use the existing lanes and gates.

Confirm that an admitted wave is implementable before the first code edit.
Readiness and opening are separate: any number of waves may be readied, while
only one wave may be open for implementation.

## Readiness checks

For readiness, collect one assigned independent reviewer’s prediction before sharing the primer or separate answer-bearing material with that reviewer. Prefer QA when assigned. Use the two exchanges in the council-chair guidance and keep the original prediction in ordinary readiness evidence.

1. Confirm every admitted spec is wave-owned and complete.
2. Resolve duplicate or staged-only placement drift.
3. Verify requirements, scope, acceptance criteria, architecture impact, and
   explicit dependencies.
4. Classify each acceptance criterion as required, important, nice-to-have, or
   not-this-scope, with rationale.
5. Follow the effective lane returned by Prepare. For ordinary review, select reviewer and builder lanes under project policy. Automatic lanes are derived from the
   explicit repo-relative paths each spec declares in
   `## Serialization Points`, never from Scope or other narrative, and never
   from prose inside that section, in either declaration form. A path is
   declared by a bullet whose content is entirely repo-relative paths, or
   inside an explicit `**Review targets (repo-relative paths):**` block whose
   backtick-quoted entries may contain spaces. One stray English word makes the
   whole bullet prose in either form, and a wrapped bullet is prose entirely.
   A declared path token has at least one `/`, so a root-level file (a
   changelog, a readme) is never a token in either form, and a bullet
   declares all or nothing in either form, so one such token turns the whole
   bullet into prose and every other path in it goes undeclared with it. In
   a bullet a `*` disqualifies the token too; inside the explicit block a span
   is kept only when its last segment carries an extension or the span ends in `/`,
   so there a `*` span is accepted as a phantom (a `*.json`, a `dir/*/`) that
   matches no file and recruits a lane only through a trigger token it happens to carry (a directory prefix, an extension, or a trigger basename),
   a block holding only phantoms leaves the document declared with whatever
   roster those triggers recruit (empty when none is a trigger), and any other
   `*` span turns its bullet into prose. Put a root-level file in its own prose bullet, and
   declare the directory that holds globbed files. Adoption is decided per
   DOCUMENT, so one spec
   declaring targets never suppresses a sibling's scoring, and a spec
   that declares no path keeps legacy whole-document scoring so coverage is
   never silently lost. That derivation is a FLOOR, not the whole answer:
   add any lane your own judgment calls for to the wave record's
   `Requested review lanes`, which is always honored and costs no receipt
   churn because `wave.md` is not part of the review-policy digest. Architecture,
   security and performance risk in particular are usually judgment calls that
   no file path expresses — an ownership shift or a protocol change can live
   entirely in files that recruit only the code lane. In ordinary review, include QA for bug fixes
   and any additional lanes required by local policy, and never read an empty
   automatic roster as evidence that no review is warranted.
6. When the current receipt requires `council-readiness`, run the readiness council and record its actual
   seats, evidence, disagreements, and verdict, including the council-chair's
   `intent_fit`: for each admitted change and the wave Objective, whether
   meeting its Requirements and ACs would establish its Product Intent, citing
   the measure of success and whether it can be read after release (seed 215).
   The typed `council-readiness` approval records that verdict as
   `evidence.intent_fit` (`establishes` or `partially`); a plan that will not
   establish its intent is a finding, not an approval.
7. Record product-owner acknowledgment when the change affects product
   behavior or acceptance expectations.
8. Use `wf_prepare_wave(mode='ready')` to ready without opening, or
   `wf_prepare_wave(mode='create')` to ready and open when the single-open-wave
   slot is available. `mode='dry_run'` validates and reports without changing
   anything; `mode='evaluate'` is an accepted read-only alias for it.

## Gate

Implementation may begin only after readiness is clean and its current approval
is recorded. The readiness verdict is the single pre-code review decision; it
confirms admissibility, not delivery approval.

## Readiness decision handoff

At the existing operator handoff after focused readiness verification, compare the next proposed repair with the outcome of the applied repair. If it would undo that outcome, cite the finding or repair evidence for each request, explain exactly what would be lost, and ask which behavior the next repair must preserve. Wait for operator direction. A revision that preserves the earlier outcome needs only the ordinary handoff.

Use `wf_review_wave(phase="prepare")` for `data.review_actions.readiness_decision_packet` and its `focused_rereview` navigation. The compact packet exposes existing canonical finding/approval facts, not a second classifier or approval. Distinguish unresolved required blockers, nonblocking notes, ordinary missing approvals and unavailable/omitted detail; inspect the named full authority when the summary is incomplete. Do not infer readiness from empty actions or a review-round stop from receipt-publication counts.

After the actual bounded repair and focused verification, give the operator a short decision handoff before any further automatic round: each remaining blocking finding and unmet obligation, decisive evidence or uncertainty, affected lanes/current approvals, advisory notes separately, and the next safe options. Offer another explicitly scoped bounded repair/verification, a plan/scope amendment with re-Prepare, or needed evidence with dependent work paused. An applicable explicit residual-risk waiver uses the existing `waiver_id`, `waiver_scope`, `waiver_reason` and `waiver_risk` protocol; it is neither independent verification nor specialist approval. Do not select an option, waive a requirement or accept sensitive-data risk on the operator's behalf. Ordinary unfinished readiness alone is not this stop boundary.

Use the existing cumulative `focused_rereview` packet: source/blocking lanes replay each finding; other approving lanes assess only delta effects plus necessary unchanged context; new lanes assess their remit once. Full amended plans remain available for context, not an invitation to an unrelated whole-document sweep. Every required lane and any receipt-required council still re-record current-receipt approvals; no approval is carried forward by the summary.

## Focused readiness re-review

For stale readiness, use the guided review actions and seed 209’s **Focused readiness re-review**. Compare cumulatively from each lane’s last approved receipt, with its prior approval/evidence, changed sections and a verified normalized before/after delta when available; provide the full amended plans and affected dependency context, and ask whether the change alters the verdict. Newly required lanes perform normal initial review. Exact raw receipt snapshots under `.wavefoundry/work/<wave-id>/receipts/` are optional aids, never approval authority. Missing legacy metadata, missing/corrupt/cleaned snapshots, stale inputs, incompatible normalization or truncated output must be explicit; obtain full text or fall back to normal full review. Reads create no snapshots. Receipt identity, required lanes, approval invalidation and deferral rules are unchanged; no approval transfers or measured effort savings are implied.

## Disposable work

Use the lifecycle-reported `.wavefoundry/work/<wave-id>/`, keyed by the resolved unique prefix, for shared temporary work; include the path and availability notices in coordinator briefs. Follow seed 180’s **Disposable work** and seed 209’s **Review Artifact Discipline**. Reads and dry-runs create nothing; unavailable work is advisory and existing host permissions apply. Receipt copies and review notes are disposable aids; preserve unique proof before final evidence and keep durable approval authority in its existing records.

Write every file you create for a wave, including coordinator briefs, logs, captured test output and build output, inside that wave's own work folder, in a child folder when that helps; never write a file directly in `.wavefoundry/work/`. Before the wave exists, keep the content in task context until a lifecycle call reports the work area. `wf_audit` and close report files and links left directly in the work root as the advisory `work_root_loose_files`. If you wrote such a file for a wave, move it into that wave's folder while the wave is open, or delete it. Leave any other loose file in place, including one you are not sure you wrote (a name that starts with a wave id does not prove who wrote it), and report it to the operator, who decides. Never move a file you did not write into a wave's folder: close removes that folder with everything in it.
