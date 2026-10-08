# 20355-adr — The council moderator actor and role are `council-chair`

Owner: Engineering
Status: accepted
Last verified: 2026-10-08

## Context

The council moderator actor and role were named `wave-council`. Wave `1zyb4` (change `1zxnx`) made the council signoff keys neutral (`council-readiness`, `council-delivery`) but kept the actor and role. A distribution that calls its delivery unit something other than a wave therefore still records, displays and lints a role named after waves. The Waveforge maintainers reported this seam publicly (R7), and the operator decided to rename the actor and role in full while every recorded approval keeps its meaning. Ledgers are append-only and every event identity hashes its actor, so recorded history cannot be rewritten.

## Decision

The council moderator actor and role are `council-chair` (`review_evidence.COUNCIL_ACTOR`), with seed `215-council-chair.prompt.md` and role doc `docs/agents/specialists/council-chair.md`. The earlier name stays in `review_evidence.LEGACY_COUNCIL_ACTORS` forever: an approval recorded by it is a valid council approval in the status projection, the independence and distinctness checks and lane logic; `wf_review_event` given it records `council-chair` and returns an `actor_alias` notice; and a replay of an approval first recorded under it is recognized by its stored identity. The legacy key prefix `wave-council-` is frozen as a literal, so earlier and distribution-configured `wave-council-<x>` keys stay council keys, and no prefix is derived from the new name. The review-policy digest maps `moderator_role: council-chair` to the earlier spelling, so the configuration edit rotates no receipt. The renderer moves an existing role doc and native wrappers byte-for-byte; docs-lint accepts the role doc at either path and the earlier `Role:` value.

## Consequences

**Positive:**
- A distribution records, displays and lints a role whose name carries no delivery-unit noun.
- Every recorded approval, ledger and closed wave record keeps its meaning without a rewrite.
- Callers and prompts written before the rename keep working through the input alias.

**Negative / tradeoffs:**
- Two actor names are accepted on read forever, so every actor comparison goes through `COUNCIL_ACTORS` or `canonical_council_actor`.
- The earlier name remains in a small, census-listed set of legacy acceptance sites.

**Constraints imposed:**
- A new actor comparison must accept every council actor name; the actor-token census in `tests/test_distribution_seams.py` lists each remaining occurrence of the earlier name with its reason.
- Recorded events, ledgers and closed wave records are never rewritten to the new name.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| `council` | Filtered by the prepare roster's hyphenated role-token rule, and a prefix of both current council keys. |
| `council-moderator` | Matches `moderator_role`, but ADR `1p5be` retired it as the earlier name of this same role; reviving it would make historical records ambiguous. |
| `review-council` | Inverts `council-review` (seed 237). |
| Refuse the earlier actor on write | Breaks every older prompt surface at once. |
| Derive the legacy key prefix from the new actor | `council-chair-*` keys would gain a meaning nobody asked for. |

## References

- Change `200ew-enh distribution-seams-and-neutral-council-role` (wave `200ey`)
- ADR `1p5be-adr retire-canonical-names-rename-manifest.md` (history, not edited)
- `.wavefoundry/framework/seeds/215-council-chair.prompt.md`
