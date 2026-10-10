# Readiness refresh adversarial primer

Owner: Engineering
Status: active
Last verified: 2026-10-08

Wave: `204mk pack-profile-qualification`

Change reviewed: `204hj-bug reload-probe-profile-portability`.
Receipt: `review-policy-9ba428eda25af71e4792`. Mode: `council-adversarial-primer`; depth: standard. Independent context: `204mk-readiness-refresh-red-team-20261008`. Actual runtime model identity and effort are not exposed. This is a primer, not an approval or lifecycle mutation.

## Challenge and alternative

**Strongest challenge:** all tasks and ACs are now checked, but this must not convert passing suites and a local-pack exception into strict release qualification. The declared profile still has 19 extra skips; exact attribution of the second profile's additional net 14 remains inferred. The change's Decision Log explicitly limits the exception to local testing. Preserve that limit in the refreshed council result and handoff.

**Best alternative:** retain the completed fixture repair and local artifact, while carrying scratch-profile history/index parity and the blanket named-profile guard into separate qualification work. Before any release-qualified claim, that work should supply the absent prerequisites or independently justify individual skips and rerun the serial profile checks. This is better because it preserves useful local testing without making skipped coverage disappear. Its cost is a separate qualification effort; reopening these two already-reviewed fixture repairs would not recover the missing coverage.

**Consequence of current path:** no demonstrated fixture defect remains in the selected cells. The risk is later reuse of the completed packet as broader release evidence. Existing explicit limitations contain that risk; do not erase them during closure or readiness refresh.

**Thinking stances applied:** adversarial: challenged promotion of bounded evidence into qualification; constructive: separated fixture completion from scratch-profile qualification follow-up; simplicity: reused current delivery evidence bound to unchanged source, with one bounded positive/negative identity probe instead of another full suite. First-principles and analogical stances are omitted at the declared standard tier.

**Recommendation:** seats should assess the refreshed completed packet with the local-only exception preserved. No new blocking finding is proposed by this primer. Confidence: high for current source and explicit claim boundaries; second-profile exact skip overlap remains an attributed inference.

## Primer questions

1. Does the refreshed result preserve the distinction between AC completion for the two repaired fixtures, three passing full-suite runs, and strict release qualification that remains unproved because of the documented skip delta?
2. Are the unchanged source hashes and existing executed delivery controls sufficient for this document-only receipt refresh, and does the current first-render positive/negative pair still reject stale stock bytes without a preparatory render or unintended skip?

## Executed evidence

MCP `code_read` and `code_keyword` were discovered in the actual tool inventory and called successfully. The current change, wave, readiness council, lane readiness, code delivery and QA delivery reports were read. Current source anchors: `test_distribution_seams.py` lines 524–573 and `test_vocabulary_prompt_names.py` lines 1244–1274. No retrieval fallback was necessary. MCP reported changed setup inputs on the initial mistyped-path call; no setup/rebuild or semantic freshness claim was made.

Current Git blob hashes match the independent QA delivery packet: distribution seams `c81059293654443b6a9c98759e4dc4735874fe18`; prompt names `2ee364b4cb5e4e47bfb2f768eac3aee33314454a`; changelog `604748186bdb903ecba78c2cf6105a73cb17c303`.

The original `DefaultRenderIdentityTests.test_render_of_this_repository_writes_nothing` ran in a fresh `python3 -B` process: one test, zero skips, OK (0.398 s). A second fresh process reused the inspected scratch-only QA control `/tmp/wf204mk_qa_controls.py stale-skill`: it appended stale bytes to the copied `.codex/skills/wf-guru/SKILL.md` before the first render. Expected: the real renderer reports a write and the unchanged owner assertion rejects it. Observed: exactly that path returned, whole-tree digest changed, and line 1271 `written == []` failed; one test, one intended failure, zero errors/skips (0.365 s). Harness exit 0 means the negative control was correctly killed, not that the mutated test passed. Reproduction algorithm is also preserved in `qa-delivery.md` lines 57–59.

For these selected cells: `test_ran_without_unintended_skip`, `public_path_reached`, `boundary_values_realistic`, `assertions_non_vacuous`, and `known_bad_detected` are true; method `focused-mutation`. The independent reference was AC-4 and its original zero-write/tree-byte contract. The harness was reused and inspected, so this is fresh execution, not an independently designed second oracle. No reload mutant, full suite, native-platform qualification or archive verification was repeated. No production source, change document, approval or ledger was written by this reviewer.

Evidence for the claim boundary is change lines 86–98 and QA delivery's Bounded packaging skip audit. The old readiness report describes its historical pre-repair packet; it is not misrepresented as current delivery proof. No new semantic finding is sealed by this primer; closing reconciliation remains with the chair.

## Closing reconciliation

Red-team result: **PASS for the focused readiness refresh**, with the empty candidate set held; no new blocker or disposition change. Read `readiness-refresh-lanes.md`: the fresh lane directly answered both primer questions, retained the distinction between local testing and strict qualification, rechecked unchanged source hashes, and executed a successful reload baseline plus a lifecycle-only stale-module mutant that failed the intended final freshness assertion. The current first-render pair above supplies the complementary surface-drift boundary. These are bounded fresh executions using inspected prior harnesses, not independent replacement implementations or repeated profile matrices.

The strongest contrary argument remains that completed checkboxes could imply strict profile parity. It does not defeat this focused verdict: the amended packet and independent seat expressly preserve the 19-extra-declared-skip exception and inferred second-profile overlap. The chair separately reports archive SHA/CRC/version verification and parsing canonical 20 versus declared 39 skips; those are attributed chair observations, not red-team executions. Archive integrity does not repair missing test coverage. No requirement in the reviewed refresh silently promotes the local pack to release-qualified status.

The concrete alternative of withholding all packaging would be stronger only for a release-qualified artifact; it would disregard the explicitly approved local-testing boundary here. Separate qualification follow-up remains appropriate. No source repair or broader review trigger emerged, and there is no semantic finding to downgrade or waive. Typed approval and lifecycle decisions remain with the coordinator; this reconciliation neither closes the wave nor authorizes publication.
