# Scan Findings Format

Owner: Engineering
Status: active
Last verified: 2026-06-28

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

## Always-present ledger (a clean scan writes `[]`)

A **full** scan with **zero findings** and no prior file writes the ledger as a
**bare `[]`** — so the file's *presence* confirms a scan ran (vs. the ambiguous
"clean or never ran?" of an absent file). This is a bare JSON empty array, **not**
a metadata wrapper: a `scanned_at`-style wrapper would rewrite the file on every
scan and churn git history, while a bare `[]` only changes when findings change.
Scan timing is already tracked separately in the indexer's `scan-state.json`.

- The bare `[]` loads as an empty list, so the `wave_close` secrets gate sees no
  findings and **does not block** (gate semantics unchanged).
- The write is **idempotent** — re-running a clean full scan finds the file
  already present and rewrites nothing, so the content never churns.
- The write is gated to **full scans only**. An *incremental* scan must not create
  the file: the indexer's `scan_secrets.update_secrets_scan` keys on the file being
  **missing** to force a full regeneration re-scan, so an incremental scan
  fabricating the file would silently disable that trigger.

## Finding record schema

Each array element is one finding. Scanner-written fields are created by
`wave_lint_lib/secrets_validators.py`'s `_match_hits_for_file`; the fields marked
*(optional)* below are added later by the security reviewer (`seed-213`) or at
`wave_close`, not by the scanner:

| Field | Type | Meaning |
| ----- | ---- | ------- |
| `id` | string | Stable finding id. New findings use a **lifecycle-backed** id `<prefix>-sec` matching `^[0-9a-z]{5}-sec$` (e.g. `1p8l0-sec`) — see **Finding ID format** below. Legacy `exc-###` ids are still tolerated and migrated on the next scan. |
| `legacy_id` | string | *(optional)* The previous `exc-###` id when a finding was migrated to the `<prefix>-sec` shape — see **Finding ID format / migration** below. Present only on migrated records. |
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

## Finding ID format

Scanner-created findings use a **lifecycle-backed** id of the form `<prefix>-sec`
matching `^[0-9a-z]{5}-sec$` (e.g. `1p8l0-sec`). The `<prefix>` is the same
5-character base36 lifecycle prefix family used by waves, changes, and ADRs (see
`lifecycle_id.py`), with a `sec` suffix.

- **No slug.** Unlike change-doc ids (`<prefix>-<kind> <slug>`), a scanner finding
  id carries **no generated slug**. Finding context lives in the structured record
  fields (`file`, `line`, `rule_id`, `line_hash`, `context_hash`, `matched_text`),
  so a slug would only duplicate already-structured data and add avoidable
  collision/determinism work. The scanner — not an agent — mints the id.
- **Collision-safe.** New and migrated ids dedupe against existing lifecycle
  prefixes (plans, waves, ADRs) **and** against existing ids in this file,
  including multiple findings minted during the same scan.
- **`sec` is scanner-scoped.** `sec` is **not** a public change-doc kind — it never
  appears in `wave_new_*` kind lists, `VALID_CHANGE_KINDS`, or plan/wave
  scaffolding. It is owned by the scanner and the lifecycle library only.
- **Distinct from reviewer-lane finding ids.** Security-reviewer lane findings use
  ordinal ids like `SEC-1` (per `213-security-reviewer.prompt.md` / the generic
  finding-record schema). Those are unrelated to scanner **ledger** ids and are not
  changed by this format.

### Migration of legacy `exc-###` ids

Earlier findings used local sequential ids such as `exc-001`. On the next scan the
scanner **migrates** any `exc-###` id to a `<prefix>-sec` id, in place:

- **Lossless.** Every non-id field — `status`, `confirmations`, `override_reason`,
  line/context hashes, redacted `matched_text`, and any security-reviewer fields —
  is preserved exactly. Only `id` is replaced.
- **Traceable.** The previous id is recorded as `legacy_id` (e.g.
  `"legacy_id": "exc-001"`) so external references to the old id (commits, notes,
  discussion) can still be traced after conversion.
- **Idempotent.** Running the scan again does not re-change already-migrated ids or
  duplicate `legacy_id`.
- **Re-binding preserved.** A migrated record still re-binds by `file` / `rule_id` /
  `line_hash` / `context_hash`, so a re-scan with line drift updates the existing
  `sec` record instead of minting a duplicate.

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
