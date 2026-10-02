# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zimd profile-and-supply-chain-follow-ups`
Title: Profile And Supply Chain Follow Ups

## Objective

Close three items from a downstream report: the uv bootstrap installs only a wheel matching recorded per-platform hashes, the vendored dashboard scripts record their npm registry integrity and the commands that reproduce them, and the nested discovery tests hold under any `MAX_DEPTH` profile.

## Changes

Change ID: `1zimh-debt nested-discovery-test-uses-max-depth`
Change Status: `implemented`

Change ID: `1zimi-enh vendored-dashboard-scripts-registry-integrity`
Change Status: `implemented`

Change ID: `1zimj-enh uv-bootstrap-hash-pinned`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zimd` (Profile And Supply Chain Follow Ups) delivered 3 changes: Nested Discovery Tests Take Their Depth From MAX_DEPTH, Vendored Dashboard Scripts Record Their npm Registry Integrity, and The uv Bootstrap Installs Only Hash-Verified Wheels. Notable adjustments during implementation: Nested Discovery Tests Take Their Depth From MAX_DEPTH: Implemented. `test_nested_finds_waves_at_depth_one_two_and_three` renamed `test_nested_finds_waves_down_to_max_depth_and_none_beyond`: waves at depths 1, `min(2, MAX_DEPTH)` and `MAX_DEPTH` are found and a wave at `MAX_DEPTH + 1` is not; the two ambiguity tests call `_nested(max_depth=2)`. Before: in-memory runs failed 3 tests at `MAX_DEPTH` 1 and 1 at 2. After: 45 tests pass at 1, 2, 3, 4 and 8 (two `default_profile_only` skips off the shipped profile). Mutation `depth >= roots.max_depth` to `>` fails the renamed test at the shipped depth and at 2; with the beyond-depth wave removed the renamed test no longer fails; without `max_depth=2` both ambiguity tests fail at depth 1; The uv Bootstrap Installs Only Hash-Verified Wheels: Implemented. `UV_BOOTSTRAP_WHEEL_SHA256` holds the 18 wheels; `_bootstrap_uv` writes a one-line requirements file with `tempfile.mkstemp` in the tool-venv base (closed before pip runs, removed in a `finally`), runs `pip install --require-hashes --only-binary :all: --no-deps -r <abs path>`, reports a non-zero exit or an `OSError` writing the file with the Requirement 3 message and returns `None`, so `_install_deps` keeps its plain-pip fallback. New tests: `test_bootstrap_installs_only_the_pinned_wheel_from_the_venv_base` (rewritten: exact command, one-line file, removal after exit 0, exit 1 and timeout), `test_uv_bootstrap_wheel_hashes_cover_the_pinned_version`, `test_a_failed_hash_bootstrap_is_reported_and_setup_falls_back_to_pip`, `test_an_unwritable_requirements_file_is_a_failed_bootstrap`; all failed before the change. Real pip 25.1.1 in a scratch venv whose path holds a space: the bootstrap installed uv 0.12.4; with the macOS arm64 hash altered pip refused it with its hash-mismatch error, the message printed, no uv was installed and no file was left. Mutations (drop `--require-hashes`, drop `--no-deps`, bump the version alone, hashes on separate lines, no removal, no message, `OSError` unhandled) each fail a named test. Checklist step 3, build-and-verification paragraph, threat-model row and CHANGELOG sentence updated.

**Changes delivered:**

- **Nested Discovery Tests Take Their Depth From MAX_DEPTH** (`1zimh-debt nested-discovery-test-uses-max-depth`) — 3 ACs completed. Key decisions: Derive the depths from `MAX_DEPTH` and assert one beyond it; Fix the two ambiguity tests with an explicit depth of 2
- **Vendored Dashboard Scripts Record Their npm Registry Integrity** (`1zimi-enh vendored-dashboard-scripts-registry-integrity`) — 4 ACs completed. Key decisions: A separate per-package registry table rather than more columns in the file table; The test pins presence and form, not registry truth
- **The uv Bootstrap Installs Only Hash-Verified Wheels** (`1zimj-enh uv-bootstrap-hash-pinned`) — 6 ACs completed. Key decisions: Keep the plain-pip fallback after a failed hash bootstrap (readiness security recommendation); Pass hashes through a temporary requirements file
## Watchpoints

- Watchpoint: the three changes touch disjoint files except `CHANGELOG.md` (`1zimi` and `1zimj` each append one sentence to an existing `## [Unreleased]` bullet); serialize those two edits.
- Watchpoint: tests never use the network; the PyPI and npm registry checks are scratch-folder transcripts (AC-4 of `1zimj`, AC-1 of `1zimi`).
- Watchpoint: a failed uv bootstrap keeps the existing plain-pip fallback for dependencies; the readiness security review recommended keeping it (Decision Log of 1zimj).
- Watchpoint: `1zimj` edits `.wavefoundry/framework/scripts/`, so run the full suite last before close for a fresh receipt.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the hash pin guards a rare path, since most machines already have uv and a failed bootstrap lets dependencies install with plain pip from the same index; it still ships because an unverified uv never lands and it costs little; strongest-alternative: a direct-URL requirement with a sha256 fragment, rejected because it bypasses the operator's index and mirror settings and puts wheel selection in our code)
- Prepare council seat evidence (2026-10-01): one independent Opus reviewer ran both seats and the code, qa, architecture, docs-contract and security lanes against the code and live registry data: all 18 uv wheel hashes match PyPI mechanically; all three npm integrity values and tarball URLs match the registry; real pip installs with the hashes on one line and refuses an altered hash; the depth census reproduces (MAX_DEPTH 1 fails 3 tests, 2 fails 1). It blocked on the README commands (GNU `base64` wraps at 76; `ReadAllBytes` resolves against the process folder) and required the one-line hash format; its edits E1-E5 were applied verbatim.

- **Delivery Wave Council [delivery-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the hash pin protects only the uv binary, since a failed bootstrap still falls back to unhashed pip for every dependency and an index that serves different uv bytes can force that fallback; accepted per the Decision Log and stated in the threat model; strongest-alternative: a committed uv-bootstrap requirements file instead of a temp file, rejected as a second artifact to keep in step with the constant while every temp-file path is tested)
- Delivery seat evidence (2026-10-01): one independent Opus reviewer diffed all 18 wheel hashes against PyPI, ran a real pip install (correct hashes install uv 0.12.4; an altered hash is refused, nothing installed, no temp file left), ran the README POSIX commands against the npm registry (integrity, tarball URLs and byte-identical files all match), ran the depth test at MAX_DEPTH 1 to 8, and killed 14 of 17 mutations (the 3 survivors benign or by design). Its six maybe-later findings were addressed (message wording, doc precision, full wheel-coverage test, `.gitattributes` `-text` for the vendored folder, PowerShell `ProviderPath`) and reverified in a fresh scratch copy.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 24 | 71,059 |
| implement | 43 | 683,142 |
| review | 10 | 46,645 |
| **Total** | **77** | **800,846** |

<!-- wave:context-efficiency-state {"generation":75,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":43,"content_source_credit":717199,"derived_artifact_credit":1147,"direct_net":683142,"estimated_tokens_saved":683142,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1155,"response_debit":35615,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1566},"plan":{"calls":24,"content_source_credit":103348,"derived_artifact_credit":1602,"direct_net":71059,"estimated_tokens_saved":71059,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3943,"response_debit":36459,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":10,"content_source_credit":64697,"derived_artifact_credit":1757,"direct_net":46645,"estimated_tokens_saved":46645,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2143,"response_debit":19982,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":77,"content_source_credit":885244,"derived_artifact_credit":4506,"direct_net":800846,"estimated_tokens_saved":800846,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7241,"response_debit":92056,"source_credit_count":52,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10393},"wave_id":"1zimd profile-and-supply-chain-follow-ups"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
