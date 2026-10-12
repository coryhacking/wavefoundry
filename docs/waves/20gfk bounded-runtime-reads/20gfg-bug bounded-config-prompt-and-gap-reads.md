# Bound Runtime Configuration, Prompt and Gap Reason Reads

Change ID: `20gfg-bug bounded-config-prompt-and-gap-reads`
Change Status: `implemented`
Owner: Engineering
Status: implementing
Last verified: 2026-10-11
Wave: `20gfk bounded-runtime-reads`

## Rationale

Bound three runtime read paths while preserving ordinary setup values, upgrade preflight compatibility and accounting-gap authority. Setup reads workflow deadlines before its download deadline starts; prompt preflight checks metadata before an unbounded second open; gap diagnostics read and parse unbounded JSON twice. These paths should reject unsuitable carriers promptly and return their established conservative fallback instead of consuming arbitrary bytes, following outside paths or losing a gap barrier.

## Requirements

1. `_setup_deadlines` reads `docs/workflow-config.json` through `contained_files.read_contained_bytes` under the supplied repository root, with an explicit `DEFAULT_MAX_BYTES` cap (currently 8 MiB). Missing, outside, nonregular, oversized, undecodable and malformed carriers return shipped defaults. Retain finite positive numeric coercion, boolean rejection, independent per-key fallback, lock-held caps and `root=None` behavior. This is a read bound before timed work, not a global filesystem deadline.
2. `review_plan_prompt_check` remains independently executable with standard-library imports only. Its incoming zip hook must work with the existing installed runner, including the supported legacy loader, without relying on installed framework modules or extracting a helper first. Preserve classification profiles, newline handling, refusal precedence and recovery messages.
3. Prompt observations use one capped file descriptor read, at most 8 MiB plus one sentinel byte, after verifying a regular lexical entry. Below the trusted repository root, refuse symlink/reparse parent components and final entries; do not resolve a link into an accepted prompt. On POSIX use descriptor-anchored parent walks and `O_NOFOLLOW`/`O_NONBLOCK`, then compare checked and opened identity. Refuse a changed/nonregular target before reading. Always close descriptors. For platforms lacking those facilities, check lexical components and opened identity, reject observable reparse/link states and document the remaining component-swap window. Do not claim an enforced total I/O deadline or native Windows race closure.
4. Prompt read refusal yields conservative observation/classification, never an absent legacy prompt or an unchecked stock profile. Genuine absence retains the existing pass behavior. Oversize and read errors carry only bounded cause/type information, not source content or absolute paths. Keep `observe_prompt` usable by current callers; pass the repository root explicitly where required for lexical containment.
5. Gap diagnostic readers use bounded contained reads under the repository root with a 64 KiB reason-carrier cap. Distinguish genuine absence from an observed present carrier whose read fails; an unreadable, oversized, undecodable, nonobject or deeply nested marker retains the named unreadable-gap result. Empty markers retain the named empty result and valid `{}` retains the established empty record behavior. Handle `RecursionError` and `MemoryError` during decode, parse and value normalization without leaking exceptions or granting healthy accounting authority. Poison-preservation claims apply to the existing live-marker authority; redesigning separate path-presence checks is outside this change.
6. Avoid reopening a live marker solely to extract its reason. Preserve normal structured reason fields and `_read_reason_file`'s first-record diagnostic use for explicit clear. Bound both the live marker and `.clearing` reader. No diagnostic reader clears, removes, creates or rewrites a marker/store; explicit `clear_accounting_gap` remains the sole existing clear operation and still marks affected waves before healthy publication can resume.
7. Tests exercise real bounded readers and upgrade dispatch, not only mocked returned values. Change-local tests must distinguish the fixed implementation from representative removed-bound, followed-link, changed-identity and parser-exception regressions. Any temporary known-bad variant runs in a disposable directory and is removed; no permanent evidence folder or mutation framework is added.

## Scope

**Problem statement:** Runtime deadline configuration, incoming prompt observation and accounting-gap reason diagnostics lack complete byte/type/path bounds and conservative malformed-input handling.

**In scope:** The three named reader modules; focused setup/download, upgrade-preflight and accounting-gap tests; a short architecture boundary note for the standalone prompt observer and bounded diagnostics.

**Out of scope:** Shared `contained_files` semantics or general reader redesign; other workflow-config consumers; prompt migration/write logic; upgrade protocol or minimum runner changes; model downloads or timeout algorithms; accounting-gap transaction semantics; packaging/release/live upgrades; native Windows qualification; unrelated source/config/generated surfaces. Canonical source is `.wavefoundry/framework/scripts/`; `docs/` records describe this repository's operation. Do not patch generated host surfaces to implement runtime behavior.

## Acceptance Criteria

- [x] AC-1: Setup deadline resolution honors valid values and existing caps while bounded malformed, oversized, outside-root and nonregular carriers return defaults without blocking on a FIFO; focused reader and timed-download-path tests prove the outcome.
- [x] AC-2: Prompt preflight reads bounded regular descriptors, refuses parent/final links, oversized carriers and changed identities, and retains all stock/customized/absent/newline classifications; real filesystem and deterministic swap tests provide the oracle.
- [x] AC-3: The standalone checker passes restricted standard-library import execution and the real legacy incoming-zip loader/hook fixture, refusing an unsuitable legacy carrier before mutation without consulting an installed helper.
- [x] AC-4: Bounded malformed gap markers, parser recursion/resource exceptions and normalization failures return conservative diagnostics, preserve the live marker and prevent healthy publication; focused health/accounting integration tests prove poison remains until explicit clear.
- [x] AC-5: Valid gap reasons and empty markers retain established results; explicit clear with unreadable bounded reasons still preserves affected-wave accounting-gap status and concurrent new-marker protection; existing and added change-local tests prove these outcomes.
- [x] AC-6: Every test added by this change and its focused owning suites pass; the documents it edits validate; temporary negative controls demonstrate guard sensitivity and leave no tracked artifacts or unrelated writes.

## Tasks

- [x] Implement bounded setup deadline read with unchanged value/default policy.
- [x] Implement the standalone prompt observer's bounded descriptor and lexical-parent checks; preserve supported platform fallback and classification compatibility.
- [x] Implement bounded, conservative single-read gap reason decoding and update explicit-clear reason calls without changing clear authority.
- [x] Add focused filesystem, parser-failure, integration and legacy-hook regression coverage; run representative temporary negative controls.
- [x] Update the architecture boundary note and record focused test/negative-control evidence in this document.
- [x] Complete required review lanes, change-local documentation validation and coordinator-owned framework qualification; hand off and pause without commit or wave closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Reader implementation | implementer | readiness and activation | Sole writer of declared source/test paths |
| Verification | qa | reader implementation | Exercise conservative outcome and real dispatch; read-only review |
| Delivery review | code-reviewer, security-reviewer, architecture-reviewer | verification | Read-only reviews; coordinator records typed findings |

## Serialization Points

The incoming hook ABI and accounting-gap authority are review boundaries. Readers and their tests are owned together. The coordinator owns wave activation, review records and repository-wide test receipt; reviewers do not write source. `contained_files.py`, incoming hook loaders, prompt migration, generated surfaces and unrelated waves are protected unless a specific scope amendment is reviewed before editing.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/review_plan_prompt_check.py`
- `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_model_download_deadline.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `docs/architecture/cross-cutting-concerns.md`

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md`: document explicit runtime read caps, conservative malformed gap diagnostics and the checker-specific standalone import boundary with platform limits. Ownership, upgrade protocol, accounting transactions and shared containment policy stay as currently documented; no ADR is needed.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The config read precedes the download guard. |
| AC-2 | required | Prompt observation must bound bytes and reject unsafe carriers. |
| AC-3 | required | Incoming preflight cannot require a newer installed framework. |
| AC-4 | required | Malformed diagnostics must preserve accounting poison. |
| AC-5 | required | Compatibility includes explicit clear authority and existing markers. |
| AC-6 | required | Change-local evidence must detect removed guards and remain contained. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-11 | Drafted from MCP-first orientation and current-file validation; source edits await readiness and activation. | `_setup_deadlines` at setup_index.py:2490; `observe_prompt` at review_plan_prompt_check.py:154; `read_gap_reason` at context_efficiency.py:1185; `_read_reason_file` at :3603; legacy-loader/import tests in test_upgrade_wavefoundry.py:3692-3779. |
| 2026-10-11 | Readback: bound setup config and standalone prompt observations to 8 MiB and gap reasons to 64 KiB; preserve setup defaults, prompt classifications/old-loader ABI and explicit-clear accounting authority. A stock prompt behind a linked parent currently passes; afterward it refuses without mutation. AC-1–AC-6 cover the three reader modules, five owning test files and architecture note; shared containment, loaders, timeout algorithms and gap transactions stay outside scope. | Current-file MCP validation and pre-implementation memory brief; readiness and implementation activation confirmed by coordinator. Real filesystem, legacy hook, health/publication/clear controls and disposable guard mutants will verify the change. |
| 2026-10-11 | Reader implementation and architecture note are in place. Config/prompt use 8 MiB bounds; live/clearing gap reasons use 64 KiB. Initial focused checks passed 18 setup-reader/prompt-preflight tests and six gap tests; model and server owning suites passed 21 and 115 tests. The first owning run was interrupted after existing uv-bootstrap tests hit sandbox EPERM creating temporary files in the tool environment; it established no complete owning-suite result or receipt. | Tool-venv `python -B -m unittest` selected reader/preflight/gap classes; canonical `run_tests.py --file` selected five owning files. Corrected an assumed deep-JSON recursion oracle: Python 3.14 accepts valid deep objects within the byte cap; only actual decode/parse/normalization failures are refused, with explicit resource-exception injection and a real oversized deep carrier. Native Windows execution remains unqualified. |
| 2026-10-11 | Six disposable known-bad variants were rejected by named tests; scratch module variants were removed without altering live source. | `setup-bound-removed` → `SetupPhase1DeadlineTests.test_setup_deadlines_bounded_real_carriers_return_defaults`; `prompt-bound-loosened` → `ReviewPlanPreflightTests.test_checker_cap_edges_and_one_descriptor_observation`; `prompt-parent-followed` → `.test_checker_lexical_parent_links_and_missing_parents`; `prompt-identity-removed` → `.test_checker_changed_regular_identity_refuses_before_read`; `gap-bound-loosened` → `BoundedGapReasonTests.test_real_malformed_carriers_keep_poison_without_writes`; `gap-resource-catch-removed` → `.test_decode_parse_and_normalization_resource_errors_are_conservative`. Each ran one selected test with zero skips and failed at the intended refusal/resource boundary. |
| 2026-10-11 | Focused implementation evidence: all five owning files passed per worker (1,202 tests total); the selected three-file canonical command returned exit 1 because authorized concurrent edits changed the prompt source/test and this change document. No canonical green or receipt is claimed. Final prompt controls passed after replacing buffered read-ahead with an `os.read` loop bounded to 8 MiB plus one byte; its cap and identity mutants were rerun and detected. AC-6 and final review/qualification task remain pending coordinator-owned quiet combined qualification. | `env -u PYTHONPYCACHEPREFIX PYTHONDONTWRITEBYTECODE=1 WAVEFOUNDRY_DISABLE_RERANKER=1 WAVEFOUNDRY_EMBED_PROVIDER=cpu python3 -B .wavefoundry/framework/scripts/run_tests.py --file test_setup_index.py --file test_upgrade_wavefoundry.py --file test_context_efficiency.py`: setup 202, upgrade 760, context 104; two existing native-Windows junction skips. Earlier five-file command: model 21 and server 115 passed. Final tool-venv `python -B -m unittest test_upgrade_wavefoundry.ReviewPlanPreflightTests`: 16 passed, zero skips. `wf_validate_docs` passed; final coordinator validation follows completed tracking. |
| 2026-10-11 | Exact existing skip identities confirmed by selected verbose execution; no added test skipped on this macOS host. | `test_upgrade_wavefoundry.JournalDeclarationMigrationTests.test_helper_junction_is_refused_on_windows`: `directory junctions exist only on native Windows`; `test_upgrade_wavefoundry.RetiredModelCleanupTests.test_native_windows_junction_root_and_nested_cleanup_preserve_referent`: `native Windows junction cleanup qualification; simulated metadata runs on every host`. Selected run: two tests, two expected skips, exit 0. |

| 2026-10-12 | Delivery repair `DEL-PER-KEY-OVERFLOW`: isolate `OverflowError` within each deadline key so an uncoercible positive integer retains only its own default and later valid overrides still apply. This satisfies unchanged Requirement 1; accepted values, lock-held caps, read bounds and timeout algorithms are unchanged. Readback: real config with first deadline `10**400` and later model deadline `7` previously returned `1800` for the latter; it now returns `7`. Only setup reader and its focused test changed. | Finding and cycle-1 repair start recorded before edits. New `SetupPhase1DeadlineTests.test_setup_deadlines_numeric_overflow_is_isolated_per_key` failed six subtests before the fix and passes afterward; all keys and boolean/nonfinite neighbors exercised. Eight selected setup tests and 21 model-download tests passed in separate interpreters, zero skips. A combined ad hoc interpreter run mixed the setup loader and model module identities and failed; isolated owning-file execution is the canonical runner model. Prior combined qualification passed 12,401 tests/185 files/12 existing skips in 769.123s, source hash `d1371cdf92a0ffc91d8ba4b7d24ebac6d6ba22cd4da16acb4876734112fbec8b`; this behavioral repair requires a fresh final receipt. Focused independent code/QA replay and council synthesis remain pending. |

| 2026-10-12 | Final implementation and required independent delivery review completed; all admitted ACs are supported. Paused for operator closure. See `wave.md` Review Checkpoints for consolidated findings, limits, source identity and reviewer roster. | Canonical final qualification: 12,402 tests / 185 files / 12 unchanged existing skips, 798.065 seconds, exit 0; matching receipt `d1ab96d12d77d992c99b700656f18ac2044068c89188efa82e531f416816d5ce`. Exact report worker/skip comparison and all reviewed source fingerprints verified. Full documentation validation passed with zero errors and warnings. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-11 | Reuse shared bounded containment for setup/gap reads; keep a small standard-library descriptor observer in the standalone checker. | Setup already reaches `contained_files` through its bootstrap-safe prefix reader; the incoming checker is deliberately loaded independently and restricted-import tested. | Import `contained_files` unconditionally into the checker: breaks the existing incoming-hook/import boundary. Extend old loaders to supply incoming dependencies: widens protocol/upgrade scope. |
| 2026-10-11 | Bound bytes and verify descriptor/type/path before parsing; preserve established conservative fallbacks. | This directly addresses reads before timed work and diagnostics that must not clear authority. | Add subprocess deadlines to every reader: introduces process/ABI complexity and still requires safe carrier handling. Add only pre-read size checks: permits replacement/growth and second-open regressions. |
| 2026-10-11 | Use 8 MiB shared/default config and prompt bounds, 64 KiB gap reasons; do not make caps repository-controlled. | Prompt/config limits follow the existing document bound; gap reasons are small fixed diagnostic records. | Configurable caps: a malformed carrier would control its own resource bound. Broad new JSON depth scanner: unnecessary when bounded parsing failures can return existing conservative results. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Hook accidentally imports installed or incoming framework helpers. | Restricted import process plus actual legacy zip hook exercise the boundary. |
| A check/open swap becomes a link or FIFO and blocks or accepts outside bytes. | POSIX anchored no-follow/nonblocking descriptors, identity/type check and child-timeout filesystem tests; Windows limitations stated explicitly. |
| Malformed gap reason becomes absence/healthy accounting. | Distinguish genuine missing carrier; assert live poison and publication outcome, including parser/normalization failures. |
| Test fixtures mutate unrelated repository state or shared wave evidence. | All filesystem cases use disposable roots; owning-suite evidence is recorded before coordinator qualification. |

## Session Handoff

See `docs/agents/session-handoff.md` for coordinator-owned session state. This change is planned only; no code edit, commit, closure or live upgrade is authorized by this record alone.
