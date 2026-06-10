# Plans

Owner: Engineering
Status: active
Last verified: 2026-06-09

Hub for in-flight planning work. Active change documents live here until admitted into a wave, at which point **Prepare wave** relocates them into `docs/waves/<wave-id>/`.

## Active Plans

- [`1p3ao-feat dynamic-workflows-framework-application`](plans/1p3ao-feat%20dynamic-workflows-framework-application.md) — roadmap doc inventorying where Claude Code dynamic workflows apply across the framework: all councils (wave + archetype + delivery + red-team) as parallel fan-outs with cross-checked synthesis; install Phase 2 as a 3-stage parallel workflow; guru with multi-path code exploration and confirmation-bias cross-checks; plan-feature multi-angle drafting; wave-readiness multi-dimension audit; coherence/garden/distill fan-outs. First experiment is the per-chunker audit step inside `1p397` (admitted to wave `1p3b9`). Individual surfaces become their own admitted changes.

## Admitted (relocated into waves)

- `1p397`, `1p399`, `1p3b5`, `1p3b6`, `1p3b7` — admitted to wave [`1p3b9 chunker-indexer-correctness-and-1-5-0-hardening`](waves/1p3b9%20chunker-indexer-correctness-and-1-5-0-hardening/wave.md). Ships jointly with wave `1p35d` under the **1.5.0** tag.

## Template

New change documents use `docs/plans/plan-template.md`. Generate change IDs with the MCP `wave_new_<kind>` tools (preferred — they dedupe against on-disk IDs). CLI fallback when the MCP server is unavailable:

```bash
python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>
```

Kind options: `feat`, `bug`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`.
