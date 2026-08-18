# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-08-18

## Idle

No wave is OPEN. Last closed: **`1viyu fresh-install-gate-coherence`** (closed 2026-08-18, uncommitted).

**What shipped (four bug changes, from the 2026-08-17 fresh-install field report):** `1vim5` ships `install/workflow-config.defaults.json` and setup Step 0 provisions the seven lint-required sections key-wise absent-only (atomic, non-ASCII-safe writer); `1vitq` ships `install/plan-template.md`, `_default_template()` reads it root-then-module, and `render_agent_surfaces` materializes `docs/plans/plan-template.md` missing-only with the date stamped; `1vitr` makes `wf_audit_install` classify absence-class lint errors as `pending_lint` while seed rows pend, block only on real findings, fail closed on `ERROR:`-less lint failures (synthesized entry bypasses the classifier), and corrects the expected returns (`phase_complete` with `phase=1`); `1viyt` retires the seed-130 install-log row without renumbering, mirrors seed-012 to the template, fixes seed-010/011 paths and the seed-040 token grammar, and removes dead seed/journal references from the framework README. Delivery review added: metadata blocks (`{{generated_at}}` stamped) to the five shipped lifecycle prompt baselines and the pointer-form review carriers, and a faithful Phase-1-complete AC-1 fixture. Final suite 7302 OK; docs-lint ok; typed ledger complete (four lanes, both council signoffs, operator signoff).

**Nothing committed.** The working tree holds this wave (24 modified files, three new: `.wavefoundry/framework/install/plan-template.md`, `.wavefoundry/framework/install/workflow-config.defaults.json`, the wave dir) plus the concurrently created `docs/waves/1vj4e backstage-techdocs-baseline/` from another session. Commit is operator-owned.

## Open questions / Deferred decisions

- **Release:** `CHANGELOG.md` carries `## [Unreleased]`; rename it to `## [1.17.2] - <date>` before `build_pack.py --version 1.17.2` (the heading must match exactly). The bullet already discloses the upgrade impact below.
- **Upgrade disclosure:** existing target repos holding older metadata-less copies of `docs/prompts/{create,prepare,implement,review,close}-wave.prompt.md` keep failing `check_metadata` after upgrade (render is missing-only; `wf_garden_docs` only refreshes an existing date). Remedy: add the three metadata lines by hand, or delete an untouched baseline copy and re-run `wf render-surfaces`. Decide whether a future upgrade step should repair this automatically.
- **Follow-up debt (not admitted anywhere):** RTD-2 shared install-asset resolve/stamp helper (three root-then-module resolver copies and two stamp loops are the CODE-DEL-1 defect class); framework README journal-philosophy prose (lines 53, 65, 318, 450-456); `docs/architecture/threat-model.md` line 60 still says `seed-130`; `install/lifecycle-prompts/memory-review.prompt.md` keeps a static `Last verified` while its siblings use `{{generated_at}}`; `pending_lint.note` says "Phase 2 seed rows" while the rule counts any-phase seed rows.
- **Accepted limitation (disclosed in 1vitr):** the pending-absence rule is global (any seed row pending), so an absence produced by an already-marked row's non-row artifact is deferred until the final gate; CHECK 2 still catches a marked row's own artifact and the final gate blocks everything once no seed row pends.
- **Field feedback still open from the same report:** none; all five reported items are addressed by this wave.

## Older closed, uncommitted waves

`1uwpf`, `1usqm`, `1uugh`, `1ur6o` (closed 2026-08-10) and the 1.17.x waves were recorded in earlier handoffs; their carried-forward findings live in their wave records (`docs/waves/<id>/wave.md` Watchpoints) and in `docs/plans/1us4q-bug ...` (parked, do not re-attempt without its Progress Log).
