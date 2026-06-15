# Scan Findings Format

Owner: Engineering
Status: active
Last verified: 2026-06-15

The canonical schema for **`docs/scan-findings.json`** — the committed ledger the
hardcoded-secrets scanner uses to record, classify, and gate every match. It is
the source of truth for the `pending → false-positive / suspected-secret /
confirmed-secret` lifecycle and for the `wave_close` secrets gate.

This reference consolidates what was previously scattered across
`wave_lint_lib/secrets_validators.py`, `213-security-reviewer.prompt.md`, and
`.wavefoundry/framework/scan-rules.toml`. Those remain the implementation source
of truth; this doc tracks them.

## File location

- **Live ledger (committed, operator-owned):** `docs/scan-findings.json` — a JSON
  array of finding records. Created/appended by the scanner; classified by the
  security reviewer (`seed-213`). Committed to the repo so classifications and
  confirmations persist across runs and reviewers.

## Finding record schema

Each array element is one finding. Scanner-written fields are created by
`wave_lint_lib/secrets_validators.py`'s `_match_hits_for_file`; the fields marked
*(optional)* below are added later by the security reviewer (`seed-213`) or at
`wave_close`, not by the scanner:

| Field | Type | Meaning |
| ----- | ---- | ------- |
| `id` | string | Stable per-findings-file id (e.g. `exc-001`). |
| `file` | string | Repo-relative path of the matched file. |
| `line` | int | 1-indexed line number of the match. |
| `line_hash` | string | Hash of the matched line — survives line drift so the entry re-binds when the line moves. |
| `context_hash` | string | Hash of the surrounding lines — disambiguates identical lines at different positions. |
| `rule_id` | string | The rule that matched (e.g. `generic-api-key`, `jwt`). Dedup is **span-based**: matches that overlap the same span keep the first rule in ruleset order, but different rules matching **disjoint** spans on one line are reported separately (e.g. an `aws-secret-access-key` and a `generic-api-key` finding on the same line are two distinct entries, not a duplicate). |
| `matched_text` | string | The **redacted** matched line (never the raw secret — see Redaction). |
| `status` | string | Lifecycle status (see below). New matches are appended as `pending`. |
| `in_comment` | bool | *(optional)* True when the match is on a leading-comment line — triage context only; a commented secret is still flagged, never auto-suppressed. |
| `exp_date` | string | *(optional, JWT findings)* Human-readable UTC `exp` claim, suffixed `(EXPIRED)` when past. Surfacing only. |
| `override_reason` | string | *(optional)* A non-empty operator reason dismisses a `false-positive` finding even below the confirmation count. **Wave 1p5pz:** no longer used to acknowledge a `confirmed-secret`/`suspected-secret` (that soft-block was dropped). |
| `acknowledged_for_wave` | string | *(optional, legacy — no longer consulted)* Wave id a finding was acknowledged for under the pre-1p5pz per-wave soft-block. `wave_close` no longer reads this field; tolerated if present on legacy findings, but unused. |
| `confirmations` | array | *(optional)* Reviewer confirmations of a `false-positive` (see below). |

### `confirmations[]` sub-schema

Each confirmation (appended by the security reviewer per
`213-security-reviewer.prompt.md`):

| Field | Type | Meaning |
| ----- | ---- | ------- |
| `git_user_name` | string | Reviewer name from `git config user.name`. |
| `git_user_email` | string | Reviewer email — the dedup key (one unique email = one confirmation). |
| `verdict` | string | The reviewer's verdict (e.g. `false-positive`). |
| `reason` | string | Free-text justification. |
| `confirmed_at` | string | UTC ISO-8601 timestamp. **Confirmations expire** (see policy); re-verifying **appends a new dated entry** — never mutate an existing one. |

## Status lifecycle

Per `213-security-reviewer.prompt.md`:

- `pending` — a new, unclassified match. `wave_close` **hard-blocks**. The
  security reviewer classifies each into one of the below.
- `false-positive` — not a real secret. Cleared once it has enough valid
  confirmations (see policy), an `override_reason`, or the effective threshold is
  met. Non-blocking once cleared.
- `suspected-secret` — looks real, unconfirmed; the reviewer must reclassify it as
  `false-positive` or `confirmed-secret`. `wave_close` **hard-blocks** (unresolved)
  until reclassified.
- `confirmed-secret` — a real secret. `wave_close` **does NOT block** (wave 1p5pz):
  classification is the acknowledgment. Instead **every** close surfaces a
  non-blocking standing reminder (`confirmed_secrets` + `secrets_reminder` in the
  `wave_close` response `data`) listing all confirmed secrets, for the agent to
  present to the operator. Remediate (rotate + remove) before distribution; re-scan
  to clear.

**`wave_close` status × gate (wave 1p5pz):**

| status | `wave_close` |
| ------ | ------------ |
| `pending` | **hard-block** until classified |
| `suspected-secret` | **hard-block** (unresolved) until reclassified |
| `confirmed-secret` | **non-blocking** — standing reminder surfaced on every close |
| `false-positive` (cleared) | clears (silent) |

> **Never** label a real secret `false-positive` to clear a gate — `false-positive`
> means "not a real credential" (env-var read, placeholder, test fixture). A known
> real secret is `confirmed-secret`, which does not block close, so there is no
> reason to mislabel it.

**Full-scan reconciliation of `pending` entries.** On a **full** scan, a `pending`
entry whose line still exists but which the current ruleset no longer produces as a
match — e.g. a rule or allowlist change has since suppressed it — is removed
automatically, so a ruleset improvement does not leave a phantom `pending` finding
blocking `wave_close`. This applies **only** to `pending` entries: `false-positive`,
`suspected-secret`, and `confirmed-secret` classifications are operator decisions and
are never auto-removed. Incremental scans (which re-evaluate only changed files) never
prune. A `pending` entry whose line was *removed* is handled by the separate
line-removed sweep regardless of scan mode.

## `[policy]` confirmation contract

From `.wavefoundry/framework/scan-rules.toml` `[policy]` (overridable in
`docs/scan-rules.toml`):

- **`false_positive_confirmations_required`** (default `2`) — distinct-reviewer
  confirmations needed to clear a `false-positive`. Auto-detected from committer
  count at install/upgrade (0–1 → 1, 2–6 → 2, 7+ → 3) and operator-tunable.
- **Effective-threshold clamp** — the threshold is clamped DOWN to the number of
  currently-confirmable (recent, non-bot) reviewers, so a lone active maintainer
  is never deadlocked. It never rises above the policy value.
- **`override_reason`** — a non-empty value dismisses a `false-positive`
  regardless of count (operator escape). *(It no longer participates in the
  `confirmed-secret` path — that soft-block was dropped in wave 1p5pz.)*
- **`confirmation_valid_days`** (default `365`; `0` disables) — a confirmation
  counts only while its `confirmed_at` is within this window of the scan's "now"
  (per-confirmation clock). Expired/undated confirmations are ignored for the
  count (fail-closed) but **left in place**; re-verify by appending a new dated
  confirmation.

## Self-scan and the `[allowlist]` self-exclusion

`docs/scan-findings.json` is **itself committed and scanned**. Without protection,
the redacted matches and free-form reviewer prose it stores would re-trigger the
rules on the next scan (phantom findings). The framework
`[allowlist].paths` therefore **self-excludes** the scanner's own artifacts —
`docs/scan-findings.json`, `scan-rules.toml`, and the allowlist file — so they are
skipped before any read. Do not remove those self-exclusion entries.

The global `[allowlist]` also applies `regexes`/`stopwords` value-filters that
suppress structural-noise match values (`$VAR`, `{{template}}`, `%FMT%`,
`/Users/…` paths, etc.) across every rule.

## Redaction

`matched_text` and `redacted_line` are length-scaled redactions — short values
expose at most a 2+2 window and never more than ~40% of characters; the 4+4 window
applies only at length ≥ 20. Raw secrets are never written to the ledger.

## See also

- `213-security-reviewer.prompt.md` — the authoritative classification/resolution loop.
- `.wavefoundry/framework/scan-rules.toml` — the merged ruleset, `[policy]`, and `[allowlist]`.
- `docs/SECURITY.md` — where the secrets gate sits in the overall posture.
