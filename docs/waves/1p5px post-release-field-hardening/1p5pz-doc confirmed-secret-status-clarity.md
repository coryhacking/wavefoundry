# Secrets gate: classify-to-unblock + persistent confirmed-secret reminder at close

Change ID: `1p5pz-doc confirmed-secret-status-clarity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-15
Wave: `1p5px post-release-field-hardening`

> **Scope grew (2026-06-15):** originally a doc-only clarification of `confirmed-secret`. After review against the current `wave_close` secrets gate, the operator chose a **behavior change** to the gate model (below). This is now a **security-control behavior change** (it *loosens* the confirmed-secret block) → requires the adversarial faithfulness-review treatment + tests, not just doc edits.

## Rationale

Field report against 1.6.0+p5lj: a downstream agent hit a **real** secret at upgrade and, lacking clear guidance, mislabeled it `false-positive` (semantically wrong). Reviewing the current `wave_close` secrets gate (`server_impl.py:8340` `_check_secrets_gate`, gated at `:8649` where any diagnostic blocks) surfaced both a doc gap and a model the operator wants changed:

**Current model (every finding produces a *blocking* diagnostic; no informational channel):**
- `pending` → hard block.
- `confirmed-secret`/`suspected-secret` without `acknowledged_for_wave == <wave>` → soft block (per-wave acknowledgment via seed-213).
- `confirmed-secret`/`suspected-secret` *with* `acknowledged_for_wave == <wave>` → **silent pass**.
- `false-positive` → silent pass.

**Operator decisions (2026-06-15) — new model:**
1. New/unresolved findings block close until classified: `pending` **and** `suspected-secret` hard-block until reclassified to `confirmed-secret` or `false-positive`.
2. `confirmed-secret` **never blocks** close. Instead, **every** `wave_close` surfaces a visible reminder listing the project's `confirmed-secret` findings; the operator need not act — it's a standing acknowledgement. The reminder is returned to the agent and the agent presents it to the human.
3. `false-positive` clears silently.
4. The per-wave `acknowledged_for_wave` / `override_reason` machinery is **dropped** — classification *is* the acknowledgment; the reminder replaces per-wave acceptance.

This is a deliberate **loosening**: close can now proceed with a known real secret in the tree (relying on the reminder), where today it soft-blocks until conscious per-wave acceptance. Operator-confirmed as intended.

## Requirements

1. **Block the unresolved.** `wave_close` hard-blocks while any finding is `pending` or `suspected-secret`, with a diagnostic naming each + how to reclassify (seed-213). (`pending` already blocks; add `suspected-secret` to the hard-block set.)
2. **Confirmed-secret is non-blocking + always reminded.** A `confirmed-secret` finding must NOT block close. On **every** `wave_close` (both the success path and any error-return path), the response carries a dedicated, machine-readable notice (e.g. `data.confirmed_secrets` list + a human-facing `secrets_reminder` string) listing every `confirmed-secret` in `docs/scan-findings.json`. It is informational only — close still succeeds on its account.
3. **Agent presents it.** The notice is shaped so the agent surfaces it to the human on close ("N confirmed secret(s) remain in the project: …"). No action required from the operator.
4. **Drop `acknowledged_for_wave` / `override_reason` from the gate.** Remove them from `_check_secrets_gate` logic, the `scan-findings` schema docs, and the seed-213 workflow. Tolerate the legacy fields if present in an existing `scan-findings.json` (ignore, don't error) — no migration required.
5. **`false-positive` stays silent and cleared** (must still be a real classification, never used for a real secret — see doc requirement).
6. **Docs match the new model.** Seed-213 decision tree + `scan-findings-format.md` status×gate matrix updated to: `pending`/`suspected-secret` block; `confirmed-secret` non-blocking + reminded; `false-positive` cleared; the false-positive-for-a-real-secret anti-pattern called out. Seed-first; weave pointers from `SECURITY.md` + the upgrade prompt.

## Scope

**In scope:**

- `server_impl.py`: `_check_secrets_gate` — add `suspected-secret` to the hard-block set, remove the `confirmed-secret` block + `acknowledged_for_wave`/`override_reason` checks; add a non-blocking confirmed-secret notice to the `wave_close` response `data` on **both** success and error returns.
- `scan-findings` schema/docs: `docs/references/scan-findings-format.md` status×gate matrix; drop `acknowledged_for_wave`/`override_reason` from the documented schema.
- `seeds/213-security-reviewer.prompt.md`: status decision tree + anti-pattern; stop instructing the reviewer to write `acknowledged_for_wave`.
- `docs/SECURITY.md` + upgrade-prompt secrets section: discoverability pointers.
- Tests (`test_server_tools.py`): pending blocks; suspected blocks; confirmed does NOT block but the notice appears (success + error paths); false-positive silent; legacy `acknowledged_for_wave` field tolerated.

**Out of scope:**

- A new `acknowledged` status or `remediate_by`/`remediation_note` fields (not needed under this model).
- The CUDA-13 work (`1p5py`).

## Acceptance Criteria

- [x] AC-1: `wave_close` hard-blocks on `pending` and `suspected-secret`; does NOT block on `confirmed-secret`; and returns a `confirmed_secrets` notice + human-facing `secrets_reminder` on **every** close (success and error) whenever the project has ≥1 `confirmed-secret`. Asserted by `WaveCloseSecretsGateTests` (13 tests covering each status + both return paths).
- [x] AC-2: `acknowledged_for_wave`/`override_reason` removed from the gate logic, schema doc (`scan-findings-format.md` + shipped template), and the seed-213 workflow; a legacy finding carrying them is tolerated (test `test_confirmed_secret_legacy_ack_fields_tolerated` + `test_suspected_secret_blocks_even_with_legacy_ack`). Grep gate: old diagnostic codes (`secrets_gate_pending`/`secrets_gate_confirmed_secret`) gone from code.
- [x] AC-4 (operator directive 2026-06-15 — `wave_close` is the *sole* gate): secret findings are **record-only** at `docs-lint` (`check_hardcoded_secrets(record_only=True)` from `cli.py`) — detected + recorded to `scan-findings.json`, surfaced as a non-fatal `[secrets]` notice, but **not** returned as lint failures, so the post-edit hook, `wave_validate`, and the **upgrade docs gate no longer block on secrets**. Only a malformed `wavefoundry-ignore` directive still fails docs-lint. `wave_close`'s `_check_secrets_gate` is the only enforcement point. Asserted by `test_record_only_records_but_does_not_fail` (records but doesn't fail; default mode still surfaces); other callers (`build_scan_allowlist`, etc.) keep findings (default `record_only=False`). Docs corrected: `build-and-verification.md`, the upgrade prompt + seed-160 (no longer "halts the upgrade"), `upgrade-wave-context.prompt.md`. **Faithfulness:** this loosens detection-time blocking but is intentional (detect-always, gate-at-ship); the fail-safe direction is preserved — a finding message missing the `[secrets]` tag would still block, and ruleset-load errors still fail.

- [x] AC-3: Seed-213 + `scan-findings-format.md` describe the new model (status×gate matrix + false-positive anti-pattern), verified against the gate code (`server_impl.py:8340`); also synced the `wave_close` tool docstring, `SECURITY.md`, `review-and-evals.md`, `mcp-tool-surface.md`, seed-190. Seed-first; docs-lint clean. **Faithfulness review PASS** — the gate is **fail-closed** (only `false-positive`/`confirmed-secret` clear; pending/suspected/unknown all block, test `test_unknown_status_fails_closed`), the confirmed reminder fires on both close paths so the loosening can't go unnoticed, and the only loosening is the intended one (confirmed no longer blocks).

## Tasks

- [x] `_check_secrets_gate`: fail-closed hard-block (only `false-positive`/`confirmed-secret` clear); removed confirmed-secret block + ack/override checks.
- [x] `wave_close` response: `_confirmed_secret_notice` builds the non-blocking `confirmed_secrets` + `secrets_reminder`; attached on both success and error returns.
- [x] Removed `acknowledged_for_wave`/`override_reason` from schema doc (+ shipped template) + seed-213 workflow (legacy tolerated in data).
- [x] Seed-213 decision tree + anti-pattern; `scan-findings-format.md` status×gate matrix; `wave_close` docstring; `SECURITY.md`/`review-and-evals.md`/`mcp-tool-surface.md`/seed-190 pointers (seed-first).
- [x] Tests (13, each status × both return paths; legacy-field tolerance; fail-closed unknown; reminder content) + faithfulness review + grep gate.

## Agent Execution Graph


| Workstream  | Owner       | Depends On | Notes |
| ----------- | ----------- | ---------- | ----- |
| gate-logic  | Engineering | —          | `_check_secrets_gate` + wave_close notice channel |
| docs+tests  | Engineering | gate-logic | seed-213, scan-findings-format, SECURITY pointers, tests, faithfulness review |


## Serialization Points

- Seed-213 + `scan-findings-format.md` are the source of truth and must match the rewritten gate code; settle wording once after the gate logic lands.

## Affected Architecture Docs

`N/A` — behavior is contained to the `wave_close` secrets gate + its docs; no boundary/data-flow contract change. The status×gate semantics live in `scan-findings-format.md`, not an architecture doc.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The new gate model is the change; pending/suspected must still block and the confirmed reminder must always surface. |
| AC-2 | required | Dropping the ack fields cleanly (incl. legacy tolerance) avoids a half-migrated gate. |
| AC-3 | required | Security-control change → docs must match code and the faithfulness review must confirm no over-narrowing beyond the intended loosening. |
| AC-4 | required | Operator directive: `wave_close` is the SOLE secrets gate — docs-lint/hook/upgrade must record, not block. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-15 | Scoped doc-only (clarify `confirmed-secret`). Reviewed against `_check_secrets_gate` (`server_impl.py:8340`, gated `:8649` — all diagnostics block; no info channel). Operator chose a behavior change: pending+suspected block; confirmed non-blocking + always-reminded; drop `acknowledged_for_wave`/`override_reason`. Expanded to a security-control behavior change (code+doc); deliberate loosening confirmed. | `server_impl.py:8340,8649` |
| 2026-06-15 | **Implemented + verified.** `_check_secrets_gate` rewritten fail-closed; `_confirmed_secret_notice` added + attached to both close paths; docs synced across seed-213/scan-findings-format(+shipped template)/wave_close docstring/SECURITY/review-and-evals/mcp-tool-surface/seed-190. 13 `WaveCloseSecretsGateTests` (incl. fail-closed unknown + reminder on both paths) + faithfulness review PASS. **Full suite 3129 OK**; docs-lint clean. | `server_impl.py`, `test_server_tools.py`, `docs/references/scan-findings-format.md`, `seeds/213` |
| 2026-06-15 | **Record-only at docs-lint (AC-4, operator directive — wave_close is the SOLE gate).** Added `record_only` to `check_hardcoded_secrets`; `cli.py` (docs-lint) opts in → secret findings recorded but not returned as lint failures (non-fatal `[secrets]` notice). Post-edit hook, `wave_validate`, and the **upgrade docs gate no longer block on secrets**. Corrected the upgrade/secrets docs (build-and-verification, upgrade prompt, seed-160, upgrade-wave-context) that claimed the docs gate halts on secrets. Test added; default mode unchanged (other callers keep findings). **Full suite 3139 OK**; docs-lint clean. | `secrets_validators.py`, `wave_lint_lib/cli.py`, `test_secrets_validators.py`, upgrade docs |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-15 | `confirmed-secret` non-blocking + persistent close reminder; drop per-wave acknowledgment | Operator wants a standing visible reminder, not a block, for known/classified secrets; classification is the acknowledgment. | (a) keep soft-block + one-time per-wave ack (rejected — operator wants no required action); (b) doc-only, no behavior change (rejected — doesn't deliver the reminder) |
| 2026-06-15 | `suspected-secret` joins `pending` in the hard-block set | 'suspected' is unresolved — it must force a classification decision, not slip through as a non-blocking reminder. | treat suspected like confirmed (rejected — it isn't a terminal classification) |
| 2026-06-15 | Secret findings are **record-only at docs-lint**; `wave_close` is the sole enforcement gate (AC-4) | Operator directive: a found secret must not block the post-edit hook, `wave_validate`, or upgrades — only the wave/ship boundary. Detect-always, gate-at-ship. | (a) keep docs-lint failing on secrets (rejected — blocks edits/upgrades, the reported friction); (b) remove the scan from docs-lint entirely (rejected — then findings wouldn't be recorded continuously) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Loosening lets a close ship with a known real secret unnoticed | The reminder is emitted on EVERY close (success + error) and presented to the human; faithfulness review confirms it always fires when a confirmed-secret exists |
| Removing ack fields breaks existing scan-findings.json | Legacy fields tolerated (ignored), no migration; test covers a legacy-field finding |
| Doc drifts from the rewritten gate | AC-3 verifies wording against the gate code; faithfulness review gate |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
