# Decision: Origin-check reconciled to the landed 1p9qi discipline and…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-origin-check-reconciled-to-the-landed-1p9qi-discipl`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9q7-enh di-signal-ast-and-language-expansion:01f5decffc4784ba`
Validation: rewrite
Validated by: agent
Action delta: Choose positive or negative origin checks according to identifier collision risk before emitting framework-specific static-analysis edges.
Validation rationale: The current graph extractor still applies this distinction across multiple sinks, and it prevents both alias under-detection and generic-name overreach.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-match-static-analysis-origin-checks-to-identifier-distinctiv`
## Summary

Decision (wave 1p9q8): Origin-check reconciled to the landed 1p9qi discipline and applied SYMMETRICALLY across Python and TS: distinctive idiom names (`Depends`, `@Injectable`/`@injectable`, `@Inject`, `@Module`) use a NEGATIVE check (fire unless the local name resolves to a non-DI-library origin; an unbound canonical spelling self-identifies and fires); the generic name `bind` uses a POSITIVE check (emit `bind().to()` only when the file imports the Inversify container). Alias-imported idioms resolve through the import binding to their origin; same-named user-defined idioms are refused.. Rationale: Matches the framework's shipped negative/positive origin-check convention (`graph_indexer.py` embedded-SQL sinks); keeps every DI edge a defensible claim while recognizing legitimate aliasing. Symmetric treatment closes both the over-fire (impostor) and under-fire (alias) failure modes in both new languages per the qa-amended AC-2..

## Evidence

- `1p9q7-enh di-signal-ast-and-language-expansion`
- `1p9q8`

## Targets

- `graph_indexer.py`
