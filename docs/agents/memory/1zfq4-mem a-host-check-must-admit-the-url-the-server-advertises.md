# A Host check must admit the URL the server advertises

Owner: Engineering
Status: active
Last verified: 2026-10-01

Memory ID: `1zfq4-mem a-host-check-must-admit-the-url-the-server-advertises`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 113318
Source event: `finding:1zim2:DEL-1ZIM2-WILDCARD-ADVERTISED-URL`
Validation: promote
Validated by: agent
Action delta: When adding a request Host/origin check to a local server, check every URL the server records or prints, including the one built from a wildcard bind host.
Validation rationale: The dashboard Host check refused the URL main recorded for a 0.0.0.0 bind; fixed by advertising 127.0.0.1 for wildcard binds (dashboard_server._advertised_host), verified on a real server.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

The dashboard's loopback-only Host check refused the URL main recorded for a wildcard bind (http://0.0.0.0:P/), so start/open handed the operator a 421 page. Wildcard binds now record a 127.0.0.1 URL (the server socket is IPv4, so a :: bind cannot start). Any origin check needs a test that the recorded/advertised URL's Host is admitted.

## Evidence

- `DEL-1ZIM2-WILDCARD-ADVERTISED-URL`
- `ev-del-1zim2-wildcard-advertised-url-3`
- `1zim2`

## Targets

- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
