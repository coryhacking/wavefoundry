# stdout-is-a-contract-when-something-parses-it

Owner: Engineering
Status: active
Last verified: 2026-07-22

Memory ID: `1tax0-mem stdout-is-a-contract-when-something-parses-it`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-07-22
Updated: 2026-07-22
Source event: `finding:1tbvp:run-garden-stdout-contract-break`
Validation: promote
Validated by: agent
Action delta: Before changing any subprocess's stdout wording, census who parses that output; prose-grep contracts (like the retired 'wrote' grep) must be replaced with an exact-prefix machine line tested against the real producer.
Validation rationale: The drafted candidate again extracted its target from the verification command (run_tests.py) instead of the contract surfaces (docs_gardener.py stdout and server_impl.py run_garden). The durable lesson is real and two-sided: changing gardener stdout silently broke run_garden's 'wrote' grep and with it the wf_garden_docs index-refresh trigger, and the suite missed it because RunGardenTests fed a hand-written fixture instead of canonical producer output.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1tbvp changed the docs gardener's stdout summary and silently broke run_garden() in server_impl.py, which detected updates by grepping output for 'wrote'; wf_garden_docs then reported files_updated 0 on stamping runs and stopped triggering the background docs-index refresh. The suite missed it because RunGardenTests fed a hand-written 'Wrote docs/foo.md' fixture (fixture-echo class). Before changing any subprocess stdout, census its parsers (code_keyword over distinctive output words); prefer an explicit machine-parseable line (docs-gardener: updated <path>) documented as a contract on both sides, with an integration test running the real producer.

## Evidence

- `run-garden-stdout-contract-break`
- `ev-run-garden-stdout-contract-break-3`
- `1tbvp`

## Targets

- `.wavefoundry/framework/scripts/docs_gardener.py`
- `.wavefoundry/framework/scripts/server_impl.py`
