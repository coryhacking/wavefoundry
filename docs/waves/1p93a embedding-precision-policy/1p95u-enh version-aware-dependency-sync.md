# Version-aware dependency sync: upgrade/setup installs pinned version bumps, not just missing packages

Change ID: `1p95u-enh version-aware-dependency-sync`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-30
Wave: `1p93a embedding-precision-policy`

## Rationale

`1p95j` pinned `lancedb==0.33.0` (via `setup_index.LANCEDB_REQUIREMENT`), but the pin does **not**
reach existing installs. The dependency check `setup_index._missing_in_venv` is **presence-only** — it
maps each pip spec to its import name and flags a dependency only when `importlib.util.find_spec(name)
is None` (`setup_index.py:214`). A machine that already imports `lancedb` 0.30.2 is never flagged, so
neither `wf setup` nor `wave_upgrade` moves it to 0.33.0. The pin only bites on a fresh install
(package absent) or the indexer auto-install path — existing installs silently stay on the old
version.

**The upgrade already runs the setup dependency-ensure.** `setup_index.main` calls `ensure_deps()` on
every invocation before indexing (`setup_index.py:1425`), and `wave_upgrade` phase 4 invokes
`setup_index.py` three times — docs (`--root`), `--graph-only`, and `--background-code`
(`upgrade_wavefoundry.py:1352–1395`). So the *only* thing standing between an upgrade and an
up-to-date dependency set is that `_missing_in_venv` ignores version. Making the check **version-aware**
makes every pinned bump propagate automatically on the next `wf setup` **and** on `wave_upgrade` —
**with no new upgrade wiring** (the `ensure_deps` chokepoint is already on the upgrade path).

**Operator goal (2026-06-30):** *"setup during upgrade should make sure that everything is ready and
up to date — new models and dependencies downloaded, installed, and ready to go."* This change
delivers the dependency half. The **model** half is an **audit-and-confirm, not new work**:
`setup_index.main` already calls `prewarm_models(...)` (`setup_index.py:1468`), which downloads/verifies
`DOCS_MODEL`, `CODE_MODEL`, and `RERANKER_MODEL` on every non-graph-only setup invocation — so model
freshness already materializes during `wave_upgrade` phase 4. AC-6 records this audit; no model-download
code is added unless the audit surfaces a real gap.

## Requirements

1. `_missing_in_venv` must flag a dependency for (re)install when the version installed in the tool
   venv **violates** the pinned specifier in `REQUIRED_IMPORTS`/`_planned_required_imports()` — not
   only when the package is absent. Version comparison uses `packaging` (`Requirement` → `SpecifierSet`),
   comparing `importlib.metadata.version(dist_name)` against the spec.
2. Dependencies with **no** version constraint (e.g. `numpy`, `mcp[cli]`, `fastembed`) keep exactly
   today's presence-only behavior — an installed-but-unpinned package is never flagged (no churn).
3. **Graceful degradation, never a regression:** if `packaging` is not importable in the venv, or a
   spec/installed-version cannot be parsed, that dependency falls back to presence-only. The probe must
   never raise or spuriously reinstall on a parse failure. A satisfied pinned dep is never flagged.
4. `_install_deps` must install the **pinned spec** (the `REQUIRED_IMPORTS` key, e.g. `lancedb==0.33.0`)
   so pip resolves an already-installed violating version up/down to the pinned one. (It already passes
   the dist keys; this change confirms the version-violating dep's full spec — not a bare name — reaches
   the pip/uv command.)
5. Propagation on upgrade requires **no** edit to `upgrade_wavefoundry.py`: because phase 4 already
   calls `setup_index.main → ensure_deps`, the version-aware `_missing_in_venv` fires there
   automatically. A test locks in `ensure_deps` as the shared chokepoint so a future refactor can't
   silently drop the version check off the upgrade path.
6. **Audit (no new code unless a gap is found):** confirm model freshness on upgrade is already covered
   by `prewarm_models` in `setup_index.main`, which runs during phase 4. Record the audit result in the
   change; add model-download work only if the audit finds a real gap.

## Scope

**Problem statement:** pinned dependency version bumps do not propagate to existing installs because
the venv dependency check is presence-only; a version bump (like `1p95j`'s `lancedb==0.33.0`) is
installed only on fresh installs, so `wf setup` / `wave_upgrade` leave existing installs on the old
version.

**In scope:**

- `setup_index.py`: make `_missing_in_venv` version-aware (parse each required spec, compare the
  installed version against its specifier, flag violations), with a presence-only fallback for
  unpinned specs and for `packaging`-absent / unparseable cases. The existing CUDA-dist
  `importlib.metadata.version` branch (`setup_index.py:215–219`) folds into the same version-aware pass.
- `tests/test_setup_index.py`: satisfied-pin (not flagged), violated-pin (flagged), unpinned
  (presence-only), unparseable-spec / `packaging`-absent (presence-only fallback, no raise),
  real-`REQUIRED_IMPORTS`-no-churn (installed range specs like `tree-sitter>=0.24,<0.26` when satisfied
  are not flagged), install-carries-pinned-spec, and the `main → ensure_deps` chokepoint assertion.
- Audit note (AC-6): `prewarm_models` already covers model freshness on upgrade.

**Out of scope:**

- Changing **what** is pinned (the pins live in `REQUIRED_IMPORTS`; this change only makes existing
  pins enforceable). Changing the lancedb pin value.
- Adding `packaging` as a **hard** dependency — the fallback keeps it optional (it is a near-universal
  transitive dep, but this change must not require it).
- A background/scheduled dependency updater or a new `wave_upgrade` phase — propagation rides the
  existing `ensure_deps` call on the upgrade path.
- Model-download behavior changes (already covered by `prewarm_models`; AC-6 audits, does not rebuild).
- Editing `upgrade_wavefoundry.py` (no new wiring needed).

## Acceptance Criteria

- [x] AC-1: `_missing_in_venv` flags a pinned dependency whose installed version violates its
      specifier, and does **not** flag one whose installed version satisfies it. Evidence:
      `test_setup_index.py::VersionAwareDependencyTests.test_violated_exact_pin_flagged`,
      `test_satisfied_exact_pin_not_flagged`.
- [x] AC-2: unpinned dependencies retain presence-only behavior — an installed unpinned package is
      never flagged; an absent one still is. Evidence: `test_unpinned_present_not_flagged`,
      `test_unpinned_absent_flagged`, `test_satisfied_range_pin_not_flagged`.
- [x] AC-3: graceful fallback — when `packaging` is unavailable or a spec/version cannot be parsed, the
      dependency falls back to presence-only and the probe never raises or spuriously reinstalls; a
      probe-subprocess failure degrades to reinstall-all rather than raising. Evidence:
      `test_unparseable_spec_degrades_to_presence_only` (same `_violates`→False path as `packaging`-absent),
      `test_probe_failure_returns_all_required_keys`.
- [x] AC-4: `_install_deps` installs the pinned spec (the `REQUIRED_IMPORTS` key) for a version-violating
      dependency, so an existing `lancedb` 0.30.2 resolves to `lancedb==0.33.0`. The probe returns the
      dist spec verbatim (not a bare name), which `_install_deps` passes to uv/pip. Evidence:
      `test_install_deps_carries_pinned_spec`.
- [x] AC-5: no unintended reinstall churn — with the **real** `REQUIRED_IMPORTS` and versions that
      satisfy every pinned range (`tree-sitter>=0.24,<0.26`, `igraph>=0.11`, `networkx>=3.0`,
      `lancedb==0.33.0`, …), `_missing_in_venv` returns no false positives. Evidence:
      `test_real_required_imports_no_false_positives`; full suite 3,772 tests OK.
- [x] AC-6: propagation on upgrade needs no `upgrade_wavefoundry.py` change — `setup_index.main` calls
      `ensure_deps` (the chokepoint phase 4 already invokes), locked by a test; **and** the model-freshness
      audit confirms `prewarm_models` already runs on the upgrade's phase-4 setup invocations (the docs
      `--root` invocation → `prewarm_models(include_code=False)` warms DOCS+RERANKER; `--background-code`
      spawns the CODE-model prewarm). No model-download code added. Evidence:
      `test_main_calls_ensure_deps_chokepoint`; `setup_index.py:1468`; `upgrade_wavefoundry.py:1352–1395`.

## Tasks

- [x] Add a version-aware helper (parse spec via `packaging.requirements.Requirement`, compare
      `importlib.metadata.version(name)` against `req.specifier`) and wire it into `_missing_in_venv`'s
      venv probe, folding in the existing CUDA-dist metadata branch. Done: `setup_index.py` probe emits
      dist specs for absent-or-violating deps; GPU dists keep dist-name presence check.
- [x] Implement the presence-only fallback for unpinned specs and for `packaging`-absent / unparseable
      cases (never raise, never spurious-reinstall). Done: `_violates` returns False on
      `not _HAVE_PACKAGING`, no specifier, or any parse/metadata exception.
- [x] Confirm `_install_deps` passes the pinned spec for version-violating deps. Done: the probe returns
      the `REQUIRED_IMPORTS` key (full spec), unchanged from `_install_deps`'s input contract.
- [x] Add tests: satisfied-pin, violated-pin, unpinned-present, unpinned-absent, unparseable-spec,
      probe-failure degradation, real-dict no-churn, install-carries-pinned-spec, `main → ensure_deps`
      chokepoint. Done: `VersionAwareDependencyTests` (10 tests).
- [x] Audit `prewarm_models` coverage on the upgrade path; record the AC-6 result. Done: covered, no
      code added (see AC-6).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`. Done: 3,772 tests OK.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single-lane change in `setup_index.py`'s dependency-resolution probe + `tests/test_setup_index.py`. |

## Serialization Points

- `setup_index.py` is shared with `1p95j` (which added `LANCEDB_REQUIREMENT` + the pinned dict entry).
  `1p95j` is already implemented; this change **reads** `REQUIRED_IMPORTS` in `_missing_in_venv` (a
  disjoint region from the constant/dict declaration), so no intra-file conflict.

## Affected Architecture Docs

`docs/contributing/build-and-verification.md` — a one-line note under the upgrade rule that pinned
dependency bumps are version-synced into the tool venv on `wf setup` / `wave_upgrade` (existing installs
move to the pinned version, not just fresh installs). No boundary/flow change. Consider a matching line
in `docs/prompts/upgrade-wavefoundry.prompt.md` if the seed-first workflow warrants it (seed
`160-upgrade-wavefoundry` owns the canonical text).

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The core fix — version violations must be detected, satisfied pins must not churn. |
| AC-2 | required   | Unpinned deps must keep presence-only behavior or every setup risks needless reinstalls. |
| AC-3 | required   | Fallback bounds the blast radius to "no regression from today"; must never raise. |
| AC-4 | required   | Without installing the pinned spec, detection is inert — the dep must actually move. |
| AC-5 | required   | Guards against reinstall churn on the real dependency set (the main behavior risk). |
| AC-6 | important  | Confirms the operator's "propagates on upgrade" + "models ready" goal is met without new wiring. |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-30 | Planned. Root cause: `_missing_in_venv` is presence-only (`find_spec`), so `1p95j`'s `lancedb==0.33.0` pin does not reach existing installs; the upgrade already runs `ensure_deps` (phase 4), so a version-aware check propagates with no upgrade wiring. Model freshness already covered by `prewarm_models`. Admitted mid-wave into `1p93a` by operator direction. | `setup_index.py:214` (find_spec), `:1425` (main→ensure_deps), `:1468` (prewarm); `upgrade_wavefoundry.py:1352–1395` (phase-4 setup_index invocations); `packaging` verified importable + `SpecifierSet('==0.33.0').contains('0.30.2')` is False. |
| 2026-06-30 | Implemented. `_missing_in_venv` probe rewritten version-aware (`packaging`-based `_violates`, presence-only fallback on `packaging`-absent/unparseable/metadata-miss); GPU-dist presence check preserved; returns dist specs so `_install_deps` installs the pinned version. Prepare-council PASS (red-team exact-pin-downgrade → documented as intended contract; security-reviewer no new trust surface). AC-1..6 met. Smoke-verified against the live venv (no false positives; violated pin flagged; range/unpinned unaffected). | `setup_index.py::_missing_in_venv` diff; `VersionAwareDependencyTests` (10); 3,772 tests OK; `wave.md` Review Checkpoints prepare-council line. |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-30 | Make `_missing_in_venv` version-aware rather than wire a separate `wf setup`/dep-install step into `wave_upgrade`. | The upgrade already calls `ensure_deps` via phase-4 `setup_index.main`; a version-aware check propagates everywhere (setup + upgrade + auto-install) with zero new wiring. | Add a dependency-install phase to `upgrade_wavefoundry.py` (rejected — redundant with the existing `ensure_deps` call). Document a manual `pip install -U` step (rejected — purely manual, the option the operator declined). |
| 2026-06-30 | General (any pinned spec) rather than a lancedb-only guard. | Future-proofs every current/future pin at ~the same code cost as a special case; the `packaging` specifier logic handles ranges (`>=`, `<`) correctly. | lancedb-targeted guard (rejected — would need re-doing for the next pinned dep). |
| 2026-06-30 | Keep `packaging` optional via a presence-only fallback. | `packaging` is near-universal transitively but must not become a hard requirement that could itself fail a constrained setup. | Hard-require `packaging` (rejected — a setup-blocking dependency for a convenience check). |
| 2026-06-30 | Model freshness is audit-and-confirm, not new code. | `prewarm_models` already downloads/verifies `DOCS_/CODE_/RERANKER_MODEL` on every non-graph-only setup invocation, which the upgrade runs in phase 4. | Add explicit model-refresh logic (rejected — duplicates existing prewarm; audit first). |
| 2026-06-30 | An **exact** pin (`==`) will **downgrade** a newer installed version to the pinned one on the next `wf setup`/`wave_upgrade` (e.g. an installed lancedb 0.34.0 reverts to `==0.33.0`); range pins (`>=`, `<`) leave any satisfying version untouched. | Reproducibility: an exact pin is the framework's *validated* version, so "install exactly this" (including downgrade) is the intended contract — a machine on an unvalidated newer build is a support risk, not a feature. Prepare-council (red-team) surfaced this as an explicit-contract gap. | Only ever upgrade, never downgrade (rejected — leaves installs on unvalidated versions the framework hasn't tested; defeats the pin's purpose). Skip enforcement for `==` when installed is newer (rejected — same reason). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Version-aware check causes reinstall churn on a satisfied range spec (false positive). | AC-5 tests the real `REQUIRED_IMPORTS` with satisfying versions → zero flags; specifier satisfaction uses `packaging`, not hand-rolled string compares. |
| `packaging` unavailable in a constrained venv breaks the probe. | AC-3 fallback: `packaging`-absent → presence-only for all specs; the probe never raises. |
| A malformed spec or unreadable installed version reinstalls a healthy package. | Parse failures fall back to presence-only for that dep (never flag on uncertainty); AC-3 covers unparseable specs. |
| A future refactor drops the version check off the upgrade path. | AC-6 test locks `main → ensure_deps` as the chokepoint the upgrade depends on. |
| An exact-pin downgrade surprises a user who deliberately installed a newer build. | Documented as an intended contract (Decision Log): `==` pins install exactly the validated version; a user wanting a newer build changes the pin. Only `==` pins downgrade; `>=`/`<` ranges leave satisfying versions alone. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
