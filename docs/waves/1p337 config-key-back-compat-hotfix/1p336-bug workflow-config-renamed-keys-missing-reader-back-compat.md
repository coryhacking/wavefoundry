# Workflow-Config Renamed Keys Missing Reader-Side Back-Compat

Change ID: `1p336-bug workflow-config-renamed-keys-missing-reader-back-compat`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-03
Wave: TBD (recommended: a small hotfix wave shipping as 1.4.0)

## Rationale

A downstream consumer upgrading their project to 1.3.32 audited the framework diff carefully and identified a real transition-state defect:

> *"1.3.32 has a transition-state inconsistency: the seed prompts and MCP tool names migrated `wave_council_policy`→`wave_review` / `wave_execution`→`wave_implement`, but the runtime config reader (`_read_wave_council_policy`, `server_impl.py:1280`) still reads the OLD key names with no fallback. Any repo that 'follows the upgraded seed guidance' and renames its `workflow-config.json` keys will silently disable Wave Council and wave-execution policy — the reader returns `{}` and `enabled` is never seen."*

The consumer correctly chose **not** to apply the rename to their config after verifying runtime behavior, but flagged the gap as a real bug. Their report is precise; both defects are confirmed.

**Defect 1 — runtime Wave Council policy reader.** `server_impl.py:1280` in `_read_wave_council_policy()`:

```python
raw = cfg.get("wave_council_policy", {})  # reads OLD key only; no fallback
```

If a consumer follows the upgraded seed guidance (which now references `wave_review.enabled` throughout) and renames their `workflow-config.json` key to `wave_review`, the reader returns `{}`, `enabled` is False by default, and Wave Council silently disables. The consumer would discover this only by noticing missing `wave-council-readiness` signoff requests — late, indirect, and hard to root-cause.

**Defect 2 — docs-lint required-keys check.** `wave_lint_lib/constants.py:41` lists `"wave_execution"` in `WORKFLOW_REQUIRED_KEYS`. `core_validators.py:190-211` requires every key in that tuple to be present in the consumer's `workflow-config.json`. If a consumer renames `wave_execution` → `wave_implement` to follow upgraded seed guidance, docs-lint fails with `missing 'wave_execution' section`.

Provenance: the seed-prose rename landed in the prior wave (`1p2q3`, packaged 1.3.27–1.3.31). The runtime reader and the lint required-keys were never updated to match. The current wave `1p31b` (1.3.32) propagated the new name in newly-authored seeds (`1p31i`) because the rename was already convention — but did not catch the runtime gap. Versions 1.3.27 through 1.3.32 all ship with this transition gap.

The consumer's discipline (verify runtime before applying prose) saved them; not every downstream operator will perform that audit. This change closes the gap with a small reader-side back-compat fix on both surfaces.

## Requirements

1. **`_read_wave_council_policy()` accepts either key.** The runtime reader at `server_impl.py:1280` reads `wave_review` first; if absent, falls back to `wave_council_policy`. Both old-key and new-key consumer configs work without silent disable.
2. **Deprecation signal on legacy-key read.** When the legacy `wave_council_policy` key is present and the new `wave_review` key is absent, emit a one-time deprecation note to stderr naming the rename and the canonical migration. Operators see a discoverable signal without breakage.
3. **`WORKFLOW_REQUIRED_KEYS` validator accepts either key for renamed entries.** The required-keys check at `core_validators.py:190-211` treats `wave_implement` and `wave_execution` as equivalent — if either is present, the requirement is satisfied. The data structure is generalized so future renames can be added without changing the validator code.
4. **`docs-lint` error message names both acceptable keys** when the requirement-with-aliases is unmet, so the operator sees the migration path inline rather than having to look it up.
5. **Tests** cover: (a) runtime reader returns the policy when the new `wave_review` key is set; (b) runtime reader returns the policy when only the legacy `wave_council_policy` key is set (back-compat); (c) runtime reader prefers `wave_review` when both are set; (d) docs-lint passes with `wave_implement` set and `wave_execution` absent; (e) docs-lint passes with `wave_execution` set and `wave_implement` absent (back-compat); (f) docs-lint fails when neither is set, naming both acceptable keys.
6. **No silent behavior change** for consumers whose `workflow-config.json` already has the legacy `wave_council_policy` and `wave_execution` keys. They keep working exactly as before; the deprecation note is informational only and does not block any operation.

## Scope

**Problem statement:** Seed prose was renamed from `wave_council_policy` → `wave_review` and `wave_execution` → `wave_implement` in the previous wave (`1p2q3`), but the runtime reader and the docs-lint required-keys check still consume the old names with no back-compat fallback. Consumers who follow the upgraded seed guidance and rename their `workflow-config.json` keys silently lose Wave Council enforcement AND fail docs-lint. The seed convention and the runtime contract are inconsistent on a security/process-relevant surface.

**In scope:**

- `server_impl.py` `_read_wave_council_policy()` — back-compat fallback (new key first, legacy second, deprecation note on legacy)
- `wave_lint_lib/constants.py` `WORKFLOW_REQUIRED_KEYS` — generalize to support alias tuples
- `wave_lint_lib/core_validators.py` required-keys validator — handle alias tuples, name both keys in error message
- Tests in `test_server_tools.py` and `test_docs_lint.py` covering the six scenarios in Req-5

**Out of scope:**

- Retroactively renaming consumer `workflow-config.json` files. This change adds reader-side back-compat; consumers can migrate at their own pace.
- Migrating the seed prose back to legacy key names. The seed convention is already aligned with the new names; the right migration direction is forward.
- A broader audit of all renamed key references in the framework. Two surface bugs were caught by the downstream consumer; this change closes those. A future cross-cut audit of any other seed-vs-runtime drift is a separate concern.
- `code_patterns` → `code_pattern` and `code_review_triggers` → `design_review_triggers` from the consumer's report. Audit confirmed: `code_pattern` is only an MCP tool argument label (no config-key read), and `code_review_triggers`/`design_review_triggers` aren't read by any script. No runtime defect on those surfaces.

## Acceptance Criteria

- [x] AC-1: `_read_wave_council_policy()` reads `wave_review` first and returns its policy dict when present. *Verified by `test_reader_uses_new_wave_review_key_when_present`.*
- [x] AC-2: `_read_wave_council_policy()` falls back to `wave_council_policy` when `wave_review` is absent and returns its policy dict. *Verified by `test_reader_falls_back_to_legacy_wave_council_policy_key`.*
- [x] AC-3: When `wave_review` is present, `wave_council_policy` is ignored entirely (no legacy-precedence ambiguity). *Verified by `test_reader_prefers_new_key_when_both_present` — `wave_review.enabled=True` wins over legacy `enabled=False`.*
- [x] AC-4: When the legacy `wave_council_policy` key is read because `wave_review` is absent, a one-line deprecation note is emitted to stderr naming the rename and the canonical new key. *Verified by `test_legacy_key_emits_one_shot_deprecation_note_to_stderr` (covers both first-emit and one-shot guard) plus `test_no_deprecation_note_when_new_key_is_used` (no spurious emit). Exact note: "workflow-config.json: legacy key `wave_council_policy` is deprecated; rename to `wave_review`. The runtime accepts both for now."*
- [x] AC-5: `WORKFLOW_REQUIRED_KEYS` data structure supports alias tuples; `wave_implement` and `wave_execution` are recorded as equivalent. *Generalized; entry is `("wave_implement", "wave_execution")`.*
- [x] AC-6: docs-lint required-keys check passes with `wave_implement` set and `wave_execution` absent. *Verified by `test_workflow_config_accepts_new_wave_implement_key`.*
- [x] AC-7: docs-lint required-keys check passes with `wave_execution` set and `wave_implement` absent. *Verified by `test_workflow_config_accepts_legacy_wave_execution_key`; base fixture uses the legacy key and lints clean.*
- [x] AC-8: docs-lint required-keys check fails when neither `wave_implement` nor `wave_execution` is set; error message names both acceptable keys so the operator sees the migration path. *Verified by `test_workflow_config_fails_when_neither_alias_present`; error format: "missing `wave_implement` or legacy `wave_execution` section".*
- [x] AC-9: Existing consumer configs with both legacy keys (`wave_council_policy`, `wave_execution`) behave unchanged — Wave Council enforcement remains active, docs-lint still passes. *All prior `WaveCouncilPolicyTests` (using legacy key) still pass; base fixture (using legacy key) still lints clean.*
- [x] AC-10: New tests cover the 6 scenarios in Req-5; full framework test suite passes. *14 new tests across two test files (5 in server-tools, 9 in docs-lint with class-inheritance reuse); full suite 2299 tests pass across 24 files.*
- [x] AC-11: `docs-lint` passes on this change doc after additions.
- [x] AC-12: `wave_validate` passes on this self-hosted repo after additions.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Modify `_read_wave_council_policy()` in `server_impl.py` — new-key-first, legacy fallback, one-shot deprecation note via module-level guard
- [x] Generalize `WORKFLOW_REQUIRED_KEYS` in `wave_lint_lib/constants.py` to accept tuple aliases for renamed keys
- [x] Update `core_validators.py` required-keys validator to handle alias tuples and name both keys in error messages
- [x] Add 5 tests in `test_server_tools.py` covering `_read_wave_council_policy()` with new-key, legacy-key, both-keys precedence, deprecation-note one-shot, and no-spurious-emit scenarios
- [x] Add 3 tests in `test_docs_lint.py` covering `wave_implement`-only, `wave_execution`-only, and neither-set scenarios
- [x] Run framework test suite — 2299 tests across 24 files pass
- [x] Run `wave_validate` — lint passes
- [x] Close gate; mark change `implemented`

## Affected Architecture Docs

`N/A` — bug fix in two existing modules adding back-compat fallback. No architectural boundary, data flow, or testing-architecture impact. The required-keys data-structure generalization is a localized refactor in an existing validator helper.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (reader uses new key first) | required | Defect 1 root cause. Without this, the seed-vs-runtime gap persists. |
| AC-2 (reader falls back to legacy) | required | The no-silent-break promise. Existing consumer configs must keep working. |
| AC-3 (new key precedence) | required | Unambiguous resolution — operators migrating need to know the new key wins. |
| AC-4 (deprecation note on legacy read) | required | Discoverability. Without a signal, operators don't know they're on the legacy path. The one-time-per-process constraint prevents log noise. |
| AC-5 (required-keys data structure supports aliases) | required | Defect 2 fix surface. The data-structure generalization is the cleanest way to support this rename and future renames. |
| AC-6 (lint passes with new key only) | required | Migration-path verification. |
| AC-7 (lint passes with legacy key only) | required | No-silent-break verification. |
| AC-8 (lint error names both acceptable keys) | required | Operator-discoverability of the migration path inline. Otherwise the operator hits the error and has to grep seeds to understand. |
| AC-9 (existing configs unchanged) | required | Hard back-compat promise. Production consumers must not regress. |
| AC-10 (tests cover 6 scenarios; suite passes) | required | Regression discipline. |
| AC-11 (docs-lint passes) | required | Standard hygiene gate. |
| AC-12 (wave_validate passes) | required | Standard hygiene gate. |

All ACs are required because every one is load-bearing on either the defect being fixed (AC-1, AC-2, AC-5, AC-6, AC-7), the no-silent-break promise (AC-3, AC-9), operator discoverability (AC-4, AC-8), or the regression guarantee (AC-10, AC-11, AC-12). There is no nice-to-have or important-tier work in this scope — the change is bounded by design.

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | New-key-first precedence with legacy fallback (read `wave_review`; if absent, read `wave_council_policy`) — the new key wins when both are present | Migrating operators expect the new key to take effect once they set it. Legacy precedence would surprise them and surface as "I set the new key but Wave Council still behaves the way the old policy said." Unambiguous new-key-wins matches the seed convention and the migration intent. | (a) Legacy-precedence — rejected; surprises migrating operators. (b) Merge both dicts when both present — rejected; merge semantics are ambiguous and not what the seed prose suggests. The seed prose treats them as a rename, not a merge. |
| 2026-06-03 | One-shot deprecation note (fires at most once per process) on legacy-key read | A deprecation signal is operator-discoverable; firing on every read would spam logs and dilute the signal. Module-level state ensures one notification per running process. | (a) Fire on every read — rejected; log noise dilutes the signal. (b) No deprecation note — rejected; operators on the legacy path have no signal that they should migrate. (c) Hard error on legacy key — rejected; breaks the no-silent-break promise. |
| 2026-06-03 | Generalize `WORKFLOW_REQUIRED_KEYS` to support tuple aliases — `(("wave_implement", "wave_execution"), "agent_memory", ...)` — rather than special-casing the two renamed keys | A data-structure generalization handles this rename AND future renames without touching the validator logic. Future-proofing has near-zero cost; special-casing accumulates. The validator already iterates the tuple, so the change is mechanical. | (a) Hardcode the rename in the validator — rejected; one-shot pattern that doesn't compose for future renames. (b) Keep the tuple flat and add both names — rejected; either both must be present (which is wrong) or only one (which loses the alias semantics). |
| 2026-06-03 | Error message when both alias members are absent must name both keys — *"missing `wave_implement` (or legacy `wave_execution`) section"* | Operator-discoverability of the migration path. Naming only the new key would force operators to grep the codebase to learn about the legacy alternative. Naming only the legacy key would tell them the wrong direction. | (a) Name only the new key — rejected; loses back-compat affordance. (b) Name only the legacy key — rejected; tells operators the wrong direction for the migration. |
| 2026-06-03 | Out-of-scope: retroactive `workflow-config.json` rename for consumer repos | This change is reader-side back-compat. The whole point is consumers can migrate at their own pace. Forcing the rename would defeat the gradual-migration premise. | Force-migrate consumer configs on upgrade — rejected; violates back-compat promise. |
| 2026-06-03 | Out-of-scope: `code_patterns`/`code_pattern` and `code_review_triggers`/`design_review_triggers` from the consumer's report | Audit confirmed neither has runtime reader-side defects — `code_pattern` is only the MCP tool argument label, and neither `code_review_triggers` nor `design_review_triggers` is read by any script. The consumer's report on the broader rename was accurate but those particular renames are prose-only changes with no runtime gap. | Include them defensively — rejected; no defect, no fix needed. |

## Risks

| Risk | Mitigation |
|---|---|
| Consumer relying on the legacy key being preserved exactly (e.g., reading it from a sidecar tool) — adding the new key without removing legacy is fine, but renaming legacy might break tooling we don't control | This change does not modify consumer config files. Reader-side back-compat means both keys work; consumers decide when to rename. The deprecation note is informational, not blocking. |
| Deprecation note implementation accidentally fires on every process startup even when neither legacy nor new key is set | The note fires only when the legacy key was the source of the returned policy — i.e., only when `wave_review` was absent AND `wave_council_policy` was present. A correctly-scoped guard prevents spurious notifications. The tests verify this explicitly. |
| `WORKFLOW_REQUIRED_KEYS` data-structure change breaks third-party readers that import the constant | The constant is internal to `wave_lint_lib`; not part of the framework's public surface. Internal callers are updated in the same change. |
| Hotfix urgency tempts skipping the deprecation note (AC-4) as a follow-on | Urgency is real but AC-4 is load-bearing on operator discoverability — without it, migrating operators have no signal. The note is ~3 lines of code; not a reason to defer. |
| The fix on this self-host shows no behavioral change because the operator's own `workflow-config.json` uses the legacy keys, masking the back-compat behavior | The tests explicitly verify the new-key path on synthetic fixtures, independent of this repo's own config. The self-host's own config is incidental to verification. |

## Related Work

- **`1p2q3` (parent of the original rename)** — packaged 1.3.27–1.3.31. Renamed seed prose from `wave_council_policy` → `wave_review` and `wave_execution` → `wave_implement` without updating the runtime reader or the docs-lint required-keys check.
- **`1p31b` (`1p31i-enh`)** — propagated the new name in newly-authored seed content because it was already convention; did not catch the runtime gap.
- **Downstream consumer report** — flagged the defect during an upgrade audit. Their verification methodology (read actual runtime reader code before applying renames) is the model for future upgrade audits.
- **Seed-first doc workflow** (memory note) — this change is the reverse direction: a runtime catches up to seed prose that landed earlier. The lesson is that seed-first changes that imply consumer config changes must include the corresponding runtime back-compat in the same release.

## Session Handoff

Unattached future-wave plan. Recommended admission path: a small hotfix wave shipping as 1.4.0, admitted and prepared in the same session to minimize the transition gap exposure window. The fix is bounded (~10 LOC across two files plus tests), so the wave can be created → admitted → prepared → implemented → reviewed → closed in a single session.
