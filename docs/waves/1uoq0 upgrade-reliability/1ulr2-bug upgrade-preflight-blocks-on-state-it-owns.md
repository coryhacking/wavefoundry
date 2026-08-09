# Upgrade Preflight Blocks On State It Owns

Change ID: `1ulr2-bug upgrade-preflight-blocks-on-state-it-owns`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-08-06
Wave: 1uoq0 upgrade-reliability

## Rationale

Field report from a downstream 1.11.0 repository upgrading to 1.15.4. The upgrade failed three times in a row, and each failure was the preflight refusing to proceed over state the framework itself produces or ships. The operator's agent diagnosed and hand-repaired all three correctly, which is the clearest evidence that none of them needed a human: the information required to fix each one was already in our code.

**Failure 1, `wave_review.enabled must be boolean`.** `migrate_wave_review_policy` (`review_policy.py`) defaults only when the key is absent:

```python
if value is None:
    return {"enabled": True, "delivery_mode": FRESH_INSTALL_DELIVERY_MODE}
```

A config carrying `"wave_review": {}` falls straight through to `normalize_wave_review_policy`, which requires `enabled` to be a bool and returns a hard error. An empty mapping means exactly what an absent key means, and the migration is the one component whose entire job is to normalize old shapes.

**Failure 2, retired prose in a file we ship.** `review_policy_reconcile.py:258-283` scans live Markdown for retired lifecycle tokens and, for any file not in the registered-carrier set, emits `retired lifecycle prose outside a registered carrier (report-only; automatic rewrite is refused) ... rewrite manually`. The operator hit this on `.wavefoundry/README.md` for the token `reviewer loop` (`review_policy.py:94`).

That file is **shipped by the pack**. `build_pack.py:797-802` adds it explicitly as a "project-owner orientation doc," and it is present in the 1.15.4 zip. So the preflight halted the upgrade to demand a manual rewrite of a file the same upgrade delivers a replacement for.

The cause is a prefix gap, not a per-file oversight. `_LIVE_MARKDOWN_EXCLUDED_PREFIXES` (`review_policy_reconcile.py:213-221`) excludes `.wavefoundry/framework/`, `.wavefoundry/index/`, and `.wavefoundry/upgrade-assets/`, but nothing at the `.wavefoundry/` root. Exactly two shipped files live there:

- `.wavefoundry/README.md`
- `.wavefoundry/CHANGELOG.md`

Both are outside every exclusion. The changelog exposure is latent and worse in kind: it is a full release history, so the first release note that names a retired concept turns every target repository's shipped changelog into a blocking preflight error about prose the operator did not write and must not edit. Our current copies are clean by accident of being at head, not by design. The root `CHANGELOG.md` is skipped by an exact-match special case (`relative == "CHANGELOG.md"`) which does not cover the shipped copy.

**Failure 3, an unrecognized placeholder.** `wf_add_change(mode='create')` repairs a scaffold `Wave:` field, but only two literal forms (`server_impl.py`):

```python
r"(?m)^Wave: (?:\[wave-id or TBD\]|TBD)$"
```

The reported document carried `Wave: <wave-id>`. Checked against history: that form never came from our template, so this is not our placeholder leaking. It is that an unambiguous angle-bracket placeholder is not recognized as one, and the operator hand-edited a value the tool could have derived.

## Requirements

1. `migrate_wave_review_policy` must treat an empty mapping exactly as it treats an absent key, returning the fresh-install default rather than an error.
2. Migration must continue to reject genuinely malformed policy (a non-mapping, or a mapping with a non-boolean `enabled`), so this widens the unset case only and does not weaken validation.
3. The live-Markdown retired-prose scan must not report framework-owned files as project drift. Coverage must be a prefix rule over the framework-owned tree rather than a per-file list, so a future shipped file at that level inherits the exclusion without a code edit. `.wavefoundry/` is framework-owned in its entirety; the operator's authored surface is `docs/`.
4. Files the operator genuinely authors must still be reported exactly as they are today. This change must not reduce what the scan catches in project-authored prose.
5. The `Wave:` scaffold repair must additionally recognize an angle-bracket placeholder (`<wave-id>`, bare or backticked), which is unambiguously a placeholder.
6. The repair must still never overwrite an operator-authored `Wave:` value, and dry-run must remain read-only. Recognition is widened to unambiguous placeholder forms only, never to "any unrecognized value".

## Scope

**Problem statement:** The upgrade preflight halts on state the framework produces or ships, sending the operator to hand-edit files the upgrade itself replaces.

**In scope:**

- The empty-mapping unset case in `migrate_wave_review_policy`.
- Exclusion of pack-shipped Markdown from the live retired-prose scan, derived from the shipped set.
- Angle-bracket placeholder recognition in the `wf_add_change` `Wave:` repair.
- Regression coverage for each, including negative controls proving nothing was weakened.

**Out of scope:**

- The bridge handoff wording that reads as an instruction to bypass operator confirmation. That is a design decision about what the bridge should say, it changes a contract test and four shipped carriers, and it is filed separately.
- The retired-token registry itself, the registered-carrier replacement set, and what counts as retired prose.
- Any change to how the pack decides which files to ship.
- The docs-lint frontmatter and leftover-upgrade-lock reports from the same field session. Those are not yet reproduced against this tree and are not claimed here.

## Acceptance Criteria

- [x] AC-1: A workflow config containing `"wave_review": {}` migrates to the fresh-install default and the upgrade proceeds, reproducing the reported failure as a red test first.
- [x] AC-2: A non-mapping `wave_review`, and a mapping whose `enabled` is present but not boolean, both still fail migration with their current messages.
- [x] AC-3: A target repository carrying a pack-shipped `.wavefoundry/README.md` that contains a retired token completes preflight without a manual-rewrite error.
- [x] AC-4: The same holds for `.wavefoundry/CHANGELOG.md`, pinning the latent exposure rather than only the reported one.
- [x] AC-5: A project-authored file outside the shipped set containing the same retired token is still reported exactly as before, proving AC-3 and AC-4 did not blanket-silence the scan.
- [x] AC-6: The exclusion is a prefix rule over `.wavefoundry/`, proven by a test that plants a NEW Markdown file directly under `.wavefoundry/` containing a retired token and observes it excluded without editing any exclusion list. The three existing `.wavefoundry/` subdirectory prefixes are subsumed rather than left as redundant entries.
- [x] AC-7: `wf_add_change(mode='create')` repairs `Wave: <wave-id>` and its backticked form to the containing wave ID.
- [x] AC-8: An operator-authored `Wave:` value is left byte-identical, and dry-run writes nothing.
- [x] AC-9: The full framework suite and docs-lint pass.

## Tasks

- [x] Write the three red tests first, each reproducing a reported failure against the current tree.
- [x] Widen the unset case in `migrate_wave_review_policy` to cover an empty mapping.
- [x] Derive the shipped-Markdown exclusion for the live scan from the pack's shipped set.
- [x] Add angle-bracket placeholder recognition to the `Wave:` repair pattern.
- [x] Add the negative controls for AC-2, AC-5, and AC-8.
- [x] Add the AC-6 derivation test that varies the shipped set rather than the exclusion list.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream       | Owner       | Depends On | Notes                                                     |
| ---------------- | ----------- | ---------- | --------------------------------------------------------- |
| red-tests        | implementer | none       | All three failures reproduced before any fix                |
| policy-migration | implementer | red-tests  | Empty-mapping unset case                                   |
| shipped-scan     | implementer | red-tests  | Derived exclusion plus the project-authored negative control |
| placeholder      | implementer | red-tests  | Angle-bracket recognition only                             |


## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/review_policy_reconcile.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

`N/A`. All three fixes widen an existing recognition rule inside its current owner. No boundary moves, no control flow changes, and the set of things the framework validates is unchanged.

## AC Priority


| AC   | Priority       | Rationale                                                                                      |
| ---- | -------------- | ----------------------------------------------------------------------------------------------- |
| AC-1 | required       | The reported blocker; without it a repo in this state cannot upgrade at all.                     |
| AC-2 | required       | Widening an unset case is only safe if malformed input still fails.                              |
| AC-3 | required       | The reported manual-rewrite demand on a file we ship.                                            |
| AC-4 | required       | The latent case is worse in kind, since a changelog must name retired concepts to do its job.    |
| AC-5 | required       | Without it the fix could silence the scan entirely and still pass every other AC.                |
| AC-6 | important      | Derivation is what stops this recurring for the next shipped file at that level.                 |
| AC-7 | required       | The reported placeholder that was hand-repaired.                                                 |
| AC-8 | required       | The 1ulnt guarantee this must not regress.                                                       |
| AC-9 | required       | Standard gate.                                                                                   |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-06 | Group three field failures into one change | Each is a small widening of an existing recognition rule on the same upgrade path, verified by the same suite; three separate change docs would cost more ceremony than the fixes | One change per failure, matching the 1uf65 field-report precedent |
| 2026-08-06 | Exclude `.wavefoundry/` by prefix rather than adding two paths | The reported README and the latent CHANGELOG are the same defect, and a hand-maintained list would miss the next shipped file at that level exactly as it missed these two. `.wavefoundry/` is framework-owned in full, so the prefix is the honest boundary and it subsumes the three existing subdirectory entries | Add the two paths as literal exclusions; register them as carriers with replacements |
| 2026-08-06 | Readiness correction: do NOT derive the exclusion from the pack's shipped set | The original plan required this and it is not achievable. `build_pack.py` does not ship to target repos (verified absent from the 1.15.4 zip), and `review_policy_reconcile.py` runs at upgrade time inside a target repo, so it cannot import the shipped set. The set is also hardcoded as two local variables rather than a shared constant, and a runtime validator depending on a build tool inverts the layering | Introduce a new shared shipped-set constant imported by both; keep the per-file list |
| 2026-08-06 | Recognize only unambiguous placeholder forms, not unrecognized values generally | 1ulnt's guarantee is that operator-authored values are never overwritten; angle-bracket text cannot be a real wave ID, but an arbitrary unknown value can | Treat any value failing wave-id shape as a placeholder |
| 2026-08-06 | File the bridge handoff wording separately | It is a design decision about what the instruction should say, and it changes a contract test plus four shipped carriers, so it does not belong with three localized bug fixes | Fold it in as a fourth requirement |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Excluding shipped Markdown silences drift the scan should catch | AC-5 keeps a project-authored file with the same token reported; the exclusion is scoped to the shipped set, not to a directory the operator writes into |
| Excluding `.wavefoundry/` wholesale hides drift in a file an operator does edit there | The operator's authored surface is `docs/`; `.wavefoundry/` holds the framework tree, index, venv, logs, and upgrade assets, three of which the scan already excludes. AC-5 keeps every `docs/` path reported. If a genuinely operator-authored file is ever placed under `.wavefoundry/`, the boundary, not this exclusion, is what would need revisiting |
| Widening the placeholder pattern overwrites a real value | AC-8 pins byte-identical preservation of an operator-authored value, and recognition is limited to bracketed forms that cannot be valid wave IDs |
| The empty-mapping default masks a genuinely broken config | AC-2 keeps every malformed shape failing; only the exact empty mapping, which is semantically identical to an absent key, is newly accepted |
| Fixes are asserted against the field report rather than reproduced | Every task begins with a red test against the current tree, so each fix is demonstrated to change a real failure |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
