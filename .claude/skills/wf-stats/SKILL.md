---
name: wf-stats
description: Report project size, progress, index figures and recorded estimates using the shared statistics tool.
---

# Project statistics

Call `wf_stats`; request relevant sections for focused questions and omit
`sections` for a full report. Without MCP, use the repository launcher with
`stats --json`. Present a concise summary, section headings and Markdown
tables, not box-drawing tables. A full report covers all eight sections:

- Code: separate code, documentation and data totals with files, total lines
  and code lines. Show returned language rows with file counts, production/test
  code lines, comments and existing test-share ratio
  (optionally formatted as a percentage). Never combine unrelated categories.
- Source-code TODO markers: marker counts and returned top files; TODO,
  FIXME, HACK and XXX are literal code occurrences, including tests,
  not implementation checklist tasks.
- Lifecycle: label groups "Changes assigned to waves" and "Plans not assigned
  to a wave", adapting lifecycle nouns to project vocabulary. Show
  "Acceptance criteria" and "Implementation tasks" as done, deferred, open and total;
  total = done + deferred + open. Keep not-this-scope separate. Lifecycle
  status rows are distinct from checkbox completion; flag incomplete coverage.
- Documents and roles: returned document, public-prompt and role counts.
- Memories: returned status and kind breakdowns.
- Index: embedding, lexical and graph figures with returned source dates;
  indexed files differ from counted source files.
- Token savings estimates: published estimates with stage and record coverage,
  exclusions and pending markers; never present them as measured savings.
- Secret findings: recorded status/rule counts and confirmation summaries;
  findings-file modification time is not scan time or proof of a clean scan.

Preserve counting rules, estimate labels, source dates and unavailable or
incomplete reasons. Use only returned rows and figures. Do not recount,
infer missing numbers or create new aggregates. Keep large breakdowns concise
and expand on request. Never expose secret-finding content. No change authority.
