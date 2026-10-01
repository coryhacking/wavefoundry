# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zicq install-and-permission-hardening`
Title: Install And Permission Hardening

## Objective

Keep a target repository from steering what goes into the shared per-user tool environment or into hosts' read-tier allow lists: the setup and upgrade installer ignores repository uv configuration, bootstraps an exact pinned uv, and bounds its install timeout, and an extension replacement can no longer downgrade a write tool or replace the edit gates. From the v1.28.0 downstream validation (requests 2, 3 and 4).

## Changes

Change ID: `1zhmd-bug setup-install-isolation`
Change Status: `implemented`

Change ID: `1zhme-bug replacement-tier-downgrade`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer


Completed At: 2026-09-30

## Wave Summary

Wave `1zicq` (Install And Permission Hardening) delivered two changes: The Setup and Upgrade Installer Honours Repository uv Config and Bootstraps an Unpinned uv and A Tool Replacement Can Relist a Write Tool as Read or Replace the Edit Gates. Notable adjustments during implementation: The Setup and Upgrade Installer Honours Repository uv Config and Bootstraps an Unpinned uv: Second post-close finding DEL-1ZICQ-TILDE-CACHE-PATH (external review): the first repair rebased `PIP_CACHE_DIR=~/.cache/pip` to a literal `~` folder because `abspath` ran before pip's own home expansion. Consumer probes: pip's `type="path"` options (`--cache-dir`, `--cert`, `--client-cert`) apply `os.path.expanduser`; uv 0.12.4 reads `UV_CONFIG_FILE` and `UV_CACHE_DIR` literally (real uv: `failed to open file ~/...`, `uv cache dir` prints `~/...`); pip reads `PIP_CONFIG_FILE` without expansion. Repair: `_PIP_EXPANDED_PATH_ENV_VARS` (`PIP_CACHE_DIR`, `PIP_CERT`, `PIP_CLIENT_CERT`) get `expanduser` before rebasing; the rest keep caller-folder rebasing. Tests: real `pip cache dir` from the tool base with the rebased env equals pip from the caller with the original env (`~` and plain relative values); per-variable consumer expectations for all eight settings. Mutations: expanding every variable, and dropping the expansion, each fail; The Setup and Upgrade Installer Honours Repository uv Config and Bootstraps an Unpinned uv: Post-close finding DEL-1ZICQ-RELATIVE-OPERATOR-CONFIG (external review, replayed independently): a relative `UV_CONFIG_FILE` resolved inside the tool-venv base after the cwd move and uv exited 2. Wave reopened; repair: `_installer_env` makes the relative path-valued uv and pip settings (`UV_CONFIG_FILE`, `UV_CACHE_DIR`, `PIP_CONFIG_FILE`, `PIP_CERT`, `PIP_CLIENT_CERT`, `PIP_CACHE_DIR`, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`) absolute against the caller's folder at all three installer call sites (`_install_deps`, `_bootstrap_uv`, `install_requirement_specs`); the null device and absolute values pass through, and an environment with nothing relative stays inherited. Tests: real-uv relative `UV_CONFIG_FILE` through `_install_deps` (fails before the repair), per-call-site resolution; removing the helper from any call site fails a test; real uv control reproduces `failed to open file`. Build guide sentence added; The Setup and Upgrade Installer Honours Repository uv Config and Bootstraps an Unpinned uv: Full suite round 1: two failures from this wave, both fixed. `test_venv_bootstrap` single-resolver scan flagged two new comments naming the tool-venv environment variable (reworded); `test_review_policy` corpus check found 1zhme's first Serialization Points bullet rejected by the strict parser because of a backticked note (note moved to its own bullet). Delivery advisories taken: `_uv_bin` returns an absolute path for a relative `PATH` entry (test added); the relative-override startup test uses `contextlib.chdir` instead of `os.path.relpath`, which raises across Windows drives. Not taken: `pip --isolated` for the bootstrap, because it would also ignore an operator's `pip.conf` proxy and index settings.

**Changes delivered:**

- **The Setup and Upgrade Installer Honours Repository uv Config and Bootstraps an Unpinned uv** (`1zhmd-bug setup-install-isolation`) — 6 ACs completed. Key decisions: Keep the plain-pip fallback; Exact pin, bumped at release
- **A Tool Replacement Can Relist a Write Tool as Read or Replace the Edit Gates** (`1zhme-bug replacement-tier-downgrade`) — 4 ACs completed. Key decisions: Refuse the declaration rather than silently keep the core tier
## Watchpoints

- Watchpoint: an existing uv in the tool venv or on `PATH` is never replaced; the pin applies only to the bootstrap.
- Follow-up: the release checklist gains the uv pin bump; offline MCP startup is covered by 1zhmd AC-4 (no opt-out).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZICQ-RELATIVE-OPERATOR-CONFIG | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| DEL-1ZICQ-TILDE-CACHE-PATH | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the gate guard covered replacements but not `EXTENSION_OVERRIDES`, so a distribution could still swap a gate handler; resolved by one protected gate-tool constant checked for overrides, replacements and hidden names, with the trusted-code boundary stated rather than overclaimed; strongest-alternative: leave the gates unprotected because extension code is trusted, rejected because the declaration check is cheap and catches careless declarations)
- Prepare council seat evidence (2026-09-30): red-team approved 1zhmd (notes on wheel-only bootstrap, absolute paths, old uv, lock-held caps and transition folded in) and blocked 1zhme on the override bypass, approved in scoped round 2; docs-contract-reviewer blocked 1zhme on the stale tool-surface spec and threat model, approved in scoped round 2.
- Readiness lanes (2026-09-30): code-reviewer blocked 1zhme on the override bypass, approved in round 2; qa-reviewer approved round 1; architecture-reviewer (added when the threat model came into scope) approved, with an implementation note to extend `docs/architecture/testing-architecture.md`'s refusal-fixture row. Reviewer models: requested opus for all council seats and lanes (judgment work); observed runtime identity unknown.

- **Delivery-phase Wave Council [delivery-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the edit-gate protection checks declarations only, so trusted module code can still rebind a gate handler at runtime; accepted and stated in the threat model and spec as not a sandbox; strongest-alternative: run the uv bootstrap with `pip --isolated`, declined because it would also ignore an operator's `pip.conf` proxy and index settings; disagreements: none)
- Delivery seat and lane evidence (2026-09-30): red-team approved with every probe and mutation reproduced; code, qa, architecture and docs-contract lanes approved (12 mutations, 11 killed; the survivor is a redundant guard). Full suite round 1 found two failures this wave caused (a comment naming the tool-venv variable; a Serialization Points bullet the strict parser rejected), fixed; the lane reviewer rechecked the fixes and the two advisories taken (absolute PATH uv, Windows-safe relative-venv test). Full suite round 2: 10198 tests OK. Reviewer models: requested opus for both delivery reviewers; observed runtime identity unknown.

- **Post-close follow-up — 2026-09-30: DEL-1ZICQ-RELATIVE-OPERATOR-CONFIG, RESOLVED** (code-reviewer, external review replayed independently). Moving installs to the tool-venv base made a relative `UV_CONFIG_FILE` resolve inside the tool environment (uv exit 2, `failed to open file`). Wave reopened; `_installer_env` now makes relative uv and pip path settings absolute against the caller's folder at all three installer call sites. Independent Opus reverifier: reverted exit 2, applied exit 0; mutations caught, the null-device survivor closed by a stricter test. Code, qa and council delivery approvals re-recorded; full suite 10202 OK.

- **Post-close follow-up — 2026-09-30: DEL-1ZICQ-TILDE-CACHE-PATH, RESOLVED** (code-reviewer and qa-reviewer, external review). The first repair rebased `PIP_CACHE_DIR=~/.cache/pip` to a literal `~` folder because `abspath` ran before pip's home expansion. Repair grounded in each consumer: pip's path options (`PIP_CACHE_DIR`, `PIP_CERT`, `PIP_CLIENT_CERT`) get `expanduser` first; uv, `PIP_CONFIG_FILE`, OpenSSL and requests read `~` literally and keep caller-folder rebasing. Independent Opus reverifier confirmed each classification against the real consumer, fixed vs reverted with real pip; five mutations caught. Code, qa and council re-approved; full suite on a quiet tree 10204 OK.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 45 | 417,055 |
| implement | 26 | 51,899 |
| review | 56 | 429,899 |
| **Total** | **127** | **898,853** |

<!-- wave:context-efficiency-state {"generation":87,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":26,"content_source_credit":72422,"derived_artifact_credit":1312,"direct_net":51899,"estimated_tokens_saved":51899,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1920,"response_debit":21869,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1954},"plan":{"calls":45,"content_source_credit":490929,"derived_artifact_credit":7356,"direct_net":417055,"estimated_tokens_saved":417055,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3024,"response_debit":84297,"source_credit_count":36,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6091},"review":{"calls":56,"content_source_credit":556310,"derived_artifact_credit":3058,"direct_net":429899,"estimated_tokens_saved":429899,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13863,"response_debit":120238,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4632}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":127,"content_source_credit":1119661,"derived_artifact_credit":11726,"direct_net":898853,"estimated_tokens_saved":898853,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18807,"response_debit":226404,"source_credit_count":99,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12677},"wave_id":"1zicq install-and-permission-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 1 | 164,400 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":164400,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
