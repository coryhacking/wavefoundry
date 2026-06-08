# Scan Rules Engine

Change ID: `1p3rn-enh scan-rules-engine`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-06
Wave: `1p3rm scan-rules-secrets-detection`

## Rationale

The framework has no mechanical check for hardcoded secrets, API keys, or credentials in project files. The security reviewer's Step 4 covers runtime exposure (logging, echoing) but not static presence. A misconfigured file with a live credential can pass every review gate today. This change adds the detection engine: a Gitleaks-compatible TOML ruleset, a pure-Python lint validator, and an exceptions lifecycle file that carries findings through to resolution.

## Requirements

1. The framework ships a default ruleset at `.wavefoundry/scan-rules.toml` sourced from the Gitleaks community rules TOML (MIT licensed). The implementer downloads the canonical Gitleaks rules file at implementation time, commits it as the framework base, and adds a header comment noting the source repository, commit SHA, and download date. On top of the downloaded rules, the file also contains a `[policy]` section:
   ```toml
   [policy]
   false_positive_confirmations_required = 2
   ```
2. Projects extend the framework default by placing `docs/scan-rules.toml` alongside it. The lint check merges both files: framework rules first, project rules additive. Projects can disable specific framework rules by rule ID in their local file. The project file may also override `[policy]` values — in particular, `false_positive_confirmations_required = 1` is appropriate for solo or very small projects.
3. The lint validator (`wave_lint_lib/secrets_validators.py`) parses the merged ruleset using pure Python TOML parsing (stdlib `tomllib` ≥ 3.11, falling back to `tomli`). No subprocess or binary dependency. If neither is importable, the validator emits a clear diagnostic (`"secrets scan requires tomllib (Python ≥ 3.11) or the tomli package; run: pip install tomli"`) and exits cleanly — it does not raise a bare `ImportError`.
4. The validator scans files in the working tree that differ from HEAD by default (`git diff --name-only HEAD`), falling back to a full-repo scan if not inside a git repository **or if HEAD does not exist** (new repo with no commits). A `--scan-all` flag forces a full-repo scan regardless.
5. For each pattern match the validator checks `docs/scan-findings.json` and applies these rules by status:
   - `pending`: lint fails; agent must analyze and re-classify.
   - `false-positive`: lint reads `confirmations[]` and the merged policy `false_positive_confirmations_required`. Three outcomes:
     - Unique confirmed-email count >= required → suppressed, no error.
     - Count < required and current git user email not in list → lint fails with prompt: `"Unconfirmed false positive — <N> of <required> confirmations. You are not yet on the list. Please review and confirm or escalate."` The agent must ask the current user for their verdict.
     - Count < required and current git user email already in list → lint fails with progress: `"<N> of <required> confirmations received from: <name list> — needs <M> more from a different reviewer."` No action required from current user.
   - `suspected-secret`: lint fails; agent must stop, analyze context, and ask the current user to classify as `false-positive` or `confirmed-secret`.
   - `confirmed-secret`: lint fails; wave close requires per-wave acknowledgment.
6. New matches with no entry in the exceptions file are: (a) reported as a lint failure, and (b) auto-appended to `docs/scan-findings.json` with `status: pending` and the matched context (file, line, rule ID, matched text redacted to first 4 and last 4 characters with `****` in between). If `len(matched_text) ≤ 8`, the matched text is redacted entirely as `****` rather than partially revealed.
7. Inline suppression is supported via a comment on the matched line: `# wavefoundry-ignore: secrets <reason>`. The reason is required; a bare `# wavefoundry-ignore: secrets` without a reason is itself a lint failure.
8. The exceptions file schema is:
   ```json
   {
     "id": "exc-001",
     "file": "relative/path/to/file.py",
     "line": 14,
     "rule_id": "stripe-api-key",
     "matched_text": "sk_li****23",
     "status": "pending | false-positive | suspected-secret | confirmed-secret",
     "override_reason": "",
     "acknowledged_for_wave": "",
     "confirmations": [
       {
         "git_user_name": "Cory Hacking",
         "git_user_email": "coryhacking@mac.com",
         "verdict": "false-positive | confirmed-secret",
         "reason": "Test fixture — not a live credential",
         "confirmed_at": "2026-06-06T22:03:00Z"
       }
     ]
   }
   ```
   - `status` is set explicitly by the agent — the validator never changes it.
   - `confirmations` records each person's verdict with git identity (`git config user.name` / `git config user.email`), reason, and UTC ISO-8601 datetime. The same `git_user_email` confirming twice counts as one unique confirmation.
   - `acknowledged_for_wave` is set by the security reviewer agent after the operator accepts a `confirmed-secret` entry for close. Wave-scoped: closing a different wave requires re-acceptance.
9. The validator is wired into `cli.py` and runs as part of the standard `docs-lint` invocation.
10. A new `constants.py` entry `SCAN_RULES_FRAMEWORK_PATH = ".wavefoundry/scan-rules.toml"` and `SCAN_EXCEPTIONS_PATH = "docs/scan-findings.json"` provide a single source of truth for file locations.

## Scope

**Problem statement:** No mechanical check exists for hardcoded credentials in project files. The gap is a silent risk: a live secret can be committed, reviewed, and shipped without any framework gate triggering.

**In scope:**

- `.wavefoundry/scan-rules.toml` — framework default ruleset (secrets category)
- `wave_lint_lib/secrets_validators.py` — pure-Python lint validator
- `wave_lint_lib/constants.py` — new path constants
- `wave_lint_lib/cli.py` — wire in the new validator
- `docs/scan-findings.json` — schema definition and empty initial file (created by the validator on first run if absent)
- Framework tests for the new validator

**Out of scope:**

- PHI, PII, PCI rule categories — named follow-on to this wave
- Entropy-based detection — separate follow-on; false-positive cost outweighs benefit at launch
- External binary integration (Gitleaks, TruffleHog) — optional interop, not required
- Git history scanning — operational concern, separate tooling
- Pre-commit hook wiring — covered in install/upgrade seeds, not this change doc

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/scan-rules.toml` exists and contains at least one rule per category: cloud provider key, source control token, payment key, private key, generic credential assignment.
- [x] AC-2: Lint validator loads and merges framework + project TOML files; project file absence is not an error.
- [x] AC-3: A file containing a pattern matching a ruleset entry fails lint with the rule ID and redacted matched text in the error message.
- [x] AC-4: A `false-positive` entry whose unique confirmed-email count meets `false_positive_confirmations_required` passes lint for that match. Below the threshold, lint fails with the appropriate message (prompt if current user not in list; progress if already in list).
- [x] AC-5: A file with a `pending` exception entry still fails lint.
- [x] AC-6: A new match with no exception entry auto-appends a `pending` entry to `docs/scan-findings.json` and fails lint.
- [x] AC-7: Inline `# wavefoundry-ignore: secrets <reason>` suppresses the match for that line. A bare suppression without reason is itself a lint failure.
- [x] AC-8: Default scan scope is wave-touched files; `--scan-all` scans the full repo.
- [x] AC-9: Validator uses pure Python TOML parsing; no subprocess calls.
- [x] AC-10: Framework tests cover: match detection, exception suppression, auto-append, inline suppression, bare suppression failure, merge of framework + project rules, project-file-absent case.
- [x] AC-11: `scan-rules.toml` contains a `[policy]` section with `false_positive_confirmations_required = 2`.
- [x] AC-12: Project `docs/scan-rules.toml` `[policy].false_positive_confirmations_required` overrides the framework default when present.
- [x] AC-13: A `false-positive` entry with a confirmation count below the required threshold fails lint with the appropriate message: prompt ("You are not yet on the list") if the current git user's email is not in `confirmations`; progress ("needs <M> more from a different reviewer") if the current user's email is already present. Message shows count, required, and confirming names.
- [x] AC-14: A `false-positive` entry whose unique confirmed-email count meets the required threshold passes lint with no error.
- [x] AC-15: Duplicate git user email in `confirmations` counts as one toward the threshold.
- [x] AC-16: `.wavefoundry/scan-rules.toml` contains a header comment with the Gitleaks source repository URL, commit SHA, and download date.

## Tasks

- [x] Download Gitleaks community rules TOML from the gitleaks/gitleaks repository; record commit SHA and download date in a header comment; commit as `.wavefoundry/scan-rules.toml`
- [x] Add `[policy]` section with `false_positive_confirmations_required = 2` to the downloaded ruleset
- [x] Add `SCAN_RULES_FRAMEWORK_PATH` and `SCAN_EXCEPTIONS_PATH` to `constants.py`
- [x] Write `wave_lint_lib/secrets_validators.py` with TOML merge logic, file scanner, and exception cross-reference
- [x] Wire `check_hardcoded_secrets` into `cli.py`
- [x] Create empty `docs/scan-findings.json` with schema comment
- [x] Write framework tests in `tests/test_secrets_validators.py`
- [x] Run full framework test suite; confirm no regressions

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| scan-rules.toml + constants | software-engineer | — | Download Gitleaks community rules; add [policy] section; record provenance in header. Validator imports constants. |
| secrets_validators.py | software-engineer | constants | Core detection and exception logic |
| cli.py wiring | software-engineer | secrets_validators.py | Wire after validator is stable |
| tests | qa-reviewer | secrets_validators.py, cli.py | Test after implementation is complete |

## Serialization Points

- `scan-findings.json` schema — finalized in this change, consumed by `1p3ro` and `1p3rp`. Do not alter field names after implementation without coordinating both downstream changes.

## Affected Architecture Docs

N/A — change is confined to `wave_lint_lib` (new module, constants additions, cli wiring) and a new framework data file. No boundary, flow, or verification architecture impact.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | No ruleset = no detection |
| AC-2 | required | Merge is the core extensibility mechanism |
| AC-3 | required | Basic detection must work |
| AC-4 | required | Suppression must work or the tool is unusable |
| AC-5 | required | Pending entries must still block |
| AC-6 | required | Auto-append is the exception lifecycle entry point |
| AC-7 | required | Inline suppression with required reason |
| AC-8 | important | Default scope is a usability requirement |
| AC-9 | required | No binary dependency |
| AC-10 | required | Tests are the verification gate |
| AC-11 | required | Policy section is the configuration contract |
| AC-12 | required | Project override is the solo-project escape hatch |
| AC-13 | required | Progress message closes the feedback loop |
| AC-14 | required | Threshold check determines lint outcome; status is not changed by the validator |
| AC-15 | required | Deduplication prevents single-user gaming |
| AC-16 | required | Provenance traceability for upstream rule updates |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| | | |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-06 | Use Gitleaks TOML schema for scan-rules.toml | Binary-optional compatibility; community ruleset is maintained and MIT licensed | Custom schema — rejected: no reuse of existing rulesets |
| 2026-06-06 | Download Gitleaks community rules as the framework default base | Community ruleset covers far more providers than a hand-crafted initial set; MIT licensed; provenance tracked via header comment. Projects extend via `docs/scan-rules.toml`. | Hand-craft initial rules — rejected: incomplete coverage at launch; link to upstream at runtime — rejected: binary dependency |
| 2026-06-06 | Pure Python TOML parsing (tomllib/tomli), no subprocess | No binary install dependency | Subprocess to gitleaks binary — rejected: hard dependency breaks installs |
| 2026-06-06 | Merge framework + project rules, not override | Override means each project maintains full ruleset; merge gives framework coverage by default | Override at project level — rejected |
| 2026-06-06 | Entropy-based detection deferred | High false-positive rate on minified assets, hashes, base64 content | Include at launch — rejected |
| 2026-06-06 | Redact matched text in exceptions file (first 4 + last 4 + ****) | Exceptions file is committed to version control; raw credential in git history is worse than the original problem | Store full match — rejected; store no match — rejected (makes review harder) |
| 2026-06-06 | Multi-confirmation required for `false-positive` (default 2), configurable via `[policy]` | False positive calls are a safety judgment requiring consensus; secret confirmation is a security action not requiring it. Solo projects can set `false_positive_confirmations_required = 1`. | Single confirmation for both — rejected: a lone developer could accidentally suppress a real credential; always require 2 — rejected: blocks solo projects |
| 2026-06-06 | Git user identity captured per confirmation, deduped by email | Provides auditability and prevents single-user gaming the threshold | Username string only — rejected: not unique; no identity capture — rejected: no audit trail |
| 2026-06-06 | Agent sets status explicitly; validator never changes status | Status is a human judgment call, not a mechanical count. Validator reads status + confirmation count to determine lint outcome. | Validator auto-promotes on count — rejected: creates split source of truth; agent should own the classification decision |
| 2026-06-06 | Four status values: pending, false-positive, suspected-secret, confirmed-secret | `false-positive` is the confirmed-safe state (requires N confirmations to suppress lint); `suspected-secret` is an intermediate "needs more analysis" state; separating suspected from confirmed gives the agent a safe holding state | Three values (pending/confirmed-safe/confirmed-secret) — rejected: no intermediate state for agent to flag a likely-real credential pending operator decision |

## Risks

| Risk | Mitigation |
|---|---|
| False positives in test fixtures block development | Inline suppression with required reason provides escape hatch; `false-positive` entries with sufficient confirmations suppress lint permanently |
| TOML schema drift between framework and Gitleaks upstream | Pin to a documented Gitleaks schema version in scan-rules.toml header comment; upgrade notes in seed-160 |
| Pattern list staleness as new providers emerge | scan-rules.toml is a versioned file upgraded via seed-160; operators can add project-level rules immediately without waiting for framework upgrade |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
