# Docs-contract reviewer and council seat: wave 24buu readiness

Owner: Engineering
Status: active
Last verified: 2026-11-24

Verdict: NOT approved. Four findings that need spec edits before readiness. No repository file was edited. Retrieval: MCP tools loaded; most reads went through shell cat/sed/grep on long markdown files. Gapfill: cheaper than paging code_read over 1000-line prompt files; every claim was read in the tree.

## Carrier map (verified)

- Seed 160 (`.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`) has no marker region. Its operating-memory checklist (the "After the upgrade reload" bullet) and its "Changed briefing-loop carriers" list are hand-authored seed prose.
- The self-hosted copy `docs/prompts/upgrade-wavefoundry.prompt.md` has no operating-memory checklist. Its only post-reload memory text is inside the renderer-owned `wavefoundry:review-policy-upgrade` region (lines 726 to 771, hand-authored file, line numbers apply to that file). That region is `review_policy.UPGRADE_POLICY_BLOCK` replayed by `review_policy_reconcile._reconcile_upgrade_policy_region`. The carrier list and the "Lifecycle baseline drift report" section in the self-hosted copy are outside any marker region.
- `tests/test_review_policy.py::test_upgrade_policy_guidance_matches_legacy_migration` pins the block, including the two-line string `never auto-curates or\npurges memory` and `curation_required=true`.
- Seeds 190 and 240 and the `memory-review` and `close-wave` baselines already carry the keep rule. No seed or baseline edit is needed for 24but; only the seed 160 carrier entry.

F7 is repaired in 24but (requirement 4 and AC-4 name the block and its rendered text). Confirmed aligned.

## Findings

**D1 (24bn8, requirement 6 and AC-6; also 24ax3 requirement 10 and 24bn9 requirement 6). Guidance edits add text without removing the sentences they contradict.**
- Seed 160 "Lifecycle baseline drift report" (and the same section in the self-hosted copy) says the `overwrite` action is a manual delete-and-re-render, and that "The report leaves the files and exit status unchanged". Code strings say "report only; project copies preserved" (`upgrade_extensions` and `upgrade_wavefoundry` drift printers) and `_BASELINE_ACTIONS` prescribes the manual overwrite.
- After 24bn8 the first two are false for the unedited case. Requirement 6 only says to "say that upgrade replaces unedited copies"; AC-6's text pin can pass beside the stale sentences.
- Same class in 24ax3: the seed 160 section "MCP tool names for change specs" (anchor `#mcp-tool-names-for-change-specs`, linked from the CHANGELOG breaking-rename entry) tells the agent to run `spec-permissions ... --confirm-effective-host-rules` per tool. 24ax3 requirement 10 never names this section, and the heading and anchor must stay.
- In 24bn9, seed 160 text that says cleanup is a separate agent step needs the same named replacement.
- Repair: each spec's guidance requirement names the section it revises and the sentence it replaces; AC text pin includes a known-bad assertion that the old sentence is gone.

**D2 (24but requirement 3 versus 24bn8). The "merge applies only to edited copies" claim is wrong.**
- 24bn8 replaces only a comparable-equal copy whose previous baseline is known and whose digest is unchanged. It skips symlinks, changed digests, `baseline_unknown` and `upstream_unchanged_local_differs`. Requirement 3 says "byte-identical" and "applies only to edited copies".
- Skipped and unknown-baseline copies still reach the agent merge and still need the keep rule. 24bn8's own Boundaries and Risks leave those findings in place.
- Repair: say the merge applies to every memory-review and close-wave copy that upgrade did not replace, and replace "byte-identical" with "comparable-equal (24bn8)".

**D3 (24but requirement 5, task "apply the same text to the self-hosted copy"). Mechanism for the renderer-owned region is unnamed.**
- The recommendation rule reaches the self-hosted copy only through the marker region; a hand edit there is overwritten by the next replay. The carrier entry is outside the region and is hand-edited.
- Repair: state that the region is regenerated from `UPGRADE_POLICY_BLOCK` by the existing replay (`wf_sync_surfaces` or the upgrade replay), and add a drift assertion that the region equals the constant.
- Also state that the new block text keeps the `never auto-curates or\npurges memory` line break, or update that pin in the same edit. AC-4's wording (no newline) can invite a reflow that breaks the existing pin.

**D4 (24ax3, 24bn8, 24bn9 guidance reach). Seed text does not reach target prompts.**
- A target's `docs/prompts/upgrade-wavefoundry.prompt.md` is outside the carrier registry (`review_policy_reconcile`, empty carrier tuple); only the marker block is refreshed. Guidance added to seed 160 for 24ax3, 24bn8 and 24bn9 therefore informs targets on the next upgrade only.
- Repair: say in each spec that the target-visible statement is the code summary line, and the seed text is source-of-truth documentation; or move one sentence per behavior into the block. Pick one; do not leave AC-6/AC-8 implying target delivery.

## Minor notes

- CHANGELOG `[Unreleased]` has only Added and Changed headings. The 24bn7 bug fix needs a Fixed heading (Keep a Changelog); entries follow the "Wave X / Y." trailer style.
- `docs/architecture/contracts/mcp-tool-surface.md`: `memory_brief` bullets sit near the description of the `active_memory_budget` paragraph; adding `revalidation` there with `churn_available` is the right carrier. No other contract changes in this wave.
- Pin carrier: AC-3 names two files and a pin; AC-4 names the block and seed 160. Right carriers. No spec asks for a hand edit inside a marker region except by the ambiguity in D3.

## Council-seat note: strongest alternative not taken

Move all three upgrade-behavior guidance statements (24ax3, 24bn8, 24bn9) into one code-printed upgrade summary plus the replayed `UPGRADE_POLICY_BLOCK`, and make the seed 160 text a single short pointer. Targets would see the current text on the upgrade that needs it, there would be one pin, and no old sentence could survive beside a new one. The cost is a larger block and a block test; the wave chose per-spec seed prose, which is why D1 and D4 arise. Not a blocker if D1 and D4 are repaired.
