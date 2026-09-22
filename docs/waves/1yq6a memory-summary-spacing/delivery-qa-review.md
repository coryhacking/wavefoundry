# Memory Summary Spacing — Delivery QA

Owner: Engineering
Status: approved
Last verified: 2026-09-22

Verdict: approve the scoped spacing repair. No blocking implementation findings.
Reviewer: `qa-reviewer`; context `spacing-delivery-qa-1yq6a`; fresh and independent of implementation and readiness.

## Contract and evidence

The independent reference is the operator requirement and admitted change's AC-1–3: exactly one empty line before the first Summary after every helper write, stable repeated updates, unchanged body/unrelated metadata, compatible missing-marker behavior, and no historical migration. Reviewed the actual diff and targeted MCP reads of the helper, validation writer, and producer-built tests before forming this verdict.

| AC | Executed evidence | Result |
| --- | --- | --- |
| AC-1 | `MemoryMetadataSpacingTests.test_insert_replace_and_repeat_have_one_blank_line` | Exact output matches for insert and replace with zero, one, excess, and whitespace-only separator lines. |
| AC-2 | Same test plus independent sequential oracle | Three repeated same-value updates and a different-field insertion remain exact. Independent oracle ran 32 transitions: eight insert/replace separator inputs, each updated through none, supplements, none, none; unrelated metadata, body metadata-like text, and a second Summary remain byte-identical. |
| AC-3 | `MemoryAgentValidationTests.test_promote_retain_and_reject_persist_compact_judgment`; missing-Summary test | Real `render_memory_record` and `write_memory_record` producers feed `memory_validate_response`; all three verdicts reach success and persist parsed status/validation fields. Exact separator, original body, and repeated writer byte equality pass. Missing Summary still permits existing replacement and raises the same insertion error. |

Whole focused module executed with:

```sh
PYTHONPATH="$PWD/.wavefoundry/framework/scripts" /Users/coryhacking/.wavefoundry/venv/bin/python -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_memory_records.py
```

Observed: 219 tests, zero failures, zero skips, 11.955 seconds. The initial discovery invocation and subsequent direct per-file invocation without explicit PYTHONPATH each ran 219 tests but failed the same unrelated child-process import (`index_compatibility` in `test_child_process_sees_live_fence_and_clear`). Explicitly propagating the scripts path to children resolves this environment issue; no source was changed to resolve it. These failed invocations are not represented as green evidence.

## Known-bad control and integrity

Independently extracted only `_replace_or_insert_metadata` from `git show HEAD:.wavefoundry/framework/scripts/memory_records.py` using Python AST and injected it in memory after each test setup. Ran the two spacing tests plus the producer validation test. Observed three tests, 11 assertion failures (eight separator subcases and three validation verdicts), zero errors, zero skips; the compatible no-marker control continued to pass. No repository source or historical record was reverted or rewritten. This falsifies both helper-output and real-writer stability claims when the repair is absent.

Exact `integrity_checks` for this lane:

```json
{
  "test_ran_without_unintended_skip": true,
  "public_path_reached": true,
  "boundary_values_realistic": true,
  "assertions_non_vacuous": true,
  "known_bad_detected": true,
  "known_bad_detection_method": "injected-old-behavior"
}
```

The complete focused run had no skips; producer-created pending records reached the real `memory_validate_response` boundary; separator cases and actual verdict records are reachable inputs; exact-output and parsed-field assertions are non-vacuous; old behavior caused the named failures. Repeated writes use the lower-level real writer because the public response intentionally refuses revalidation after pending disposition.

## Limits and safety

All probes were authorized local tests with temporary record roots or in-memory strings. No historical-memory mutation, lifecycle event, source edit, commit, or closure was performed by this reviewer. The production response boundary was executed; an MCP transport round trip was not needed to prove this formatting mechanism. This review makes no whole-framework result claim: the coordinator owns the concurrently running full-suite evidence. No concurrency or arbitrary Markdown normalization claim is made; this bounded formatter has no new concurrent state or public signature. Common-mode limitation: the committed producer regression shares the real parser, mitigated by exact byte assertions and the separately constructed contract oracle.
