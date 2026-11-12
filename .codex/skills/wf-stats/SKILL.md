---
name: wf-stats
description: Report project size, progress, index figures and recorded estimates using the shared statistics tool.
---

# Project statistics

Call `wf_stats`; request relevant sections for focused questions and omit
`sections` for a full report. Leave `include_wave_details` false unless the
question asks for per-wave accounting; then request it explicitly. Request
`group_by="directory"` only for directory composition. Without MCP, use the repository launcher with
`stats --json`. Present a concise summary, section headings and Markdown
tables, not box-drawing tables. A full report covers all eight sections:

- Code: separate code, documentation and data totals with files, total lines
  and code lines. Prefer returned effective non-test/test line counts and
  test-share ratio, with inline-analysis precision beside them. Legacy
  production/test fields are path-only compatibility counts, not shipping
  evidence. Show configured or inferred roles separately from language and
  format; a declared shipped file can contain test code. Use "non-test" for
  the unconfigured bucket. Test share is not test coverage. Mixed-file counts
  overlap; do not sum them as distinct files. Directory rows use the same
  included-file totals. Never combine unrelated categories. Unsupported Rust
  syntax or unavailable parsing keeps a labelled path-only fallback; Swift
  target roots are explicit declarations, not discovered by running builds.
- Source-code TODO markers: marker counts and returned top files; TODO,
  FIXME, HACK and XXX are literal code occurrences, including tests,
  not implementation checklist tasks.
- Lifecycle: label groups "Changes assigned to waves" and "Plans not assigned
  to a wave", adapting lifecycle nouns to project vocabulary. Show
  "Acceptance criteria" and "Implementation tasks" as done, deferred, open and total;
  total = done + deferred + open. Keep not-this-scope separate. Lifecycle
  status rows are distinct from checkbox completion; flag incomplete coverage.
  Explain the returned completion rule. Show open work in active and paused
  containers from returned checklist rows, with an omitted-row count if shortened.
- Documents and roles: returned document, public-prompt and role counts.
- Memories: every returned status, including candidates awaiting validation,
  rejected and archived records, plus active kinds. Candidate records are
  not unwritten proposals or an upgrade's backfill worklist.
- Index: embedding, lexical and graph figures with returned source dates;
  indexed files differ from counted source files.
- Token savings estimates: published estimates with stage and record coverage,
  credits, recorded request/response debits, exclusions and pending markers.
  Put "No paired evaluations recorded" beside the estimate when the returned
  paired count is zero. Debits are recorded accounting estimates, not total
  model consumption or billing; never call the net estimate measured savings.
- Secret findings: recorded status/rule counts and confirmation summaries;
  findings-file modification time is not scan time or proof of a clean scan.
  Separately show machine-local latest/last-full scan observations and current
  outstanding incomplete coverage. Missing history is unknown; dated history
  does not prove the current tree clean. Allowlist entries are not matched files.

Preserve counting rules, estimate labels, source dates and unavailable or
incomplete reasons. Describe skipped-file reasons and bounded examples, including omitted counts;
observed excluded directories do not count their unvisited descendants.
Use only returned rows and figures. Do not recount, infer missing numbers
or create new aggregates. Keep large breakdowns concise
and expand on request. Never expose secret-finding content. No change authority.
