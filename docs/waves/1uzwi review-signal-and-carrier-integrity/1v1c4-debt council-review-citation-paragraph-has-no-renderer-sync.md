# The Council-Review Citation Paragraph Has No Renderer Sync

Change ID: `1v1c4-debt council-review-citation-paragraph-has-no-renderer-sync`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-10
Wave: 1uzwi review-signal-and-carrier-integrity

## Rationale

`1uu9y` added the resolvable-anchor authoring paragraph to `docs/prompts/council-review.prompt.md` (line 50 today). That paragraph sits **outside** both of the file's renderer-owned regions (`wavefoundry:review-policy`, lines 111–116, and `wave:executable-review-evidence`, lines 118–155), so no re-render or upgrade reaches it: the same drift class `1tmb4` fixed one bullet earlier in the same file. An inline comment in `test_seed_237_code_grounded_rule_is_pinned_exactly`'s body records the mechanism: the live copy "sits OUTSIDE any renderer-owned marker region, so no re-render reaches it" (the docstring itself covers only the exact-value pin). The `1uwpf` qa lane flagged the recurrence: the new paragraph is pinned nowhere, so a drifted copy passes every gate.

Today the paragraph is byte-identical to seed 237's (verified twice during `1uwpf`). The debt is that nothing keeps it so.

## Requirements

1. **The paragraph gets a sync or a pin — the `1tmb4` decision applies.** Either move the shared text into a renderer-owned mechanism, or pin the live copy byte-exactly against the seed in a test, as `1tmb4` did for the verification sentence one bullet up. The choice follows `1tmb4`'s own precedent unless the census finds a reason to diverge, and the divergence is then recorded.
2. **A census of `1uu9y`'s other carriers rides along.** The same wave also updated `_prepare_council_instructions` (pinned by `test_brief_carries_the_finding_authoring_citation_rule` — verified) and seeds 209/237 (pinned — verified). The census confirms nothing else from that wave is sync-less, so this debt is retired once, not per carrier. The census method enumerates renderer-owned regions across **all marker families** (`wavefoundry:*` and `wave:*`): the plan-time census missed the `wave:executable-review-evidence` region in this very file (corrected at readiness review), which is exactly the census-method lesson.

## Scope

**Problem statement:** a shipped behavioral rule lives in a hand-edited prompt copy that no mechanism keeps aligned with its canonical seed.

**In scope:** the pin or sync for the paragraph; the carrier census; `test_docs_lint.py` as the pin's default home, beside the `1tmb4` precedent pin (`CouncilSeedVerificationContractTests` in `test_docs_lint.py` is where that precedent actually lives, a readiness-council correction to the earlier `test_review_policy.py`/`test_server_tools.py` phrasing).

**Out of scope:** rewording the paragraph anywhere; the broader carrier-parity lint (`1v1c5`, a separate change — that one covers renderer-owned regions, this one covers text outside them).

## Acceptance Criteria

- [x] AC-1: A drifted live copy of the paragraph fails a test naming the seed as canonical, demonstrated red-first by mutating a scratch copy.
- [x] AC-2: The carrier census is recorded here with each `1uu9y` surface's sync/pin status.
- [x] AC-3: The full framework suite and docs-lint pass.

## Tasks

- [x] Run the carrier census; record it.
- [x] Add the pin (or sync) per the `1tmb4` precedent.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | — | AC-2 |
| pin | implementer | census | `1tmb4` precedent |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/prompts/council-review.prompt.md`

## Affected Architecture Docs

`N/A` with rationale: no behavior or boundary change; this adds drift protection for text that already shipped.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The debt: an unprotected shipped rule. |
| AC-2 | important | Retire the class, not the instance. |
| AC-3 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Planned from wave `1uwpf`'s carried-forward findings (qa lane). Premises verified before authoring: paragraph at line 50, sole marker region at 111–116, `1tmb4` pin precedent one bullet up with the mechanism documented in its docstring | grep of markers and paragraph, 2026-08-10 |
| 2026-08-10 | Readiness council (red-team and docs-contract seats): the plan-time census was wrong. The file has TWO renderer-owned regions (`wave:executable-review-evidence` at 118–155 was missed); the paragraph verified outside both and byte-identical to seed 237 by executed comparison. The precedent pin's home is `test_docs_lint.py` (now the declared review target, replacing `test_review_policy.py`), and the mechanism quote is an inline test comment, not the docstring. Requirement 2's census method now mandates all marker families | both seat reports, executed reads and byte comparison, 2026-08-10 |
| 2026-08-10 | Thought: pin per the `1tmb4` precedent (exact literal in `CouncilSeedVerificationContractTests`, asserted in seed AND live copy), then run the AC-2 census across all marker families plus a repo-wide text sweep before deciding what else the pin must cover | implementation start, 2026-08-10 |
| 2026-08-10 | Carrier census (AC-2) executed, repo-wide sweep on the rule's distinctive phrase plus both marker families. 1uu9y carriers: (1) live `docs/prompts/council-review.prompt.md` paragraph (line 50, outside both renderer-owned regions): was sync-less, NOW PINNED; (2) seed 237 authoring paragraph: was sync-less (the pre-existing exact pin covers only the older code-grounded verification bullet, so the plan's "seeds 209/237 pinned" premise was wrong for the authoring text), NOW PINNED byte-exact by the same test; (3) seed 209 authoring variant: was sync-less, NOW PINNED (audience head, shared carve-out middle, immutability tail); (4) `_prepare_council_instructions` runtime brief: already clause-pinned by `test_brief_carries_the_finding_authoring_citation_rule`, verified. Adjacent discovery OUTSIDE 1uu9y's set: seed 170 carries the `1urlb`-era change-document variant ("When a change document cites code...", expanded multi-paragraph wording) with no exact pin; recorded for the delivery review to disposition rather than pinned here, per scope discipline | repo-wide grep census, 2026-08-10 |
| 2026-08-10 | Implemented: `test_1uu9y_citation_paragraph_pinned_in_seed_237_and_live_copy` and `test_1uu9y_citation_paragraph_pinned_in_seed_209` added beside the `1tmb4` precedent pin. Red-first demonstrated on a scratch tree copy in BOTH drift directions (mutated live copy: assertion failure naming the live copy; mutated seed: failure naming seed 237 as canonical), observed as failures, not skips. Green in the live tree: `CouncilSeedVerificationContractTests` 11/11 | scratch red runs plus live-tree class run, 2026-08-10 |
| 2026-08-10 | Delivery qa lane census supplement: seed `180-implement-feature.prompt.md` also carries the distinctive `cite a **resolvable anchor**` phrase (the implement-phase bullet, landed in commit 6224b7e0 alongside seed 170's variant) and is neither pinned nor previously recorded. Disposition matches seed 170's: outside 1uu9y's carrier set, recorded for a future debt change if the family warrants pinning; the delivery docs-contract lane's independent disposition of the seed-170 discovery concurs (accept as recorded). Canonical suite tally on the delivered tree: 7087/62 OK | qa and docs-contract delivery lane reports, 2026-08-10 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Follow the `1tmb4` precedent by default | The same file, the same drift class, one bullet apart; two mechanisms in one file needs a reason | Renderer region migration (kept open: the census may show it cheaper; recorded either way) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Pinning byte-exactly makes legitimate seed edits two-step | That is the pin's purpose; `1tmb4` accepted the same trade and the failure message names both files |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
