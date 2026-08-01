# server_runner_version Cannot Distinguish a Stale Runner From a Current One

Change ID: `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-31
Wave: `1u2b0 host-surface-hardening`

## Rationale

`SERVER_RUNNER_VERSION` is hardcoded to `"1"` in `server.py:36` (canonical, with a re-exported
alias at `server_impl.py:23317`) and has never been bumped, including across the 1.15.0
protocol-bridge release that replaced the runner file. Under the hot-reload design the runner
process stays loaded while `server_impl` reloads, and `server_runner_version` in `wf_server_info`
exists precisely to tell an operator or agent that the long-lived runner process is stale relative
to disk and a full host restart is needed. With the constant frozen at `"1"`, a pre-1.15 runner and
a current one report identically, so the field carries no signal.

Field-observed twice: an earlier unfiled finding noted the constant never bumps, and the 2026-07-31
1.14.0 to 1.15.0 bridge upgrade in a target repository reported `server_runner_version: "1"` after
a full restart onto the new runner, indistinguishable from the pre-restart value. Note this field
is distinct from the upgrade protocol (`upgrade_bridge_bootstrap.PROTOCOL = 2`), which versions the
upgrade boundary, not the MCP runner.

Council-verified mechanics (prepare-phase red-team, 2026-07-31): `wf_reload_mcp` reloads only
`server_impl` and evicts `wave_lint_lib*` (`server.py:258-266`); `server.py` itself is never
reloaded and re-propagates the runner identity on reload (`server.py:267`, `:385`), so
capture-at-launch survives in-process reloads structurally. The un-reloadable runner set is larger
than `server.py`: `venv_bootstrap` executes at process start (`server.py:22-24`) and is never
evicted either.

## Requirements

1. `wf_server_info` exposes a runner identity that changes whenever the on-disk runner changes,
   captured at process launch, so a running-but-stale runner is detectable by comparing the
   reported value against the current disk state. The identity covers the un-reloadable runner
   set: `server.py` AND `venv_bootstrap.py` (both execute at launch and neither is reloaded); if
   implementation narrows this set, the change doc must say why.
2. The mechanism must not depend on a human remembering to bump a constant. (Council note: the
   "GRAPH_BUILDER_VERSION bump-guard test" pattern does NOT exist as a test today; that constant is
   enforced by prose plus after-bump behavior tests only, so a manual-constant option would be
   inventing a guard mechanism, not copying one.)
3. In-process `wf_reload_mcp` must not change the reported runner identity (the runner is exactly
   the part a reload does not replace); only a real process restart may change it.
4. Staleness is legible, not just different: when the runner-at-launch identity differs from the
   current on-disk runner, `wf_server_info` surfaces an explicit stale indication naming the
   full-restart recovery. In the self-hosting repo, an uncommitted runner edit truthfully reports
   stale; the indication text must read sensibly in that benign case (development edit vs upgrade).
5. Fail-safe comparison semantics: if the disk side is unreadable or torn (mid-upgrade copy,
   Windows file locks, deleted-then-recreated file), the comparison degrades to explicit unknowns
   (disk hash null, `runner_stale` null) and never raises; `wf_server_info` is exactly the tool
   operators reach for mid-upgrade. A spurious stale from a torn read is acceptable (restart is the
   safe recovery); an exception is not.
6. Path identity: capture the unresolved launch path and re-resolve at query time, so a symlinked
   install whose target is swapped by an upgrade is still detected. The exec-vs-read launch race
   (upgrade replaces the file between process exec and the launch hash read) is documented as an
   accepted milliseconds-wide window, not engineered around. Bytecode caching is a non-issue
   (`sys.dont_write_bytecode = True` at `server.py:14`).
7. Alias and no-runner plumbing: the frozen alias at `server_impl.py:23317` is removed or derived
   (never left as a silently-diverging literal behind `server.py`'s module `__getattr__` fallback
   at `server.py:48-50`), and a standalone `server_impl` import with no runner process reports an
   explicit null identity, not a fake one (the `_runner_version` empty-string default path at
   `server_impl.py:23339` and the `server_identity` fallback).

## Scope

**Problem statement:** the runner-version field meant to signal "restart required, your runner is
stale" is a frozen constant, so it can never fire.

**In scope:**

- `.wavefoundry/framework/scripts/server.py` (identity capture at launch)
- `.wavefoundry/framework/scripts/server_impl.py` (`wf_server_info` reporting, the re-exported
  alias, the no-runner default path)
- Tests in `test_server_tools.py` pinning the current behavior, including the hardcoded `"1"`
  fixture pins at `:23920` and `:23994`
- Docs companions: `docs/specs/mcp-tool-surface.md` gains the `wf_server_info` field documentation
  (the spec currently does not document the tool at all, yet `docs/architecture/current-state.md:128`
  names it the governing MCP contract), and seed-160's restart guidance gains a stale-runner
  detection pointer (seed edit under the `seed_edit_allowed` gate; rendered upgrade prompt
  reconciled to match)

**Out of scope:**

- The upgrade protocol constant (`upgrade_bridge_bootstrap.PROTOCOL`) and bridge selection logic
- Any host-side reconnect automation
- The historical hot-reload wave archive (`docs/waves/12rbc .../12rb9-enh mcp-impl-hot-reload.md`)
  stays untouched per the preservation policy

## Design Options (decide at Prepare)

1. **Derive at launch from content (recommended, council-confirmed feasible):** runner records a
   short hash of the un-reloadable runner set's bytes at process start; `wf_server_info` compares
   against the current on-disk hashes and reports both plus a `runner_stale` tri-state
   (true/false/null-unknown). No manual bumping.
2. **Derive from framework VERSION at launch:** simpler to read, but misses runner changes within a
   version during development and reports staleness even when the runner files did not change.
3. **Manual constant plus bump-guard test:** requires inventing the guard mechanism (no existing
   precedent test to copy); weakest option.

## Acceptance Criteria

- [x] AC-1: After replacing `server.py` (or `venv_bootstrap.py`) on disk while a runner process
  launched from the old bytes is still serving, `wf_server_info` reports a stale-runner indication
  naming the full-restart recovery. (Test shape: fresh-subprocess MCP probe per the wave-1t3gt
  tools/list precedent, or injection of the captured identity; name the choice in the
  implementation.) Chosen shape: injection of the captured identity (`RunnerIdentityTests` in
  `test_server_tools.py` injects the launch state over temp copies of the real runner files via
  `set_server_runner_version`, then mutates the copies on disk).
- [x] AC-2: An in-process `wf_reload_mcp` does not change the reported runner identity; a fresh
  process launch from the new bytes reports current, with no stale indication.
- [x] AC-3: With the disk side unreadable or missing, `wf_server_info` returns explicit null
  unknowns and does not raise.
- [x] AC-4: A standalone `server_impl` context with no runner process reports a null runner
  identity, and no code path can silently serve the retired literal `"1"` (alias removed or
  derived; `__getattr__` fallback covered by test).
- [x] AC-5: Existing `wf_server_info` consumers are updated coherently, including the hardcoded
  fixture pins; `docs/specs/mcp-tool-surface.md` documents the new field semantics and seed-160
  carries the restart-guidance pointer; docs-lint passes; full framework suite passes.

## Tasks

- [x] Decide the identity mechanism at Prepare (options above; option 1 recommended)
- [x] Implement capture-at-launch over the un-reloadable runner set and comparison reporting in
  `wf_server_info` with tri-state staleness
- [x] Update or replace the tests pinning the frozen constant (module-attribute pins and hardcoded
  fixture pins)
- [x] Add the docs companions (mcp-tool-surface.md field docs; seed-160 restart-guidance pointer
  under the seed gate; rendered upgrade prompt reconciled by hand to match the seed wording)
- [x] Run the full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                              |
| ---------- | ----------- | ---------- | ---------------------------------- |
| fix        | implementer | —          | Small, two files plus their tests |
| docs       | implementer | fix        | Spec field docs + seed pointer     |


## Serialization Points

- `server.py` / `server_impl.py` (single coordinated edit); seed edit under `seed_edit_allowed`

## Affected Architecture Docs

N/A (resolved at Prepare, council-verified): no `docs/architecture/` doc describes the hot-reload
runner/impl split or the runner-version contract; that material lives only in the closed wave
archive for `12rbc mcp-impl-hot-reload`, which is historical and preserved as-is. The governing
public contract update happens in `docs/specs/mcp-tool-surface.md` (in scope).

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect: the staleness signal can never fire |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-31 | Implemented capture-at-launch runner identity (Design Option 1): `server.py` captures `SERVER_RUNNER_FILES` (unresolved launch paths of `server.py` + `venv_bootstrap.py`) and derives `SERVER_RUNNER_VERSION` from `server_impl.compute_runner_identity` (first 12 sha256 hex over both files' bytes in fixed order); `set_server_runner_version` extended with `runner_files`; `version_payload` reports `server_runner_version` (launch), `runner_disk_identity`, tri-state `runner_stale`, and `runner_stale_detail` + a `runner_stale` diagnostic on stale; frozen `server_impl` alias removed; `server_identity` now always emits the version block so a standalone impl reports explicit nulls | `server.py:38-62,276,329,394-407`; `server_impl.py:23317-23343` (compute), `:24856-24923` (setter/detail/payload), `:3305-3309`, `:25120-25133` |
| 2026-07-31 | Tests: new `RunnerIdentityTests` (9 tests: AC-1 stale via injected identity over temp copies for both runner files, AC-2 fresh-launch-current, AC-3 nulls on unreadable disk, AC-4 standalone nulls + retired-literal absence, pre-hash `"1"` compares null, set coverage); updated `test_wf_server_info_returns_repo_identity`, reload version test, and both hardcoded `"1"` fixture pins | `test_server_tools.py` `RunnerIdentityTests`; targeted runs: RunnerIdentityTests + WaveMcpReloadTests + GuidedContractTests = 35 OK; WaveUpgradeMcpToolTests = 43 OK |
| 2026-07-31 | Docs companions: `wf_server_info` Tool Detail entry added to `docs/specs/mcp-tool-surface.md` (Framework Operations) with tri-state semantics; seed-160 restart-exception paragraph now names both runner files and the `runner_stale` check (edited under `seed_edit_allowed` gate, closed immediately after); rendered `docs/prompts/upgrade-wavefoundry.prompt.md` reconciled (step 5 tool list + step 6 reload wording); docs-lint ok via `wf_validate_docs` | `mcp-tool-surface.md:774-800`; seed-160 step 12 exception paragraph; upgrade prompt steps 5-6 |
| 2026-07-31 | Delivery-review docs repair pass (docs P3s + finding F10): the `wf_server_info` spec entry now states the REAL path-resolution guarantee instead of a flat symlink-swap-detection claim (only `server.py`'s launch path is stored unresolved; the `venv_bootstrap` path comes back directory-resolved through the resolved `sys.path` entry, so a swap that leaves either recorded path unreadable degrades `runner_stale` to `null`, not `true`, and after an upgrade `null` carries the same action as `true`), and documents the `"unavailable"` launch sentinel a torn mid-upgrade tree injects so a reader can explain an observed value. Front-matter `Status` aligned to `implemented` (it read `active` against `Change Status: implemented`). CHANGELOG `[1.15.0]` **Fixed** bullet added for the tri-state runner-staleness field | `docs/specs/mcp-tool-surface.md` `wf_server_info` runner-staleness bullet; this change doc line 6; `CHANGELOG.md` `[1.15.0]` Fixed; `wf_validate_docs` pass |
| 2026-07-31 | Full-suite verification: the implementer's first run FAILED (2 failures in test_context_efficiency.py, 6582 tests) while the main session was concurrently writing ledger approvals through the live MCP server; the file passes 53/53 in isolation, 1596 OK paired with test_server_tools, and a quiet full rerun is green. Recorded as a concurrency flake correlated with live MCP store writes, not a 1u2ay regression; watch for recurrence | full rerun: Ran 6582 tests across 61 files, OK (scratchpad full-suite-1u2ay.log); failed-run tail retained in task output |
| 2026-07-31 | Reverification cycle 2, repair pass. `runner-identity-helper-guards-only-typeerror`: `_record_runner_identity` documents that it NEVER raises and two callers depend on it, but the first setter call caught only `TypeError`, so a setter raising `ValueError` / `OSError` / `AttributeError` escaped, and at the reload site (which calls this AFTER closing the pre-reload handler) that leaves the CLOSED handler installed in a live process. The first call now catches `Exception` and branches on `TypeError` for the single-argument fallback; the degradation-string return contract is unchanged, and the docstring states why the broad catch is required | `server.py:73-116` (`_record_runner_identity`). Tests: `RunnerIdentitySetterCompatibilityTests::test_non_typeerror_setter_failure_degrades_instead_of_raising` (ValueError / OSError / AttributeError subtests: no raise, reason string names the type) and `::test_reload_survives_a_non_typeerror_setter_and_keeps_handler_usable` (reload completes, `runner_identity_unrecorded` diagnostic present, live handler is not the closed one and a second reload succeeds). Mutation-checked: restoring the `TypeError`-only catch fails exactly these two and no others (6 tests, 4 errors) |


## Decision Log


| Date       | Decision                        | Reason                                        | Alternatives     |
| ---------- | ------------------------------- | --------------------------------------------- | ---------------- |
| 2026-07-31 | Filed from field observation    | Twice-observed; the field is currently inert  | Leave unfiled    |
| 2026-07-31 | Hash the un-reloadable runner SET, tri-state staleness, null-safe reads | Council: venv_bootstrap is equally restart-required and invisible to a server.py-only hash; wf_server_info is used mid-upgrade so torn reads must degrade, never raise | server.py-only hash (rejected: under-covers); manual constant plus guard test (weakest: no existing guard mechanism to copy) |
| 2026-07-31 | AC-1 test shape: injection of the captured identity (the allowed alternative), not a fresh-subprocess MCP probe | The comparison seam is exactly the (identity, runner_files) pair `server.py` records at launch; injecting it over temp copies of the real runner files exercises the same code path deterministically and lets both stale directions and both files be covered without subprocess flake | Fresh-subprocess tools/list probe (slower, adds mcp-package dependency to the new tests; reload-invariance is still covered by the existing subprocess-free `perform_mcp_reload` test) |
| 2026-07-31 | Hash implementation lives once in `server_impl.compute_runner_identity`; `server.py` calls it at launch | One canonical algorithm, no duplicated hashing that could silently diverge; server.py imports server_impl before the capture so ordering is safe. If a future wave changed the algorithm, the runner file ships alongside, so the resulting stale=true is truthful; an impl-only algorithm edit in a dev checkout yields an acceptable spurious stale (restart is the safe recovery, per req 5) | Duplicate hash code in both files (divergence risk); passing the runner's hash function as a callable (more plumbing for the same outcome) |
| 2026-07-31 | Launch-identity capture failure falls back to the sentinel `"unavailable"`; comparisons require a 12-hex launch identity | The version field stays a string for the existing plumbing shape, while non-hash identities (the sentinel, or a pre-hash runner's frozen `"1"`) degrade the comparison to null instead of a false stale | Nullable SERVER_RUNNER_VERSION in server.py (breaks the `set_server_runner_version(str)` shape); comparing raw strings (an old runner's `"1"` vs a disk hash would report a meaningless stale=true against an unknowable launch state) |
| 2026-07-31 | Rendered upgrade prompt reconciled by hand rather than re-rendered | The project-local `docs/prompts/upgrade-wavefoundry.prompt.md` is an upgrade-reconciled surface, not a verbatim script render in this repo's flow; hand-reconciling the two restart-wording sites matches prior waves' practice | Running a renderer (no renderer produces this file verbatim from seed-160) |


## Risks


| Risk                                                        | Mitigation                                                    |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| Hash-at-launch reads disk state that changes mid-upgrade    | Capture once at process start; query-time comparison is read-only, tri-state, and never raises |
| Self-host development edits report stale constantly         | Truthful by design; indication text reads sensibly for the development case (req 4) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
