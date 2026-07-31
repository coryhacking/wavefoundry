# Review Policy Adoption Baseline

Owner: Engineering
Status: active
Last verified: 2026-07-28

Wave: `1tuoc review-policy-and-delivery-evaluator`
Measured: 2026-07-28
Decision: keep the fresh-install delivery mode `universal`

## Question

Does the corrected post-`1tsyx` lifecycle provide enough evidence to make risk-selected delivery
Council the default without weakening required review?

## Eligible corpus

Only completed waves whose delivery path follows the corrected `1tsyx` contract are eligible. At
measurement time that corpus contains one wave: `1tsyx review-lifecycle-simplification` itself. Older
waves are excluded because their roster and delivery behavior predate the correction this change is
meant to evaluate. Planned or open waves are excluded because they have no terminal delivery result.

The reproducible inputs are:

| Input | SHA-256 |
| --- | --- |
| `1tsyx/wave.md` | `ad73aa0b898035f7b0f27c263811e0e21b826109c0bb6ef298307ed6b6907320` |
| `1tsyx/events.jsonl` | `5d1dc7d39141176aa555fc2c4195afa282130c78742a9537984f78d6ba685233` |
| `1tsyx/1tr85-enh single-pass-review-lifecycle.md` | `4b21d3b0f64a7fbbc9aba6113f90ccb38ce9df90d19383453e0f2014e3cff07e` |

## Replay method

The baseline is the shipped universal policy. The candidate applies the documented targeted trigger
set to the same delivered boundary while retaining every project-required lane. `1tsyx` changes
lifecycle enforcement, upgrade behavior, canonical prompts, and cross-component review authority;
those are full-Council triggers, so targeted mode still requires delivery Council. Its authoritative
ledger contains no specialist-lane approval key beyond the Council and operator keys, so neither mode
can remove a specialist approval in this sample.

## Result

| Measure | Universal baseline | Targeted candidate | Reduction |
| --- | ---: | ---: | ---: |
| Delivery-Council invocations | 1 | 1 | 0% |
| Required specialist-lane approvals | 0 | 0 | 0% |
| Required lanes omitted | 0 | 0 | 0 |

The adoption gate requires at least 20% fewer delivery-Council invocations, 15% fewer required
specialist-lane approvals, and zero omissions. The current evidence meets only the safety condition,
not either materiality threshold. Fresh installs therefore remain `universal`; `targeted` ships only
as an explicit opt-in. A later default change needs a larger qualifying corpus or an explicit operator
decision accepting a smaller measured benefit.

The executable release guard is `review_policy.targeted_default_adoption_allowed`; its three
independent predicates use these exact thresholds, and the fresh-install default consumes the
registered `FRESH_INSTALL_DELIVERY_MODE` constant.

## Limitations

- The sample is one high-risk lifecycle wave, so it cannot estimate the frequency of routine low-risk
  work.
- Zero specialist approvals means the specialist-lane percentage has no positive denominator; it is
  conservatively reported as 0% reduction rather than an undefined favorable result.
- This artifact measures policy adoption, not reviewer quality or token savings.
