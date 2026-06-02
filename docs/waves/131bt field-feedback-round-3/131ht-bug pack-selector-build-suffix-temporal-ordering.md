# Pack Selector Picks Stale Build When Multiple Same-Semver Packs Coexist

Change ID: `131ht-bug pack-selector-build-suffix-temporal-ordering`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

## Rationale

`_find_latest_release_zip` (`upgrade_wavefoundry.py:160`) selects the newest pack by `(semver_tuple, build_string)` where the secondary tie-break is lexicographic comparison of the 4-character build suffix. Two design choices interact to break temporal ordering:

1. **Build suffix is not monotonic.** `lifecycle_id.build_prefix` constructs the 5-character prefix as `encode_base36(elapsed_hours).rjust(4, "0") + BASE36_ALPHABET[elapsed_minutes % 36]`. The build suffix is `prefix[-4:]` — the LAST 4 chars, which include the minute char that wraps every 36 minutes. Two builds at minute 5 and minute 41 of any hour produce suffixes ending in the same character; lexicographic ordering doesn't match wall-clock order across the wrap.

2. **Semver comparison strips build metadata.** `check_version.compare_versions` returns "same" for `1.3.2+31gk` vs `1.3.2+31gb` per semver spec. So any same-version repackage is invisible to `wave_upgrade` — the operator on the older build never picks up the newer one unless someone bumps the patch number.

3. **The selector's lexicographic tie-break amplifies the failure mode.** When same-semver packs coexist in `~/.wavefoundry/dist/`, the selector picks the lexicographically-greatest suffix regardless of mtime. Concrete failure observed in wave 131bt close-out: three 1.3.2 builds shipped within 30 minutes — `31gk` (22:32, oldest), `31g4` (22:52), `31gb` (22:59, newest with the 131bu notification fix). Lexicographic order is `31g4 < 31gb < 31gk`, so the selector picks `31gk` — the oldest build, missing the fix. Aceiss field validation reported they were stuck on the wrong build despite multiple `wave_upgrade` attempts; the selector was working as coded, the coding was wrong.

Workaround applied in wave 131bt: bump semver patch on every meaningful republish. That works when the operator remembers, but the latent failure mode remains for any future case where same-semver packs accumulate.

## Approach

Three independent fixes, ranked by directness:

**Fix A (primary, low risk) — tie-break by file mtime instead of build suffix.** In `_find_latest_release_zip`, when two candidates share the same semver tuple, compare by file mtime rather than build string. Eliminates the lexicographic-vs-temporal mismatch entirely. File mtime is the ground truth for "which was built more recently"; build suffix is a derived label that doesn't preserve that ordering.

**Fix B (defensive, low risk) — fail the build when the produced suffix collides with an existing pack of the same semver.** In `build_pack.py`, before stamping VERSION, check whether `~/.wavefoundry/dist/wavefoundry-<MAJOR.MINOR.PATCH>.<suffix>.zip` already exists. If yes, increment the lifecycle prefix (or pad with a disambiguator) until unique. Prevents silent collisions across the 36-minute wrap window.

**Fix C (warn, low effort) — surface a build_pack warning when same-semver packs exist in dist.** Informational only — prompts the operator to either bump semver or accept the warning. Catches the wave-131bt failure pattern at packaging time before the broken pack ships.

Recommendation: **ship A + C together. B is overkill** for the actual failure mode (same-semver-different-build-suffix collision in a 36-minute window is rare; the lexicographic mis-pick is the failure that actually bit us). C catches the same-semver case before the operator hits it; A makes the selector robust against future cases.

**Wave 131bt amendment:** the "out of scope" item — making the build suffix monotonic — was actually addressed in the same wave by [[131bu]]'s integer-packed lifecycle/build-suffix encoding. That removes the lex-vs-temporal mismatch at its source. Fixes A and C are still shipped here as defense in depth: A handles the 5-minute-bucket collision window in the new encoding (two builds in the same bucket get identical suffixes), and C catches same-semver repackages at build time so operators can choose to bump explicitly.

## Requirements

1. `_find_latest_release_zip` returns the newer of two same-semver packs by file mtime, not by build-string lexicographic comparison.
2. `_find_latest_release_zip` continues to use semver as the primary key — a 1.3.3 pack always beats any 1.3.2 pack regardless of mtime.
3. `build_pack.py` emits a structured warning when at least one same-semver pack already exists in `~/.wavefoundry/dist/` at build time. Warning includes the existing pack paths so the operator can decide whether to bump semver or proceed.
4. Build_pack warning does NOT block the build — operators have legitimate reasons to repackage at the same semver (e.g., bad-artifact recovery), and bumping semver isn't always the right call.
5. Existing 2167 framework tests pass without modification.
6. New regression test in `test_upgrade_wavefoundry.py` (or wherever the selector is tested) covering the exact failure mode: three same-semver packs with non-monotonic build suffixes, verify the highest-mtime one is selected regardless of lexicographic ordering.

## Scope

**Problem statement:** the pack selector picks lexicographically-greatest build suffix among same-semver packs, but build suffix doesn't sort temporally. Operators on an older pack can fail to upgrade to a newer same-semver pack, or upgrade to a stale pack when newer same-semver packs are available.

**In scope:**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` — replace lexicographic build-suffix tie-break with file mtime tie-break in `_find_latest_release_zip`.
- `.wavefoundry/framework/scripts/build_pack.py` — emit warning when same-semver pack exists in dist.
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` (or equivalent) — regression test for the lexicographic-vs-mtime case.

**Out of scope:**

- Making the build suffix actually monotonic (the deeper fix). The 36-minute wrap is the root cause; making the suffix temporally-sortable would require changing the lifecycle ID format, which has broader implications (waves, changes, and plans all use lifecycle IDs). Fix A makes the selector correct without changing the ID format. Revisit if other ID consumers hit the same trap.
- Removing build metadata from semver entirely (using a pure semver like `1.3.2-build-31gb`). The build suffix has value for traceability; the bug is selector logic, not the suffix itself.
- Backporting the fix to existing installed packs. Operators on an older selector pick the highest-mtime pack on next `wave_upgrade` — the fix lands when they upgrade.

## Acceptance Criteria

- [x] AC-1: `_find_latest_release_zip` returns the highest-mtime pack among same-semver candidates.
- [x] AC-2: Same-semver selection now uses mtime as the secondary key — lex-greatest suffix no longer dominates among same-semver packs.
- [x] AC-3: Cross-semver selection still uses semver as the primary key — `1.3.3+xxxx` beats `1.3.2+yyyy` regardless of either build suffix's mtime (tuple compare: semver, then mtime, then build-string).
- [x] AC-4: When mtimes are equal (extremely unlikely but possible on filesystem-snapshotted dist directories), the lexicographic build-suffix tie-break is the deterministic fallback.
- [x] AC-5: `build_pack.py` emits a structured warning when same-semver packs already exist in the output directory at build time, listing the existing pack filenames.
- [x] AC-6: The warning does NOT block the build — exit code 0, build proceeds, operator can override or accept.
- [x] AC-7: Wave-131bt failure mode (three same-semver packs with non-monotonic build suffixes — `31g4`, `31gb`, `31gk` in lex order vs `31gk`, `31g4`, `31gb` in mtime order) is now handled by the new mtime-primary tie-break.
- [x] AC-8: All existing 2169 framework tests pass.
- [x] AC-9 *(1.3.4 amendment)*: Build suffix is monotonic at the encoding layer — integer-packed `(days * 288 + bucket_5min) mod 36^4` from [[131bu]] makes lex order match wall-clock for any two suffixes more than 5 minutes apart. This was listed out-of-scope in the original plan; landed alongside the lifecycle ID rewrite.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Update `_find_latest_release_zip` tie-break to file mtime in `upgrade_wavefoundry.py`
- [x] Add same-semver-collision warning in `build_pack.py`
- [x] Make build suffix monotonic at the encoding layer (amendment — landed with [[131bu]] integer-packed encoding rewrite)
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`

## Affected Architecture Docs

- N/A — the change strengthens the existing upgrade-selector path and the existing build_pack pre-flight chain. No architectural boundary or data flow change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core selector correctness |
| AC-2 | required | Eliminates the lex tie-break that caused the wave-131bt failure |
| AC-3 | required | Semver still wins as primary key — no regression for cross-version upgrades |
| AC-4 | required | Deterministic fallback for the edge case |
| AC-5 | required | Operator-facing visibility into the same-semver case |
| AC-6 | required | Operator can still ship at same semver when intentional |
| AC-7 | required | Reproduces the exact failure mode the wave hit |
| AC-8 | required | No baseline regression |
| AC-9 | required | Encoding-layer fix — defense in depth from 1.3.4 amendment |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Original plan: fix the selector tie-break, leave the suffix encoding alone | At plan time, changing the lifecycle ID format seemed too cross-cutting for a fix that only addressed one consumer's bug. The selector tie-break is local to the upgrade path and resolves the failure cleanly | Make build suffix monotonic (rejected at plan time — broad impact); remove build metadata from packs entirely (rejected — traceability value); enforce semver-bump-on-republish via build_pack (rejected — too aggressive; same-version repackage has legitimate uses) |
| 2026-06-01 | **Amendment: also fix the encoding** via [[131bu]] integer-packed packing | During wave 131bt close-out the lifecycle ID was being rewritten anyway (description-refresh and other 131bu work). At that point the "broad impact" cost was already being paid; folding in the suffix-monotonicity fix had zero marginal cost. Defense in depth: encoding-layer monotonicity + selector mtime tie-break + build-time same-semver warning each catch a different failure window | Keep suffix non-monotonic and rely solely on selector (rejected — leaves a latent trap when 131ht's selector fix gets reworked or copied); ship encoding fix without selector mtime (rejected — selector still needs to handle same-bucket collisions in the 5-min window) |
| 2026-06-01 | Use mtime as primary tie-break, lexicographic as deterministic fallback | mtime is the ground truth for "which was built more recently"; fallback to lexicographic ordering on tie keeps the selector deterministic if two packs somehow share mtime (atomic filesystem operations, snapshot restore, etc.) | Pure mtime (rejected — needs deterministic fallback); pure lexicographic (rejected — the bug we're fixing) |
| 2026-06-01 | Warn at build time but don't block | Operators have legitimate reasons to repackage at the same semver (bad artifact recovery, content fix without behavior change). Blocking would force semver bumps that don't reflect semantic reality. Warning surfaces the risk without removing the option | Block on same-semver collision (rejected — too restrictive); silent acceptance (rejected — the original failure mode) |

## Risks

| Risk | Mitigation |
|---|---|
| mtime can be misleading if packs are copied/moved between directories (mtime preserved on copy, sometimes updated, depending on filesystem) | Document mtime semantics; operators copying packs across machines should bump semver. The dist directory is conventionally local-build; remote-copied packs are rare in current workflows |
| Filesystem mtime resolution may be insufficient on some platforms (1-second precision) — two packs built within the same second tie on mtime | Lexicographic build-suffix fallback (AC-4) handles ties; same-second collision is the wave-131bt failure mode, which the fallback would still mis-pick. Acceptable: when two packs land within the same second, operators should bump semver to disambiguate |
| Warning at build time triggers on every legitimate same-semver repackage and operators learn to ignore it | The warning is one line per existing pack; specific enough to act on but quiet enough not to spam. If ignoring becomes a pattern, revisit |
| Existing operators on selector-built packs don't pick up the fix until they upgrade | Standard upgrade-lifecycle behavior; no special handling needed |

## Related Work

- Failure surfaced during wave 131bt close-out — three 1.3.2 builds shipped same-day, lexicographic ordering picked the oldest.
- Direct dependency on [[131bu]] — the integer-packed encoding rewrite makes the suffix lex-monotonic at the source, complementing this change's mtime tie-break and same-semver warning. The two changes ship together in 1.3.4.
- Companion to [[131hh]] (MCP protocol surface opportunities) — both are framework-internal hygiene improvements that don't change operator-facing functionality but tighten failure modes.

## Session Handoff

Admitted to wave 131bt for close-out alongside [[131bu]]'s encoding rewrite. All ACs implemented; change ships in 1.3.4.
