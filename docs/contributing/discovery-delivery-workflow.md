# Discovery and Delivery Workflow

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Working Modes

**Discovery** — use when scope, durable decisions, risk posture, or wave shape are still unresolved. Produce: a refined change doc, architecture decision records, or a wave plan. Output: draft change doc at `docs/plans/`.

**Delivery** — use when scope is approved and wave execution can proceed. Pre-condition: Prepare wave passed. Output: implemented and reviewed changes committed to the repo.

If delivery uncovers a new durable decision or invalidated shared assumption, return to discovery before proceeding.

## Discovery Triggers

- New feature request with unclear scope or multiple valid approaches
- Architecture or integration boundary change
- Security or trust boundary change
- Framework seed or MCP tool contract change

## Delivery Pre-conditions

1. Consolidated change doc exists and is admitted into a wave
2. `Prepare wave` passed cleanly as the immediately preceding lifecycle step
3. Required review lanes identified

## Post-Delivery Verification

After implementation, before wave closure:
1. `python3 .wavefoundry/framework/scripts/run_tests.py` passes
2. `./docs-gardener && ./docs-lint` passes
3. All required review lanes complete with findings recorded in `## Review checkpoints`
4. Docs-contract review disposition recorded (reviewed or N/A with rationale)
