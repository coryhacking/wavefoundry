# Code review — upgrade profile qualification

Owner: Engineering
Status: active
Last verified: 2026-10-08

## Scope and disposition

Independent code-reviewer examined change 203h9, the complete source diff in `test_upgrade_wavefoundry.py`, and the Waveforge handoff. No blocking finding. Approved for code delivery after the coordinator started implementation review and this reviewer checked the quiet-run receipt, log, updated handoff, and unchanged source fingerprint. Context ID: `203ha-code-qualification-independent-1`.

Reviewed file fingerprint, both before and after probes: `f89d39d7dd3bea415852c8d8f7b7a802bc110925` (`git hash-object`). Initial budget: 180 seconds. Sweep rule: targeted case per mutant; owner-file sweep only for survivors. No survivor required expansion. Model inherited for scoped Python fixture/oracle review; actual model identity is not independently observable.

MCP source tools were discovered and confirmed callable, then `code_outline`, targeted `code_read`, and `code_keyword` supplied source inspection. Shell was used for Git diff/fingerprint and executed probes. No repository source was edited by this reviewer.

## Independent reference and findings

Reference: independently read change requirements and AC-1–AC-3, historical migration fixture inputs, and exact output invariants. Literal `plan-change`, `implement-change`, `close-change`, and other canonical API keys remain literal. Historical feature prompt paths, labels, and the legacy skill remain historical inputs. Destination selection now follows the active profile; exact byte equality and exact ordered manifest equality remain enforced. New skill presence and legacy removal assertions remain present.

The quote-tolerant mutation preserves substitution-count checking, exception identity, and diagnostic assertions, and strengthens the phase boundary with `downstream.assert_not_called()`. Both quote styles are exercised. Positive protocol fixtures add the documented readable-manifest precondition while retaining actual rendering, extension preservation, idempotence, and before-index carrier assertions. No skips, profile reset, production changes, or weakened assertion were introduced.

## Executable evidence

Own public-path baseline: `ChangePromptRenameInstallingUpgradeTests.test_installing_upgrade_moves_prompts_rewrites_manifest_and_replaces_skills` invokes real `phase_surface_rendering` and passed once, zero skips. A temporary wrapper called that real phase, then modified its temporary output before the unchanged test assertions.

| Mutation | Expected | Observed | Sweep |
| --- | --- | --- | --- |
| Replace first migrated manifest shortcut with `Wrong shortcut` | Exact manifest assertion fails | One assertion failure, zero errors/skips | Named rename case only |
| Append unexpected manifest entry | Exact manifest assertion fails | One assertion failure, zero errors/skips | Named rename case only |
| Delete newly rendered plan skill | Required skill assertion fails | One assertion failure, zero errors/skips | Named rename case only |

Additional independent run: both `PostExtractStaleLeafRefreshTests` AC9 tests and both changed `PublicUpgradeReviewProtocolIntegrationTests` cases passed (4 tests, 1.456 seconds, zero skips). The latter exercises `main(["--root", ..., "--yes"])` with real surface rendering and bounded peripheral-phase mocks. Log: `/tmp/203ha-code-bounded.log` (local ephemeral evidence).

Integrity facts: `independent=true`; `public_path_exercised=true`; `known_bad_detected=true`; `zero_unintended_skips=true`; `tree_unchanged=true`; `reviewer_source_edits=false`.

Final evidence check: `.wavefoundry/framework/test-cache.json` has `result: ok`, 11,885 tests, `ran_at: 2026-10-08T19:13:12.019056+00:00`, and input hash `dde11ab2ef7918216ee07fa1ab0244033acfd6bc8f590157818322a084e17c2f`. `/tmp/wf-203ha-canonical-quiet.log` ends with 11,885 tests across 173 files in 431.917 seconds, 20 skips, and `OK`. This is coordinator-executed evidence independently inspected, not a second reviewer-executed full run. The earlier run rejected for concurrent documentation writes is not the delivery receipt. Final source hash remains `f89d39d7dd3bea415852c8d8f7b7a802bc110925`. The final handoff accurately distinguishes full shipped-default coverage from two profile-specific upgrade-owner qualifications and retains downstream limitations.

## Limitations

Profile owner runs and canonical-suite evidence belong to the coordinator; this reviewer did not rerun the full runner. Getter-derived expectations share vocabulary getter assumptions and do not independently qualify getter correctness. Temporary output mutants establish assertion sensitivity, not a production mutation census. No native Windows, published archive, Waveforge checkout, or live host qualification occurred. Historical R1–R9/A1–A3 implementation was not reopened. Handoff correctly distinguishes incoming-extension disclosure from the unchanged older runner's final line.
