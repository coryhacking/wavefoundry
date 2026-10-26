# AC-6 results

Owner: implementer
Status: active
Last verified: 2026-10-25

Declared gap: `ac6-declared-gap.md` (written before either plan existed). Plans written by a separate agent in neutral wording: `plan-a-one-command-bootstrap.txt` (expected to show the gap) and `plan-b-one-command-bootstrap.txt` (control).

Brief given to each fresh qa-reviewer, verbatim apart from the file name: "You are the qa-reviewer lane, readiness phase. Read your role: docs/agents/qa-reviewer.md. Then review this plan per your role: <plan file>. The plan is for a fictional project; there is no code to inspect, so review the plan document itself. Do not read any other file in that folder. Read-only: edit nothing. Report your readiness review (under 400 words) in your role's output shape, with a verdict and numbered findings with severity."

## Run 1, plan A (mis-aimed)

Verdict: needs more evidence (blocking). Intent-coverage map lists "On native Windows: no AC" and "Without prior toolchain setup: no AC. Hosted runners come with Python, make and bash already installed." Finding 1 (blocking): native Windows has no AC or runner. Finding 2 (blocking): "without prior toolchain setup" is never tested. Other findings (Requirement 4 vs AC-3 wording, negative paths, hook install check, page removal, pip freeze fragility, no after-release measure) are not intent-coverage findings about the declared gap.

Result: names both halves of the declared gap. Pass.

## Run 1, plan B (control)

Verdict: not ready. Intent-coverage map: Windows covered by AC-2; clean machine covered by AC-3 for Linux and Windows only; "macOS is not tested" on a clean machine; no after-release measure for "often failed". Finding 2 (blocker): macOS has no fresh-machine AC.

Result against the pass condition: fail, because an intent-coverage finding was raised on the control. Cause, checked against the control text: plan B AC-3 names "a fresh container image and a fresh Windows VM image", so macOS on a clean machine is genuinely untested; the control was not fully well-aimed. The reviewer did not raise the declared gap (Windows, clean machine in general) on the control. This is a fixture defect, not over-flagging by the reviewer; the seed 239 clause is not changed.

## Run 2, corrected control

One run on a corrected control, `plan-c-one-command-bootstrap.txt`: plan B with only AC-3 extended to a fresh macOS machine without Command Line Tools and an explicit after-release measure. Written by the coordinator, who knew the declared gap, so it is less independent than plans A and B.

Verdict: needs more evidence. The declared gap is not raised: Windows and the clean machine are mapped to AC-2 and AC-3, and the after-release measure (AC-8) is accepted. New intent-coverage findings, both genuine in the plan text: the documented command (`make bootstrap`) is not the command AC-3 tests on a machine with no toolchain, and "fresh clone" assumes git, which a fresh Windows VM or a macOS machine without Command Line Tools lacks.

Result against the pass condition: fail again, for the same reason as run 1: the control still has real intent gaps, which the reviewer names. No further run, per AC-6 ("never retries until it passes").

## Reading

The reviewer named the declared gap as blocking on the mis-aimed plan, and on both controls it did not raise that gap and instead named different gaps that are present in the control text. This is consistent with discrimination on the declared gap, but it is not proof: the pre-registered control condition failed twice, so specificity is unshown. The pre-written control condition (no intent-coverage finding at all) was not met, because neither control was free of intent gaps; writing a gap-free control turned out to be the hard part, not the reviewer's judgment. One sample per plan; this shows the guidance can work, not that it always will.

## Follow-up run, gap-free control (operator-directed)

Declared in advance in `ac6-control-run-declaration.md`. A separate agent authored `plan-d-control.txt` (a `--version` flag for a small fictional CLI) in neutral wording. A second, independent agent vetted it for intent coverage only and rated it gap-free, with one optional tightening (AC-4 should also rule out an offline update check); the author made that single revision and the plan froze (sha256 76e97b9ce281601a2ae057f581cee84e5a29d7bf7aad42bb2d23d13d86efc2dc). One fresh qa-reviewer, briefed only with `docs/agents/qa-reviewer.md` and the same neutral brief as plans A to C, reviewed it once.

Verdict: approve with findings, none blocking. Its intent-coverage map traced every Product Intent part (beneficiary, before, after, boundary) to ACs and stated "Untested part of the intent: none". Its five findings concern test strength and edge cases outside the Product Intent: AC-3's oracle shares the helper's metadata source, AC-4 needs a socket-blocking harness and a planted mutation, the missing-metadata fallback has no AC, AC-2's argument precedence is open, and config-load skipping is untested. None is an intent-coverage finding, so no adjudication was needed.

Result against the declaration: pass. On an independently authored and vetted gap-free control, the qa-reviewer raised no intent-coverage finding while still reviewing the plan critically. Together with run 1 (the declared gap named on the mis-aimed plan), this is one positive and one negative sample: the duty caught a planted intent gap and did not over-flag a covered plan. Two samples are evidence, not proof of reliability.
