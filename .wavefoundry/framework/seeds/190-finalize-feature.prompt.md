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
   - architecture review: describe what boundaries or module interfaces were touched, whether the change is consistent with existing patterns, and any design decisions that should be recorded; omit only when the change touches no module boundaries
   - **QA review** (`qa-reviewer`): **required for any bug fix** affecting product behavior (`change-id` kind `bug` or user-visible defect repair) — minimum bar; describe what behaviors were verified, which specs or contracts were checked against, and any edge cases confirmed or deferred; when state persists across steps or timer ticks, require or record **multi-step** verification (match → mismatch → match, or equivalent) or an explicit deferral with residual risk. For non-bug changes, omit only when the change is trivial docs-only work or when `docs/contributing/agent-team-workflow.md` / readiness evaluation explicitly does not select `qa-reviewer` (record why). For closed waves that predated this policy, a **retrospective QA** entry in **Review checkpoints** is acceptable when bringing the record into compliance
   - docs-contract review: name which canonical docs were updated to reflect durable outcomes from this change, including behavioral specs when runtime contracts changed rather than only workflow or wave-local artifacts; if a follow-up review finds stale docs after a wave was marked complete, repair both the canonical docs and the wave checkpoint text before treating the review lane as reconciled
   - security review: confirm no new surfaces, data exposures, or trust boundary changes were introduced, or document what was scoped in; required for any change touching notification, network, or persistence surfaces
   - performance review: confirm no hot-path regressions, polling frequency changes, or synchronous additions were introduced without guards; required for any change touching scheduling, timers, or per-request paths
   - record why a lane was skipped rather than leaving the checkpoint blank
   - **Close wave and behavioral specs:** When using `Close wave`, if the wave’s admitted changes touched any `docs/specs/*.md` or other canonical docs that define runtime behavior, closure is incomplete until **docs-contract review** (spec review) is recorded in the wave’s **Review checkpoints** — scope, evidence, findings or explicit clean bill. If no behavioral spec or equivalent canonical doc changed, record **Docs-contract review: not applicable** with a one-line rationale; do not omit the checkpoint entirely.
   - **product-owner review** (`product-owner`): when the wave changed product behavior, UX, or durable feature semantics, record alignment with wave **Product intent**, list **`docs/specs/*.md`** files updated to reflect **final** intent, or **product-owner: N/A** / no spec promotion with rationale. Framework-only or internal-tooling waves may use **N/A** when no product semantics moved (`docs/agents/product-owner.md`)
8. **Design language closure checkpoint**: when the closed wave's admitted changes touch any source path in `docs/repo-profile.json` `design_system.ui_roots` (or when the `design_review` trigger fired during the wave), record a design-language review checkpoint before closure: (1) confirm that new color usage, component patterns, or HIG departures introduced by the wave are either already documented in `docs/design/design-language.md` or are scheduled for promotion in a follow-up; (2) if any `## Design Intent` section from the wave's change documents contains departures from the HIG, verify those departures were not silently dropped; (3) note whether `docs/design/design-language.md` needs a `Last verified:` date refresh; (4) if the wave's `## Design Intent` named a platform surface and `docs/design/platforms/<surface>/` exists (Split C), confirm that any per-surface token overrides or narrative deltas in that directory are up to date with what the wave delivered — record "Platforms delta: not applicable" when `platforms/` is absent or the wave targeted no specific surface. If the wave touched no `ui_roots` paths, record "Design language checkpoint: N/A — no UI surface changes" and continue.
9. Rerun the wave-readiness evaluation during final review so any reviewer or persona lanes newly triggered by the delivered implementation are identified and reconciled before closure.
10. Distill change-local recent captures and incidents into journal files. Journals record durable operating-memory signals: role/persona identity changes, high-salience observations, operator directives, bugs that reached review, rework cycles, invalidated assumptions, hard-to-find constraints, and mistakes corrected. Do not add journal entries for tasks that completed normally. If no durable signal occurred, the existing journal sections can remain unchanged — absence of new entries is correct when work went smoothly.
11. Update core memory with durable lessons. Memory captures recurring patterns and critical constraints — things that would help a future agent avoid a mistake, retrieve the right guidance, or preserve role/persona behavior after context loss. Do not add memory entries for outcomes that went well on the first try; those do not need to survive across sessions. For each candidate: ask whether it belongs in a journal, handoff, project memory, or a canonical doc; promote, retire, or supersede accordingly.
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
15. Archive reports into the wave folder. Scan `docs/reports/` for any reports that fall within the wave's active period (reindex reports, review reports, audit reports, or any other generated artifacts dated within `Activated at`–`Completed at`). Move them into `docs/waves/<wave-id>/`. Add a `## Reports` section to `wave.md` summarizing the key findings from each archived report. After moving, `docs/reports/` should contain only reports that belong to future waves — the wave folder is the permanent archive; `docs/reports/` is a staging area only. If `.wavefoundry/bin/docs-gardener` later regenerates a report for the same already-closed wave, refresh or replace the archived copy in the wave folder and clear the duplicate from `docs/reports/` before treating finalization as complete.
16. Preserve cumulative journals, refresh role/persona guidance when lessons changed their operating advice, and retire stale cautions. For each active caution and memory entry touched by this wave: ask whether the risk still exists in the current codebase. If the root cause was fixed by this change, retire or supersede the caution in the journal and corresponding memory — do not leave it as a false warning for future agents. Stale cautions are actively harmful: they train agents to distrust the journal.
17. Run the docs gate: **agents with MCP** — **`wave_garden`** then **`wave_validate`** (or **`wave_audit`**); **operators / CI / no MCP** — **`.wavefoundry/bin/docs-gardener`** then **`.wavefoundry/bin/docs-lint`**. Pass `--date <YYYY-MM-DD>` only when overriding today’s date; use `--paths <doc>` or `--all-docs` to stamp files that are not git-changed.

Promotion destinations may include:

- journal durable lessons
- `docs/references/project-context-memory.md` (required — see task 9)
- canonical behavioral specs (`docs/specs/*.md`)
- reliability, architecture, quality, security docs
- persona docs
- repo-local workflow and contributing docs

Commonly missed closure work to check explicitly:

- `docs/references/project-context-memory.md` left empty or unchanged despite the change surfacing reusable workflow guidance
- **code review** missing, generic, or treated as optional when the wave changed non-trivial product logic — especially when per-key state or repeated-invocation paths were involved
- **`qa-reviewer` missing** on a **bug** or product defect wave when `docs/workflow-config.json` `review_policies.require_qa_reviewer_for_bug_fixes` is true — record retrospective QA or obtain an explicit waiver in the wave/change doc
- review checkpoints written as "Passed" without documenting what was actually reviewed
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
- **Never call `wave_close(mode="create"|"apply")` unless the operator explicitly said "close the wave" (or equivalent) in the current request, or confirmed when asked.** Completing review tasks, removing dead code, fixing test failures, or running `wave_close(mode="dry_run")` does not constitute close approval. When in doubt, run a dry-run and present the result — then wait for explicit operator confirmation before writing.
