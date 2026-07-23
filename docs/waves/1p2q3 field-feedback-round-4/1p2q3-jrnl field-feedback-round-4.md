# Journal - Field Feedback Round 4

Owner: Engineering
Status: active
Last verified: 2026-06-02

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-02

wave-id: `1p2q3 field-feedback-round-4`

## Operating Identity

- Role: wave-coordinator - coordinating the planned `code_graph_path` result-quality follow-up from field validation after wave `131bt`.
- Responsibilities include: preserve the legitimate external-as-endpoint use case while preventing external nodes from acting as intermediate BFS shortcuts; document the default relation-filter contract shift before implementation.

## Salience Triggers

- **High:** `code_graph_path` returns `found: true` through an intermediate `external::*` bridge with only `imports` / `EXTRACTED` edges. Treat this as the core defect.
- **High:** A fix blocks external nodes entirely, including when the external node is the requested endpoint. The non-transitive rule applies only to intermediate nodes.
- **Medium:** Changing the default traversal to calls-only without seed/doc migration. The no-arg behavior change is a contract shift and needs explicit guidance.

## Distillation

- The Aceiss reproducer shows BFS preferring a short junk path through `external::e` over a longer real call chain. The problem is traversal policy, not endpoint resolution.
- The planned bundled fix covers non-transitive intermediate externals, calls-only default traversal, structural-path diagnostics, and a confidence filter on `code_graph_path`.

## Active Signals

wave-id: `1p2q3 field-feedback-round-4`

- Created 2026-06-02: one planned change, `1p2q4-bug code-graph-path-external-bridge-and-result-quality`.

## Promotion Evidence

- Stable artifact: `docs/waves/1p2q3 field-feedback-round-4/wave.md`

## Retirement And Supersession

- None yet.

## Governance

- No secrets, credentials, or PII in journals.
- Framework script edits require the normal wave stage gate before implementation.
