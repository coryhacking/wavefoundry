# 1p5be-adr — Retire the canonical-names rename manifest (removal pulled forward to 1.6)

Owner: Engineering
Status: accepted
Last verified: 2026-07-20

## Context

`.wavefoundry/framework/canonical-names.json` was the single source of truth for framework-shipped renames — role slugs (`council-moderator` → `wave-council`, `code-insight-agent` → `guru`; `removed_in: null`) and config keys (`wave_execution` → `wf_implement_wave`, `wave_council_policy` → `wf_review_wave`; `removed_in: "2.0.0"`). A loader (`wave_lint_lib/canonical_names.py`) fed three consumers:

- **docs-lint** — accepted legacy config-key spellings as aliases for required keys, warned on retired role slugs in hand-authored docs, and escalated legacy config keys to an ERROR at/after their `removed_in` version.
- **the upgrade migrator** (`upgrade_extensions`) — an unconditional, idempotent convergence pass that rewrote legacy config keys to canonical in `docs/workflow-config.json` on **every** upgrade (no version gate).
- a **runtime fallback** in `server_impl._read_wave_council_policy` (independent of the manifest) that read `wf_review_wave`, falling back to `wave_council_policy`.

By 1.6 the manifest's job is essentially done: the convergence migration has run on every upgrade since it shipped, so maintained projects have already converged to canonical, and active surfaces use the canonical names. The published contract said the config-key aliases would be removed at `2.0.0`; the operator chose to **retire the whole mechanism in 1.6** and keep only a one-shot convergence safety net.

## Decision

1. **Delete the manifest and loader** (`canonical-names.json`, `wave_lint_lib/canonical_names.py`).
2. **Keep a self-contained one-shot convergence** in `upgrade_extensions`: a hardcoded `{wave_execution → wf_implement_wave, wave_council_policy → wf_review_wave}` map (no manifest), still run on every upgrade so a skip-version operator's legacy config is rewritten to canonical before the docs gate. This migration is itself **slated for removal at 2.0.0**.
3. **docs-lint requires canonical keys only** — the legacy-alias acceptance, the `removed_in` escalation check (`check_workflow_config_removed_keys`), and the legacy-alias warning (`check_workflow_config_legacy_aliases`) are removed. `WORKFLOW_REQUIRED_KEYS` is the flat canonical set.
4. **Drop the retired-role-slug warning** (`check_deprecated_role_references`, `RETIRED_ROLE_NAMES`) — these were courtesy `removed_in: null` warnings; active docs already use canonical slugs.
5. **Remove the `server_impl` runtime fallback** — `_read_wave_council_policy` reads `wf_review_wave` only. The one-shot convergence guarantees runtime sees the canonical key.

This **pulls the published `removed_in: 2.0.0` config-key removal forward to 1.6.**

## Consequences

- Less machinery: one fewer shipped file, ~one fewer validator module, three fewer docs-lint checks, no runtime fallback branch. The rename system is now a single hardcoded upgrade migration.
- A project that authors a legacy key *after* 1.6 and never upgrades gets no migration and no docs-lint alias acceptance — it must use the canonical key. This is the intended bounded break; the convergence covers the upgrade path.
- The byte-identical parity concern is unrelated (that is the shipped reference-doc templates, guarded separately by `test_shipped_reference_docs.py`).

## Alternatives considered

- **Remove at 2.0.0 as originally published.** Rejected by operator — the convergence has already run everywhere; the mechanism is dead weight now.
- **Hard removal with no convergence net.** Rejected — a skip-version operator on a legacy key would be stranded; the one-shot convergence is cheap insurance until 2.0.0.
- **Keep the manifest, just stop adding entries.** Rejected — leaves the loader, three docs-lint checks, and the runtime fallback in place for two entries that have already converged.

## References

- Change: `docs/waves/1p58z repo-portability-and-install-docs/1p5b4-ref remove-canonical-names-rename-manifest.md`
- Supersedes the mechanism from `1p3iv`/`1p3j6`/`1p3j7` (manifest-derived aliases + convergence) and `1p337` (reader-side fallback).
