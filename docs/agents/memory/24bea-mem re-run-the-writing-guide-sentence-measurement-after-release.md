# Re-run the writing-guide sentence measurement after release

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bea-mem re-run-the-writing-guide-sentence-measurement-after-release`
Kind: `decision`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `240wz-rerun-writing-guide`
Checked at: 2026-11-26T06:32:44Z
Check note: The retained baseline specifies a post-release sampling window. Keep the operator's revisit condition attached to the writing evidence. Reviewed docs/waves/241c3 writing-guide-sentence-structure/evidence/README.md:39.
Check flags: none

## Summary

When three waves have closed after the first release that contains change 240wz, or when someone proposes revising the writing guide's sentence-length guidance, re-run measure.py by following 'Re-run after release' in docs/waves/241c3 writing-guide-sentence-structure/evidence/README.md and read the specs POST over25_pct figure. At 14.0% or lower keep the guidance; above 14.0% plan a revision; with fewer than 700 post-release spec sentences include the next closed wave. Why: the baseline is 18.0% of 2,062 sentences, and this re-run is the agreed test of whether .wavefoundry/framework/docs/writing-guide.md changed spec writing.

## Evidence

- `241c3`
- `240wz-doc writing-guide-sentence-structure`
- `docs/waves/241c3 writing-guide-sentence-structure/evidence/README.md`

## Targets

- `.wavefoundry/framework/docs/writing-guide.md`
- `docs/waves/241c3 writing-guide-sentence-structure/evidence/README.md`
