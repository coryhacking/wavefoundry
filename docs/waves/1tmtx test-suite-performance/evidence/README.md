# Wave 1tmtx Evidence Index

Owner: Engineering
Status: active
Last verified: 2026-08-27

Measurement and preservation evidence for change `1tm6d-enh
test-suite-critical-path-acceleration`. The typed delivery approvals in the
sibling `events.jsonl` cite these artifacts by name; do not rename or trim
them while those approvals are live. None of this folder is semantically
indexed (the docs layer chunks markdown only; the code layer's include
prefixes do not cover `docs/`) and none of it ships in the distribution pack.

## Headline results

- Original-source baseline: median **216.665 s** external invocation-to-exit
  (`baseline.json`; samples 217.9 / 216.0 / 216.7, warm-up uncounted).
- Post-change final: median **135.946 s**, a **37.3% improvement** against the
  25% target; worst sample 34.8% (`benchmark_final.json`; all runs green, 3
  skips unchanged).
- Schedule winner: **alphabetical** over timing-guided longest-first
  (counterbalanced A-T-T-A means 130.499 s vs 136.755 s,
  `schedule_controls.json`); longest-first saturates the host, confirming the
  prepare-phase watchpoint.
- Shard preservation: exact frozen identity-set equality and per-class AST
  fingerprint equality with one reviewed Guard exception; all five mutants
  caught (`verify_shards.json`).
- True test counts: the pre-wave runner total (7,499) carried +5 mock-output
  contamination; the census-true base was 7,494, and the delivered tree runs
  7,554 (the wave added 60 runner regressions).

## Artifact map

| Artifact | What it proves |
| --- | --- |
| `freeze.json` | Requirement 1 frozen inventory: framework digest, per-file digests, 963 class AST fingerprints, 6,750 static identities, environment. The diff basis for any future shard rebalance or preservation re-check. |
| `census.json` | Executed per-file identity/skip census of the pre-change corpus (7,494 ran, 3 skipped) via `capture_baseline.py` phase B. |
| `baseline.json` + `logs/baseline-*.log` | Original-source external baseline series. |
| `instrumented.json` + `logs/instrumented-*.log` | Telemetry-runner pre-optimization distribution (per-file medians; `test_server_tools.py` 182.1 s under load, the feasibility-gate input). `logs/attempt1/` is the disclosed first series, invalidated by a missed `_run_file` consumer, retained as the failure trail. |
| `class_timings.json` + `measure_classes.py` | Per-class isolation timings for all 223 classes; the shard-balance input. |
| `shard_manifest.json` + `shard_split.py` | The 3-shard + support-module layout and its mechanical producer. The split is REGENERABLE from the pre-split git HEAD source; the producer runs four pre-write gates. |
| `verify_shards.py` + `verify_shards.json` | The AC-3 proof harness: identity/fingerprint equality, the mechanically proven Guard exception, the cross-test-import census (two disclosed pre-existing exclusions), and the five scratch-tree mutant probes. |
| `timings-manifest.json` | The digest-bound bootstrap timing manifest the schedule candidates consumed byte-identically. |
| `schedule_controls.json` + `logs/control-*.log` | The counterbalanced schedule comparison and measured winner. |
| `benchmark_final.json` + `logs/final-*.log` | The Requirement 11/12 post-change benchmark series and 25%-target verdict. |
| `logs/focused-shards.log` | Focused-isolation proof that each shard discovers and executes its exact expected subset (336 + 891 + 510 = 1,737). |
| `capture_*.py` + `capture*.log` | The reproducible drivers for every series above, with their run logs. |
