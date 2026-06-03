# Migrate Active Docs To Canonical Renamed Config Keys

Change ID: `1p33b-doc migrate-active-docs-to-canonical-renamed-config-keys`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-03
Wave: `1p337 config-key-back-compat-hotfix` (admitted post-reopen as the docs-migration companion to `1p336`'s back-compat fix)

## Rationale

`1p336` shipped reader-side back-compat for the seed-prose rename `wave_council_policy` → `wave_review` and `wave_execution` → `wave_implement`. Before the back-compat fix, rewriting active docs to the new canonical names would have been **wrong** — the consumer's report correctly noted that doc renames would diverge from runtime behavior. With back-compat in 1.4.0, that constraint lifts: both key names are accepted by the runtime, so docs can reference the new canonical names without breaking runtime semantics.

A review of `docs/` and `.wavefoundry/framework/seeds/` (separate from historical wave records, which are out of scope per the no-retrofit principle) found **10 active references** to the legacy keys across **9 operational doc files** plus the self-host `docs/workflow-config.json`:

- `docs/agents/architecture-reviewer.md:20` — reviewer-routing condition referencing `wave_council_policy`
- `docs/contributing/agent-team-workflow.md:17,33` — council-moderator activation guidance
- `docs/references/project-overview.md:77` — project orientation prose
- `docs/agents/guru.md:276,332` — Guru architecture-doc escalation rules
- `docs/contributing/feature-wave-lifecycle-overview.md:65` — lifecycle prose
- `docs/contributing/review-and-evals.md:18,19,29,37,48` — required-lane / closure-checklist content (5 references)
- `docs/agents/specialists/environment-auditor.md:26` — key-flag list the auditor inspects
- `docs/agents/specialists/red-team.md:158` — Wave Council config-file pointer
- `docs/agents/personas/wave-coordinator.md:55` — wave-record schema reference (uses legacy `wave_execution`)
- `docs/workflow-config.json:12,106` — the self-host config itself

Leaving the docs as-is is a defensible status-quo choice (factually accurate against the legacy keys, both work via back-compat). Migrating now is the cleanup payoff the `1p337` wave doc named as a deferred successor concern: *"a cross-cut audit for any other seed-vs-runtime drift surfaces. If discovered, scope as a follow-on after 1.4.0 ships."* The audit happened (this change doc), the surfaces are identified, the fix is mechanical. The cleanup belongs in the same release as the back-compat fix so that consumers upgrading to 1.4.0 see consistent prose-and-runtime semantics, not a transition gap.

Self-host `docs/workflow-config.json` is also migrated — this dogfoods the back-compat fix (the self-host now exercises the new-key path that downstream consumers will exercise), confirming the back-compat behavior end-to-end on the canonical example.

## Requirements

1. **Active operational doc references rewritten to the new canonical key names.** The 9 operational doc files (listed in Rationale) are updated so each `wave_council_policy` reference becomes `wave_review` and each `wave_execution` reference becomes `wave_implement` — matching the canonical names that seed prose adopted in `1p2q3` and that `1p336` made safe via reader-side back-compat.
2. **Self-host `docs/workflow-config.json` migrated to new keys.** Replace the top-level `wave_execution` key with `wave_implement` and the top-level `wave_council_policy` key with `wave_review`. Value contents are unchanged. This dogfoods the back-compat fix and aligns the canonical example with the canonical seed prose.
3. **No historical wave records modified.** Wave records under previously-closed waves (`1p2q3`, `12g27`, `12xr1`, `12sg7`, `12sq2`, etc.) describe work as done at the time and remain factually accurate to their wave's contemporaneous runtime. Per the no-retrofit principle (`1p336` Req-9 equivalent), they are out of scope.
4. **`docs/workflow-config.json` migration verified at runtime.** After the rename, `wave_validate` must pass against this self-host without lint errors, and `_read_wave_council_policy()` must return the policy via the new-key path (no deprecation note emitted).
5. **Optional `(formerly wave_council_policy)` annotation** added on the highest-traffic operator-facing surface — recommended location: `docs/contributing/feature-wave-lifecycle-overview.md` and `docs/contributing/review-and-evals.md` — so migrating-operator readers see the rename pointer without having to know about it. Annotation appears at most twice across the doc tree; not on every reference.
6. **No code changes.** This is documentation-only. Tests added in `1p336` remain the regression coverage for the back-compat behavior; this change adds none.
7. **No behavior change on the self-host post-migration.** The hotfix in `1p336` made the new-key path active. After this change ships, `_read_wave_council_policy()` returns the same policy it did before — just via the new key path. No silent disable, no behavior shift.

## Scope

**Problem statement:** Active operational docs reference the legacy config-key names (`wave_council_policy`, `wave_execution`), but seed prose since `1p2q3` uses the canonical new names (`wave_review`, `wave_implement`). Before `1p336`, that mismatch was load-bearing — docs matching legacy runtime was correct. After `1p336` shipped reader-side back-compat in 1.4.0, the constraint inverted: docs should match the canonical seed prose, with the legacy keys remaining as runtime-supported fallbacks.

**In scope:**

- 9 active operational doc files (listed in Rationale) — rewrite legacy key references to new canonical names
- `docs/workflow-config.json` self-host config — rename top-level keys to new canonical names; values unchanged
- Optional `(formerly wave_council_policy)` annotations on 1-2 high-traffic operator surfaces
- `wave_validate` verification after rename — must still pass

**Out of scope:**

- Historical wave records under previously-closed waves. The no-retrofit principle applies; those docs describe contemporaneous runtime and are kept as-is.
- Code changes. `1p336` carries the back-compat code; this change is documentation cleanup only.
- Cross-cut audit for *other* seed-vs-runtime drift surfaces beyond the `wave_council_policy` / `wave_execution` renames. Other renames (`code_patterns` / `code_pattern`, `code_review_triggers` / `design_review_triggers`) were audited in `1p336` and found to be prose-only with no runtime gap.
- Adding the alias-tuple pattern to seeds for `wave_review` / `wave_council_policy`. That's documentation-of-implementation-detail; the alias pattern is enforced by the validator, not the seed prose.

## Acceptance Criteria

- [x] AC-1: `docs/workflow-config.json` top-level `wave_execution` key renamed to `wave_implement`; value object unchanged.
- [x] AC-2: `docs/workflow-config.json` top-level `wave_council_policy` key renamed to `wave_review`; value object unchanged.
- [x] AC-3: After AC-1 and AC-2 land, `wave_validate` passes against this self-host without lint errors.
- [x] AC-4: After AC-1 and AC-2 land, `_read_wave_council_policy()` returns the policy via the new-key path — verified by inspection of stderr during a tool call (no deprecation note emitted).
- [x] AC-5: `docs/agents/architecture-reviewer.md` line 20 reference updated from `wave_council_policy` to `wave_review.enabled`.
- [x] AC-6: `docs/contributing/agent-team-workflow.md` both references updated to `wave_review.enabled`.
- [x] AC-7: `docs/references/project-overview.md` reference updated to `wave_review.enabled`.
- [x] AC-8: `docs/agents/guru.md` both references updated to `wave_review`.
- [x] AC-9: `docs/contributing/feature-wave-lifecycle-overview.md` reference updated to `wave_review.enabled`; optional `(formerly wave_council_policy)` annotation added on the first reference.
- [x] AC-10: `docs/contributing/review-and-evals.md` all 5 references updated to `wave_review.enabled`; optional `(formerly wave_council_policy)` annotation added on the first reference.
- [x] AC-11: `docs/agents/specialists/environment-auditor.md` reference updated to `wave_review`.
- [x] AC-12: `docs/agents/specialists/red-team.md` reference updated to `wave_review`.
- [x] AC-13: `docs/agents/personas/wave-coordinator.md` reference updated from `wave_execution` to `wave_implement`.
- [x] AC-14: No historical wave records under previously-closed waves are modified.
- [x] AC-15: `docs-lint` passes on this change doc after additions.
- [x] AC-16: Full framework test suite passes after additions (regression discipline — `1p336`'s tests carry the runtime behavior coverage; this change should not affect any test).

## Tasks

- [x] Open `framework_edit_allowed` gate (covers the self-host workflow-config edit; the doc edits don't require it but this is the broadest gate)
- [x] Rewrite `wave_council_policy` references to `wave_review` (with `.enabled` where appropriate) across the 9 named operational doc files
- [x] Rewrite `wave_execution` reference to `wave_implement` in `docs/agents/personas/wave-coordinator.md`
- [x] Add `(formerly wave_council_policy)` annotation on the first reference in `feature-wave-lifecycle-overview.md` and `review-and-evals.md`
- [x] Rename top-level keys in `docs/workflow-config.json` (`wave_execution` → `wave_implement`; `wave_council_policy` → `wave_review`)
- [x] Verify `wave_validate` passes against this self-host after the workflow-config rename — wave_audit returned ready=true, validation.passed=true post-rename
- [x] Verify `_read_wave_council_policy()` returns policy via new-key path (no deprecation note emitted) by tool-call inspection — `_WAVE_REVIEW_LEGACY_DEPRECATION_NOTED=False` after read on dogfooded self-host config
- [x] Run framework test suite — verify no regressions — 2299 tests across 24 files, all pass
- [x] Close gate; mark change `implemented`

## Affected Architecture Docs

`N/A` — this change is documentation-only with one config-file key rename. No architectural boundary, data flow, or testing-architecture impact. The runtime contract was already established in `1p336`; this change is cosmetic-cleanup on the consumer side of that contract.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (`wave_execution` → `wave_implement` in self-host config) | required | Dogfoods the back-compat fix; aligns the canonical example with the canonical seed prose. Without this, the self-host stays on the legacy path while telling downstream consumers to use the new path. |
| AC-2 (`wave_council_policy` → `wave_review` in self-host config) | required | Same rationale as AC-1; the two renames are paired. |
| AC-3 (`wave_validate` passes post-rename) | required | Hard regression gate — back-compat must hold on the self-host's actual config. |
| AC-4 (`_read_wave_council_policy()` returns via new-key path, no deprecation note) | required | Verifies the migration actually flipped the active path. If the deprecation note fires, something is wrong with the rename or the back-compat reader. |
| AC-5 (`architecture-reviewer.md` rewrite) | required | Active operator-facing reviewer-routing reference; must match canonical seed prose. |
| AC-6 (`agent-team-workflow.md` rewrites) | required | Active operator-facing council activation guidance; must match canonical seed prose. |
| AC-7 (`project-overview.md` rewrite) | required | High-traffic project orientation doc; visitor surface must match canonical seed prose. |
| AC-8 (`guru.md` rewrites) | required | Guru escalation rules reference an active runtime contract; must match canonical seed prose. |
| AC-9 (`feature-wave-lifecycle-overview.md` rewrite + annotation) | required | Highest-traffic lifecycle prose; the migration annotation here makes the back-compat affordance discoverable. |
| AC-10 (`review-and-evals.md` rewrites + annotation) | required | High-traffic closure-checklist content with 5 references; the second migration annotation location. |
| AC-11 (`environment-auditor.md` rewrite) | required | Environment-audit doc lists config keys for inspection; must reflect canonical names. |
| AC-12 (`red-team.md` rewrite) | required | Red-team Wave Council config pointer; must reflect canonical name. |
| AC-13 (`wave-coordinator.md` rewrite) | required | Wave-record schema reference using the other renamed key (`wave_execution`); must match canonical seed prose. |
| AC-14 (no historical wave records modified) | required | Hard scope bound per the no-retrofit principle. A historical wave doc rewrite would be a different kind of change and is explicitly out of scope here. |
| AC-15 (docs-lint passes) | required | Standard hygiene gate. |
| AC-16 (framework test suite passes) | required | Regression discipline. |

All ACs are required; this is a focused documentation-cleanup change with no nice-to-have or optional surface beyond the formerly-annotation guidance (which is folded into AC-9 and AC-10 as a recommendation, not a separate AC).

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Migrate self-host `docs/workflow-config.json` to new key names as part of this change, not deferred to a future cleanup | Dogfooding the back-compat fix on the self-host's actual config is the strongest verification — the self-host now exercises the new-key path that downstream consumers will exercise. Deferring would leave the self-host as the only place still proving the legacy path works while telling consumers to use the new path. | (a) Leave self-host on legacy keys — rejected; the back-compat fix is unverified end-to-end on the canonical example. (b) Migrate self-host but not active docs — rejected; mixed state across the same release is the failure mode this change is fixing. |
| 2026-06-03 | Add `(formerly wave_council_policy)` annotation only on 1-2 high-traffic operator surfaces, not on every reference | Annotation on every reference dilutes the migration signal and adds visual noise; once-or-twice on the highest-traffic surfaces ensures migrating-operator readers encounter the pointer without having to know about it. | (a) Annotate every reference — rejected; visual noise on 10 sites for a one-time migration signal. (b) Annotate zero references — rejected; migrating-operator discoverability matters. |
| 2026-06-03 | No code changes in this doc-only change; tests from `1p336` carry the runtime regression coverage | Separation of concerns. `1p336` owns the back-compat behavior and its tests. This change is consumer-side doc cleanup; adding tests here would either duplicate `1p336`'s coverage or test the docs themselves (which isn't useful). | (a) Add tests against this self-host's workflow-config to verify the post-migration runtime behavior — rejected; that's tautologically tested by `_read_wave_council_policy()`'s existing tests. |
| 2026-06-03 | No historical wave records modified — the no-retrofit principle from `1p32k` Req-9 applies here too | Historical wave records describe contemporaneous runtime; rewriting them would lose the audit trail of what the framework actually looked like at that time. The principle is forward-only migration. | Rewrite historical wave records too — rejected; loses audit-trail value and contradicts the no-retrofit principle. |
| 2026-06-03 | Admit to `1p337` (reopened) rather than create a new follow-on wave | The cleanup belongs in the same release as the back-compat fix so consumers upgrading to 1.4.0 see consistent prose-and-runtime semantics. Splitting across releases would leave 1.4.0 in a transition state where the runtime is fixed but docs still use legacy names. The operator explicitly directed this admission path. | (a) Create a new wave shipping as 1.3.34 — rejected per operator. The transition-state argument applies: 1.4.0 should ship the cleanup with the fix. |

## Risks

| Risk | Mitigation |
|---|---|
| The workflow-config rename triggers an unexpected runtime failure on the self-host (e.g., a tool or test reads the legacy key directly elsewhere) | Audited in `1p336` — only one runtime reader for `wave_council_policy` (the one with back-compat) and zero readers for `wave_execution`. Re-verify after the rename by running the framework test suite. If a failure emerges, it's a real gap that wasn't caught and should be patched in this same change. |
| `wave_validate` fails on the self-host post-migration because the docs-lint required-keys check doesn't actually accept the new key (i.e., `1p336`'s alias-tuple fix has a bug) | `1p336`'s tests verify the alias-tuple behavior on synthetic fixtures, but the self-host fixture is the end-to-end verification. AC-3 is the hard gate — if `wave_validate` fails, the back-compat fix has a real bug that must be patched before this migration ships. |
| Operators consuming the new-key seed prose see this self-host's `docs/workflow-config.json` and think they MUST migrate. The back-compat is for them; the new keys are the canonical convention they should adopt at their own pace. | This self-host is the canonical example. Migrating it aligns the example with the seed prose. Downstream operators still control their own migration timing — the back-compat reader doesn't force them. The annotation in AC-9 and AC-10 makes the back-compat affordance explicit. |
| Annotation text drifts across instances if applied to >2 locations | AC-9 and AC-10 explicitly bound the annotation to 2 locations. The decision-log entry names the rationale. Any drift is a follow-on concern, not a v1 risk. |
| Doc rewrites introduce subtle prose drift (e.g., changing surrounding sentence structure while updating the key reference) | The rewrite is mechanical — only the key name changes, surrounding prose preserved verbatim. Edit operations should be string-replace, not paragraph rewrite. Review the diffs before commit to verify. |

## Related Work

- **`1p336` (this wave's primary change)** — shipped the reader-side back-compat that makes this doc migration safe. Without `1p336`, doc renames would silently break runtime.
- **`1p2q3` (parent of the original seed-prose rename)** — landed `wave_council_policy` → `wave_review` and `wave_execution` → `wave_implement` in seed prose. This change is the final cleanup of the transition that `1p2q3` started.
- **`1p32k` Req-9 (no-retrofit principle)** — same forward-only migration discipline applied here: don't rewrite historical wave records.
- **Downstream consumer report** — explicitly noted *"~9 local docs referencing the old keys — leave them. They correctly match both the actual config and what the runtime reads."* That assessment was correct under 1.3.32 runtime; the back-compat fix in `1p336` (1.4.0) inverts it.

## Session Handoff

Admitted to `1p337` post-reopen. Sequenced after `1p336` per the back-compat-first ordering: the runtime contract must allow both keys before consumer docs migrate.
