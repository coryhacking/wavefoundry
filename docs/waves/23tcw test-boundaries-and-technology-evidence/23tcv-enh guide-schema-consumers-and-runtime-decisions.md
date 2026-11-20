# Guide Rust schema consumers and runtime performance decisions

Change ID: `23tcv-enh guide-schema-consumers-and-runtime-decisions`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23tcw test-boundaries-and-technology-evidence

## Product Intent

These questions help maintainers make two independent decisions when a technology change is under consideration:

- **Can we rely on this generated decoder for this contract?** The Rust builder presents independently produced payloads from each supported version. QA checks that valid payloads decode and that changing one relevant constraint produces the expected rejection at the responsible layer. A valid-response failure is enough to decline the decoder for that use. AC-1 checks that judgment.
- **Is a runtime comparison worth running?** The builder identifies how much CPU time or tail latency the production workload spends on transport. When that attribution is missing, the useful outcome is a decision to retain the current runtime and identify the next measurement. When the profile implicates transport, QA can specify a matched trial on the affected OS. AC-2 checks both decisions.

The worked examples establish whether reviewers can use the guidance. At the next relevant project evaluation, look for the decision the team made and the evidence it cited.

## Rationale

Tensorwell wave `0evgw` evaluated Typify 0.10.1 for one endpoint and assessed a possible runtime migration. The following results come from its wave record and change `0evgv`. Wavefoundry has not independently repeated the evaluation.

### Schema consumer

Two model-free HTTP tests produced valid v1 and v2 responses for `GET /v1/capabilities` independently of the generator. The Rust decoder generated from the published OpenAPI 3.1 contract rejected both. It also rejected copies with swapped version tags. Since it already rejected the valid originals, those rejections do not establish version enforcement. Changing only the v1 supported-workloads list from `["interactive", "batch"]` to `[]` yielded a payload the decoder accepted despite the schema's two-item minimum. Tensorwell declined Typify 0.10.1 for this endpoint. Other schemas and generator versions require their own evidence.

### Runtime decision

Tensorwell retained Tokio. Its existing measurements varied inference-worker topology and could not isolate transport cost. No Compio benchmark ran. A later transport trial would need to cover buffer lifetime, deadlines, cancellation and graceful shutdown on the affected OS. Keep runtime names in the field rationale. Tensorwell references: `docs/api/openapi.json`, `docs/api.md`, and `crates/tensorwell-daemon/src/service.rs`.

## Requirements

1. When a Rust project evaluates a generator for a separately versioned JSON contract, ask: “Does the generated decoder accept a real response from every supported version and reject a minimally corrupted copy for the expected reason?” Pair independently produced positive fixtures with single-change negative controls for the schema features the project relies on. Identify which layer enforces each constraint. A same-generator round trip alone cannot establish compatibility. Cite [Typify](https://github.com/oxidecomputer/typify) as an optional example.
2. When performance motivates a runtime migration, ask: “Which production measurement attributes material CPU use or tail latency to transport, and what comparison would show the candidate runtime improves it?” If a representative profile supports a trial, hold handler, application work, payload, concurrency and connection reuse constant. Compare end-to-end tail latency and CPU use on the affected OS and replay deadlines, cancellation and graceful shutdown. If attribution is missing, name the measurement needed to decide whether a trial is worthwhile.
3. Ensure builders can find these questions when proposing a change and QA reviewers can find them when judging evidence. Reuse the Rust baseline and performance guidance as owners. Keep both questions conditional on the relevant evaluation.

## Scope

Guidance and its appropriate local counterparts only. The Rust baseline owns the schema advice. Seed 212 already asks the reviewer to identify hot paths and qualify performance claims; extend it at the decision point. Locate the corresponding builder instruction before editing. No generator installation, runtime switch, production access, or changes to Tensorwell are needed.

## Acceptance Criteria

- [x] AC-1: Given Tensorwell's positive, swapped-tag and empty-list results, the reviewer identifies the valid-response failures, explains why discriminator enforcement remains unproven, and identifies the accepted minimum-length violation. The reviewer recommends declining Typify 0.10.1 for this endpoint and identifies which observations justify that decision.
- [x] AC-2: Given only worker-topology measurements, the builder recommends retaining the current runtime and names a measurement that could justify a trial. For a hypothetical profile that does implicate transport, QA can identify the fixed workload, comparison metrics and lifecycle behaviors needed to interpret a runtime trial.
- [x] AC-3: Following ordinary builder and QA instructions reaches the relevant conditional advice without adding a new review lane.

## Tasks

- [x] Add the situational Rust entry and its example, source and costs.
- [x] Reconcile builder and QA/performance-review guidance at the points where a change is proposed and evaluated.
- [x] Exercise both examples and validate the affected documents.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guidance | Documentation writer | Readiness | One writer for both practices |
| Examples | Reviewer | Draft | Separate schema and runtime cases |

## Serialization Points

- `.wavefoundry/framework/docs/rust-practices.md`, `.wavefoundry/framework/seeds/180-implement-spec.prompt.md`, `.wavefoundry/framework/seeds/212-performance-reviewer.prompt.md`, `docs/agents/implementer.md`, `docs/agents/performance-reviewer.md`, `docs/agents/qa-reviewer.md`, `.wavefoundry/framework/seeds/239-qa-reviewer.prompt.md`

## Affected Architecture Docs

No architecture change proposed.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Checks the contract against independent wire evidence. |
| AC-2 | required | Checks that a runtime proposal follows a measured workload. |
| AC-3 | required | Both roles must be able to use the questions. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Recorded Tensorwell engineering feedback. | Rust baseline states that project records govern tool choices; seed 212 already asks reviewers to use the project's workload. |
| 2026-11-19 | Readback: choose evidence for the decision in scope. | Exercise ordinary role instructions against the case observations before sharing the scoring criteria. |
| 2026-11-19 | QA declined the evaluated decoder on valid v1/v2 failures and the accepted empty list. Swapped-tag rejection was inconclusive. Builder retained the runtime on worker-only measurements. QA specified the controlled transport trial, metrics and lifecycle checks. These are exercises against supplied observations. | Fresh role readers used the normal role entry points before seeing the scoring criteria. Full docs lint passed. |
| 2026-11-19 | Corrected the two seed instructions after the partial-install audit exposed links that broke when copied into a project. | Independent reviewer rendered a downstream fixture twice, resolved six paths and exact headings, and rejected the obsolete relative link and twelve altered paths or titles. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Put schema generation in situational Rust guidance and workload measurement in shared guidance. | Each practice reaches its relevant audience. | Naming a preferred runtime would generalize beyond the evidence. Requiring Typify for every JSON payload would extend the advice beyond independently versioned contracts. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Successful generation is mistaken for wire compatibility. | Demonstrate a fixture drawn independently of the generator under test. |
| A benchmark of an unrelated workload steers a runtime decision. | State the actual workload, the time breakdown and the limits of the replay. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
