# The Dashboard Request-Target Tests Match What a Real Server Receives

Change ID: `1zim8-bug dashboard-network-path-target-test-fidelity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zim9 dashboard-target-test-fidelity

## Rationale

Operator review of wave 1zim2 noted a test-fidelity issue. `test_dashboard_server.DashboardHttpTests.test_absolute_form_targets_and_repeated_hosts_are_refused` includes the network-path target `//evil.example/api/project` and expects 421. The handler harness sets `self.path` directly, so it skips `BaseHTTPRequestHandler.parse_request`. Since gh-87389, CPython's `parse_request` rewrites a leading `//` to a single `/` before `do_GET` runs (verified on Python 3.13.5; present since 3.11.0, the supported minimum). On a real server the request therefore becomes the path `/evil.example/api/project` and gets 404: it is never served as `/api/project`, and the Host check still runs. The test asserts a status a real client never sees, and nothing pins the real behaviour. The `netloc` branch in `DashboardHandler._request_addressed_here` remains valid defence in depth for a handler whose path was not normalized; no Host-check bypass was demonstrated.

## Requirements

1. The harness test keeps the `//...` case only as an explicitly labelled defence-in-depth check of `_request_addressed_here` (a path that reaches `do_GET` un-normalized), separate from the cases a real client can send.
2. A real-server test (the existing `ThreadingHTTPServer` fixture class used for `test_absolute_form_target_and_repeated_host_get_421_on_a_real_server`) sends a raw `GET //evil.example/api/project HTTP/1.1` with a loopback Host and asserts what the server actually returns: not the project payload, the status it really gives (404 on current CPython), and the CSP and `nosniff` headers. With a non-loopback Host the same target gets 421.
3. No production code changes. The threat-model rows say 421 for an absolute-form target, which `//host/path` is not (it is origin-form), so they stay unchanged.
4. Windows, macOS, Linux and WSL2 behave the same (the normalization is in CPython's request parser).
5. No CHANGELOG entry (test-only).

## Scope

**Problem statement:** a dashboard test asserts a 421 for a network-path request target that a real server never returns, because its harness bypasses the request parser.

**In scope:**

- `tests/test_dashboard_server.py`.

**Out of scope:**

- Changing `_request_addressed_here` or any other production code.

## Acceptance Criteria

- [x] AC-1: the harness test separates real-client cases from the labelled defence-in-depth `//` case, with every existing assertion kept.
- [x] AC-2: a real-server test pins the actual response to `GET //evil.example/api/project` under a loopback Host (no project payload, the real status, CSP and `nosniff`) and 421 under a non-loopback Host; the response body is not the `/api/project` payload, and `///evil.example/api/project` behaves the same. (A `//api/project` target legitimately serves the payload under a loopback Host; the assertion is about network-path targets naming another host.)
- [x] AC-3: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Relabel the harness case.
- [x] Add the real-server test.
- [x] Confirm the threat-model rows need no change (they cover absolute-form targets only).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Test fidelity | implementer | readiness | test-only |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A: the threat-model rows cover absolute-form targets only and stay accurate.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The harness test must not claim real-client behaviour |
| AC-2 | required | The real behaviour must be pinned |
| AC-3 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Implemented (test-only). The harness test keeps its five real-client cases and adds the `//evil.example/api/project` case separately, labelled as defence in depth for a target reaching `do_GET` un-normalized. New `DashboardRealServerHeaderTests.test_network_path_target_is_normalized_on_a_real_server` sends `//evil.example/api/project` and `///evil.example/api/project` to a real server: 404 under a loopback Host and 421 under `evil.example` with and without a port, never the `/api/project` payload, with the CSP and nosniff headers. Scratch mutations: serving `/api/project` for any path ending in it fails the loopback cases; skipping the Host check fails the non-loopback cases. Threat model unchanged (its rows cover absolute-form targets only). Windows, macOS, Linux and WSL2 behave the same: the normalization is in CPython's request parser | `tests/test_dashboard_server.py` 226 OK |
| 2026-10-01 | Planned from the operator's 1zim2 review note. Verified: CPython 3.13.5 `BaseHTTPRequestHandler.parse_request` collapses a leading `//` (gh-87389); the 1zim2 delivery reverifier observed `GET //x/` returning 404 on a real server | `http.server.BaseHTTPRequestHandler.parse_request`; `dashboard_server.DashboardHandler._request_addressed_here` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Keep the `netloc` check and its harness case, labelled as defence in depth | It guards a handler path that reaches `do_GET` un-normalized; removing it would weaken the control | Drop the `//` case from the harness test |

## Risks

| Risk | Mitigation |
| --- | --- |
| A future CPython stops normalizing `//` | The real-server test asserts no project payload and the Host check, so it fails loudly rather than passing silently |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
