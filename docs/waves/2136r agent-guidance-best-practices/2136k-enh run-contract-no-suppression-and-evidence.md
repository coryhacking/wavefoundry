# Run contract: no suppressed failures, two-attempt stop, evidence in reports

Change ID: `2136k-enh run-contract-no-suppression-and-evidence`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: 2136r agent-guidance-best-practices

## Rationale

Adopts three points from the Claude Code best-practices guide (code.claude.com/docs/en/best-practices) that the framework's run contract, seed 020, does not yet state. The seed already asks for the smallest change that addresses the root cause (020:20), and for diagnosis before a different approach (020:26). Three gaps remain.

1. **Suppressed failures.** Nothing forbids making a failing check pass without fixing its cause: skipping a test or marking it expected to fail, loosening an assertion or pattern, swallowing an exception, adding a lint or type ignore, raising a timeout or threshold, or deleting the check. Line 20 even permits a symptom-only patch once it is explained, which leaves room for exactly this.
2. **Repeated failed attempts.** Line 26 says "do not retry blindly" but names no point at which to step back. The guide's "correcting over and over" failure pattern recommends restarting from a better plan after two failed corrections. The implement-change loop (edit, test, observe, fix; `180-implement-change.prompt.md:48`) has no such point either. The trigger here is a reassessment, not a permission gate: ordinary debugging must stay autonomous.
3. **Evidence to the operator.** Nothing requires an agent's report to the operator to carry the command it ran and what it returned. Claude Code's host prompt says this for Claude. Codex, Cursor and the other hosts get only what the seeds say. The closest seed text, the `commands_and_results` briefing field (209:47), goes to reviewers.

Seed 020 renders to every target through the run contract, so the rules reach every host. The code-reviewer seed, 221, gets a matching review question, so the rule is checked at delivery and not only stated.

## Requirements

1. Seed 020 gains a rule, next to line 20, saying a failing check is never made to pass by suppressing it. The rule names these forms:
   - skipping a test or marking it expected to fail;
   - loosening an assertion or pattern;
   - catching and discarding an exception;
   - adding a lint or type ignore;
   - raising a timeout or threshold;
   - removing the check.

   The one exception is when the check itself is shown to be wrong; the agent then says so and names the evidence. A failure with an environmental cause (missing dependency, platform capability, timing) is reported as environmental, not hidden. Line 20's symptom-only allowance stays, and it is made explicit that the allowance does not cover suppression.
2. Seed 020 line 26 gains a reassessment trigger: after two unsuccessful attempts at the same fix, the agent stops editing long enough to reassess the evidence and the approach. When a justified next step exists, it continues autonomously. It escalates to the operator only when it is blocked. This is not a permission gate, and it sets no attempt cap.
3. Seed 020 gains a rule that a report to the operator claiming something passed, failed or works carries concise evidence: the command and its result, or a reference to evidence already recorded (a captured output path or a Progress Log row). A claim with no evidence is reported as unverified.
4. Seed 221 gains one review question in its failure-path material: does any change make a failure disappear without fixing its cause? The question covers the forms 221:58 does not already cover: a skip or expected-failure mark, a loosened assertion, an ignore comment, a raised threshold, and a deleted check. A suppression with no evidence that the check was wrong is a finding. This repo's `docs/agents/code-reviewer.md` Review Rubric gains the same question by hand edit, because its carrier (`review_policy.py:367`) renders only the executable-review region. Target role docs pick it up at their next seed-050 synthesis.
5. Prose-only change to two seeds. Behaviour is the same on Windows, macOS, Linux and WSL2: no script, path or subprocess changes.

## Scope

**Problem statement:** the run contract does not forbid suppressing a failing check, does not bound repeated failed attempts, and does not require evidence in reports to the operator.

**In scope:**

- Requirements 1 to 3 in `.wavefoundry/framework/seeds/020-run-contract.prompt.md`.
- Requirement 4 in `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md`.
- The `## Review Rubric` of `docs/agents/code-reviewer.md`: one hand-edited bullet (Requirement 4).

**Out of scope:**

- Mechanical enforcement, such as a scanner for new `skip` or `noqa` lines. Possible follow-up.
- Changes to seed 209's repair-cycle machinery or its delivery loop.
- Other role seeds (222 to 225). Seed 020 already reaches every role.

## Acceptance Criteria

- [x] AC-1: Seed 020 states the no-suppression rule with the six named forms, the shown-wrong exception, and the environmental-cause reporting. Line 20's symptom-only allowance explicitly excludes suppression.
- [x] AC-2: Seed 020 states the reassessment trigger after two unsuccessful attempts. It says the agent continues autonomously when a justified next step exists and escalates only when blocked.
- [x] AC-3: Seed 020 states that a pass, fail or works claim to the operator carries concise evidence (the command and result, or a reference to recorded evidence), and is otherwise reported as unverified.
- [x] AC-4: Seed 221 and this repo's code-reviewer Review Rubric carry the suppression review question.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change. No suite pins the edited lines; the suites reading seeds 020 and 221 (`test_per_area_agents_context.py`, `test_server_tools_lifecycle.py`, review-policy carrier parity) count as the change's own.

## Tasks

- [x] Edit seed 020 under `seed_edit_allowed` (Requirements 1 to 3).
- [x] Edit seed 221 under `seed_edit_allowed` (Requirement 4).
- [x] Add the Review Rubric bullet to `docs/agents/code-reviewer.md`, and check carrier parity is unchanged.
- [x] Run the seed-pinning test files, then the whole suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seeds | implementer | none | Requirements 1 to 4 |

## Serialization Points

- `.wavefoundry/framework/seeds/020-run-contract.prompt.md`, `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md`

## Affected Architecture Docs

N/A: guidance prose in two seeds, with no boundary, flow or verification-architecture change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The operator asked for this rule. |
| AC-2 | required | Breaks the costliest failure pattern without adding a gate. |
| AC-3 | required | Non-Claude hosts get no such rule otherwise. |
| AC-4 | required | The rule has to be checked at review. |
| AC-5 | required | Seeds are pinned by tests. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned from the best-practices review. Seed locations were confirmed: 020:20 root cause, 020:26 retry, 209:47 briefing field, and no evidence rule in 020. | Guru investigation |
| 2026-10-18 | Implemented under `seed_edit_allowed`: seed 020 gains the no-suppression rule (six forms, shown-wrong exception, environmental reporting) beside the root-cause line, which now says the symptom-only allowance never covers suppression; the two-attempt reassessment joins the do-not-retry-blindly line; the evidence rule follows the reason-through-changes line. Seed 221 gains a Suppressed failures bullet in Failure Path And Boundary Correctness; `docs/agents/code-reviewer.md` Review Rubric gains the same question by hand, outside the renderer-owned region. Delivery: docs-contract, code and qa lanes approved; no suite pins the edited lines. Gapfill: shell edits for exact-string seed insertions. | Full suite 11907 tests, no test failures (repository-change guard tripped on concurrent edits by another session, see wave record); delivery lane reviews |
| 2026-10-18 | Whole suite `--no-cache` after settled inputs: 11907 tests OK, fresh green receipt. Two earlier runs had no test failures but tripped the repository-change guard on concurrent edits (CHANGELOG, gardener stamps, and another session writing wave 2124l). | scratchpad suite-2136r-3.txt |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | -------- |
| 2026-10-18 | Use prose rules in seed 020, plus one review question in 221. | Seed 020 reaches every host and role; the reviewer question checks it. Smallest change. | (a) A scanner flagging new skip, ignore and broad-except lines; noisy, and it cannot tell a justified skip from a suppression. (b) Edit every role seed; duplicates 020. |
| 2026-10-18 | Make two unsuccessful attempts a reassessment trigger, not a cap. | Matches the guide without turning ordinary debugging into a permission gate (operator plan review). | A fixed two-attempt stop with report; adds a gate. |
| 2026-10-18 | Do not adopt a separate rule telling reviewers to report only correctness and requirement gaps. | Seed 209's actionability gate (209:240-253) and readiness bar (209:222) already type preferences as untyped notes. Its one optional class, `maybe_later`, is gated on positive value, bounded safe repair and admitted scope. That is a deliberate design, not a gap. | A new reviewer threshold sentence; it would restate 209. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| An agent reads the trigger as permission to give up, or as a reason to ask. | The rule says to continue when a justified next step exists; abandoning a viable path stays forbidden by 020:26. |
| A legitimate capability skip reads as suppression. | Requirement 1 names environmental and capability causes as reportable, not forbidden. The test is whether the reason is stated. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
