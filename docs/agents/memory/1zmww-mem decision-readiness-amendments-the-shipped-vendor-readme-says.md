# Decision: Readiness amendments: the shipped vendor README says the ve…

Owner: Engineering
Status: rejected
Last verified: 2026-10-03

Memory ID: `1zmww-mem decision-readiness-amendments-the-shipped-vendor-readme-says`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 214355
Source event: `decision-log:1zltw-enh vendored-scripts-online-integrity-check:82ce78fecc7b4a18`
Validation: reject
Validated by: agent
Action delta: No durable action: the redirect and README rules are superseded by 1zodv and pinned by RedirectBeforeFollowTests and MalformedRowTests.
Validation rationale: The amendment's post-follow geturl check was itself found insufficient and replaced in 1zodv by checking each redirect before following; the current behaviour lives in verify_vendored_scripts and its tests, so a memory would only restate superseded design.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1zls7): Readiness amendments: the shipped vendor README says the verifier exists only in the source repository; the verifier checks `response.geturl()` against the registry prefix after redirects and caps tarball size (AC-1 extended); the exclusion test copies the `test_build_pack.py` `test_manifest_does_not_list_excluded_files` pattern (AC-4). Rationale: Readiness review: targets read a README naming a script they do not have, a redirect could leave the registry, and an unbounded body could exhaust memory.

## Evidence

- `1zltw-enh vendored-scripts-online-integrity-check`
- `1zls7`

## Targets

- `test_build_pack.py`
