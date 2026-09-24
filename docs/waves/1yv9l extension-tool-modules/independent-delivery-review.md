# Independent Extension Review

Owner: Engineering
Status: active
Last verified: 2026-09-24

## Verdict

One blocking design/contract gap: DEL-OVERRIDE-VALUE-COMPATIBILITY. Recorded through wf_review_event; no implementation edits, closure or operator signoff performed.

The independent code/security context and the coordinator each reproduced the failure: changing only the fixture override wf_create_wave parameter from slug: str to slug: int passes real build_server registration, then FastMCP call_tool with {"slug": "probe"} raises ToolError / Pydantic int_parsing. The retained reproducer is evidence/override-type-compatibility-probe.py; run from the repository root with the configured MCP-capable tool interpreter and -B. It uses disposable copies and prints the child result (returncode 1 and the validation failure on the reviewed tree).

server_impl.py:17139-17154 checks property names and requiredness, not accepted value schemas. The implementation matches the explicitly enumerated readiness check; the gap is between that enumeration and the broader call-compatible/no-breaking-schema objective. A bounded preservation check for existing parameter schemas and a public-path refusal regression are recommended before close. General JSON Schema subtyping is not required to address the demonstrated case.

## Independent checks

All 13 paths in evidence/final-fingerprint.txt match before and after review. Two reviewer contexts were independent of this wave's implementation: extension_code_security (new context), and pin_readiness (reused from an unrelated wave, with no prior involvement in this wave). Coordinator reviewed architecture/spec changes and independently reproduced the type-narrowing case. These are two independent contexts, not five isolated role seats or a newly convened council.

- Code/security: 18 extension tests passed; no additional security finding within the documented trusted-distribution boundary.
- QA: 18 extension and 13 tool-surface golden tests passed without skips.
- Coordinator: 18 extension tests passed and narrowed-type probe reproduced through real call_tool.
- QA independently recomputed the current full-suite receipt hash: 086c2fe35a28cd3ed69427f44864da76571626dd0a16bfc8934dc1ebab718f5e, recording 9,568 tests. The full suite was not rerun during this review.
- Full docs validation passed on review entry; git diff --check passed.

## Mutation observations

| Context | Mutation | Detection |
| --- | --- | --- |
| Code/security and QA separately | Remove failure cleanup | Failed reload retains 89 extra tools instead of only the runner |
| Code/security and QA separately | Skip override compatibility | Existing malformed overrides register |
| Code/security | Remove extension writer guard | Missing middleware marker; this run stopped before the behavioral assertion |
| QA | Remove extension writer guard | Real call_tool returns ok during the upgrade checkpoint |
| Code/security | Remove async refusal | Async tool registers |
| Code/security | Remove source-location confinement | Escaped module source loads |

No survivors in these bounded sweeps. Initial plain-system-Python attempts had missing imports; results above use the shared tool runtime and scripts PYTHONPATH. No downstream distribution integration, native Windows run or deliberate in-place/postregistration monkeypatch attack was performed. The known trusted-code limitations are not treated as a new sandbox requirement.
