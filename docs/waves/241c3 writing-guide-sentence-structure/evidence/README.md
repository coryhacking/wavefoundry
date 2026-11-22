# Writing Measures for Change 240wz

Owner: Engineering
Status: active
Last verified: 2026-11-21

These scripts measured project writing for the 2026-11-21 ASD-STE100 review, the source of change `240wz-doc writing-guide-sentence-structure`. The operator re-runs `measure.py` on specs written after release and compares one figure with its baseline. The scripts read the repository and write output only to the current directory.

## Files

| File | Purpose |
| --- | --- |
| `measure.py` | Sentence length, passive voice, noun stacks and term counts per corpus; writes `measures.json`, `measures.md` and `terms.md` |
| `newprose.py`, `newprose2.py` | Separate new seed and prompt prose from older blocks that an edit touched; `newprose2.py` writes `newprose2.json` |
| `validate.py`, `extra.py`, `extra2.py` | Sample checks of the heuristics and the extra counts in the report; `extra2.py` reads `newprose2.json` |
| `check_sentences.py` | Delivery oracle: confirms each added guide sentence is present once in its section, and with `--pointers` the three pointer sentences |

## Settings

`measure.py` reads four environment variables. The helper scripts run the top of `measure.py`, so they use the same values.

| Variable | Meaning | Default |
| --- | --- | --- |
| `WF_REPO` | Repository root | `git rev-parse --show-toplevel` in the current directory |
| `WF_BASE` | Commit for the "added since" corpora (handoff, new seed prose) | `189a2502`, the guide's adoption |
| `WF_POST_WAVES` | Space-separated wave id prefixes for the post sample | the six waves the report used |
| `WF_POST_VERSIONS` | Space-separated changelog versions for the post sample | `Unreleased` and 1.43.0 to 1.47.0 |

`measure.py` exits 1 when it cannot find the repository or when every corpus is empty. A corpus can still be empty when the others are not, so check the sentence count of each post corpus in `measures.md` before reading its rates.

The spec measurements use the change IDs listed under `## Changes` in each selected wave record. The script reads the corresponding spec files. Supporting reports stay outside the sample, and wave records have their own corpus.

## Re-run after release

1. Wait until three waves have closed after the first release that contains change 240wz.
2. Copy this folder's scripts to a scratch directory outside the repository and run them from there, so their output stays out of the wave folder.
3. Set `WF_REPO` to the repository root, `WF_POST_WAVES` to the ids of the waves closed after that release, `WF_BASE` to the release commit and `WF_POST_VERSIONS` to the versions released after it.
4. Run `python3 -X utf8 -I measure.py`. The `-X utf8` flag keeps native Windows from decoding repository text as cp1252.
5. Read the `specs POST (WF_POST_WAVES)` row in `measures.md`: its `sentences` and `over25_pct` columns give the primary measure. Compare it with the decision rule in the change's Product Intent.
6. For the secondary figures, run `newprose2.py` before `extra2.py`, because `extra2.py` reads `newprose2.json`.

## Where each baseline comes from

| Figure | Baseline | Script and row |
| --- | --- | --- |
| Primary: spec sentences over 25 words | 18.0% of 2,062 | `measure.py`, row `specs POST`, column `over25_pct` |
| Task-section imperative sentences with a second instruction | 43 of 118 (36.4%) | `measure.py`, row `spec tasks POST`, column `multi_instr_pct` |
| Changelog sentences over 25 words | 22.8% of 285 | `measure.py`, row `changelog POST`, column `over25_pct` |
| Noun stacks per 1,000 words, review `observed` text | 28.3 | `measure.py`, row `review observed POST`, column `noun_clusters_per_1k` |
| Noun stacks per 1,000 words, handoff lines added since `WF_BASE` | 33.3 | `validate.py`, the line after `handoff POST (lines added since 189a2502)` |

Only the primary figure has enough sentences to show an effect of a few points. The others are descriptive. The noun-stack heuristic over-counts by about half. The handoff and changelog figures read the working tree, so uncommitted edits move them slightly.

To check delivery, run `python3 -X utf8 -I check_sentences.py .wavefoundry/framework/docs/writing-guide.md --pointers` from the repository root, with the script path adjusted to this folder.
