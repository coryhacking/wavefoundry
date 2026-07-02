# Plans

Owner: Engineering
Status: active
Last verified: 2026-07-02

Hub for in-flight planning work. Active change documents live here until admitted into a wave, at which point **Prepare wave** relocates them into `docs/waves/<wave-id>/`.

## Active Plans

- None currently listed here — see `docs/plans/` for pending change docs (`wave_list_plans` gives the live view).

## Retired Plans

- `1p3ao-feat dynamic-workflows-framework-application` — retired 2026-07-01 (backlog triage): roadmap partially overtaken; individual surfaces become their own admitted changes when pursued.
- `12mc3-bug agent-detail-panel-blank-hardcoded-section-allowlist` — retired 2026-07-01: superseded by closed wave `12mc3` (full-body render replaced the `_DETAIL_SECTIONS` allowlist entirely).
- `12pn3-enh chunk-context-enrichment` — retired 2026-07-01: docs breadcrumb prepend shipped via wave `1p4u5` change `1p4w9`; remaining `File:`/`Language:` prefixes contra-indicated for current models.
- `12pn3-enh code-embedding-model-jina-v2` — retired 2026-07-01: premise (bge-base drop-in) obsolete after the 1p50s model split; jina repeatedly rejected (no INT8 export).
- `12pn3-enh nomic-embed-docs-model-evaluation` — retired 2026-07-01: premise obsolete after the 1p50s model split; re-evaluate models via the embedding-model ADR track instead.

## Admitted (relocated into waves)

- `1p397`, `1p399`, `1p3b5`, `1p3b6`, `1p3b7` — admitted to wave [`1p3b9 chunker-indexer-correctness-and-1-5-0-hardening`](waves/1p3b9%20chunker-indexer-correctness-and-1-5-0-hardening/wave.md). Ships jointly with wave `1p35d` under the **1.5.0** tag.

## Template

New change documents use `docs/plans/plan-template.md`. Generate change IDs with the MCP `wave_new_<kind>` tools (preferred — they dedupe against on-disk IDs). CLI fallback when the MCP server is unavailable:

```bash
wf lifecycle-id --kind <kind> --slug <slug>
```

Kind options: `feat`, `bug`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`.
