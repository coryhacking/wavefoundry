# CRLF-Safe Review Evidence Reprojection and Parity Check

Change ID: `208l3-bug crlf-safe-review-evidence-and-parity`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: 20b39 windows-crlf-correctness

## Rationale

Brief: a field upgrade on Windows (1.15.4 to 1.28.0) failed repeatedly because Markdown was checked out with CRLF (`core.autocrlf`) and two code paths match or compare LF-only. The goal is that a CRLF checkout never blocks an upgrade, a Prepare, or docs-lint, and that framework code never writes mixed line endings into a CRLF file on the upgrade and render paths. Consumers are Windows operators and agents; constraint is no change to LF-checkout behavior; success is observable through new CRLF tests that fail before the fix and pass after it.

Verified at HEAD by reading the code (no CRLF experiment was run):

- `.wavefoundry/framework/scripts/review_evidence.py:2767` defines `_REVIEW_EVIDENCE_SECTION_RE` as `^## Review Evidence[ \t]*$\n...`. `[ \t]*` cannot consume `\r` and multiline `$` matches only before `\n`, so a CRLF heading gets zero matches and `render_review_status_projection` raises "external wave must contain exactly one Review Evidence section" (`review_evidence.py:2846-2848`). `_status_block_row_keys` (`:2778-2780`) silently returns `()` on the same failure.
- The path that triggers it in the field is `review_policy_upgrade.py:116-117`, which does `wave_md.read_bytes().decode("utf-8")` with no newline normalization and then calls the projection functions (`:137-142`). The error is prefixed `cannot reproject:` at `:143-144`.
- The sibling Finding Synthesis regex `_SECTION_RE` (`review_evidence.py:196-198`) uses `\s*$\n` and tolerates CRLF, so the Review Evidence regex is the odd one out. With the seam in this change, the regex tolerance is belt-and-braces: lint and the gates already read records with universal newlines and see LF.
- Even when a match succeeds on CRLF text, `render_review_status_projection` (`review_evidence.py:2860-2886`) and `render_review_evidence_projection` (the Finding Synthesis rebuild, uses `_SECTION_RE`) splice LF-only text, producing mixed endings. `review_policy.set_reprepare_marker` (`review_policy.py:1288-1298`) is a third LF-only splicer on the same path: it inserts `"\n" + line` after `rstrip()` at the first `"\n## "` and its `\s*$` substitution swallows a trailing `\r`. On the upgrade path it is called at `review_policy_upgrade.py:136`. This is read from the code, not reproduced.
- The upgrade path builds its result as `WaveMigration(wave_md, before, marked_text.encode(), projected_text.encode())` (`review_policy_upgrade.py:136-149`): two byte strings, both of which must end up with the original convention.
- The other caller, `wf_server/server_impl.py` (`_publish_prepare_policy_state`, `set_reprepare_marker` at about `:8083`), is not exposed to CRLF the same way. It reads the wave through `_read_wave_record_text` (`lifecycle_gate_support.py` `:711-723`), which is `read_text(encoding="utf-8")` and so applies universal newlines, and it compares `live != wave_text` in that form. The helper therefore never sees CRLF there, and writing `final.encode("utf-8")` rewrites a CRLF wave.md as all-LF on every Prepare. The result is consistent, not mixed. See Decision 4.
- Docs-lint reads records through `wave_lint_lib/helpers.py:175` `read_record_text` (universal newlines), so docs-lint itself is not exposed on that path. The other renderer callers (`wf_server/server_impl.py` at about `:8312`, `:10637`, `:11548`, `:25852`, and `dashboard_lib.py` at about `:1008`) read text through universal-newline paths and are expected to be unaffected; Requirement 7 and AC-6 make the implementer confirm each one.
- Separately, the "rendered review-policy/review-protocol region differs from its registered block source" failure is not caused by the renderer writing CRLF: `render_agent_surfaces.write_text` (`render_agent_surfaces.py:2099-2111`) writes bytes verbatim. The CRLF comes from the checkout. `wave_lint_lib/core_validators.py:507-508` reads the carrier file verbatim (`newline=""`), calls the upsert helper (`_upsert_review_protocol_region` `render_agent_surfaces.py:2141-2167`, `_upsert_review_policy_region` `:2170-2200`) at `:516`, which finds the region (the marker regexes tolerate `\r`) and replaces it with an LF-only block, so `updated != text` and `:532-537` reports the difference. Re-rendering would write an LF region inside a CRLF file (mixed endings), and the next checkout can bring the failure back.
- The upsert helpers have two further CRLF hazards beyond the `"\n" + marked` tails: the end-marker pattern `[ \t\r]*(?=\n|\Z)` consumes the `\r` before the final `\n`, so substituting a block that ends at the end marker leaves a bare `\n` after it; and the interior of the registered block is LF, so only converting the tails still leaves LF lines inside a CRLF carrier. The whole replacement must be built with the carrier newline, including the begin-marker line.
- A CRLF `events.jsonl` ledger is rejected before any reprojection runs: `parse_review_event_bytes` (`review_evidence.py:833`) returns "events.jsonl must use LF line endings; CR/CRLF bytes are forbidden" for any `\r`, and `review_policy_upgrade.py:125` calls `read_review_event_ledger` before the reproject step. Decision: this rejection stays intentionally. The ledger is the sole, byte-exact review authority, so tolerating CRLF would let a checkout setting change what is authoritative. The cure for an operator is to keep `events.jsonl` LF (for example `events.jsonl text eol=lf` in `.gitattributes`, or re-checkout that file with LF); this change does not edit the ledger. What this change makes true and testable is that the refusal is explicit, names the file and the LF requirement, and does not mask the wave.md fix (see AC-8).
- Test coverage gap: no test passes CRLF input to `render_review_status_projection` / `render_review_evidence_projection`, to `review_policy_upgrade` reprojection, or to the `core_validators` parity check on a CRLF carrier. There is no dedicated test file for `review_policy_upgrade`. Existing CRLF tests cover per-change lint (`tests/test_docs_lint.py:6598-6640`) and review-policy parsing (`tests/test_review_policy.py:1190-1201`, `:2632-2658`).

## Requirements

1. On the upgrade path, `review_policy_upgrade` reprojection of a wave record must succeed for a wave.md whose line endings are CRLF, and must leave the file's line-ending convention unchanged (no mixed endings after the write).
2. The Review Evidence section matcher in `review_evidence.py` must tolerate a trailing `\r` on the heading line, consistent with the Finding Synthesis matcher. This is defensive; the seam in Requirement 3 is what cures the field failure.
3. The newline seam lives in `review_policy_upgrade`: it reads the wave text, records the original newline with the exact rule "CRLF if any `\r\n` is present, else LF" (`"\r\n" if "\r\n" in original else "\n"`), normalizes to LF once, runs `set_reprepare_marker`, `render_review_evidence_projection` (the Finding Synthesis rebuild) and `render_review_status_projection` on the LF text, and restores the original newline on BOTH byte strings it hands to `WaveMigration` (`marked_text` and `projected_text`). One stray CRLF in an otherwise LF file therefore restores the whole file as CRLF; this is the defined behavior, pinned by a fixture. The three functions themselves are not made newline-aware.
3a. The Prepare publish path in `wf_server/server_impl.py` (`_publish_prepare_policy_state`) is NOT wrapped. It never sees CRLF (universal-newline read) and rewrites a CRLF wave.md as all-LF. This is the recorded behavior (Decision 4), pinned by a test, not a defect fixed here. Reading raw bytes and restoring the newline on that path is out of scope.
4. The review-policy and review-protocol region parity check in `core_validators.py` stays an exact comparison. It reports no difference for a carrier file whose owned region equals the registered block and whose newlines inside the region are consistent with the carrier's convention, and it still reports a difference when the region content differs. The drift claim is limited to endings INSIDE the owned region: a region containing a bare `\n` among CRLF lines (or a `\r\n` among LF lines) differs from the rebuilt region and is reported. Line endings outside the owned region are not examined by the parity check and are out of scope (Decision 5).
5. The upsert helpers (`_upsert_review_protocol_region`, `_upsert_review_policy_region`) build the WHOLE replacement block with the carrier's newline, using the same "CRLF if any `\r\n`" rule: the begin-marker line, the interior of the registered block, the end-marker line, and the `"\n" + marked` tails. When the matched span ended with a `\r` that the end-marker pattern consumed, the replacement re-emits it so no bare `\n` follows the end marker. For a consistent CRLF or LF carrier, `updated == text`, so the parity compare needs no tolerance.
6. LF-checkout behavior is unchanged for every path touched.
6a. The CRLF `events.jsonl` rejection is unchanged. A CRLF wave.md paired with an LF ledger reprojects successfully; a CRLF ledger is refused with the existing explicit message and does not produce a misleading "Review Evidence section" error.
7. The set of raw-byte readers that feed these regexes is derived by rule: every call site that reads wave or carrier text as bytes or with `newline=""` and then applies a `^...$` multiline pattern or a region compare. The implementer enumerates that set from the code and records it in the change doc Progress Log, including the renderer callers named in the Rationale; the sites named above are the confirmed members, not the whole set.

## Scope

**Problem statement:** Review Evidence reprojection and the review-policy parity check assume LF. On a CRLF checkout the upgrade aborts ("exactly one Review Evidence section") and docs-lint reports a false region difference; the render path would otherwise produce mixed endings.

**In scope:**

- `review_evidence.py` Review Evidence regex (`_REVIEW_EVIDENCE_SECTION_RE`); the projection renderers are not made newline-aware, the seam in `review_policy_upgrade` covers them along with `review_policy.set_reprepare_marker`.
- The raw-byte read and the `WaveMigration` byte strings in `review_policy_upgrade.py`.
- The parity compare in `wave_lint_lib/core_validators.py` and the upsert helpers it calls in `render_agent_surfaces.py`.
- New CRLF tests for each of the above, plus the LF-rewrite pin for the Prepare publish path.
- Auditing the other raw-byte readers listed in Requirement 7 and fixing those that are on the same failure path.

**Out of scope:**

- A repository `.gitattributes` policy (an operator decision recorded in the field report, not a framework change).
- Converting existing project files between LF and CRLF.
- Preserving CRLF on the `wf_server/server_impl.py` Prepare publish path (it keeps rewriting to LF; Decision 4).
- Line endings outside the owned region of a carrier file.
- Changing how docs-lint reads records generally (it already uses universal newlines).
- Accepting CRLF in `events.jsonl` (the LF-only ledger contract is kept; the operator cure is recorded in the Rationale).
- The BOM handling in docs-lint (separate change `20b32-bug docs-lint-leading-bom-owner-metadata`).

## Acceptance Criteria

Test locations (existing files, named so the implementer does not invent new ones): reprojection seam and ledger tests in `tests/test_review_policy.py`; matcher and renderer tests in `tests/test_review_evidence.py`; upsert-helper tests in `tests/test_render_agent_surfaces.py`; parity-check tests in `tests/test_docs_lint.py`; the Prepare-path LF pin in `tests/test_server_tools_lifecycle.py`. Every CRLF fixture is built from the canonical producer (the repo's wave template or the renderer helper that creates a wave record), converted with `.replace("\n", "\r\n")`, and written with `write_bytes` (never `write_text`, which translates newlines on Windows).

- [x] AC-1: Reprojecting a CRLF wave.md fixture through `review_policy_upgrade` succeeds with the reprepare marker absent from the input (so `set_reprepare_marker` inserts it). The fixture exercises `set_reprepare_marker`, `render_review_evidence_projection` and `render_review_status_projection`, and BOTH byte strings handed to `WaveMigration` (the observation point: the test captures the `WaveMigration` constructor arguments) satisfy `re.search(rb"(?<!\r)\n", data) is None`. The projected content equals the LF-run output after `.replace(b"\r\n", b"\n")` (new test that fails on the unfixed code and on a mixed-output implementation).
- [x] AC-2: `render_review_status_projection` and the Review Evidence section matcher accept a CRLF-terminated `## Review Evidence` heading and return the same logical content as for the LF equivalent (new test with both inputs; documented as belt-and-braces beside the seam).
- [x] AC-3: For an LF input the projection output is byte-identical to the output before this change. The expected bytes are captured from the current tree BEFORE any code change (first task) and kept as the fixture, so the pin cannot be written after the fact.
- [x] AC-4: The review-policy and review-protocol parity check reports no finding for a consistent CRLF carrier and a consistent LF carrier whose region equals the registered block, reports a finding when one line of the region content differs (one fixture per region, CRLF and LF carriers), and reports a finding for a carrier whose region has mixed endings (new tests; the comparison is exact, no line-ending tolerance).
- [x] AC-5: After an upsert helper rewrites a region in a CRLF carrier, `re.search(rb"(?<!\r)\n", data) is None` holds for the whole file (begin-marker line, interior, end-marker line and tails); for an LF carrier the file contains no `\r`. The owned region is rebuilt with the carrier newline; bytes outside the region are untouched. Under the pinned "CRLF if any" rule, a stray out-of-region CRLF in an otherwise-LF carrier makes the region rebuild as CRLF, so the parity check can report a finding for it; this is accepted and pinned by one stray-CRLF fixture (the finding is expected, and the bytes outside the region stay unchanged). Applying the helper to the helper's own CRLF output changes nothing (new tests, both upsert helpers).
- [x] AC-6: The Progress Log records the enumerated set of raw-byte readers from Requirement 7, each with a file and symbol and a disposition (fixed, or not on the failure path with the reason). The enumeration includes `wf_server/server_impl.py` at about `:8312`, `:10637`, `:11548` and `:25852` and `dashboard_lib.py` at about `:1008`.
- [x] AC-7: The suites `tests/test_review_evidence.py`, `tests/test_review_policy.py`, `tests/test_docs_lint.py`, `tests/test_render_agent_surfaces.py` and `tests/test_server_tools_lifecycle.py`, and every test this change adds, pass; the documents this change authors or edits validate.
- [x] AC-8: A CRLF `events.jsonl` ledger paired with a wave.md is refused with an error containing the substring `events.jsonl must use LF line endings` and not containing `Review Evidence section`, and a CRLF wave.md paired with an LF ledger succeeds (new tests; the CRLF ledger bytes are written with `write_bytes`).
- [x] AC-9: The Prepare publish path (`_publish_prepare_policy_state`) given a CRLF wave.md writes an all-LF file (no `\r`), and given an LF wave.md writes it byte-identically to before this change (new test pinning the recorded behavior).

## Tasks

- [x] Capture the LF projection output bytes from the unmodified tree as the AC-3 fixture before any code change.
- [x] Add failing CRLF tests: reprojection via `review_policy_upgrade` (both `WaveMigration` byte strings), the Review Evidence matcher, projection renderer output endings, the `core_validators` parity check on CRLF and mixed-region carriers, the upsert helpers, and the Prepare-path LF pin (AC-9). Run them against the unfixed tree and record the failures in the Progress Log.
- [x] Update `_REVIEW_EVIDENCE_SECTION_RE` to tolerate `\r`; align with the Finding Synthesis matcher.
- [x] Add the normalize-to-LF / restore-newline seam at the `review_policy_upgrade.py:116-117` read and the `WaveMigration` construction, restoring both byte strings, using the exact rule `"\r\n" if "\r\n" in original else "\n"` (as at `render_agent_surfaces.py:2934` and `:3720`).
- [x] Do not wrap the `wf_server/server_impl.py` (~8083) call; record the LF-rewrite decision in the Decision Log and keep the AC-9 test.
- [x] Make the upsert helpers build the whole replacement (begin marker, interior, end marker, tails) with the carrier newline and re-emit the `\r` the end-marker pattern consumed; keep the parity compare exact (`core_validators.py:507-516`).
- [x] Enumerate raw-byte readers per Requirement 7, fix those on the failure path, and log dispositions.
- [x] Add a one-line CRLF seam row to `docs/architecture/testing-architecture.md` (it currently has only the LF-based review-protocol rows).
- [x] Add tests for the CRLF ledger refusal and the CRLF wave.md plus LF ledger success (AC-8).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| lf-snapshot | implementer | none | AC-3 bytes captured before any code change |
| crlf-tests | implementer | lf-snapshot | Failing tests first for all seams, results logged |
| evidence-matcher-and-renderers | implementer | crlf-tests | `review_evidence.py`, `review_policy_upgrade.py` |
| parity-and-upsert | implementer | crlf-tests | `core_validators.py`, `render_agent_surfaces.py` |
| reader-audit | guru | none | Read-only enumeration for Requirement 7 |


## Serialization Points

Windows (native), macOS, Linux and WSL2 behavior: on macOS and Linux the default checkout is LF and behavior must be unchanged (AC-3, AC-5). On native Windows with `core.autocrlf=true` checkouts are CRLF, which is the failing case this change fixes. On WSL2 behavior depends on the checkout location and git config; both conventions must work. No platform-specific code path is introduced; the fix is newline-agnostic, and every fixture is written with `write_bytes` so tests behave the same on Windows hosts.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/review_policy_upgrade.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/core_validators.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` gets a one-line CRLF seam row (the doc exists and today records only the LF-based review-protocol rows). No other architecture doc changes: the change is confined to text matching and newline handling inside existing modules, with no boundary, flow or contract change.

## AC Priority


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Blocks the upgrade in the field |
| AC-2 | important | Defensive matcher; the seam is the cure |
| AC-3 | required | Guards LF regressions |
| AC-4 | required | Blocks the docs gate in the field |
| AC-5 | important | Prevents mixed endings returning the failure on next checkout |
| AC-6 | important | Bounds the audit for the unverified readers |
| AC-7 | required | Named suites and doc validity |
| AC-8 | required | Pins the ledger decision and the field abort path |
| AC-9 | important | Pins the recorded Prepare-path behavior so it is a decision, not drift |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-10 | Planned from field upgrade report; claims verified by code reading, no CRLF experiment run | Verification agent report, file:line citations in Rationale |
| 2026-10-10 | Product Intent: waived (bug fix, no product scope; default applied by the planning agent, not yet confirmed by the operator) | Readiness review round 2 |
| 2026-10-10 | Round-2 readiness repair: dropped the server_impl wrapper (universal-newline read), added end-marker `\r` and whole-block newline handling, scoped the drift claim to the owned region, named test files and fixture construction | Council round-2 findings |

| 2026-10-10 | Readback: upgrade CRLF records retain one CRLF convention in both WaveMigration payloads; LF output stays byte-identical to the pre-edit capture. A CRLF Review Evidence heading previously aborted and will project normally. Carrier upserts rebuild only owned regions with the selected newline; exact parity, immutable LF-only ledger and Prepare all-LF publication remain unchanged (AC-1–AC-9). Files: review_evidence.py, review_policy_upgrade.py, render_agent_surfaces.py and the five named test files; testing-architecture adds the seam row. | Activated 20b39; captured LF bytes/source identities in temporary preflight state |
| 2026-10-10 | Thought: add canonical-producer CRLF tests and captured LF byte pin first, observe the named defects, then add the reader newline seam and whole-block upsert correction; keep Prepare and parity code unchanged. | Preflight reproduced upgrade error, mixed carrier output and both shared-reader Owner failures |
| 2026-10-10 | Observe: the 11 new tests ran on the unfixed tree: 13 failing subtests and one reprojection error reproduce the intended CRLF defects; LF captured-byte pin, ledger refusal and Prepare LF policy controls already pass. Matcher cannot select CRLF Review Evidence; carrier upserts produce bare LF and false parity findings; stray CRLF does not rebuild the owned region yet. | test_review_policy.ReviewPolicyCRLFUpgradeTests; ReviewEvidenceCRLFHeadingTests; ReviewCarrierCRLFUpsertTests; ReviewCarrierCRLFParityTests; PrepareCRLFPublicationTests; temporary crlf-red.log |
| 2026-10-10 | Observe: all 11 new CRLF/LF tests pass, without skips. The byte pin uses the captured input d7f05c7ba68b26643b402bc21868f03992f87e3a186a5c7d3f24bfd81606f4f6 and expected payload 0df8f3ba63e819d0af68c7d885fe2d2e9f5b14317f92ba39fc52ad240f2f8a0b. Both constructor payloads are CRLF-only; marker insertion, apply write, stray CRLF, owned-region preservation, parity negatives and Prepare LF controls execute. | Named new classes in the five admitted suites; temporary crlf-green.log |
| 2026-10-10 | Reader census: review_policy_upgrade.plan_review_policy_upgrade raw wave bytes fixed by normalize/restore; core_validators._check_marker_family_parity newline-empty carrier read fixed through upserts, exact comparison unchanged; render_agent_surfaces.reconcile_review_protocol_surfaces, _preflight_review_protocol_reconciliation and reconcile_review_policy_surfaces read verbatim via _read_repo_text(translate_newlines=False), fixed through shared upserts. Manifest _repair_change_prompt_manifest/_read_prompt_manifest parse JSON and already restore convention; migrate_review_plan_prompt uses physical-line ending preservation; _council_role_link_plan preserves replacement spans and _confirmed_council_role_pairs tolerates CR on anchored Role, neither on evidence/parity failure path. | Live MCP token census and targeted reads; helpers are the sole owned-region rewrite seams |
| 2026-10-10 | Reader census: server_impl.create_wave (about 8312) produces LF in memory; _publish_prepare_policy_state consumes _read_wave_record_text universal newlines and intentionally publishes all-LF; _project_current_review_status (about 10637) consumes normalized callers; wf_review_event (about 11548) reads original via _read_wave_record_text; wave resource recovery (about 25852) uses _read_repo_text_checked, which normalizes contained bytes. dashboard_lib._review_evidence_dashboard_state (about 1008) consumes list_waves_snapshot read_text universal newlines. lifecycle_gates projection comparison uses _read_wave_record_text; wave_validators check_wave_docs uses read_doc_text/read_record_text; review_evidence.validate_external_review_evidence default read_text normalizes. No additional evidence raw-byte reader needs a source change; read_review_event_ledger raw bytes intentionally remain LF-only authority. | Live symbols and read boundaries; no Prepare wrapper, ledger tolerance or parity normalization |
| 2026-10-10 | Guard mutants: removing CR heading tolerance fails ReviewEvidenceCRLFHeadingTests; deleting upgrade seam fails test_upgrade_preserves_both_crlf_payloads_and_lf_equivalence; restoring LF-only upserts fails ReviewCarrierCRLFUpsertTests; loosening exact parity to newline-normalized equality fails test_mixed_region_endings_and_stray_outside_crlf_report_drift. | Executed temporary in-memory mutants; each ran without skips and failed its named regression |

| 2026-10-10 | Observe: named module checks pass for review_evidence (192), review_policy (111), render_agent_surfaces (165) and server_tools_lifecycle (621; 2 existing skips). All 11 new CRLF methods pass with no skips; docs_lint and final document validation remain pending. | Focused module logs; canonical framework run reserved for parent integration |

| 2026-10-10 | Readback and Thought: integration found the two immutable LF baseline literals lack individual declaration classifications. Add an immediately adjacent reasoned producer/component fixture comment for each token, retaining the pre-edit captured bytes, producer, assertions and declaration scanner unchanged. Verify AST literal hashes against the original capture before and after, then run the named baseline and declaration census tests. | Parent reproduced declaration audit failure; admitted comments-only test repair |

| 2026-10-10 | Observe: named LF baseline and declaration census tests pass after the two adjacent reasoned comments. Both AST byte values are identical before/after and equal the immutable preflight input/marked/projected captures: input d7f05c7ba68b26643b402bc21868f03992f87e3a186a5c7d3f24bfd81606f4f6; expected 0df8f3ba63e819d0af68c7d885fe2d2e9f5b14317f92ba39fc52ad240f2f8a0b. | literal-classification-repair.log: 2 pass; literal-preservation.json; bytes, generator, assertions and scanner unchanged |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-10 | Fix at the readers and the compare (tolerate and preserve newlines), not by normalizing files on disk | Preserves the operator's checkout convention and works whichever way git config changes | A: normalize every file to LF on read and write LF (weakness: rewrites a CRLF checkout to LF, producing diff churn and fighting autocrlf). B: require operators to add a `.gitattributes` `eol=lf` rule (weakness: pushes a framework defect onto every Windows consumer and does not fix already-checked-out files). C (rejected): tolerate `\r` in matchers and teach every renderer to emit the carrier's newline (weakness: leaves each LF-only splicer, such as `set_reprepare_marker`, as a separate place to miss). D (selected): one normalize-to-LF / restore-newline seam in `review_policy_upgrade`, tolerate `\r` in the Review Evidence matcher, make the upsert helpers newline-preserving so parity stays exact |
| 2026-10-10 | Treat the Review Evidence regex and the parity compare as one change | Same root cause and shared test seam; splitting would duplicate the CRLF fixtures | Two separate bug docs (weakness: the CRLF fixtures and the newline helper would be written twice and could diverge, but the fixes touch disjoint modules, so a split would also be safe and is the fallback if review finds the combined diff too large) |
| 2026-10-10 | Keep the LF-only `events.jsonl` contract | The ledger is the byte-exact review authority; tolerating CRLF would let a checkout setting alter it | Accept CRLF in `parse_review_event_bytes` (weakness: weakens the integrity contract and the hash binding) |
| 2026-10-10 | The Prepare publish path in `server_impl.py` keeps rewriting a CRLF wave.md as all-LF, pinned by a test | It reads universal-newline text so the helper never sees CRLF; the result is consistent, not mixed, and raw-byte handling there is a larger change than the field failure needs | Read raw bytes and restore the newline there (weakness: widens the edit surface into the most frequently used mutator for a case no field report showed failing); wrap `set_reprepare_marker` there (weakness: a no-op, since the input is already LF) |
| 2026-10-10 | Drift detection for mixed endings is limited to the owned region | The parity compare already looks only at the region; the upsert helper rebuilds the region with the carrier newline, and bytes outside the region are left untouched. Under the "CRLF if any" rule a stray out-of-region CRLF in an otherwise-LF carrier can still produce a parity finding; that is accepted and pinned by one fixture (AC-5) | Add a whole-file consistency check to the parity compare (weakness: a new finding class that flags files the framework does not own the endings of, and that would fire on every carrier with a stray CRLF) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| "CRLF if any" rebuilds the region as CRLF when an otherwise-LF carrier has one stray out-of-region CRLF, so parity can report a finding (bytes outside the region are untouched) | The rule is defined, the outcome is accepted, and a stray-CRLF fixture in AC-5 pins it |
| Other raw-byte readers on the failure path are missed | Requirement 7 derives the set by rule and AC-6 requires the logged enumeration, including the named renderer callers |
| A region with mixed endings is hidden as clean | The comparison stays exact inside the region and AC-4 pins a mixed-region fixture as drift |
| The wave.md fix lets the upgrade proceed but a CRLF ledger still aborts it | The decision and cure are recorded; AC-8 pins an explicit refusal rather than a misleading error |
| Prepare silently normalizes a CRLF wave.md to LF | Recorded in Decision 4 and pinned by AC-9 so a future change to it is deliberate |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
