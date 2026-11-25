# Council-chair readiness synthesis: wave 24buu

Owner: Engineering
Status: active
Last verified: 2026-11-24

- Moderator: council-chair, fresh context, independent (took no part in the lane reviews, the primer or the repair).
- Primer depth: standard. Seats: red-team (primer), code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, release-reviewer, docs-contract-reviewer (rotating best-alternative seat).
- Read: seed 215; wave.md and the five specs; red-team.md; the six lane reviews; repair-1.md; upgrade-rehearsal.md; the 1.51.0 target upgrade prompt (`git show 03672b89:docs/prompts/upgrade-wavefoundry.prompt.md`) for the installing-hop check below.
- Ledger verified with `wf_review_wave(wave_id='24buu', phase='prepare')`: 17 findings (AR-1..3, CR-1..2, DC-1..4, QA-1..7, SEC-1), every head `do_now`, terminal, repair completed, no unresolved required lane; all six required readiness lanes approved and current; lint passed; the only remaining action is `council-readiness`.
- No repository file was edited.

## Verdict

PASS. No unresolved blocking finding. Every plan, if its Requirements and ACs are met, establishes its Product Intent.

## seat_agreement_aggregate

- Before repair: five lanes not approved (code, qa, architecture, security, docs-contract), release approved.
- After cycle-1 repair and independent reverification: unanimous approval. Convergence came from repair, not from moderator weighting.
- max_severity of any finding: material (SEC-1, AR-2 integrity, low authority delta). All repaired and reverified by their source lanes.

## intent_fit

| Spec | Verdict | Measure of success | Readable after release | Why |
| --- | --- | --- | --- | --- |
| 24but | establishes | AC-1/AC-2/AC-7 (counts trustworthy, `churn_available` never reads an unavailable source as clean), AC-3/AC-4 (carrier entry and the replayed `UPGRADE_POLICY_BLOCK` rule), AC-5 measured on this repository | Yes: the counts and recommendation appear in a target's upgrade summary; whether maintainers act is observable only after release, as Risks states | The recommendation reaches targets on the installing hop through the replayed block (F7 repaired). The keep-rule merge: unedited copies are replaced by 24bn8; an edited copy is reported by the lifecycle drift report with a merge action, which carries the incoming baseline's keep rule on the installing hop even though the 1.51.0 prompt has no seed 240 carrier entry (checked). |
| 24ax3 | establishes | AC-1, AC-2, AC-4, AC-5, AC-6, AC-10, AC-11 | Yes: cleanup summary (`spec_tool_permission_holds` empty, no `Withheld renamed tool:`), setup readiness after a pull | Migration plus per-route upgrade receipt with a distinct body, outside layers read only, separated holds; restricted routes stay withheld with a named remedy. |
| 24bn7 | establishes | AC-1 (end-to-end direct entry from `python3 -I`, both zips, non-dry run) | Yes: the documented command runs | Fix lives in the zip's own entry code, so no old-code window; member set unchanged (AC-2). |
| 24bn8 | establishes | AC-1, AC-3 (1.51.0 bytes as installed) | Yes: summary lists `replaced` paths; git shows the diff | Replacement runs in the Phase 1 new-code render child before the docs gate and index, with digest guard and owned regions re-rendered. |
| 24bn9 | establishes | AC-1, AC-2, AC-8, AC-9 | Only from a 1.52.0-or-later installation; the 1.51.0 CLI hop still needs one `--cleanup`, which the intent and release notes state. The wave watchpoint rehearses a 1.52.0 candidate to a later candidate before delivery review | The intent is scoped honestly to the hop where its code runs; MCP opt-out is explicit (flag plus env var). |
| Objective | establishes | The specs' combined measures plus the two-hop rehearsal watchpoint | Yes, through upgrade summaries and setup readiness | Counts and keep rule delivered; upgrade never curates; spec tools served after upgrade with restrictions preserved. |

Worst: **establishes**.

## Strongest challenge (primer F1) and the answer

Challenge: 24ax3 turned an operator attestation into an upgrade side effect, so a user-level or enterprise deny on an old name would silently be lost on the new name, widening a grant.

Answer in the repaired plan: requirement 4 separates repository, outside-layer and review holds; requirement 5 reads user-level Claude, Codex user and enterprise managed settings read-only with the existing matchers, follows symlinks, honors `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and an isolation override, and holds every route named in an unparseable file; requirement 7 writes a distinct upgrade receipt body only for routes with no hold. AC-4 pins six outside-layer cases, AC-5 the pattern rule, AC-3/AC-9 the unwritable files. Policy upgrade cannot read (MDM, registry, launch flags) remains a named residual in Risks and the guidance. Security-reviewer reverified SEC-1.

## Strongest alternative not taken

- Docs-contract rotating seat: put the target-visible upgrade guidance for 24ax3, 24bn8 and 24bn9 into code-printed summary lines plus the replayed `UPGRADE_POLICY_BLOCK`, with seed 160 a short pointer. Better because targets see current text on the hop that needs it and one pin prevents stale sentences. Not taken: the wave kept per-spec seed prose and repaired D1 (old sentences removed and pinned absent) and D4 (each spec states that the target-visible carrier on the installing hop is the code summary). Weighed: the remaining cost is seed text that informs targets one hop late, which is documentation, not behavior. Not stronger enough to block.
- Primer: add a 1.52.0-to-1.52.x rehearsal hop to the readiness evidence. Partly taken: the plan moved it to a delivery watchpoint. Accepted because the code a second hop would exercise is not implemented at readiness; the cost is that a 24bn9 defect would surface at delivery.
- Primer alternatives adopted: gated upgrade receipt with distinct body (24ax3), zip `sys.path` entry instead of new members (24bn7), previous-label matching (24bn8).

## Falsification Check

Working verdict: PASS, intent_fit establishes. Strongest counter-argument: 24but's edited-copy keep-rule merge has no carrier entry in the 1.51.0 target prompt, so on the installing hop it might not reach edited copies. Does not change verdict: the drift report, printed by the installing code, prescribes a merge for every edited baseline copy, and unedited copies are replaced by 24bn8.

## improvements_recommended

1. During implementation, check that the lifecycle drift report's merge action for an edited memory-review or close-wave copy names the incoming baseline, so the 24but merge is visibly carried on the installing hop.
2. Sweep the other live statements release-reviewer listed (data-and-control-flow.md, native-windows-support.md) when 24bn9 lands.
3. At delivery, record each remaining intervention from the two-hop rehearsal in the Progress Log against the spec it belongs to.
