# The Dashboard Loads Its Scripts Locally and Answers Only Loopback Origins

Change ID: `1zilx-enh dashboard-local-assets-and-origin-checks`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-30
Wave: 1zim2 local-surface-hardening

## Rationale

From a downstream report (verified 2026-09-30 against `v1.28.0`): `dashboard/dashboard.html` loads React and ReactDOM 18.3.1 from unpkg with `crossorigin` but no `integrity`, and elkjs 0.10.0 with neither, so the dashboard depends on a third-party CDN serving exactly those bytes and needs the network to render. `dashboard_server.py` answers every `GET` (`do_GET`, the only method served) whatever the request's `Host` header says; the only host check is on the bind address. The dashboard serves project content (`/api/doc`, `/api/diff`, `/api/project`, `/api/graph`), so it should run entirely from local files and answer only requests addressed to a loopback name (or the host the operator deliberately bound).

## Requirements

1. **Vendored scripts.** React, ReactDOM and elkjs at the same pinned versions ship under `dashboard/vendor/`, taken once from the npm registry (`npm pack`, which checks each tarball against the registry's published integrity), with their licence texts, React's MIT headers kept, and for elkjs (EPL-2.0) a notice of where its source is available. `dashboard.html` loads them from the dashboard's own origin; no external `<script>` or `<link>` remains. The indexer excludes `dashboard/vendor/` (today only `.min.js`/`.min.css` are excluded, so `elk.bundled.js` would be embedded).
2. **Host check.** The first statement of `do_GET` refuses, through `send_error` with 421 Misdirected Request and a short reason, a request whose `Host` is missing or whose hostname (lowercased, one trailing dot removed, IPv6 in brackets) is not `localhost`, `127.0.0.1` or `::1`, on any port (so port forwards keep working; DNS rebinding is blocked by the hostname). When the operator deliberately binds a non-loopback host (the existing warning path), that bound hostname is also accepted; binding `0.0.0.0` therefore admits loopback names only, which is documented.
3. **Response headers.** An `end_headers` override adds `Content-Security-Policy: default-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'` and `X-Content-Type-Options: nosniff` to every response (JSON, assets, SSE, the redirect, `send_error` including the automatic 501).
4. **Packaging and docs.** The vendored files ship in the framework pack (`test_build_pack.py` asserts them) and the upgrade installs them. The docs that describe the CDN load or the network need are updated: `docs/architecture/threat-model.md` dashboard rows, `docs/architecture/data-and-control-flow.md`, `docs/references/dashboard-install-upgrade.md`, `docs/index.md`, `docs/ARCHITECTURE.md`.
5. **Platforms.** Windows, macOS, Linux and WSL2 behave the same.
6. **Transition.** Takes effect when the dashboard restarts on the new release. CHANGELOG under `### Security` in `## [Unreleased]`, worded as hardening.

## Scope

**Problem statement:** the dashboard relies on an external CDN for its scripts and does not restrict which origins it answers.

**In scope:**

- `dashboard/dashboard.html`, `dashboard/vendor/` (new), `scripts/dashboard_server.py` request handling, the indexer exclusion; tests; the listed docs; CHANGELOG.

**Out of scope:**

- Authentication on the dashboard (it stays a loopback, single-operator tool).
- Changes to the API payloads.
- The existing `""` entry in `_LOOPBACK_HOSTS` used by the bind-address warning (the bind host defaults to `127.0.0.1`).

## Acceptance Criteria

- [x] AC-1: `dashboard.html`, parsed, contains no external `<script>` or `<link>`; the three vendored files exist with licence and source notices and match the pinned versions; the existing test that pins the unpkg URLs is replaced by this one.
- [x] AC-2: through the handler: a missing `Host` and a non-loopback hostname are refused with 421 for `/api/project` and `/dashboard.html`; `localhost`, `127.0.0.1` and `[::1]` with any port (and with a trailing dot or upper case) are served; an explicit non-loopback bind also accepts its own hostname.
- [x] AC-3: through a real `ThreadingHTTPServer` on an ephemeral port: every response kind (asset, JSON, SSE, redirect, 404 via `send_error`, 501 for an unsupported method) carries the CSP and `nosniff` headers.
- [x] AC-4: through a real server under the Host check and CSP: every `<script>` and `<link>` in the served page returns 200 from the same origin; the indexer excludes `dashboard/vendor/`; `test_build_pack.py` asserts the vendored files ship. A headless-browser render of the main view under the final policy is recorded as evidence (elkjs may need a CSP allowance; if so the policy states it and why).
- [x] AC-5: the listed docs and CHANGELOG describe the vendored scripts, Host check and headers.
- [x] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Vendor the three scripts with licences and notices; point `dashboard.html` at them; exclude `dashboard/vendor/` from the index.
- [x] Host check first in `do_GET`; harness gets a default `Host` header.
- [x] `end_headers` override for CSP and nosniff.
- [x] Tests (handler, real server, build_pack); secrets scan over the vendored files.
- [x] Docs; CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Dashboard hardening | implementer | readiness | |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.html`, `.wavefoundry/framework/dashboard/vendor/`, `.wavefoundry/framework/scripts/dashboard_server.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`, `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `docs/architecture/threat-model.md`, `docs/architecture/data-and-control-flow.md`, `docs/references/dashboard-install-upgrade.md`, `docs/index.md`, `docs/ARCHITECTURE.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (dashboard rows), `docs/architecture/data-and-control-flow.md`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the external script dependency |
| AC-2 | required | Origin restriction |
| AC-3 | required | Defence in depth on every response |
| AC-4 | important | Local-only operation, packaging and indexing |
| AC-5 | required | Docs stay true |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Delivery repair. DEL-1ZIM2-WILDCARD-ADVERTISED-URL: `main` records `http://{_advertised_host(host)}:...`; a wildcard bind (`0.0.0.0`, `::`, empty) advertises `127.0.0.1` (the server socket is IPv4, so a wildcard bind listens on 127.0.0.1); the readiness probe, `wf_open_dashboard` and the printed URL all read that recorded URL. DEL-1ZIM2-FILES-SEAM-UNPINNED: a real `build_index(files=...)` test. Red-team advisory: `do_GET` also refuses with 421 more than one `Host` header and a request target that is absolute-form or does not start with `/`; threat model, data-and-control-flow and CHANGELOG updated. Progress row on the secrets scan reworded (only the one long line is skipped) | `test_dashboard_main_on_a_wildcard_bind_records_a_url_the_host_check_admits`, `test_host_check_on_a_wildcard_bind_admits_loopback_names_only`, `test_absolute_form_targets_and_repeated_hosts_are_refused`, `test_absolute_form_target_and_repeated_host_get_421_on_a_real_server`, `test_indexer.test_explicit_build_excludes_dashboard_vendor_scripts`. Scratch-copy mutations: URL from bind host, 2 failures; `return name == bound`, 2 failures; target/duplicate check removed, 6+ failures; `files=` filter replaced with `pass`, indexer test fails. Focused: dashboard 225, indexer 384, build_pack 116 OK |
| 2026-10-01 | Implemented. `npm pack react@18.3.1 react-dom@18.3.1 elkjs@0.10.0` (registry integrity checked by npm); unmodified `umd/react.production.min.js`, `umd/react-dom.production.min.js`, `lib/elk.bundled.js` plus licences copied to `dashboard/vendor/{react,react-dom,elkjs}/` with `vendor/README.md` (versions, sources, SHA-256, EPL-2.0 source at kieler/elkjs tag 0.10.0). SHA-256: react `d949f1c3...c4dd`, react-dom `35f4f974...0f6d`, elk `48d338d5...f6bf`. `dashboard.html` loads only `/vendor/...`, `/ds/wfds.js`, `/dashboard.js`, `/dashboard.css`. `dashboard_server`: `_host_allowed` is the first statement of `do_GET` (421 via `send_error`; loopback names on any port, lowercase, one trailing dot, bracketed IPv6; the explicitly bound host via `httpd.bound_host`; wildcard binds admit loopback only); `end_headers` override adds the exact CSP and `nosniff`. Indexer: `VENDORED_ASSET_PREFIXES` applied at the prefix layer and on the `files=` seam; no `WALKER_VERSION` bump (new directory, no rows to evict; consumers never walk `.wavefoundry/`). Harness default `Host: 127.0.0.1:43127`; the two unpkg/CDN pin tests replaced. Headless Chrome (CDP via node) against a real dashboard server for this repository under the final policy: main view rendered (React and ELK loaded, 8356 chars, 4 SVGs), Graph view rendered, an in-page `new ELK().layout()` succeeded, zero CSP issues; negative control (injected inline script) produced a ContentSecurityPolicyIssue, so the probe detects violations. No allowance needed. Secrets: `wf_scan_secrets` incremental clean, findings file unchanged; the scanner skips only the one line of `elk.bundled.js` over 32 KiB (warning in docs-lint output) and scans the rest of the file (cached clean); an ad-hoc windowed scan with the merged 279 rules found only identifier matches (`key: "knownLayoutAlgorithms"`), no credentials; scan-allowlist not touched. Docs and CHANGELOG `### Security` updated; stale `docs/index.md` line citations refreshed. Gapfill: shell grep used for doc and scanner reads where the files were already open | `test_dashboard_server` (`test_dashboard_html_loads_only_same_origin_vendored_scripts`, `test_host_check_*` x3, `DashboardRealServerHeaderTests` x3), `test_build_pack.test_install_pack_carries_the_vendored_dashboard_scripts`, `test_indexer.test_dashboard_vendor_scripts_are_excluded_from_walk_and_files_seam`. Mutations: Host check removed, 23 failures; header loop removed, 15 failures; walk exclusion removed, indexer test fails. Focused: dashboard 221, build_pack 116, indexer 383, server_tools 375 OK; residue census, terminology, secrets validators, docs_lint 1303 OK; `wf_validate_docs` passed |
| 2026-09-30 | Readiness round 1: red-team and the lanes approved with notes, folded in: Host check accepts loopback names on any port and refuses with 421; headers through an `end_headers` override (covers `send_error` and SSE) with `base-uri 'none'` and `frame-ancestors 'none'`; the browser-free AC-4 replaces the untestable render AC, with a headless render as evidence; `dashboard/vendor/` excluded from the index; stale docs, EPL source notice, build_pack asserts and the handler harness `Host` default added. Verified: no `eval`, `Function`, `Worker`, blob or data URLs in `dashboard.js`, `wfds.js` or `dashboard.css`; `new ELK()` passes no `workerUrl` | Prepare council and lane review |
| 2026-09-30 | Planned from a downstream report, verified: unpkg React/ReactDOM 18.3.1 with `crossorigin` and no `integrity`, elkjs 0.10.0 with neither (`dashboard.html` lines 11-13); `do_GET` is the only method and never reads `Host`; `_LOOPBACK_HOSTS` is used only to warn on the bind address; responses set `Content-Type`, `Content-Length` and `Cache-Control` only | Code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Vendor rather than add `integrity` | Removes the network dependency as well as the integrity gap | Pin with `integrity` and `crossorigin` |
| 2026-09-30 | Loopback names on any port | DNS rebinding is defeated by the hostname; exact-port matching breaks port forwards | Exact bound port only |
| 2026-09-30 | Keep this plan local until the fix ships | The repository is public; publish the plan with the fix | Commit the plan first |

## Risks

| Risk | Mitigation |
| --- | --- |
| Vendoring adds about 1.5 MB (elkjs) to the pack | Acceptable; it is downloaded on every dashboard load today; excluded from indexing |
| elkjs needs an eval or worker allowance under CSP | The headless render under the final policy decides; any allowance is stated in the policy and the doc |
| An operator relies on remote access through a `0.0.0.0` bind | Documented; they can bind the specific host they use |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
