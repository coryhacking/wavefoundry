# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-05-19

wave-id: `12rnv agent-prompt-harness`
Title: Agent Prompt Harness

## Objective

Upgrade the Wave Framework **agent prompt generation surface** so reviewer and coordinator behavior matches a multi-stage **harness** (narrow scope, split questions, adversarial disprove, structured findings, project-evidence grounding)—not a single monolithic chat. All deliverables are **framework seeds** and bootstrap references first; target-repo `docs/agents/` extensions are generated from seeds plus local evidence on upgrade, not hand-edited as substitutes for seeds.

## Changes

Change ID: `12rbe-enh security-reviewer-exploit-chains`
Change Status: `planned`

Change ID: `12rnv-enh agent-prompt-harness-effectiveness`
Change Status: `planned`

Change ID: `12rcp-enh prompt-preflight-rubric`
Change Status: `planned`

Change ID: `12rcd-maint agents-md-implementation-principles`
Change Status: `planned`

## Wave Summary

Three framework changes on this wave: **`12rbe`** generalizes security-review seeds (`213`, security sections of `007`); **`12rnv`** adds harness core (`209`), other inferential sensors, specialists (`217`–`219`), and coordinator/bootstrap updates; **`12rcp`** consolidates prompt-preflight language for ambiguity routing and evidence-first review. Independent of wave **`12rbc mcp-impl-hot-reload`** (MCP hot reload), which may implement in parallel.

## Journal Watchpoints

- **Watchpoint:** `seed_edit_allowed` gate required for all edits under `.wavefoundry/framework/seeds/` — open immediately before seed work, close immediately after.
- **Watchpoint:** No implementation until **Prepare wave** completes successfully on this change.
- **Watchpoint:** Framework seeds stay **product-agnostic**; Wavefoundry-specific security checks (MCP path confinement, symbol extraction, etc.) belong in `docs/agents/security-reviewer.md` **after** seed land, via upgrade render—not in seed-213.
- **Watchpoint:** Do not treat draft work in agent chat as shipped until tests pass and `MANIFEST` lists new seed files.

## Review checkpoints

- (empty until Prepare wave / Review wave)

## Review Evidence

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Informed by Cloudflare [Project Glasswing](https://blog.cloudflare.com/cyber-frontier-models/) harness lessons and community “environment over prompts” practice (layered entry surface, skeptical review, model-tier discipline).
- No code changes to `server.py` or MCP runtime in this wave.

## Serialization Points

- `209` must be drafted before other seeds reference it.
- `seed_edit_allowed` gate: single open/close around all seed edits.
- Shared bootstrap surfaces (`050`, `100`, `020`, `docs/prompts/index.md`) are a single write set; coordinate them as one serialized pass even if the surrounding seed bodies are split across changes.
