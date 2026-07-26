# Remove the unused Context Efficiency pair schema

Change ID: `1th3p-maint remove-unused-context-efficiency-schema`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-25
Wave: `1ti11 remove-unused-context-efficiency-schema`

## Rationale

Wavefoundry currently ships
`.wavefoundry/framework/evals/context-efficiency-pairs.schema.json`, but no
runtime or registered project tool reads it. `wf_context_efficiency_eval`
derives scaffolds from the scorer's canonical constants and validates attached
reports with `score_context_efficiency_pairs.py`. Keeping a separately
maintained, undiscoverable schema creates a second contract that can drift
without providing value to installed projects.

## Requirements

1. Remove the unused JSON Schema from the canonical framework tree and future
   distribution packs.
2. Preserve the existing `wf_context_efficiency_eval` register, scaffold,
   attach, replace, and revoke behavior; the scorer remains the executable
   contract and scaffold source of truth.
3. Remove schema-specific packaging and upgrade expectations, replacing them
   with a negative distribution assertion that prevents accidental
   reintroduction.
4. Preserve closed-wave history that accurately records the artifact shipped
   in the release where paired evaluation was introduced.
5. Ensure upgrade pruning can remove the previously pack-delivered schema from
   target projects through the existing MANIFEST-based lifecycle.

## Scope

**Problem statement:** An unused, manually maintained schema is shipped to
every target project even though installed tooling neither reads nor advertises
it.

**In scope:**

- Delete `.wavefoundry/framework/evals/context-efficiency-pairs.schema.json`.
- Update build-pack and upgrade regression expectations.
- Retain direct scorer-contract coverage and the scorer-derived scaffold.
- Verify that no live runtime reference to the schema filename remains.

**Out of scope:**

- Changing paired-evaluation scoring, applicability, quality gates, or Context
  Efficiency accounting.
- Adding a replacement schema-validation dependency.
- Rewriting closed wave records or historical release statements.

## Acceptance Criteria

- [x] AC-1: A built distribution does not contain
  `.wavefoundry/framework/evals/context-efficiency-pairs.schema.json`.
- [x] AC-2: `wf_context_efficiency_eval` still scaffolds from scorer constants
  and validates attached reports through `score_pairs`.
- [x] AC-3: Upgrade coverage no longer expects the schema to be installed, and
  the existing MANIFEST pruning contract remains the removal path for
  previously installed copies.
- [x] AC-4: An exact live-source census finds no runtime reference to the schema
  filename; closed historical records may retain it.
- [~] AC-5: No CHANGELOG entry. Operator direction, confirmed 2026-07-25 on a
  verified basis: the schema DID ship (it landed in `4f0c8d4e`, an ancestor of
  the 1.14.0 release and contained in tag `v1.14.0`), but the operator is the
  sole deployer of 1.14.0, so there is no third-party installed base to notify
  and the silent prune has no field impact.

## Tasks

- [x] Delete the redundant schema artifact.
- [x] Replace positive package assertions with a negative non-shipping pin.
- [x] Remove the schema from the representative upgrade fixture and
  post-extraction expectations.
- [x] Remove or replace schema-specific parity coverage with direct scorer
  contract coverage where it is not already present.
- [~] Add the removal and supported replacement path to the unreleased
  CHANGELOG section. Operator direction: not a release-note item, because the
  only 1.14.0 deployment is the operator's own.
- [x] Run targeted build-pack, upgrade, and Context Efficiency tests.
- [x] Run docs validation and record implementation evidence.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Artifact and package cleanup | implementer | — | Delete the schema and update pack expectations. |
| Upgrade and scorer verification | implementer | Artifact and package cleanup | Confirm pruning compatibility and unchanged scorer behavior. |


## Serialization Points

- Package expectations must be updated in the same change that deletes the
  artifact.
- Upgrade fixture changes follow the package-contract decision and must not
  alter unrelated extraction behavior.

## Affected Architecture Docs

N/A — this removes a redundant support artifact without changing runtime
boundaries, data flow, or the paired-evaluation protocol.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The requested outcome is that target distributions stop carrying the unused schema. |
| AC-2 | required | Cleanup must not regress the installed paired-evaluation tool. |
| AC-3 | required | Existing target projects need a clean upgrade path. |
| AC-4 | important | The census guards the no-runtime-dependency premise. |
| AC-5 | not-this-scope | Operator directed that this cleanup is not a CHANGELOG item. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-25 | Planned after a runtime and packaging census showed the schema has no project-tool consumer. | `wf_context_efficiency_eval_response`; exact filename census; build-pack and upgrade tests. |
| 2026-07-25 | Readiness council added a release-note requirement. | The file is unused by project tools but remains an intentionally shipped distribution surface. |
| 2026-07-25 | Withdrew the release-note item by operator direction. | AC-5 and its task are `[~]`; no CHANGELOG entry remains. |
| 2026-07-25 | Removed the schema and replaced its positive distribution expectations with absence and upgrade-pruning coverage. | `test_build_pack.py` 101/101; `test_prune_framework.py` 17/17; `test_upgrade_wavefoundry.py` 350/350. |
| 2026-07-25 | Confirmed the executable paired-evaluation contract remains scorer-backed. | `test_context_efficiency.py` 53/53; `test_server_context_efficiency.py` 67/67. |
| 2026-07-25 | Independent delivery review re-tested the premise instead of accepting it: 19 mutation probes confirm `score_pairs` still rejects every constraint the deleted schema encoded (and is stricter on three), `mode="scaffold"` preserves the producer-facing shape from the same constants, and the prune test genuinely removes an installed copy plus the emptied directory. The emptied local `evals/` directory was removed; it was untracked, so it never reached the repository. | Mutation-probe harness; `test_prune_framework` 17/17; `test_build_pack` 101/101 |
| 2026-07-25 | Review disproved the stated basis for the CHANGELOG exclusion (the file was believed uncommitted; it shipped in v1.14.0). Referred back to the operator, who re-confirmed the exclusion on the verified basis that they are the sole 1.14.0 deployer. AC-5, its task, the Decision Log, and the external-harness risk row now record that reason. | `git merge-base --is-ancestor 4f0c8d4e d3722719`; `git tag --contains 4f0c8d4e` -> v1.14.0 |
| 2026-07-25 | Completed live filename census and docs validation. | No runtime filename reference; closed history retained; `wf_validate_docs` passed. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-25 | Remove rather than retain the schema as a source-only artifact. | The scorer and scorer-derived scaffold are already the canonical executable contract; a second manual contract adds drift risk. | Keep shipping it as a third-party integration contract, or generate it from scorer constants. Neither surface is currently exposed or required. |
| 2026-07-25 | Preserve closed-wave references. | They accurately describe what shipped historically and are not live product guidance. | Rewrite history, rejected. |
| 2026-07-25 | Do not add a 1.15.0 CHANGELOG entry for this cleanup. | Operator direction, re-confirmed after review disproved the original premise. The schema was NOT uncommitted intermediate work: it shipped in v1.14.0. The direction stands on a different and verified basis — the operator is the sole deployer of 1.14.0, so no third party holds an installed copy. | Retain the readiness-council compatibility note, rejected. Add the note anyway as cheap insurance, rejected once the installed base was established as empty. |


## Risks


| Risk | Mitigation |
| --- | --- |
| An undocumented external harness may have discovered and consumed the schema. | RESOLVED, not merely accepted: the schema shipped only in v1.14.0 and the operator is that release's sole deployer, so no external installed base exists. The scorer-backed tool and `mode="scaffold"` remain the supported contract. |
| Previously installed copies linger in target repositories. | Rely on the existing old-vs-new MANIFEST pruning path and retain regression coverage for framework pruning. |
| Tests lose semantic validation that existed only in the schema. | Preserve or add direct scorer assertions for any runtime rule not already covered. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
