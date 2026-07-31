# 1tsbu-adr — Review-policy authority and upgrade protocol 2

Owner: Engineering
Status: accepted
Last verified: 2026-07-28

## Context

Review readiness, delivery review, and close independently re-derived overlapping policy and diagnostic state. The universal Council default was valuable but expensive for low-risk delivery, while merely changing the default without persisted provenance would let lifecycle boundaries disagree. Upgrade also had to retire already-installed lifecycle prose and reproject in-flight waves, but the supported-floor runner could extract feature code before it knew how to require the new migration. Its JSON sentinel was recovery state, not process exclusion.

## Decision

1. `wave_review.enabled` controls readiness and `delivery_mode` is exactly `disabled | targeted | universal`. Fresh and legacy-enabled installs remain `universal`; legacy-disabled installs become `disabled`.
2. Prepare alone derives the ordered specialist roster and appends a parent-bound `review_policy_receipt` to the canonical wave ledger. Readiness approval binds that receipt. Review and Close consume it without selecting a different roster.
3. Review and Close use one shared delivery evaluator. Close adds only a finite registered closure-only diagnostic set.
4. Executed review evidence carries caller-authored integrity facts, and approvals carry explicit readiness/delivery phase currency.
5. One typed carrier registry assigns each review-policy surface to `renderer`, `lifecycle_reconciler`, or `direct_docs`. The reconciler may replace only exact registered legacy sections or managed regions and refuses ambiguity before any write. Validation-only direct documents may share a destination with a separate renderer companion that owns only the portable marker-bounded policy baseline; project prose outside that region remains immutable.
6. Upgrade and lifecycle mutations share the strict lifecycle lock, then the project publication lock, releasing in reverse. The durable upgrade checkpoint is recovery state only. Unrelated publishers fail fast while it exists; only memory recovery writers are allowed at the exact validation pause.
7. Distribution protocol 2 makes pack metadata mandatory before extraction. Protocol-1 runners use the builder-emitted, framework-only bridge archive and standalone stdlib bootstrap, which verifies hashes and host quiescence, atomically swaps only the framework tree with rollback, then directs the operator to retry the exact feature pack under protocol 2.

## Consequences

- Targeted delivery review is an explicit opt-in; the shipped default does not silently reduce review.
- Policy changes invalidate bound readiness without rewriting historical approval rows.
- Closed waves remain byte-immutable during upgrade; non-closed declared waves are marked and reprojected, then must re-Prepare.
- A malformed or unknown feature pack stops before extraction. The bridge is an installation mechanism, not a product release, and cannot write project surfaces.
- Every authority-bearing mutation fails closed when lock ownership cannot be proven.
- Pre-existing projects receive portable policy vocabulary through owned regions before the new carrier gate runs; absent conditional documents remain absent.

## Alternatives considered

- **Re-derive policy at Review and Close.** Rejected because independent derivation can silently drop lanes or change Council requirements.
- **Keep separate Review and Close implementations.** Rejected because their shared diagnostics repeatedly drifted; making them identical was also rejected because Close owns real terminal-only controls.
- **Prose-directed carrier cleanup.** Rejected after repeated review showed exact wording and scope drift; the reconciler makes ambiguity a typed failure.
- **One-hop protocol-1 upgrade.** Rejected because the old runner cannot make new mandatory code load before extraction or prevent its own post-extract project writes.
- **Treat the JSON checkpoint as a lock.** Rejected because durable state does not provide mutual exclusion.

## References

- Wave `1tuoc review-policy-and-delivery-evaluator`
- Change `1tsbu-enh review-policy-and-delivery-evaluator`
- `docs/architecture/data-and-control-flow.md`
- `docs/contributing/review-and-evals.md`
