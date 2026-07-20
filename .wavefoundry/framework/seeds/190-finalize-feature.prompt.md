# 190 - Finalize Feature (Shortcut)

Use this when you want a single command-style request such as:

- `Finalize feature`
- `Finalize enhancement`
- `Finalize bug`
- `Finalize refactor`
- `Finalize reliability change`
- `Finalize security change`
- `Close wave`

Intent:

- Close a planned change after implementation is complete, all waves are resolved, and durable learnings are ready for promotion or archival.

Operator trigger:

- Run this body only when the operator invoked **`Finalize feature`** / **`Close wave`** in the current request **or** explicitly confirmed closure (e.g. yes after you asked). Do not infer it from a prior **`Implement wave`** / **`Implement feature`** request alone.

Required closure tasks:

1. Confirm the active change is truly ready for closure.
2. Verify that all waves are `completed`, `superseded`, or intentionally archived.
3. Confirm each wave's chronology metadata is up to date, especially `Completed at`.
4. Confirm each closed wave has a readable final `Title` and folder-safe summary slug derived from the implemented changes.
5. Reconcile plan-index and wave-listing surfaces so a closed wave and its admitted change docs are no longer advertised as `active`.
6. Reconcile behind-the-scenes operational artifacts: wave memory, next-step handoff state, and pending journal refs.
7. For each applicable review lane, produce an actual review output rather than a pass/fail placeholder — record the findings in the wave's review checkpoint section or as a dedicated review file:
   - **code review** (`code-reviewer`): patch-level logic and state handling; required whenever `docs/contributing/agent-team-workflow.md` / the final readiness evaluation selects `code-reviewer` or the wave changed non-trivial control flow or product implementation. The output must be more than "LGTM": explicitly address **branch completeness** and **re-entrant state** when the change touches per-key mutable state (for example `[String: Date]` grace maps, caches, or actor fields updated across timer/loop/step calls). Minimum bar: for each such map or field, either note "not touched by this wave" with evidence, or walk **set / clear / unchanged** across **every** branch (including `else` arms when a flag like `powerStateChanged` splits paths) and across **repeated calls** of the same function; when two similar functions exist (for example `checkDawnSleepOverridesWithDelays` vs `checkDawnSleepOverrides`), call out symmetry or intentional differences. Omit only for trivial docs-only changes
   - **architecture review** (`architecture-reviewer` — `seed-214`): when `architecture-review` is declared in `required_review_lanes` or when the wave touched module boundaries, use `214-architecture-reviewer.prompt.md` to run a structured review. The reviewer reads `docs/architecture/` before assessing; record the structured verdict (`approved`, `approved-with-notes`, or `needs-revision`) with severity and findings in Review Evidence. For ad-hoc assessment without the seed: describe what boundaries or module interfaces were touched, whether the change is consistent with existing patterns, and any design decisions that should be recorded. Omit only when the change clearly touches no module boundaries and `architecture-review` is not a declared required lane.
   - **QA review** (`qa-reviewer`): **required for any bug fix** affecting product behavior (`change-id` kind `bug` or user-visible defect repair) — minimum bar; describe what behaviors were verified, which specs or contracts were checked against, and any edge cases confirmed or deferred; when state persists across steps or timer ticks, require or record **multi-step** verification (match → mismatch → match, or equivalent) or an explicit deferral with residual risk. For non-bug changes, omit only when the change is trivial docs-only work or when `docs/contributing/agent-team-workflow.md` / readiness evaluation explicitly does not select `qa-reviewer` (record why). For closed waves that predated this policy, a **retrospective QA** entry in **Review checkpoints** is acceptable when bringing the record into compliance
   - docs-contract review: name which canonical docs were updated to reflect durable outcomes from this change, including behavioral specs when runtime contracts changed rather than only workflow or wave-local artifacts; if a follow-up review finds stale docs after a wave was marked complete, repair both the canonical docs and the wave checkpoint text before treating the review lane as reconciled
   - security review: confirm no new surfaces, data exposures, or trust boundary changes were introduced, or document what was scoped in; required for any change touching notification, network, or persistence surfaces
   - performance review: confirm no hot-path regressions, polling frequency changes, or synchronous additions were introduced without guards; required for any change touching scheduling, timers, or per-request paths
   - record why a lane was skipped rather than leaving the checkpoint blank
   - **Close wave and behavioral specs:** When using `Close wave`, if the wave’s admitted changes touched any `docs/specs/*.md` or other canonical docs that define runtime behavior, closure is incomplete until **docs-contract review** (spec review) is recorded in the wave’s **Review checkpoints** — scope, evidence, findings or explicit clean bill. If no behavioral spec or equivalent canonical doc changed, record **Docs-contract review: not applicable** with a one-line rationale; do not omit the checkpoint entirely.
   - **product-owner review** (`product-owner`): when the wave changed product behavior, UX, or durable feature semantics, record alignment with wave **Product intent**, list **`docs/specs/*.md`** files updated to reflect **final** intent, or **product-owner: N/A** / no spec promotion with rationale. Framework-only or internal-tooling waves may use **N/A** when no product semantics moved (`docs/agents/product-owner.md`)
8. When `wave_review.enabled` is true, confirm both universal council signoffs exist in `## Review Evidence` before closure:
   - `wave-council-readiness`
   - `wave-council-delivery`
   Record the narrative council synthesis in `## Review checkpoints`. The wave-council owns those verdicts. The checkpoint must include the phase roster, the rotating fifth seat when present, any material disagreements between seats, and how those disagreements were resolved or why they remain unresolved. Wave Council is universal meta-review and does not waive blocking required specialist lanes.
9. **Design language closure checkpoint**: when the closed wave's admitted changes touch any source path in `docs/repo-profile.json` `design_system.ui_roots` (or when the `design_review` trigger fired during the wave), record a design-language review checkpoint before closure: (1) confirm that new color usage, component patterns, or HIG departures introduced by the wave are either already documented in `docs/design-system/design-language.md` or are scheduled for promotion in a follow-up; (2) if any `## Design Intent` section from the wave's change documents contains departures from the HIG, verify those departures were not silently dropped; (3) note whether `docs/design-system/design-language.md` needs a `Last verified:` date refresh; (4) if the wave's `## Design Intent` named a platform surface and `docs/design-system/platforms/<surface>/` exists (Split C), confirm that any per-surface token overrides or narrative deltas in that directory are up to date with what the wave delivered — record "Platforms delta: not applicable" when `platforms/` is absent or the wave targeted no specific surface. If the wave touched no `ui_roots` paths, record "Design language checkpoint: N/A — no UI surface changes" and continue.
9. Rerun the wave-readiness evaluation during final review so any reviewer or persona lanes newly triggered by the delivered implementation are identified and reconciled before closure.
10. Distill change-local recent captures and incidents into journal files. Journals record durable operating-memory signals: role/persona identity changes, high-salience observations, operator directives, bugs that reached review, rework cycles, invalidated assumptions, hard-to-find constraints, and mistakes corrected. Do not add journal entries for tasks that completed normally. If no durable signal occurred, the existing journal sections can remain unchanged — absence of new entries is correct when work went smoothly.
11. Update core memory with durable lessons. Memory captures recurring patterns and critical constraints — things that would help a future agent avoid a mistake, retrieve the right guidance, or preserve role/persona behavior after context loss. Do not add memory entries for routine outcomes that taught nothing non-obvious. When MCP memory tools are attached, first run `wave_memory_propose(wave_id, mode='create')`, then validate every evidence-derived candidate with `wave_memory_validate`: follow the linked evidence and current target; state what changes the next action; check durability, canonical overlap, target accuracy, duplicate/contradictory records, and confidence; choose promote, retain, reject, or rewrite. A canonical contract that already fully owns the rule is normally a rejection, while a practical action-time gotcha may supplement it. This is a bounded focused pass, not a new council; a wave may correctly yield zero memories. History and rejected source dispositions are preserved so later runs do not regenerate or silently rewrite them.
   - `docs/references/project-context-memory.md` — reusable workflow guidance derived from real incidents or recurring patterns; add an entry only if it would prevent a future mistake or surface a non-obvious constraint
   - `docs/RELIABILITY.md` — reliability patterns, recovery behaviors, catch-up policies, or failure modes addressed by this change
   - `docs/ARCHITECTURE.md` — hub updates when child architecture docs changed
   - `docs/architecture/domain-map.md`, `docs/architecture/layering-rules.md`, `docs/architecture/cross-cutting-concerns.md` — when boundaries, dependency rules, or shared concerns moved
   - `docs/architecture/data-and-control-flow.md` — when control paths or authoritative state ownership changed
   - `docs/architecture/testing-architecture.md` — when test tiers, target ownership, CI gates, or doubles policy changed
   - `docs/architecture/decisions/` — new or superseded records when durable choices were made
   - `docs/QUALITY_SCORE.md` — quality posture changes or tech debt resolved by this change
12. Promote repeated durable lessons to their correct destinations (persona docs, canonical behavioral specs, workflow docs).
13. Archive or freeze change-local wave memory and close or clear transient handoff artifacts.
14. Confirm the wave-owned change docs are already in place. For each item in the closed wave(s), verify `docs/waves/<wave-id>/<change-id>.md` exists and repair any stale references that still point at `docs/plans/` staging paths before closure. The wave folder is the permanent archive and active working home; normal wave flow should not route admitted docs through `docs/plans/completed/`.
15. Archive reports into the wave folder. Scan `docs/reports/` for any reports that fall within the wave's active period (reindex reports, review reports, audit reports, or any other generated artifacts dated within `Activated at`–`Completed at`). Move them into `docs/waves/<wave-id>/`. Add a `## Reports` section to `wave.md` summarizing the key findings from each archived report. After moving, `docs/reports/` should contain only reports that belong to future waves — the wave folder is the permanent archive; `docs/reports/` is a staging area only. If `wf docs-gardener` later regenerates a report for the same already-closed wave, refresh or replace the archived copy in the wave folder and clear the duplicate from `docs/reports/` before treating finalization as complete.
16. Preserve cumulative journals, refresh role/persona guidance when lessons changed their operating advice, and retire stale cautions. For each active caution and memory entry touched by this wave: ask whether the risk still exists in the current codebase. If the root cause was fixed by this change, retire or supersede the caution in the journal and corresponding memory — do not leave it as a false warning for future agents. Stale cautions are actively harmful: they train agents to distrust the journal.
17. Run the docs gate: **agents with MCP** — **`wave_garden`** then **`wave_validate`** (or **`wave_audit`**); **operators / CI / no MCP** — **`wf docs-gardener`** then **`wf docs-lint`**. Pass `--date <YYYY-MM-DD>` only when overriding today’s date; use `--paths <doc>` or `--all-docs` to stamp files that are not git-changed.

Promotion destinations may include:

- journal durable lessons
- `docs/references/project-context-memory.md` (required — see task 9)
- canonical behavioral specs (`docs/specs/*.md`)
- reliability, architecture, quality, security docs
- persona docs
- repo-local workflow and contributing docs

Commonly missed closure work to check explicitly:

- **`docs/scan-findings.json` not checked before close**: `wave_close` hard-blocks on any `pending` or `suspected-secret` entry (unresolved — must be classified); `confirmed-secret` entries do not block but surface a standing reminder on every close. Before invoking `wave_close`, read `docs/scan-findings.json` and resolve all unresolved (`pending`/`suspected-secret`) entries using the security reviewer (seed-213). If the file is absent or has no unresolved entries, proceed normally.
- `docs/references/project-context-memory.md` left empty or unchanged despite the change surfacing reusable workflow guidance
- **code review** missing, generic, or treated as optional when the wave changed non-trivial product logic — especially when per-key state or repeated-invocation paths were involved
- **`qa-reviewer` missing** on a **bug** or product defect wave when `docs/workflow-config.json` `review_policies.require_qa_reviewer_for_bug_fixes` is true — record retrospective QA or obtain an explicit waiver in the wave/change doc
- review checkpoints written as "Passed" without documenting what was actually reviewed
- `wave_review` enabled but `wave-council-readiness` or `wave-council-delivery` missing from `## Review Evidence`
- docs-contract review limited to wave/workflow files even though the implemented behavior changed a canonical spec
- `Close wave` completed without a **Docs-contract review** checkpoint when `docs/specs/*.md` or other behavior contracts were updated during the wave
- closed wave still claiming "no remaining mismatches" after a follow-up review proved canonical docs were stale
- final review skipped a rerun of the readiness evaluation, so newly relevant persona or reviewer lanes were never invited back in
- journal recent captures or incidents filled with success summaries instead of durable operating-memory signals, or left as placeholders; distillation left as a placeholder instead of synthesized lessons from real signals
- persona guidance refresh when the change altered review heuristics or operating cautions
- handoff clearing when the feature is truly done, or handoff refresh when a successor wave remains
- stale caution and memory entry retirement skipped when this wave fixed the root cause — active cautions whose risk no longer exists must be removed, not left in place
- `docs/references/project-context-memory.md` updated with routine outcomes instead of problem-derived lessons — memory entries should answer "would this prevent a future mistake?" not "did this go well?"
- `docs/PLANS.md` or similar plan indexes still advertising the closed wave or its admitted change docs as `active`
- ready/active-wave change docs left in `docs/plans/` or otherwise missing from the wave folder (relocation belongs to `Prepare wave`)
- reports left in `docs/reports/` without being archived into the wave folder and summarized in `## Reports`
- duplicate regenerated wave-period reports left in `docs/reports/` after an archived copy already exists in the closed wave folder
- high-salience journal entries left unreviewed at closure instead of being validated, promoted, decayed, retired, or superseded

Guardrails:

- Do not finalize if open wave obligations or review gaps remain.
- Do not leave final behavior or durable lessons only in transient wave artifacts.
- Before invoking inferential reviewer lanes, run `wave_run_sensors()` if the project has computational sensors configured — fix any sensor failures before proceeding. After all declared lanes have run, record their signoffs in `## Review Evidence` using the format `- <lane-name>: <verdict> (<severity> — <one-line summary>)`. Check `wave_review()` to confirm `required_lanes` — any lane declared in `required_review_lanes` must have a recorded signoff before `wave_close` will pass.
- **Operator review is required before calling `wave_close(mode="create"|"apply")`.** The operator review lane gives the operator an opportunity to do manual testing, spot-checks, or any other review before the wave is permanently sealed. Approval is satisfied by one of two paths:
  1. **Operator-initiated close** — the operator explicitly said "close the wave" (or equivalent) in the current request. This counts as implicit operator approval; proceed with closure.
  2. **Agent-prompted approval** — if the operator has not issued a close request, the agent must stop and ask the operator for review approval before calling `wave_close`. The prompt must include the `max_severity` from `wave_review()` so the operator can triage. If `max_severity` is `critical` or `high`, name the findings explicitly. Invite the operator to do any manual tests or review they want first. Only proceed after receiving a positive confirmation.
- Completing review tasks, removing dead code, fixing test failures, or running `wave_close(mode="dry_run")` does not constitute operator approval. When in doubt, ask.
- Record operator approval by writing `operator-signoff: approved` in the `## Review Evidence` section of `wave.md` before or alongside the `wave_close` call. `wave_review` enforces this as a required lane and `wave_close` blocks if it is absent.
- **If a wave was closed by mistake**, use `wave_reopen(wave_id)` to restore it to `active` status. `wave_reopen` only works on waves with `Status: closed` and removes the `Completed At` stamp. After reopening, verify with `wave_review` before attempting closure again.
