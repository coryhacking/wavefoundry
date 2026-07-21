# Context Efficiency Signal Contract

Owner: Engineering
Status: active
Last verified: 2026-07-20

Wavefoundry reports one conservative estimate of tokens saved while its tools
support a wave. The estimate is an accounting signal, not a billing record and
not a causal claim about what a model would have done without Wavefoundry.

## Closed ledger

Each wave phase uses this closed equation:

```text
direct net =
  content source credit
  + structural source credit
  + workflow prompt credit
  + derived artifact credit
  - request debit
  - response debit

estimated token savings =
  max(0, direct net + matched-pair residual)
```

Derived artifact credit is avoided WRITING: the UTF-8/4 size of textual
artifacts a tool persisted that the caller did not supply (canonical review
ledger records and their projections, drafted memory records, generated
change-doc scaffolds, and the platform surfaces a sync render actually
changed — its manifest records new-or-changed content from inside the write
chokepoints, so a byte-identical re-render credits nothing), floored per
artifact after subtracting the caller-supplied request. It is a deterministic byte count of a real persisted
artifact — never an estimate of what an agent "would have" done manually;
that counterfactual remains gated behind paired evaluations. Tools that
derive nothing textual (validation, gardening, gates, audits) are
instrumented debit-only: every first-party `wf_`/`memory_`/`index_` call now
records its request/response cost, so phase totals no longer silently omit
the non-retrieval surface. Replays deduplicate through stable artifact event
identities derived from the operation's request digest.

Artifact tools may additionally carry content source credit for the state
files they demonstrably READ on the caller's behalf — the evidence tool
consumes the canonical ledger and the wave record to validate, order, and
re-project; the memory validator reads the candidate record; the proposer
reads its source change docs; the change lookup returns the documents it
read, so it credits exactly the docs whose content its response conveys
(untruncated rows only). These ride the same source-proof machinery as
retrieval credit (opaque identifiers, stat-signature versions, once-only per
wave/phase/source/version), so an unchanged file credits once per phase while
a grown ledger legitimately earns a fresh credit for its new version. Tools
that read nothing for the caller (memory_add, the scaffold generators) carry
no source credit. Listings credit a bounded middle ground: never the whole
swept corpus (whole-file credit for every listed document would scale with
repository history rather than information delivered), and never zero —
instead exactly the LIVE set the response enumerates. `wf_current_wave` and
`wf_list_waves` credit only non-closed wave records; `wf_list_plans` credits
the pending plan docs it lists (pending by construction); `wf_map` credits
the one resolved existing document; `memory_search` and `memory_brief`
credit the capped set of record files they surface — each surfaced row names
a real record an agent without the tool would have opened. Credit therefore
tracks work in flight, not repository age; the closed-history tail never
credits. The remaining counterfactual (what an agent would have read beyond
the live set) belongs to paired evaluations. The bright line is unchanged:
this is avoided reading of named files at measured sizes, never an estimate
of agent behavior.

The `wave.md` projection intentionally shows only:

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |

The SQLite authority retains the components for audit and testing.

## Retrieval credit

The 20 retrieval tools are:

- `code_ask`, `code_search`, `code_lexical`, `docs_search`
- `code_keyword`, `code_pattern`, `code_constants`
- `code_read`, `code_hover`, `code_outline`, `code_definition`,
  `code_references`, `code_callhierarchy`
- `code_impact`, `code_dependencies`, `code_callgraph`,
  `code_graph_path`, `code_graph_community`, `code_risk_score`
- `code_commit_provenance`

A retrieval event always debits the canonical request arguments and the complete
public response. It may credit contained project files that would otherwise
have had to be read to obtain the returned content or structure.

Content-bearing responses use their returned file paths. Structural tools use
only their documented path fields:

- `code_dependencies.data.path`
- `code_impact.data.path`, `importers[*].file`, and
  `affected[*].source_file`
- `code_callgraph.data.nodes[*].source_file`
- `code_graph_path.data.path_nodes[*].source_file`
- `code_graph_community.data.nodes[*].source_file`
- `code_risk_score.data.results[*].source_file`

Paths are converted to opaque identifiers before persistence. A source version
is credited at most once for `(wave, phase, source, version)`, even when both a
content and a structural tool return it. A changed version or a new phase may
earn a new credit. Source size uses UTF-8 bytes divided by four; a stable serving
epoch or read boundary marks the measurement verified, while an already-known
contained current/captured size is labeled estimated. Telemetry never performs
an otherwise-unneeded whole-file read merely to increase credit.

A phase stores at most 100,000 source identities. Later unique sources are
reported as dropped credit while their request/response debits still count.

## Lifecycle credit

The five lifecycle tools are `wf_create_wave`, `wf_prepare_wave`,
`wf_implement_wave`, `wf_review_wave`, and `wf_close_wave`.

Stage accounting uses exactly three canonical stage values — `plan`,
`implement`, `review` — and the rendered Context Efficiency table shows its
rows in that fixed order. Lifecycle tools map onto them as: create and
prepare stamp `plan`; implement stamps `implement`; review and close stamp
`review`. No other stage value is ever written, and the code recognizes no
legacy vocabulary (pre-rename records were cleaned up once, by hand, when
this model landed).

Checkpoint publication is symmetric with the stages: activation publishes the
`plan` totals, the implementation-phase review publishes the `implement`
totals (a review that ran publishes even when signoffs are still pending —
the normal pre-close state; a review that could not run publishes nothing),
and close publishes the `review` totals, then seals and compacts. The review
tool remains observational with respect to wave state: the only file write it
performs is the marker-owned checkpoint block.

The retrieval-posture sensor rides on this telemetry: `wf_implement_wave`'s
activation response carries an in-band `retrieval_posture` directive (rule,
`Gapfill:` escape hatch, and the advisory it clears), and the
implementation-phase review and close dry-run compute a
`retrieval_posture_gap` when implement-stage retrieval events are at or below
`sensors.retrieval_posture.max_retrieval_calls` (default 0) while the changed
non-docs file footprint is at or above `min_changed_files` (default 5). A
recorded `Gapfill:` entry anywhere in the wave record clears it. At review
the gap is an advisory diagnostic that never affects the review status; at
close it is surfaced in the response data and never blocks by itself. The
implementation-phase review response also carries an
`implement_stage_telemetry` summary (stage totals plus retrieval-call count)
so the delivery council reads the numbers in context.

Every call that reaches a lifecycle handler records its request and response
debits. A completed new milestone may also credit exactly one contained
project-local lifecycle prompt. Dry runs, refused operations, retries that do
not advance state, and incomplete reviews receive no prompt credit, but their
debits remain in the ledger.

General retrieval work performed with no lifecycle focus first tries
open-wave attribution: when exactly one wave is OPEN (`active`/`implementing`),
a focus-less producer attributes the event to that wave directly — stage
`implement`, or `review` once the wave's canonical ledger holds a delivery
run record — marked with `open_wave` provenance in the store. This is what
captures helper-agent sessions (planners, reviewers, second implementers)
that never run the lifecycle gates themselves. Zero OPEN waves, more than
one, or any resolution failure keeps today's general-bucket behavior; the
resolution is TTL-cached and never blocks or fails the tool call. The
totals may therefore include exploration not exclusive to the wave — the
same honest-labeling caveat the general note has always carried.

Work that still lands in a general bucket remains isolated by producer. Each
producer holds a random identity plus a crash-released OS lease. Successful
create or prepare transfers the invoking producer's general events and source
credits into the target wave, and the implementation-phase review and a
mutating close do the same — so exited helpers' buckets land on THIS wave at
the boundary that follows their work, not on the next wave's prepare. Adopted
rows are marked `adopted` and stamped with the wave's stage at adoption time
(`plan` while planned, `implement` while OPEN, `review` once the ledger holds
a delivery run). Boundaries may atomically claim producers whose persisted
lease is provably unheld. Live peers and ambiguous/missing leases remain
untouched; concurrent claims serialize through SQLite. Events and debits move
exactly once; repeated source/version pairs from different producer buckets
collapse under the target phase's once-only source-credit key rather than
being double-counted.

## Durable authority and projection

`.wavefoundry/logs/context-efficiency.sqlite` is the live write-through
authority. It is created lazily on the first eligible recorded event, not by
installation, upgrade, rendering, or read-only inspection. SQLite uniqueness
constraints provide cross-process event replay protection and phase/source
deduplication.

`wave.md` is a portable, marker-owned checkpoint:

```html
<!-- wave:context-efficiency begin -->
...
<!-- wave:context-efficiency end -->
```

Lifecycle projection boundaries update it under the shared wave writer lock.
Pending generations are also projected before MCP reload and before framework
upgrade. Projection is idempotent and uses a generation compare-and-set so a
newer event cannot be marked published by an older projection.

Close publication seals the wave at that exact generation. After the Markdown
replacement and SQLite compare-and-set both succeed, payload-bearing event,
source, phase, and evaluation rows are replaced transactionally by the
cumulative published floor. Reads add that floor to any rows from a later
reopen. Compact event-ID tombstones retain exact replay protection; source
deduplication and paired evaluations remain fully authoritative in every active
phase. A failed compaction remains discoverable as pending and is retried at
reload/upgrade or the next lifecycle projection.

The SQLite store has a random instance identity. If an active checkpoint names
an identity that the current store cannot prove, the wave becomes
`credit_history_unavailable`; numeric totals are not reconstructed from an
active checkpoint. A closed, validator-valid checkpoint is different: it is the
durable sealed aggregate and can restore the compact floor after disposable
store loss. This is the first shipped telemetry schema, so no versioned
pre-release compatibility layer is retained.

## Failure semantics

An event transaction either commits atomically or writes the durable
`.wavefoundry/logs/context-efficiency.gap` poison marker. While poisoned, the
public headline is zero and new positive credit is refused. If neither the event
nor the poison marker can be persisted, the public tool call fails with
`telemetry_persistence_failed`; otherwise telemetry does not alter the core tool
result. Exceptions raised before the ordinary commit path use the same poison
or fatal-failure decision; they cannot silently return an unaccounted success.

Store health is explicit: `absent`, `healthy`, `accounting_gap`, or `failed`.
An unreadable store never masquerades as authoritative zero.

## Saved output and avoided tool loops

Direct accounting covers source/prompt input credit and the request/response
debits actually observed. Saved model output and avoided tool loops are counted
only by a pre-registered, quality-equivalent paired evaluation.

The applicability key fixes the wave, phase, stage, task specification,
repository snapshot, model and model version, and tool configuration. An
artifact needs at least five completed pairs. The assisted arm must be no worse
than the baseline on correctness, completeness, evidence, and maintainability.
Each arm declares provider-reported usage and rubric scores completed blind before
the arm labels were unmasked. Attachment rechecks the five-pair quality gate and
requires every reported assisted direct-net value to match the authoritative
phase ledger; a caller cannot supply a larger or smaller unbound direct-net
subtraction.
For each qualifying pair:

```text
residual = max(
  0,
  baseline input + baseline output
  - assisted input - assisted output
  - assisted direct net
)
```

The attached residual is the minimum across qualifying pairs. One evaluation is
active per phase. Replay is idempotent; replacement must explicitly supersede
the active evaluation; revocation removes its contribution. The checkpoint
retains both `matched_pair_residual` and `paired_evaluation_count`, so a
non-zero residual and its active quality-qualified evidence count remain
auditable without expanding the human table. Pair artifacts are
operator-supplied evidence and are not collected automatically.

Producing an artifact is a guided flow: register the applicability, generate a
skeleton with `wf_context_efficiency_eval(mode='scaffold')` (its shape derives
from the scorer's own canonical constants, and unfilled placeholders are
rejected by the scorer so a scaffold can never accidentally qualify), run and
blind-score the pairs, fill, and attach. The full protocol is
`docs/references/context-efficiency-paired-evaluation.md`.

## Privacy and limits

The store retains opaque source/version identifiers, token estimates, tool
names, wave/phase/stage identifiers, event IDs, evaluation digests, and
aggregate state. It does not persist query text, response content, prompts,
source paths, or model conversations.

The estimate demonstrates attributable context efficiency under this contract.
It does not establish provider billing savings, latency improvement, or
counterfactual causality.
