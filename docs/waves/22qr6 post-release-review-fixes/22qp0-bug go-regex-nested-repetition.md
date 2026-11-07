# Reject Go-invalid nested repetition in rule regexes

Change ID: `22qp0-bug go-regex-nested-repetition`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: 22qr6 post-release-review-fixes

## Rationale

`wave_lint_lib/expr_filter.py` translates Go RE2 rule regexes for Python and promises to refuse syntax that Go rejects. In an executed probe, `compile_regex` accepted `a*+`, `a++`, `a?+` and `a{2}+`. Python 3.11+ reads them as possessive quantifiers; Go's `regexp/syntax` rejects them with "invalid nested repetition operator". A rule that upstream refuses therefore compiles locally with different matching semantics: possessive matching gives up backtracking and can miss matches. The same review claimed that string indexing should return a string. That was verified as not a defect: Go Expr indexing of a string yields a byte, which the port mirrors.

## Product Intent

Project and imported scanner rules that Go would refuse also fail to compile locally, with a clear error, instead of silently matching differently from the pinned upstream semantics.

## Requirements

1. After a quantifier (`*`, `+`, `?`, `{n}`, `{n,}`, `{n,m}`) and its optional lazy `?`, another quantifier raises `CompileError` naming invalid nested repetition.
2. Valid lazy forms (`a*?`, `a+?`, `a??`, `a{2,3}?`) still compile with unchanged behavior.
3. A quantifier that follows a flag-only group (`(?i)`) directly after a quantified atom never fuses with the earlier quantifier in the emitted Python pattern. Today `a*(?i)+` emits a possessive and `a*(?i)?` a lazy quantifier. Such a pattern raises `CompileError` unless its translation is shown to be Go-equivalent.

## Scope

**In scope:** the quantifier branch of the translator, plus tests.

**Out of scope:** the string-indexing semantics (verified faithful to upstream); other translator constructs.

## Acceptance Criteria

- [x] AC-1: `a*+`, `a++`, `a?+`, `a{2}+` and `a*??` each raise `CompileError` through the public compile path; on the current code the first four compile.
- [x] AC-2: `a*?`, `a+?`, `a??` and `a{2,3}?` compile and match as before, and the existing reference cases pass unchanged.
- [x] AC-2a: `a*(?i)+` and `a*(?i)?` no longer produce a fused possessive or lazy quantifier; on the current code they do.
- [x] AC-3: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Reject a quantifier that directly follows a quantifier.
- [x] Add regression tests, including a known-bad control.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| translator | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/expr_filter.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: confined to one module, with no boundary or flow change.

## Platform Behavior

Pure Python. Identical on Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect. |
| AC-2 | required | No regression of valid lazy forms. |
| AC-2a | required | The same defect reached through a flag group (red-team RT-2). |
| AC-3 | required | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Planned from verified review finding 5; finding 4 dispositioned not a defect. | Verifier probe f45 plus the upstream `vm/runtime/runtime.go` `Fetch` |
| 2026-11-06 | Implemented in `_Regex.group`'s quantifier branch: a quantifier, its optional lazy `?`, then another quantifier (`*`, `+`, `?`, `{n...}`) raises `CompileError("invalid nested repetition operator")`. A repetition after one or more flag-only groups that follow a repetition raises `CompileError` naming the flag group. Go accepts that form as a repetition of the earlier repetition, so a Go-equivalent translation would need wrapping; refusal was chosen because it is simpler and no shipped rule uses the form. Escaped, bracketed and non-repeat `{` characters are unchanged. | `expr_filter.py` diff; HEAD probe: `a*+`, `a++`, `a?+`, `a{2}+` compiled verbatim and `a*(?i)+` became `a*+`, `a*(?i)?` became `a*?`, `a*(?i)(?s)+` became `a*+` and `a{2}(?i)+` became `a{2}+` |
| 2026-11-06 | Tests added to `test_expr_filter.py`: nested-repetition refusals (message asserted), flag-group refusals (multiple groups, `{n}`, lazy-before), unchanged lazy and literal quantifier forms, and compilation of every shipped regex source. Known-bad: the same tests run against HEAD's `expr_filter.py` in a scratch tree fail 14 subtests (8 nested, 6 flag-group) and pass with the fix. Shipped rules: 811 regex sources (rule `regex`/`path`, global allowlist `regexes`/`paths`, backtick literals in rule and global filter/prefilter) compile with 0 refusals both before and after. Platform: pure Python, identical on Windows, macOS, Linux and WSL2. | `run_tests.py --file test_expr_filter.py` OK (18 tests); `--file test_betterleaks_engine.py` OK (30 tests); scratch `impl-regex/` run FAILED (failures=14) on HEAD module |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-06 | Reject in the translator's quantifier branch. | This is where Go's rule lives; efficacy: each motivating pattern then fails to compile as upstream does. | Post-compile pattern scan; duplicates parsing. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A shipped rule uses such a form | Compile all 474 shipped rules in the tests; any hit is a real upstream incompatibility. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
