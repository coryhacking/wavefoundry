# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-06-22

## `1p79y factor-surface-integrity` (OPEN / close-eligible) — 3 changes, all IMPLEMENTED + delivery-reviewed
- **`1p79x-enh`** — `check_factor_surface` declared-but-missing factor gate + seed-238/160 reconciliation + renderer audit.
- **`1p7ac-enh`** — re-keyed the gate to `workflow-config factor_review_policy.applicable_factors` (operational lane set); retired-lane=no docs; assessment-vs-lane drift = non-blocking WARNING (`(failures, warnings)` tuple); reconciled self-host `07` (→partial, removed factor-07 doc).
- **`1p7bi-enh`** — delegation-layer MCP-first rule (route code subagents through role-typed agents or carry the directive; subagents inherit MCP tools) in `seed-180`/`seed-100`/`seed-050` + `AGENTS.md`; references the existing exploration order, no restate. Prompt-only.
- Readiness + delivery councils recorded for all three (with `1p7ac`/`1p7bi` addenda). **Close dry-run GREEN.** Suite **3394 green**; docs-lint clean.

## Full 1.8.0 release scope (ready, HELD)
1.8.0 = `1p75h` design-system foundation (closed/pushed) + `1p79y` factor-surface integrity (gate + lane-aware re-key + delegation rule) + vendor-neutrality scrub. Downstream-validated across Java (happy path), solaris (retired-lane), RDS (10-vs-7) consumers; `1p7ac`/`1p7bi` correct the gaps those surfaced.

## Finalize sequence (operator-owned — explicit go on each)
1. **Commit + push `1p79y`** (uncommitted since `63121a9`) — `coryhacking` gh account.
2. **Close `1p79y`** (`wave_close mode=create`).
3. Optional: a fresh local `1.8.0` build with `1p7ac`+`1p7bi` for one more downstream pass.
4. **Cut the real `1.8.0`**: VERSION `1.7.3→1.8.0`, CHANGELOG `1.8.0` section, `build_pack --version 1.8.0 --release` (clean tree + main + `coryhacking`). Real publish — needs explicit go.

## Constraints
- `~/.wavefoundry/venv/bin/python`; tests bytecode-free. Gates open-before/close-after. Wave-record fields `;`-delimited, no `<`. Commit msgs: no AI attribution / no `Co-Authored-By`. No `git commit`/`wave_close(create)`/release without explicit operator request this turn.
- Behavioral adoption (1p7bi): delegate code work via role-typed agents or carry the MCP-first directive; require the `Gapfill:` note.

## Other
- Closed/pushed: `1p75h` + scrub (`6f228b4`, `63121a9` on origin/main). Memory: `project_factor_gate_keying_and_1p8_validation`, `project_mcp_code_tool_quality_log` (session 12).
- Planned, not started: `1p6lp cross-host-skills`.

## Current Session

**Active wave:** *(none)*
