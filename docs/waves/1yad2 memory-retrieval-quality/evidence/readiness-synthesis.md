# Memory retrieval readiness synthesis

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Decision

Phase: readiness. Verdict: **approve the evaluation-first scope**, with production adoption remaining conditional on the admitted architecture decision and frozen quality/performance gates. No unresolved readiness blocker remains. This is not approval of relevance-first production behavior, a delivered implementation, or closure.

Local prepare policy selected standard-depth targeted review: red-team primer, independent docs-contract-reviewer seat, and synthesis. The generic fixed-seat/full-depth council was not run. The moderator is the same actor and context as the primer (`memory_readiness_primer`), distinct from the coordinator/implementer and independent docs seat. That reuse is explicit; no independent-primer-versus-moderator claim is made.

## Merit-first assessment

The one independent seat was first assessed as Seat 1 on its evidence and reasoning. Its source-verified observations support the plan's diagnosis: current sampled self-summary evaluation is insufficient, memory candidates are filtered after ordinary docs limits, and current policy precedes query relevance. Its executed controls demonstrate current aggregate response, unavailable evidence, empty candidate and non-adoption behavior only. Those observations justify building the proposed evidence; they do not establish that either finalist wins.

Reattached identity: Seat 1 is `docs-contract-reviewer`, recorded in [readiness-contract-review.md](readiness-contract-review.md). Its approval is scoped to readiness with no remaining docs-contract blocker. There is no multi-seat consensus inference from this single independent seat.

## Primer response and resolved improvements

The strongest challenge was conflating candidate discovery, relevance and authority. The revised [readiness contract](readiness-contract.md) separates them: experimental relevance-first applies only to explicit free-text queries; architecture approval and measured adoption precede integration; target-only, brief and advisory ordering remain unchanged. Active contradictions require provenance, not similarity-based supersession.

The evidence question is resolved by independent QA ownership, immutable development/holdout separation, the actual public production baseline and a shared-candidate-source ablation. All answerable queries remain in denominators, including empty responses; every nonempty no-match return is a false positive even if labeled uncertain; judged irrelevant and unjudged outputs remain separate. Minimum effect and performance budgets are fixed before scoring.

Resource limits distinguish 20 distinct candidates per channel, a maximum 40-record union and 20 public results from physical scan work. The contract permits an exact eligible-chunk scan with reported population and timing, not a false sublinear-work claim. Safety-bound exhaustion cannot masquerade as complete coverage. The docs seat added a necessary archive identity clarification: multiple compact register entries share a manifest path but retain individual memory IDs and lexical eligibility; grouping body vectors by path cannot collapse these entries.

The contract now limits ordinary MCP evaluation to aggregates and detailed evidence to explicit local artifacts. Delivery must additionally test leakage through values and diagnostics, not just forbidden response keys. These are admitted obligations, not new feature scope.

## Alternative and tradeoff

Strongest alternative: deliver a reusable evaluator and truthful non-adoption report if neither finalist passes, leaving production ranking unchanged. This is preferable to forcing a marginal measured winner through unresolved authority or no-match behavior. Cost: immediate retrieval gains may not ship in this wave. Benefit: trustworthy selection infrastructure and protected current behavior. A candidate-source-only improvement is measured as an ablation, not an escape hatch around the same adoption gates.

Seat agreement aggregate: `unanimous` within the selected targeted review (primer recommendations incorporated; one independent approving seat). Maximum unresolved severity: `none`. No targeted challenge round was necessary; no required specialist finding was waived. Remaining architecture, code, QA, performance, security and docs delivery lanes retain their authority.

## Evidence integrity and approval facts

- Suggested signoff: `wave-council-readiness`; verdict: approved for gated evaluation and conditional integration only.
- Moderator actor/context: `memory_readiness_primer`; shared with primer, separate from coordinator/implementation and docs seat. No implementation or repair had occurred in this review scope.
- The moderator recomputed SHA-256 of the admitted plan, readiness contract and primer; all three exactly match the independent seat's recorded digests. This establishes artifact identity, not correctness by hashing.
- Source mechanism verification and the four passing existing tests plus four direct assertions belong to the docs seat, not to moderator execution. See its report for commands, expected/observed results and macOS Python 3.13 limits.
- No proposed product behavior was executed, no holdout scored, and no source mutated by this review. No native Windows/Linux, GPU, full-corpus quality or scaling qualification is claimed.
- The reviewer conclusions preserve negative and unavailable controls and distinguish current implementation observations from future requirements. The retained exploration remains explicitly non-independent exploratory evidence.
- No typed event was authored by this moderator; coordinator records the approval and reruns Prepare before opening implementation.

## Follow-through

Freeze final normalization and any relevance representation/threshold before holdout scoring, execute matched cold/warm measurements including complete response costs, verify archive/history and duplicate-heavy behavior, and record adoption or non-adoption against the declared gates. These are implementation/delivery tasks, not conditions silently represented as already tested.
