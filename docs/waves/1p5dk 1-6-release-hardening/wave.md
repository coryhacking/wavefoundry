# Wave Record

Owner: Engineering
Status: active
Last verified: 2026-06-13

wave-id: `1p5dk 1-6-release-hardening`
Title: 1 6 Release Hardening

## Objective

Make the 1.6.0 release shippable and self-consistent. A review of the 1.5→1.6 upgrade surface found the release record and operator instructions materially out of date — the CHANGELOG omits ~4 landed waves and both forced-rebuild version bumps (`GRAPH_BUILDER_VERSION`/`CHUNKER_VERSION` 25→30), and the upgrade prompt describes a pre-1.6 flow (separate index update, hard MCP restart, no secrets gate, no resume). When this wave closes, 1.6.0 is the single official release record (no build was ever distributed), the operator upgrade docs match the shipped flow, and the upgrade-floor / migration-failure-surfacing robustness gaps are closed.

**Scope note (2026-06-13):** the originally-admitted `1p5dn` (enforce the full-tree secrets baseline at upgrade) was **dropped** — verification showed the full baseline already runs automatically. On a 1.5→1.6 upgrade `docs/scan-findings.json` is absent, so the Phase-4 index build's `update_secrets_scan` escalates to a full-tree scan (`scan_secrets.py:172`) and classifies findings up front; the docs gate (incremental) and the next `wave_close` enforce blocking. No enforcement gap — only a documentation gap, folded into `1p5dm`.

## Changes

Change ID: `1p5dl-doc changelog-1-6-official-release-record`
Change Status: `implemented`

Change ID: `1p5dm-doc upgrade-operator-docs-1-6-refresh`
Change Status: `implemented`

Change ID: `1p5do-enh upgrade-floor-and-migration-log-surfacing`
Change Status: `implemented`

Change ID: `1p5ik-bug remove-stale-framework-index-on-upgrade`
Change Status: `implemented`

Change ID: `1p5k0-bug nested-type-constant-retrieval`
Change Status: `implemented`

Change ID: `1p5l4-bug confidence-weighted-blast-radius-risk`
Change Status: `implemented`

## Wave Summary

Three changes close the 1.6 release-readiness gaps found in the upgrade review: (`1p5dl`) reconstruct the CHANGELOG so `## [1.6.0]` is the complete official first release — absorbing `[Unreleased]` and every post-06-09 wave (1p4wz model split + index-fold, 1p4hi, 1p58z, 1p5cg) and stating the forced full rebuild; (`1p5dm`) rewrite the operator upgrade docs to match the shipped flow (auto index-update, in-process MCP reload, the real secrets-scan behavior + `--resume-after-gate`, the floor); (`1p5do`) add an explicit upgrade floor and surface `post_extract` migration-log errors so a partially-migrated tree can't report a clean summary. (A fourth change, `1p5dn`, was admitted then dropped — see the Objective scope note; the full-tree secrets baseline already runs automatically via the Phase-4 index build.)

## Journal Watchpoints

- **Sequencing (follow-up):** `1p5cg` has closed and no wave is OPEN — this wave can activate. `1p5dl` (done) and `1p5do` are independent; `1p5dm` documents the floor `1p5do` lands, so author `1p5dm` after/with `1p5do`.
- **Versioning decision (load-bearing):** operator confirmed no 1.6 build was ever distributed, so `## [1.6.0]` becomes the single official release — do NOT cut 1.6.1/1.7.0. `1p5dl` folds everything into 1.6.0; the date advances to the actual assembly/ship date.
- **Descope (resolved):** `1p5dn` (enforce full secrets baseline) was dropped — the full-tree baseline already runs automatically via the Phase-4 index build's `update_secrets_scan` escalation (full when `scan-findings.json` is absent, as on a 1.5→1.6 upgrade). `1p5dm` must document the *real* mechanism, not claim the docs gate runs the full scan.
- **Framework-edit gate:** `1p5do` edits `upgrade_wavefoundry.py` + `upgrade_extensions.py`; open `framework_edit_allowed` before edits and close immediately after.
- **CHANGELOG style (watchpoint):** `1p5dl` follows the repo convention — git-commit-message-style bullets, no build numbers, no wave IDs, no internal version constants in the prose (the forced-rebuild note may name `GRAPH_BUILDER_VERSION`/`CHUNKER_VERSION` since that is the operator-relevant fact).
- **Don't over-scope (defer):** the code changes target the upgrade flow's correctness gaps only. The "version bumps are logged not force-rebuilt" design (log-and-trust) is intentional; do not convert it to a forced rebuild here — defer any rebuild-policy change to a separate decision.

## Review Evidence

- wave-council-readiness: READY-WITH-NOTES — readiness sign-off recorded 2026-06-13. Four coherent, right-sized changes closing verified 1.5→1.6 release-readiness gaps. Notes: (1) **`1p5dn` is a security-detection-control change** — AC-1 must reproduce/verify the incremental-vs-full gap BEFORE changing behavior, and AC-5 mandates an adversarial faithfulness review before close (a green test must not mask a control scanning less than claimed). (2) **Claim/enforcement must agree** — `1p5dl`'s "full baseline at upgrade" wording and `1p5dn`'s enforcement are two halves of one decision; if enforcement is rejected, soften the claim in `1p5dl` instead (reconcile at implement). (3) **`1p5dm` documents the floor `1p5do` establishes** — settle the floor value once and author the doc after/with the code. (4) Leave the intentional "log-don't-force-rebuild" version-transition design alone (defer any rebuild-policy change). No retrieval/index-output surface; the only adversarial concern is the secrets-control faithfulness in `1p5dn`.
- wave-council-delivery (addendum, 2026-06-14): three upgrade-flow items were added after the initial delivery sign-off, all discovered during downstream 1.6 validation and all upgrade-hardening in theme: (a) `~/Downloads/` added as a 5th pack search path (`1p5do` + doc enumerations in `1p5dm`) — browser-downloaded packs were silently missed; (b) agent zip-discovery hardened to a "never `ls`, the pack lives in `~/.wavefoundry/dist/`, use `wave_upgrade`/`--detect-zip`" hard rule in the seed + prompt (`1p5dm`); (c) `1p5ik` (new bug) removes the deprecated `.wavefoundry/framework/index/` on upgrade — a guru trace confirmed the framework index layer is fully dead (all reads hard-reject non-`project` layer) and that manifest-prune structurally cannot remove it (index `.lance` files were never in MANIFEST), so an explicit `shutil.rmtree` in the prune phase is the fix; the false `WALKER_VERSION` comment was corrected. All additive/cleanup-only; full suite **3120 OK**; docs-lint clean. Scope note: the wave has accreted four upgrade-flow items beyond its original three — coherent ("1.6 release hardening") but a reminder to keep future waves tighter.
- wave-council-delivery (addendum 2, 2026-06-14): `1p5k0` (new bug) added — a downstream-surfaced (solaris/Swift) retrieval miss where a **nested-type constant** (`AutomationController.RoutineConfig.maxRetries`) wasn't retrieved. Root cause (operator + downstream investigation, after two wrong hypotheses from me): symbol-first injection was gated explanatory-only so navigational value/where-is queries got no injection; plus the chunk lane flattened nested-type members onto the outermost type. Fix: widen the injection gate to navigational, qualify nested-type member qnames (`CHUNKER_VERSION` 30→31), match intermediate dotted suffixes in `code_constants`, and stoplist decoy graph-seed words. **Gate satisfied:** the patch touches the AC-10-calibrated retrieval path, so `run_recall_eval.py` was run post-patch on a v31 rebuild → **11/11 pass, exit 0** (navigational symbol queries still rank #1 — no dilution). Patches were authored/unit-verified downstream and applied to this tree before tracking; recorded retroactively as `1p5k0` (placeholder `1p5xx` replaced). This is a retrieval/chunker change (not upgrade-hardening) — folded in at operator request; it reinforces the standing "keep future waves tighter" note.
- wave-council-delivery (addendum 3, 2026-06-14): `1p5l4` (new bug) added — Aceiss/javaagent (Java) reported in two `1.6.0+p5ky` smoke tests that `code_risk_score` ranked a trivial accessor (`ApplicationToken.getKey`) #1 purely on a name collision: `code_impact`/`code_risk_score` folded heuristic `EXTRACTED` name-based call edges into blast-radius/`fan_in` at full weight, while only 2 of 9 `getKey` call sites are the real symbol (the rest `Map.Entry.getKey()`, all `EXTRACTED`). Same low-trust edge class that `1p41l` found *under*-counting on Python — opposite symptom, same root. Operator chose: fold into this wave; scope = down-weight `EXTRACTED` in the composite + transparency fields (no hard `min_confidence` filter). Fix is **query-layer only** (`graph_query.py` `graph_impact`+`risk_score`): `risk = weighted_affected_file_count * log1p(weighted_fan_in)` with `EXTRACTED` edges at 0.25, per-result `extracted_edge_fraction` + raw + weighted components; **no `GRAPH_BUILDER_VERSION` bump** (graph shape unchanged). **Gate satisfied:** full suite **3125 OK** (+4 collision-repro tests), AC-10 eval **11/11**, docs-lint clean, live-graph dogfood confirms weighting + non-degeneracy; adversarial faithfulness review PASS (fractional-not-zero weight + raw counts retained = no silent narrowing). This is a graph-scoring change (not release-hardening) — folded in at operator request; reinforces the standing "keep future waves tighter" note (this wave has now taken five post-original items).
- wave-council-delivery: READY — delivery sign-off recorded 2026-06-13. Three changes implemented (`1p5dl` CHANGELOG, `1p5dm` operator docs, `1p5do` upgrade-flow robustness); `1p5dn` descoped after verification showed the full-tree secrets baseline already runs automatically (Phase-4 index build escalates to full when `scan-findings.json` is absent). Verified at delivery: full suite **3116 OK** (+9 `1p5do` tests); `wave_validate` docs-lint clean; the rewritten operator docs re-checked against `upgrade_wavefoundry.py` (in-process `wave_mcp_reload`, auto Phase-4 index, 1.4.0 warn-floor, `--resume-after-gate`, Phase-4 full-scan-on-missing-findings per `scan_secrets.py:172`); the CHANGELOG cross-checked against `git log` since the 1.6.0 cut. `1p5do`'s code is additive-warnings-only (floor warns not aborts; log scan + signals are read-only/print-only; convergence warning sits in a branch that already returned) — no behavioral risk to the upgrade success path. No security/secrets/binding change (the secrets-control change was descoped). The CHANGELOG `## [1.6.0]` date is 2026-06-13 (assembly date) — confirm/adjust at release if it ships on a different day.
- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-13: PASS WITH NOTES** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1p5dn` changes a secrets-detection control and could rest on a misread of the current gate scope or make every upgrade slow / block on pre-existing secrets in untouched files — MITIGATED because AC-1 requires reproducing the incremental-only gate before any change, the change is scoped to scan scope/timing not detection semantics, AC-5 mandates an adversarial faithfulness review before close, Phase-2b policy materialization is preserved so a fresh project is not deadlocked, and the blocked-finding recovery path is the existing non-destructive `--resume-after-gate` documented in `1p5dm`; strongest-alternative: skip the code change and instead soften the CHANGELOG "full baseline at upgrade" claim in `1p5dl` to match the incremental-gate-plus-agent-full-scan reality — rejected because the operator chose enforcement and a security baseline that only runs when an agent remembers a seed step is a weak guarantee, but recorded as the fallback in `1p5dn`'s decision log; docs-contract note: `1p5dl` (changelog) and `1p5dm` (operator docs) are documentation-only and the floor wording in `1p5dm` must match the behavior `1p5do` lands, captured as a serialization point)

## Dependencies

- No external wave dependencies.
