# Readiness Review: Retire Optional Server Aliases

Owner: Engineering
Status: active
Last verified: 2026-09-25

## Round 1 (receipt `review-policy-9a919bf44bf6a558e0c0`)

| Lane | Verdict | Blocking findings |
| --- | --- | --- |
| code-reviewer | approve | none |
| qa-reviewer | approve | none |
| release-reviewer | block | CRQ-READY-5: the plan assumed 1.27 shipped the aliases; 1.27.0 is untagged and carries full flat modules, and `1yzd0` is unreleased, so the changelog and upgrade matrix must be framed as one release |
| architecture-reviewer (rotating seat) | block | ARCH-READY-1: narrowing `_FLAT_ALIASES` drops the stale-copy refusal, old-runner flat-key eviction and reserved-name pin for the ten |
| docs-contract-reviewer | block | DOCS-READY-1: a second changelog bullet would contradict the unreleased `1yzd0` bullet |
| red-team (fixed seat) | block | RT-READY-1: executed; a restored full flat `index_handlers.py` imports silently once the table narrows |

Non-blocking findings folded into the same repair:

- The old-runner mechanism wording (ARCH, RT-READY-5).
- The census predicate and re-derived counts: `import_module` calls, embedded scripts, bare-name checks, and a vacuous assertion (CRQ-READY-3, ARCH-READY-2, RT-READY-3).
- The 1.26 in-process reload test (CRQ-READY-1, RT-READY-2).
- The new-layout evaluator test (CRQ-READY-4).
- The executed `project_context_efficiency` check (RT-READY-6).
- The fixture ref for 1.27.0 (ARCH-READY-3, RT-READY-4).
- The complete stale-docs list and a dated ADR amendment (DOCS-READY-2, DOCS-READY-3).

Strongest challenge (both seats): the gain is ten fewer three-line files at the cost of guard rework and an evaluator re-receipt, justified only if nothing released carries the aliases. The repaired plan requires one release with `1yzd0`.

Strongest alternative: keep the twelve-entry refusal and purge while deleting the files. The repaired plan adopts it as `_RETIRED_FLAT_NAMES`.

## Round 2 (receipt `review-policy-60db6ebc9b7c940b8775`)

Every lane (code, QA, release, architecture, docs-contract) and both council seats (red-team fixed, architecture rotating) approve; all round-1 findings are resolved against the tree. Non-blocking notes are carried as implementation notes in the change doc Progress Log: explicit unlink of the retired files by the new pack's upgrade hook, the operator-visible remedy when the refusal fires, an unproven-prune upgrade case, and evidence citation for the reload probe.

Strongest challenge (red-team): removal otherwise depends on the MANIFEST-diff prune; the refusal turns every prune gap into a server that will not start. Strongest alternative: have the new pack's upgrade hook unlink the ten files, adopted as implementation note 1.
