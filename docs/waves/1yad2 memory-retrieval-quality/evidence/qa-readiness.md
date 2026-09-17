# QA readiness review

Owner: Engineering
Status: active
Last verified: 2026-09-16

Reviewer: independent QA `/root/memory_holdout`.
Verdict: **approved for implementation**, not delivery/adoption.

The plan fixes quality and performance gates before holdout scoring, explicitly permits non-adoption, requires production-path and shared-source controls, and protects history/status/archive/target contracts. Frozen QA evidence supplies 24 independently authored holdout cases (16 positive, eight no-match), plus five policy cases and a complete corpus snapshot. The baseline public-path probe passed 14/14 controls, including 11/11 existing hermetic invariants. Positive unlabeled returns remain unjudged. The archive-body type erratum in policy-controls.md must be applied explicitly; it changes no relevance labels.

## Integrity checks actually performed

- Verified 24 holdout queries are distinct from the 20 retained development queries, eight have empty expected sets, all IDs exist, and relevant/irrelevant/unjudged sets are disjoint.
- Executed canonical public memory search against scratch fixtures for missing/broken index, semantic hits to excluded statuses, explicit history/status, two compact archive entries and their bodies, target/symbol filters and contradictory active claims. No live store writes.
- Challenged an independent readiness arithmetic oracle with known-bad adoption cases: unchanged result, speed gain hiding quality loss, speed gain hiding an extra false positive, quality gain hiding slower latency, and a dropped empty answerable response. Also checked an exact 20% speed positive control. These are requirements checks, **not tests of an implementation that does not yet exist**.

```json
{
  "unchanged_is_not_material": true,
  "speed_win_does_not_erase_quality_loss": true,
  "speed_win_does_not_erase_false_positive": true,
  "quality_win_does_not_erase_latency_regression": true,
  "uncertain_nonempty_negative_is_false_positive": true,
  "empty_answerable_denominator": true,
  "positive_speed_control": true
}
```

Implementation verification still owes public baseline/finalist parity, raw score/fusion invariants, complete candidate coverage under duplicates and filters, qualification/fault behavior, metrics and privacy mutations, native CPU timing and declared platform coverage. No score, production improvement, supported-platform execution or adoption approval is asserted here. Holdout scoring must occur only after parameter freeze and must not be used for retuning.
