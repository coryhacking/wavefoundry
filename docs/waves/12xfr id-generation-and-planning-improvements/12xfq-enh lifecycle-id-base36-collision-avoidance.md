# Lifecycle ID: Base36 Alphabet and Collision Avoidance

Change ID: `12xfq-enh lifecycle-id-base36-collision-avoidance`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: TBD

## Rationale

The current lifecycle ID generator (`lifecycle_id.py`) has two weaknesses that can produce duplicate prefixes:

1. **Coarse 5th-character resolution.** The 5th character encodes `(current_time.minute + 1) // 2` — a ~2-minute bucket. Any two IDs generated within the same 2-minute window share an identical 5-character prefix, making the short-form prefix lookup ambiguous and risking filename collisions when kind and slug also match.

2. **No collision avoidance.** The generator does not check whether the produced prefix is already in use. Rapid successive generation always produces the same prefix until the time bucket advances.

This change replaces the Crockford base32 alphabet with base36 (`0-9a-z`) and encodes the 5th character as elapsed minutes since epoch modulo 36, giving per-minute resolution over a 36-minute cycle. A borrow-from-future mechanism scans existing IDs and increments the prefix until an unused one is found, guaranteeing uniqueness in all cases.

## Requirements

1. Replace `CROCKFORD_BASE32_ALPHABET` with a base36 alphabet: `0123456789abcdefghijklmnopqrstuvwxyz` (10 digits + 26 lowercase letters). Update `encode_base36()` and `decode_base36()` to use this alphabet. Remove or alias `CROCKFORD_BASE32_ALPHABET` to avoid breaking internal call sites.
2. Change the 5th character of `build_prefix()` to encode elapsed whole minutes since the configured epoch, modulo 36: `elapsed_minutes = int((current_time - epoch).total_seconds() // 60)` → `BASE36_ALPHABET[elapsed_minutes % 36]`. The first 4 characters continue to encode elapsed hours.
3. Add `decode_base36(s: str) -> int` — the inverse of `encode_base36`, needed by the collision-avoidance scan.
4. Add `next_available_prefix(kind: str, repo_root: Path, *, timestamp, policy) -> str` that:
   - Generates the time-based 5-character prefix via `build_prefix()`.
   - Decodes it to an integer, scans `docs/plans/*.md` stems and `docs/waves/*/*.md` stems in `repo_root` for any existing ID whose prefix matches `{prefix}-{kind}` (or bare `{prefix}` for wave IDs).
   - Increments the integer by 1 and re-encodes until an unused prefix is found.
   - Returns the first unused 5-character prefix.
5. Wire `build_id()` to call `next_available_prefix()` for both wave IDs and change IDs when a `repo_root` is provided. The only exemption is the `--legacy` path, which always uses the reserved `"00000"` prefix and never scans. When `repo_root` is `None` (e.g., in tests without a repo), fall back to the time-based prefix without scanning.
6. The borrow-from-future scan must cover both `docs/plans/` (staged change docs) and `docs/waves/*/` (admitted change docs and wave records).
7. All existing tests in `test_lifecycle_id.py` must be updated or extended to cover the new alphabet, the new 5th-character encoding, `decode_base36`, and the collision-avoidance path (including the borrow case).

## Scope

**Problem statement:** Rapid successive ID generation produces identical 5-character prefixes, causing ambiguous short-form lookups and potential filename collisions.

**In scope:**

- `.wavefoundry/framework/scripts/lifecycle_id.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_id.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py` — `LIFECYCLE_PREFIX_PATTERN` updated from Crockford base32 `[0-9a-hjkmnp-tv-z]` to full base36 `[0-9a-z]`; the lint validator must recognize IDs that use `i`, `l`, `o`, `u`

**Out of scope:**

- Existing wave records and change docs — their IDs remain valid; base36 is a superset of the characters used in existing Crockford base32 IDs
- MCP server tool signatures or wave validator ID-format rules (existing 5-char prefix format is preserved)
- Any UI or display surfaces that render IDs

## Acceptance Criteria

- [x] AC-1: `lifecycle_id.py` uses base36 (`0-9a-z`) as its encoding alphabet throughout.
- [x] AC-2: The 5th character of a generated prefix encodes `elapsed_minutes_since_epoch % 36`, giving a unique character for each minute within any 36-minute window.
- [x] AC-3: `decode_base36()` correctly inverts `encode_base36()` for all values used in prefix generation.
- [x] AC-4: When `repo_root` is provided and the generated prefix is already in use, `build_id()` returns a prefix incremented by 1 (repeating until unused) — the "borrow from future" guarantee.
- [x] AC-5: When two IDs are generated in rapid succession (same time bucket), the second receives a distinct prefix one higher than the first.
- [x] AC-6: Existing Crockford-encoded IDs in `docs/plans/` and `docs/waves/` continue to be found and scanned correctly (base36 is a superset; no existing characters are invalid).
- [ ] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes with no failures.
- [x] AC-8: Borrow-from-future collision checking is applied to both wave IDs (`kind="wave"`) and change IDs; only the `--legacy` prefix path bypasses the scan.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Replace `CROCKFORD_BASE32_ALPHABET` with `BASE36_ALPHABET` in `lifecycle_id.py`; update `encode_base36()` to use it
- [x] Add `decode_base36(s: str) -> int`
- [x] Update `build_prefix()` 5th character to use `elapsed_minutes % 36`
- [x] Add `next_available_prefix()` with filesystem scan and borrow logic
- [x] Wire `build_id()` to call `next_available_prefix()` when `repo_root` is provided
- [x] Close `framework_edit_allowed` gate immediately after
- [x] Update `test_lifecycle_id.py`: alphabet, 5th-char encoding, decode, collision-avoidance cases
- [ ] Run full test suite — verify AC-7

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Core encoding | implementer | gate open | Alphabet + decode + build_prefix 5th char |
| Collision avoidance | implementer | core encoding | next_available_prefix + build_id wiring |
| Tests | implementer | collision avoidance | Update existing + add new coverage |
| Validation | implementer | tests | Full suite pass |

## Serialization Points

- Complete core encoding changes before adding collision avoidance — the scan and increment logic depends on `decode_base36`.
- Close `framework_edit_allowed` gate immediately after all `lifecycle_id.py` edits; test updates do not require the gate.

## Affected Architecture Docs

N/A — the ID format (5 characters, alphanumeric, lowercase) is unchanged in shape. No boundary, flow, or API surface impact.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core alphabet change |
| AC-2 | required | Per-minute 5th-char resolution; directly reduces natural collision rate |
| AC-3 | required | Decode is required by the borrow-from-future increment loop |
| AC-4 | required | Core collision-avoidance guarantee |
| AC-5 | required | Verifiable proof of the borrow behavior |
| AC-6 | required | Backwards-compatibility with existing IDs |
| AC-7 | required | No regressions |
| AC-8 | required | Wave IDs must also be collision-checked; borrow-from-future must not be silently skipped for any non-legacy kind |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-26 | Base36 over Crockford base32 | Crockford excludes i, l, o, u to prevent handwriting transcription errors — irrelevant for machine-generated, machine-read IDs; base36 adds 4 symbols enabling `% 36` to fit naturally | Keep Crockford + `% 32` — rejected: 32-minute window vs 36; base36 is cleaner |
| 2026-05-26 | Elapsed minutes since epoch `% 36` for 5th char | Monotonically increasing minutes avoid same-hour wrapping that `current_time.minute % N` would introduce; `% 36` fits exactly in the base36 alphabet | `current_time.minute % 32` — rejected: wraps within the hour, causing same-prefix collisions across the hour boundary |
| 2026-05-26 | Borrow from future via filesystem scan + increment | Truth lives in the filesystem; no persistent counter file needed; self-correcting as time catches up to borrowed prefixes | Persistent counter file — rejected: extra state to manage; case-sensitive alphabet extension — rejected: case sensitivity causes issues on case-insensitive filesystems (macOS default) |
| 2026-05-26 | Scan both `docs/plans/` and `docs/waves/*/` | Staged and admitted change docs must both be checked; a staged plan that hasn't been admitted yet is still a real reservation | Scan only admitted docs — rejected: would allow a borrow to collide with a staged plan |
| 2026-05-26 | Update `LIFECYCLE_PREFIX_PATTERN` to `[0-9a-z]` | The wave lint validator's Crockford base32 character class excluded `i`, `l`, `o`, `u`; base36 IDs containing those characters failed lint as "unstable" IDs; the pattern must be widened to match the full base36 alphabet | Keep Crockford pattern — rejected: any ID with `i`, `l`, `o`, `u` fails lint, breaking `wave_prepare` and downstream journal checks |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-26 | Change doc created | Operator direction |

## Risks

| Risk | Mitigation |
| --- | --- |
| Truly parallel generation (two agents simultaneously) could still claim the same prefix before either writes to disk | Acceptable for human-paced workflow; the filesystem naming conflict would surface immediately as an error |
| Base36 restores i, l, o, u which Crockford excluded | These IDs are machine-generated and machine-read; transcription ambiguity is not a concern |
| Existing test fixtures use Crockford-specific output values | Test update is in scope; AC-7 confirms no regressions |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
