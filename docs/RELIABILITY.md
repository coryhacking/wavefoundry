# Reliability

Owner: Engineering
Status: active
Last verified: 2026-09-13

## Reliability Posture

Wavefoundry is local developer tooling. No uptime SLA; failures are
immediately visible to the operator. The primary reliability concern is
**correctness** (valid framework distributions, truthful lint results, and a
semantic index that never serves stale data as fresh) rather than
availability. The shipped posture is fail-soft with visible degradation:
every derived store can be dropped and rebuilt, and readers report degraded
modes explicitly instead of guessing.

## Shipped Reliability Mechanisms

- **Derived-only stores, drop-and-rebuild:** the project index
  (`.wavefoundry/index/index.sqlite`: docs/code chunks, vectors, FTS, the
  code graph and its communities in one SQLite database) is entirely
  derived from the repository. Corruption recovery uses a compatible current
  runtime and rebuild via `index_build` (supported
  index_build content values: `docs/code/all/graph/map/fts`); nothing
  authoritative lives there.
- **Stale-writer refusal:** persisted ordered revisions and the loaded producer
  source contract are checked before preparation and within publication for
  graph, semantic, lexical and chunker/walker writes. Newer or unproven populated
  metadata is preserved with restart guidance. Equal/older supported state
  retains incremental/forward-rebuild behavior. Model and tokenizer identities
  are not numerically ordered. First-hop upgrades from unprotected hosts require
  the confirmed fresh-CLI handoff even at the same schema; host discovery is
  best effort and does not prove every host stopped.
- **Build lock + `lock.held` contract:** whole-index builds serialize on
  `index-build.lock`. The lock FILE persists by design as a last-owner
  record — liveness is the OS lock, surfaced as
  `index_build_status.lock.held` (never inferred from file presence);
  `ended_at` distinguishes a clean finish from an interrupted build.
- **Fail-soft search degradation:** when the semantic store is not servable,
  search envelopes degrade explicitly (`search_mode: lexical_fallback` with a
  named `fallback_reason`) rather than failing or silently serving stale
  vectors. Envelope freshness is a first-class verdict with
  index_freshness states: `current/stale/unknown` — `unknown` means the
  check could not run, never "assume fresh".
- **Persisted build log + versioned state:** index builds append to the
  persisted build log under `.wavefoundry/logs/`; the index database
  (SQLite, state-store schema version `8`) carries builder/walker versions,
  the build epoch, and per-file state, so an interrupted build is detected
  and superseded on the next pass, never trusted.
- **One publication transaction (wave 1xny6):** a build's semantic rows and
  its graph, extraction, community and per-layer bookkeeping rows commit in
  the SAME transaction, so no partial cross-store state can survive a crash.
  The few named control transactions that stay outside it — the durable
  build fence, the secrets-scan cache, post-commit derived-FTS verification,
  freshness/drift/reap residents and the completion compare-and-set — are
  each recoverable on their own. Readers take a generation-bound snapshot,
  so one response never spans two index generations.
- **Forward-only storage recovery (wave 1xny6):** the schema-8 conversion is
  recorded as a versioned kind in the retained `sqlite-migration.json`
  receipt. A failed or refused cutover is recovered by re-running the
  standard upgrade from the retained source; there is no backward rollback
  to the previous runner, and the retained rollback copy is never read back
  into service.
- **Per-layer freshness and the heal:** each layer records its builder
  version (graph builder version `52` currently); a version advance triggers
  re-extraction, and read-side heals repair false-stale verdicts without a
  rebuild.
- **Secrets-scan cache posture:** the secrets scan runs inside index builds
  with a content-keyed cache; classifications live in
  `docs/scan-findings.json` and gate wave close (pending findings block
  close; classification is the acknowledgment).
- **Lifecycle mutation safety (wave 1seax):** the mutating lifecycle MCP
  tools serialize on the advisory per-root `lifecycle-mutation.lock`
  (structured busy response, never corruption), and every multi-file
  lifecycle mutation writes its referencing record last, so a retry after
  any interruption converges forward (locking inventory:
  `docs/architecture/cross-cutting-concerns.md`).

## Known Reliability Risks


| Risk | Affected Domain | Mitigation |
| ---- | --------------- | ---------- |
| `.wavefoundry/framework/` missing or corrupted | All scripts | `git checkout HEAD -- .wavefoundry/framework` |
| VERSION stamp mismatch | build_pack.py / distribution | Always use `build_pack.py`; never hand-edit VERSION |
| Interrupted index build | Semantic search | Detected via the build epoch (`ended_at` absent); the next build supersedes the dead attempt; readers report `index_not_ready` meanwhile |
| Concurrent lifecycle mutations (multi-agent) | Wave records | `lifecycle-mutation.lock` serializes; the loser gets a structured busy response and retries |
| Docs-vs-code fact drift | Trust in tier-1 operational docs | The docs-constants lint binds documented facts to code constants; drift fails the docs gate |


## Recovery Behaviors

- **Framework dir missing:** `git checkout HEAD -- .wavefoundry/framework`
- **Docs gate failing:** with MCP, `wf_validate_docs` (or `wf_audit` for
  combined diagnostics); CLI fallback `wf docs-lint`
- **Hook entrypoints missing:** re-run `wf render-surfaces`
- **Index unhealthy or suspect:** `index_health()` for the verdict;
  `index_build(mode='rebuild')` for the affected layer; `index_optimize` for
  bloat reclaim. Compatibility refusal requires a current host first; preserve
  the index and recovery files instead of deleting or repeatedly rebuilding them
- **Partial zip archive:** re-run `build_pack.py`; idempotent,
  letter-suffixed archives
- **Half-completed lifecycle mutation** (crash between file steps): re-run
  the SAME tool call — admission, removal, and close converge forward by
  design; `git status` shows any intermediate state when in doubt
