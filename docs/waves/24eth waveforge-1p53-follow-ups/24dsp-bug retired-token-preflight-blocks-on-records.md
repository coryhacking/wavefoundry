# The retired-token preflight error says "report-only" while it blocks the upgrade

Spec ID: `24dsp-bug retired-token-preflight-blocks-on-records`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-26
Wave: 24eth waveforge-1p53-follow-ups

## Rationale

Waveforge reported, on v1.53.0, that the upgrade preflight refused because a filed record quoted a retired lifecycle token. The record was `tools/upstream-sync/baselines/t1jvi/known-failures-delta.md`, an evidence file in a folder their distribution defines. They reworded it and the apply passed. They do not need an exemption and find the refusal acceptable when it is clear.

The refusal is not clear about its own effect. The scan `review_policy_reconcile._live_markdown_retired_errors` labels each error `(report-only; automatic rewrite is refused)`, but `review_policy_reconcile.plan_reconciliation` raises every collected error as `ValueError("lifecycle carrier preflight failed: ...")`, so the upgrade stops. Waveforge's exact output shows both: "upgrade review-policy preflight failed before mutation: lifecycle carrier preflight failed: ... (report-only; automatic rewrite is refused) ...". Blocking on unregistered retired prose is intended (change `1txh7`, Requirement 19: "ambiguous project prose remains fail-closed"); the label is what misleads. (inferred: read of the scan and raise sites; Waveforge's quoted output.)

## Product Intent

An operator whose upgrade stops on retired lifecycle prose outside a registered carrier reads an error that says the upgrade is blocked until the listed prose is edited. Before: the same error calls itself report-only. After: it says it blocks. Which files are scanned, and what blocks, does not change. AC-1 tests this.

## Requirements

1. The error for retired prose outside a registered carrier states that it blocks the upgrade until the listed prose is edited, and that automatic rewrite is refused. The string `report-only` no longer appears in it.
2. The error keeps the file path, the complete token worklist with line numbers, the replacement preview or "rewrite manually" text, and the edit-then-retry recovery.
3. The scan's inputs, exclusions, registered carriers, retired-token list and raise behaviour are unchanged.
4. Behaviour is identical on Windows, macOS, Linux and WSL2: only message text changes.

## Scope

**Problem statement:** the refusal misstates its own effect.

**In scope:**

- The message in `review_policy_reconcile.py`.
- Tests in `test_review_policy.py`.

**Out of scope:**

- Exempting plan, arc or distribution evidence records from the scan (operator decision 2026-11-26).
- A configuration entry for registering a distribution folder as a non-carrier (declined; Waveforge said the clear refusal is acceptable).
- Upgrade prompt text: no copy of the upgrade prompt describes this refusal today (checked with a search of `docs/prompts/upgrade-wavefoundry.prompt.md`).

## Acceptance Criteria

- [x] AC-1: A project Markdown file outside every registered carrier and exclusion, quoting `pre-implementation-review`, makes `plan_reconciliation` raise an error that names the file, the token and its line, says the upgrade is blocked until the prose is edited, and does not contain `report-only`; with the old wording restored, the test fails.
- [x] AC-2: The control: the same file is still reported and still blocks, and a file under an existing exclusion (the waves root) is still not reported, so the scan's coverage is unchanged.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change edits validate.

## Tasks

- [x] Correct the refusal wording.
- [x] Tests for AC-1 and AC-2.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| wording | implementer | — | AC-1 to AC-3 |

## Serialization Points

- `.wavefoundry/framework/scripts/review_policy_reconcile.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`

## Affected Architecture Docs

N/A: an error message inside one upgrade reconciler; no boundary, flow or verification seam moves.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The message must match the behaviour. |
| AC-2 | required | Proves the wording change did not change coverage. |
| AC-3 | required | Change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-26 | Planned from the Waveforge v1.53.0 report, finding 2, with a plans-and-arcs record exemption plus the wording fix. | `_live_markdown_retired_errors(Path('.'))` returned 0 errors on this repository. |
| 2026-11-26 | Readiness round one raised RDY-3 against the exemption's invalid-layout rule; repaired and reverified. | Red-team readiness and reverification reports. |
| 2026-11-26 | Waveforge answered: the blocking file was `tools/upstream-sync/baselines/t1jvi/known-failures-delta.md`, outside the plans and arcs roots with no lifecycle id, so the exemption would not have covered it. Their refusal output confirms the "report-only" mislabel. | Waveforge reply relayed by the operator. |
| 2026-11-26 | Narrowed to the message fix by operator decision: "A, narrow 24dsp to the message fix". The exemption, its invalid-layout rule and its ACs are removed. | Operator instruction. |
| 2026-11-26 | Implementation notes from the narrowed readiness round (nonblocking): (1) AC-1 pins one concrete phrase such as "blocks the upgrade" and also asserts the kept "rewrite manually" and "retry the same upgrade command" recovery text, because the old message already says "edit ... then retry". (2) AC-2's control uses Waveforge's real shape, a `tools/...` evidence file, plus a file under `docs/plans/`, both still reported, and a waves-root file still not reported. (3) Requirement 19 of `1txh7` also says to "report" matches; "report-only" meant "not auto-rewritten", which the new wording keeps as "automatic rewrite is refused". (4) Seed 160 was checked as well: its "report-only" wording belongs to the separate `reconcile_scan.py` scanner and is accurate, so it is unchanged. (5) Keep the substring `outside a registered carrier`, which `test_review_policy.py` pins. | Red-team and docs-contract narrowed-readiness reports. |
| 2026-11-26 | Readback: Clarify the blocking diagnostic in review_policy_reconcile.py and test its wording and unchanged scan boundaries through plan_reconciliation. | ACs in this spec. |
| 2026-11-26 | The new public preflight regression failed on the original report-only wording. After the message change all 134 review-policy tests passed, including the evidence, plan and wave-history controls. | Delivery verification. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-26 | Fix the message only; keep the scan's coverage and fail-closed behaviour. Operator: "A, narrow 24dsp to the message fix". | The motivating case lies outside any record root and no plan or arc record has hit the scan in either repository, so an exemption has no observed benefit. The mislabel is confirmed by Waveforge's output. Replaying their case: the corrected error tells them the upgrade is blocked and what to edit, which they said is acceptable. | (B) Keep the plans-and-arcs exemption: a mechanism with no observed case. (C) A configuration entry to register distribution evidence folders as non-carriers: new surface Waveforge said they do not need. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A test elsewhere pins the old wording. | Census of `report-only` and `outside a registered carrier` in tests during implementation; the known pin (`test_review_policy.py`) asserts only `outside a registered carrier`, which stays. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
