# Drop the legacy `exc-###` secret-scan ID backward-compat

Change ID: `1p8vq-debt drop-legacy-exc-secret-scan-ids`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-29
Wave: `1p8vd gpu-doctor-mcp-stdout-fd-hang` (requires `framework_edit_allowed` + `seed_edit_allowed` at implementation)

## Rationale

Wave `1p8nw` (shipped in 1.9.5, ~2026-06-28) replaced the old sequential secret-finding IDs (`exc-###`) with `<prefix>-sec` lifecycle IDs, and added a migration shim (`migrate_legacy_finding_ids` + `legacy_id` field) that auto-converts `exc-###` ledgers on the next scan. Operator direction: **do not carry the `exc-###` backward-compat** — the `sec` IDs are only ~1 day old, so the migration baggage isn't worth keeping.

The removal is safe because the secrets gate does **not** depend on ID shape — `_check_secrets_gate` (`server_impl.py:8928`) keys only on `status`, and `_find_exception` re-binds findings by `file`/`line`/`rule_id` + `line_hash`/`context_hash`, never validating the id form. So an un-migrated `exc-###` ledger stays fully readable and gate-correct; dropping migration just stops auto-rewriting old IDs. The exposure window is ~1 day (any repo that upgraded to 1.9.5 and ran the mandated full baseline scan already migrated), and this repo's `docs/scan-findings.json` is `[]` (nothing to migrate).

## Requirements

1. **Remove the migration shim** in `wave_lint_lib/secrets_validators.py`: delete `_LEGACY_EXC_ID_RE` (`:472`), `migrate_legacy_finding_ids` (`:523–570`), and its call + `if` block in `check_hardcoded_secrets` (`:1432–1438`). Leave `_existing_finding_ids` as-is (it reads all `id`s regardless of shape — still needed for `sec`-vs-`sec` dedup).
2. **Drop the `legacy_id` field** from the schema and any always-keep handling — new ledgers will simply never carry it.
3. **Update the schema docs** — remove the "Migration of legacy `exc-###` ids" subsection and the `legacy_id` row, and drop the "legacy `exc-###` tolerated/migrated" note on the `id` field, in **both** `docs/references/scan-findings-format.md` and the framework twin `.wavefoundry/framework/docs/scan-findings-format.md` (keep them byte-identical).
4. **Update seed-213** (security reviewer): remove the `exc-###` tolerance / `legacy_id` surfacing clause (`:17`).
5. **Remove the migration tests**; keep gate-semantics tests green. Delete `TestMigrateSecFindingIds`, `TestLegacyExcIdTolerance`, `TestLineDriftAfterMigration` (migration-specific) in `test_secrets_validators.py`; collapse the `TestGateSemanticsUnchanged` both-shapes subtests to `sec`-only (the gate is shape-agnostic, so they pass either way). Other fixtures that incidentally use `exc-001` while testing non-migration behavior may stay.

## Scope

**Problem statement:** the `exc-###` → `sec` migration/compat is unnecessary baggage (feature ~1 day old); remove it cleanly without breaking gate behavior on any existing ledger.

**In scope:**

- `wave_lint_lib/secrets_validators.py`: delete the migration cluster.
- `docs/references/scan-findings-format.md` + framework twin: schema doc edits.
- `seed-213`: prose edit.
- `test_secrets_validators.py`: remove migration tests; collapse the gate dual-shape subtests.

**Out of scope:**

- The `sec` ID minting itself (`_next_secret_finding_id`) — unchanged.
- The gate / `_find_exception` matching — unchanged (already ID-shape-agnostic).
- Re-keying or touching any existing target-repo ledger (those stay readable; new findings mint `sec`).

## Acceptance Criteria

- [x] AC-1: `_LEGACY_EXC_ID_RE`, `migrate_legacy_finding_ids`, and its call in `check_hardcoded_secrets` are removed; no remaining migration reference in `secrets_validators.py`. (grep clean across scripts + docs except the historical `1p8nw` archive, which is preserved)
- [x] AC-2: a scan of a ledger containing an `exc-###` entry still reads + gate-evaluates it (pending still blocks) and does NOT rewrite its id. (`TestGateSemanticsUnchanged.test_legacy_ledger_gates_correctly_and_is_not_rewritten`; the both-shape gate subtests also pass)
- [x] AC-3: new findings are minted as `<prefix>-sec`; no `legacy_id` field is written. (existing `sec`-minting tests stay green; the AC-2 test asserts `assertNotIn("legacy_id", …)`)
- [x] AC-4: both `scan-findings-format.md` files drop the migration subsection + `legacy_id` row and stay byte-identical; seed-213 drops the `exc-###` clause. (`diff -q` byte-identical; seed-213 edited; the shipped-docs parity test passes)
- [x] AC-5: migration-specific tests removed (3 classes); the gate class keeps the shape-agnostic tests + an AC-2 test; the full framework suite + docs-lint stay green. (suite 3696 ok; docs-lint ok)

## Tasks

- [x] Delete the migration cluster in `secrets_validators.py` (regex, function, call) (under `framework_edit_allowed`).
- [x] Remove the `legacy_id` field references / schema rows.
- [x] Edit both `scan-findings-format.md` files (drop migration subsection + `legacy_id`; copied canonical → twin, byte-identical).
- [x] Edit seed-213 to drop the `exc-###` tolerance clause (under `seed_edit_allowed`).
- [x] Remove migration tests (3 classes + unused `migrate`/`save_exceptions` imports); repurpose the gate class + add the "old ledger still gate-correct, not rewritten" assertion (AC-2).
- [x] Run the framework suite + docs-lint; confirm green (incl. the shipped-docs byte-parity test). (suite 3696 ok; docs-lint ok)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| remove migration cluster + tests | implementer | — | `framework_edit_allowed`; clean deletes |
| schema-doc + seed-213 edits | implementer | code removal | `seed_edit_allowed`; keep twin byte-identical |
| suite + docs-lint (incl. byte-parity) | qa-reviewer | both | AC-5 |

## Serialization Points

- The two `scan-findings-format.md` files must stay byte-identical (a parity test enforces it) — edit both together.

## Affected Architecture Docs

`N/A` — removes a migration shim and its docs; no boundary/flow/verification-architecture change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The actual removal. |
| AC-2 | required | Must not break gate behavior on an existing `exc-###` ledger. |
| AC-3 | required | New findings still mint `sec`; no `legacy_id`. |
| AC-4 | required | Docs/seed reflect the removal; twin parity preserved. |
| AC-5 | required | Tests + suite + docs-lint green. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-29 | Drafted from operator direction (don't carry `exc-###` compat — `sec` IDs ~1 day old). Mapped the migration cluster + docs/seed/test sites; confirmed removal is safe (gate is ID-shape-agnostic; this repo's ledger is empty; ~1-day exposure window). Added to wave `1p8vd` per operator direction. | `secrets_validators.py:472,523-570,1432-1438`; `server_impl.py:8928` (gate keys on status); `scan-findings-format.md` (×2); seed-213:17; `docs/scan-findings.json` = `[]`. |
| 2026-06-29 | Implemented. Deleted `_LEGACY_EXC_ID_RE` + `migrate_legacy_finding_ids` + its call; removed `legacy_id` from schema docs (both twins, byte-identical) + the seed-213 clause; removed 3 migration test classes + unused imports; the gate class keeps shape-agnostic tests + a new "legacy ledger still gate-correct and NOT rewritten" test. Historical `1p8nw` closed-wave records left intact (preservation policy). | `secrets_validators.py` + `scan-findings-format.md` ×2 + seed-213 diffs; secrets tests 141 ok; suite 3696 ok; docs-lint + shipped-docs byte-parity ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-29 | Delete the `exc-###` migration shim entirely (no deprecation window). | Feature is ~1 day old; gate is ID-shape-agnostic so old ledgers stay readable without migration; carrying the shim is unjustified complexity. | Keep migration for one more release (rejected — operator direction, negligible benefit). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A target repo still on a pre-1.9.5 `exc-###` ledger loses auto-migration. | The gate reads `exc-###` ledgers correctly regardless (keys on `status`, matches by file/line/hash); only the cosmetic id-rewrite stops. New findings still mint `sec`. |
| The two schema-doc twins drift (byte-parity test). | Edit both in the same pass; the existing parity test enforces identity. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
