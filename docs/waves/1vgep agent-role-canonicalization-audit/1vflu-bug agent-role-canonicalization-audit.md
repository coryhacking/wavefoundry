# Prevent Agent Role Canonicalization Drift

Change ID: `1vflu-bug agent-role-canonicalization-audit`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-08-16
Wave: 1vgep agent-role-canonicalization-audit

## Rationale

Two upgraded target repositories independently accumulated duplicate framework specialist role documents. The review-protocol renderer materializes its canonical specialist carriers when absent, while existing repo-grown top-level documents remain live routing targets. The metadata validator checks only whether each file's `Role:` equals its filename, so both copies pass lint even when their `Category:`, protocol marker, and substantive guidance conflict. This leaves live agents following an obsolete document while the framework-owned executable-review-evidence block is attached only to an orphaned duplicate.

The framework needs one shared, read-only agent-surface integrity audit that detects and explains this drift during upgrade and ordinary validation without deleting, moving, or overwriting project-owned material.

## Requirements

1. Build one reusable agent-role inventory over the recursive `docs/agents/` tree that identifies role docs, excludes non-role/memory/journal artifacts, and groups documents by declared `Role:` identity.
2. Define framework-owned canonical role destinations from the existing review-policy carrier registry; do not introduce a second hand-maintained list.
3. Detect duplicate identities for framework-owned carriers and report every contributing path, the canonical destination, category/marker summary, and merge-before-retire remediation.
4. Surface that advisory through `wf_audit` and the upgrade operator summary without causing a docs-lint or upgrade failure solely because a merge is required.
5. Preserve renderer marker ownership and project-authored content boundaries: never auto-delete, move, overwrite, or rewrite role documents or history.

## Scope

**Problem statement:** Carrier creation is safe for a fresh repository but not convergent for an upgraded repository that retains an older role doc at a different live path. Existing lint only validates each document in isolation, so it cannot identify duplicate role identities or stale routing.

**In scope:**

- A shared agent-surface integrity inventory and advisory diagnostics.
- Registry-derived canonical specialist-carrier path checks.
- Advisory `wf_audit` and upgrade-summary reporting, plus a focused regression fixture.

**Out of scope:**

- Automatic merge, relocation, deletion, or replacement of target-repository role documents.
- Rewriting historical wave records or changelogs.
- Requiring wrappers for roles that are not enabled by the repository's platform-generation policy.
- A generalized registry for every user-defined role; this change only establishes framework-owned canonical destinations plus duplicate-identity detection.
- Promoting the advisory to a blocking docs-lint error in this release.
- Live-reference, wrapper, provenance, and historical-reference classification.
- Upgrade-seed and rendered-prompt reconciliation.

## Acceptance Criteria

- [x] AC-1: A shared inventory groups all eligible `docs/agents/**` role docs by declared `Role:` and reports duplicate identities with every contributing path; README, handoff, platform-mapping, memory, and journal artifacts are excluded.
- [x] AC-2: Canonical destinations for framework review carriers are derived from `REVIEW_POLICY_CARRIER_REGISTRY`; a test proves the audit follows a registry destination change without a parallel role-path list.
- [x] AC-3: A fixture containing a top-level `red-team` plus canonical specialist carrier produces one advisory that identifies both paths, the canonical destination, metadata/owned-marker differences, and the needed merge-before-retire remediation.
- [~] AC-4: The audit distinguishes a duplicate framework role from a single repo-local role at a non-framework path and does not label the latter as canonical-path drift. *Operator-directed scope narrowing: ship the framework-carrier duplicate detector first; repo-local classification is deferred.*
- [~] AC-5: A live-reference census identifies active links to a noncanonical duplicate in agent catalogs, prompt docs, root entry surfaces, and enabled native wrappers, while historical wave/changelog references do not create actionable routing failures. *Operator-directed scope narrowing: reference census is deferred; the audit reports duplicate identities and canonical paths only.*
- [~] AC-6: The target repository's enabled-only wrapper policy is honored: a missing wrapper is reported only when its role is enabled for that platform; optional/disabled wrappers are not findings. *Operator-directed scope narrowing: wrapper coverage is deferred.*
- [x] AC-7: `wf_audit` and the upgrade operator summary include the advisory report while ordinary docs-lint remains passing when the only issue is a merge-required role fork.
- [~] AC-8: Upgrade guidance consistently names the registry-backed specialist destinations for `red-team`, `reality-checker`, `wave-council`, `archetype-council`, and `senior-engineering-challenger`; it no longer authorizes a competing top-level framework path. *Operator-directed scope narrowing: seed and prompt reconciliation is deferred.*
- [x] AC-9: Tests prove the audit never modifies a duplicate role document or renderer-owned marker regions.
- [x] AC-10: Focused framework tests and full docs validation pass, including a target with a live top-level role duplicate plus canonical carrier.

## Tasks

- [x] Design the inventory result schema and advisory severity/exit semantics, using the existing review-policy carrier registry as canonical-path authority.
- [x] Implement recursive role discovery, duplicate grouping, and metadata/marker comparison.
- [~] Implement a bounded active-reference census and classification for routing versus historical references. *Operator-directed scope narrowing: defer reference census.*
- [x] Integrate the audit into targeted/full upgrade reporting.
- [~] Correct conflicting specialist-path instructions in the upgrade seed and rendered upgrade prompt. *Operator-directed scope narrowing: documentation reconciliation is deferred.*
- [x] Add a hermetic fixture for a live top-level role duplicate plus canonical carrier, including no-mutation behavior and registry-derived canonical paths.
- [x] Run focused framework tests and full docs validation; record results in this change doc.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Inventory and canonical authority | implementer | — | Registry-derived; no second destination list. |
| Reference/wrapper classification | deferred | — | Intentionally deferred from this first increment. |
| Upgrade and audit reporting | implementer | Inventory | Advisory-only in this release. |
| Seed/prompt reconciliation | deferred | — | Intentionally deferred from this first increment. |
| Verification | qa-reviewer | All implementation workstreams | Hermetic fixtures plus full suite/docs validation. |

## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`

## Affected Architecture Docs

N/A — this bounded advisory does not establish a new architecture-level subsystem.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Duplicate role identity is the defect's primary detection signal. |
| AC-2 | required | A second path authority would recreate drift. |
| AC-3 | required | Reproduces the renderer-created canonical carrier field failure. |
| AC-4 | important | Prevents false positives for legitimate project-local roles. |
| AC-5 | required | Deferred by operator direction for this first increment. |
| AC-6 | important | Prevents optional wrapper policy from becoming accidental enforcement. |
| AC-7 | required | Makes the sensor reachable without trapping upgrades. |
| AC-8 | required | Deferred by operator direction for this first increment. |
| AC-9 | required | Preserves project-owned role material and history. |
| AC-10 | required | Verifies both observed target patterns and regression safety. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-16 | Planned from two independent target-repository audits. | Both reports found framework-owned specialist carriers created beside active repo-grown copies; neither can be safely auto-resolved. |
| 2026-08-16 | Thought: implement a shared, advisory-only agent-surface inventory before wiring it into audit and upgrade reporting. Gapfill: Wavefoundry MCP code-navigation tools are not attached in this session, so targeted shell reads/searches are used for implementation discovery. | Wave activated as `implementing`; current registry, lint validator, audit, and upgrade seams will be read before edits. |
| 2026-08-16 | Observe: added a registry-derived, read-only `agent_surface_integrity` inventory and surfaced it through `wf_audit` as a non-blocking advisory. | New focused fixture reproduces canonical-carrier creation beside a top-level duplicate while current lint passes, then verifies the audit reports the canonical specialist remediation; 2 focused tests pass. |
| 2026-08-16 | Operator narrowed scope to the audit-only first increment. | Focused tests pass; `wf_audit` live probe reports the new structured surface; docs-lint passes. |
| 2026-08-16 | Added advisory-only upgrade-summary reporting and completed verification. | Full framework suite: 7,256 tests across 63 files passed; `./.wavefoundry/bin/wf docs-lint` and `git diff --check` passed. |
| 2026-08-16 | Repaired delivery findings by removing premature orphan/reference reporting and reconciling the change contract with the narrowed scope. | Focused audit regression, docs-lint, diff check, and the full framework suite (7,256 tests across 63 files) pass. |
| 2026-08-16 | Independent review (second session, MCP attached) recorded two more delivery findings and repaired both. `agent-surface-advisory-integrations-untested`: neither AC-7 seam had a regression test; added `test_agent_surface_integrity_advisory_rides_the_audit_envelope` (real audit through `wf_audit_response` on a fixture root: clean tree carries the report with zero findings and no diagnostic, a forked `red-team` yields the report, both paths, the canonical path, the `agent_surface_integrity_drift` diagnostic, envelope still ok, docs untouched) and `UpgradeSurfacesTests` (scan helper None-root and finding paths; `_print_operator_summary` prints the advisory with per-role paths). `agent-surface-advisory-absent-on-delivering-upgrade`: the runner-owned summary line executes from the installed (pre-upgrade) runner, so the delivering upgrade could not print it; added a version-gated `upgrade_extensions.pre_cleanup` hook (zip-loaded, runs the just-extracted audit, prints the same advisory when `from_version` predates 1.17.1, swallows every failure so an advisory can never abort an upgrade). Runner summary and hook now both print per-role path lines. Also documented that the audit's `Role:` parse rule is deliberately identical to lint's `_ROLE_RE`. Executed known-bads in scratch: hook neutered, gate removed, exception guard narrowed, runner line dropped, and the `wf_audit` diagnostic dropped each fail exactly the intended test and pass on restore. Focused: `test_agent_surface_integrity` 6 OK, `WaveAuditTests` 7 OK. Gapfill: none needed, discovery ran through `code_outline`/`code_read`/`code_keyword`. | typed ledger findings + repair_start; scratch `mut-1vgep` |
| 2026-08-16 | Reverification (fresh code and docs-contract contexts) falsified the second finding's premise and found the cycle-2 hook DUPLICATED the advisory on the delivering upgrade (executed real `--cleanup`: two blocks from 1.17.0, one from 1.17.1). Recorded as `pre-cleanup-hook-duplicates-advisory` and repaired: `pre_cleanup` and its cutoff constant removed (`upgrade_extensions.py` is byte-identical to HEAD again), the two hook tests replaced by `test_delivering_upgrade_cleanup_prints_the_advisory_exactly_once` (real `main([--cleanup])` on a from-1.17.0 lock with a zip-carried extension module, forked red-team, asserts one advisory block and one per-role line on both the delivering and a later upgrade; it counted 2 against the hook-present tree before the removal), runner-line comment corrected, CHANGELOG sentence corrected (cleanup runs the freshly installed runner), Decision Log superseded. From the docs lane's low items: AC-2 now proven by `test_audit_follows_a_registry_destination_change` (patched registry destination moves the canonical path; a non-renderer carrier never becomes canonical); AC-9 now byte-for-byte (`read_bytes` snapshot of every `docs/agents/**` doc incl. the marker-bearing carrier, equal after the audit); CHANGELOG attributes paths/canonical/remediation to the report and says review-carrier role (reviewer or specialist). Not planned (info): the `agent_surface_integrity_drift` diagnostic omits the structured `advisory=True` flag (message says advisory; readiness ignores it; adding the flag means extending the sanctioned advisory-site set). | typed ledger; `tests.test_agent_surface_integrity` 6 OK |
| 2026-08-16 | Cycle-3 reverification (fresh code and docs-contract contexts): `pre-cleanup-hook-duplicates-advisory` repaired (hook re-added in scratch makes the cleanup-driver test count 2, runner guard neutered makes it count 0, restore 13 OK; `upgrade_extensions.py` byte-identical to HEAD); contract consistent (AST-backed check: `_print_operator_summary` is emitted only by `phase_cleanup`, called once under `args.cleanup`; the false sentence reinserted in a scratch CHANGELOG copy is flagged). Two cosmetic residuals fixed in-session (stale `UpgradeSurfacesTests` docstring naming the removed hook; dead `_ctx` helper). Receipt re-published (`review-policy-fcb24349`) after the change-doc digest moved; readiness re-approved (inputs unchanged in substance); code-reviewer and docs-contract-reviewer delivery approvals re-recorded on the current receipt. Full suite 7261 tests / 63 files OK; docs-lint ok. | typed ledger; `suite-1vgep-2.log` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-08-16 | Add a shared advisory integrity audit, integrated with `wf_audit` and targeted/full upgrade reporting. | It detects framework-carrier duplicate identities without mutating local content. | **Lint-only blocker:** catches duplicates but can strand existing repos at the docs gate. **Upgrade-only reconciliation:** misses ordinary drift and would need unsafe content selection. |
| 2026-08-16 | Derive framework canonical destinations from the existing review-policy carrier registry. | The registry already drives carrier creation; deriving from it prevents split path authority. | Maintain a new role-path constant: rejected because its eventual divergence would recreate the defect. |
| 2026-08-16 | Keep first-release findings advisory. | Every observed duplicate contains project-local material that needs a merge decision. | Auto-merge/delete: rejected because no mechanical rule can safely reconcile substantive forks. Immediate lint error: rejected until a migration window and assisted remediation have shipped. |
| 2026-08-16 | Surface the advisory on the DELIVERING upgrade through a version-gated `pre_cleanup` extension hook, and keep the runner-owned summary line as the durable home from 1.17.1 onward. | The extension module is loaded from inside the zip before extraction, so it is the only code that can run on the upgrade that installs the audit; gating on `_from_version_predates(from, "1.17.1")` means each later upgrade prints the advisory once, from the runner. | Hook only (rejected: hooks are the migration seam, and a zip-less upgrade from the current tree loads no extension module, so the runner line is the durable home). Runner line only (rejected: class-b transition, the first upgrade after install would be silent). Same-process dedupe flag between hook and runner (rejected: more state than the documented version-gate pattern for a rare duplicate line on a new-runner cleanup resume). |
| 2026-08-16 | SUPERSEDES the previous row: no extension hook; the runner-owned summary line is the advisory's single owner. | Two independent reverifiers executed the real `--cleanup` on the delivering-upgrade shape (lock from 1.17.0, zip-carried extension module) and counted the advisory block twice with the hook and once without: `phase_cleanup` is emitted only by the standalone `--cleanup` process, which every documented path runs from the freshly extracted runner (`_new_code_upgrade_backstop`, memory `1u8q3`), so the delivering upgrade already reports the advisory and the previous row's premise was false. A cleanup-driver test now pins exactly one block on both the delivering and a later upgrade. | Keep the hook with a same-process dedupe (rejected: solves a problem that does not exist). |

## Risks

| Risk | Mitigation |
| --- | --- |
| Reference and wrapper analysis would broaden the first increment beyond the duplicate detector. | Defer it until a separately scoped change can define routing semantics. |
| A new registry duplicates carrier authority. | Derive all framework destinations directly from `REVIEW_POLICY_CARRIER_REGISTRY`; regression-test the derivation. |
| Upgrade changes or loses project-authored role material. | Audit only; test byte-for-byte no mutation of duplicate docs and marker regions. |
| Git metadata is unavailable in some target environments. | Make tracked/untracked provenance best-effort diagnostic context, never a detection prerequisite. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
