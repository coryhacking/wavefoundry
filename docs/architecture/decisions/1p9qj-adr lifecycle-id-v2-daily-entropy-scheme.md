# 1p9qj-adr — Lifecycle-ID scheme v2: daily time index + 12-bit deterministic entropy

Owner: Engineering
Status: accepted
Last verified: 2026-07-03

## Context

The v1 lifecycle-ID encoding spends the entire 5-char base36 budget (~25.85 bits) on a pure time axis: `(days_since_epoch × 288 + bucket_5min) mod 36^5` — a 575-year horizon at 5-minute resolution and zero collision resistance. Within one branch the linear-probe dedup keeps mints unique, but two branches (or agents, or clones) minting in the same 5-minute window compute the **identical** prefix — a *guaranteed* cross-branch collision, observed in practice (the `1p9hh` incident) and rising with enterprise rollout (3–10 minters per project). Wave `1p9jn` added detection; this decision is the rate-reduction counterpart. Compounding defects: provisioning was agent-driven seed prose that set a nondeterministic ~5-year-past epoch (`random.randint`), burning horizon 1:1 with elapsed time, and the build suffix was coupled to the mint encoding by a `[-4:]` slice.

## Decision

Adopt scheme v2 for new mints, config-dispatched per repo: `value = OFFSET + day_index × 4096 + entropy`, base36, min-width 5, **no modulo**.

- `entropy` = 12 deterministic bits of `blake2s(kind + "\x00" + slug)` (digest_size 8, big-endian, UTF-8, `% 4096`) — frozen as a contract by a golden-vector test; no RNG, no wall-clock.
- `day_index` = whole days since a **provisioning-time epoch** (install/rollout date), written by code (`upgrade_wavefoundry.py --materialize-lifecycle-policy` / upgrade Phase 2c), never by agent prose.
- `OFFSET`: migrated repos = scanned existing max + a 1-year merge margin (new IDs continue the existing band and sort after all history); fresh repos = deterministic scatter into `[36^3, 619,520)` — first char `0`, second char `1`–`d`, ≥40.0-year worst-case horizon (572,864 start points).
- Past `36^5` the value encodes naturally to 6 chars (never wraps; a 6-char value always sorts after every 5-char value under decode-keyed ordering). Ordering-sensitive listing consumers sort by decoded prefix value, not filename string.
- The same-repo linear probe is retained as tiebreaker; v1 repos keep minting v1 unchanged until the idempotent migration writes `scheme_version: "v2"`.
- The `build_pack` suffix is decoupled: a standalone pure-time index `base36((days × 288 + bucket_5min) mod 36^4)` on a pinned build epoch (1999-05-01, value-identical with shipped packs).

## Consequences

**Positive:**
- The guaranteed same-window cross-branch collision becomes a rare (~1–2 per project-year at 3–10 minters), still-detectable event — a large rate reduction for zero configuration.
- Lex/value order = time order preserved for existing and new IDs across the cutover; fresh installs stop burning horizon on past epochs.
- Provisioning and migration are deterministic, idempotent, atomic, and unit-testable code.

**Negative / tradeoffs:**
- Daily (not 5-minute) time resolution for new IDs; same-day mints order by hash entropy, then probe.
- 12-bit entropy is rate reduction, not prevention — only explicitly-assigned node IDs guarantee disjointness (deferred).
- The "new > all existing" invariant is time-bounded by the merge margin (~1 year of v1 sibling-branch drift).

**Constraints imposed:**
- The blake2s entropy mapping (variant, digest_size, byte order, separator, encoding, `% 4096`) is frozen under `scheme_version: "v2"`; any change requires a new scheme version.
- `epoch_utc`, `offset`, `scheme_version` are code-provisioned and must never be hand-edited after provisioning.
- ID-format consumers must accept 5–6 char prefixes and sort by decoded value.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Widen IDs to 6–7 chars | Hard operator constraint: stay 5 chars. |
| Random/UUID-style entropy | Breaks determinism/reproducibility and the no-RNG convention. |
| Explicit per-minter node IDs now | Requires an operator assignment surface not yet justified at 3–10 minters; layout reserved (`node_bits`, unset = full 12-bit hash) so a later carve is config-only. |
| Global fixed epoch + offset | Per-repo scanned offset self-adjusts to each repo's history; a global value either wastes band or under-clears history. |
| Keep `% 36^5` wrap | A wrap silently re-orders every listing; the no-modulo 6-char overflow is a safety valve with no overlap by construction. |

## Forward compatibility

When explicit node assignment ships, the top 4 entropy bits become `(node_id << 8) | (hash % 256)` **only when `node_bits` is set in policy**; node unset = full 12-bit hash (today's behavior, pinned — a hard 4/8 split from day one would silently narrow entropy 4096→256). Carving later never changes already-minted values and must be flag-stamped in policy, not silent.
