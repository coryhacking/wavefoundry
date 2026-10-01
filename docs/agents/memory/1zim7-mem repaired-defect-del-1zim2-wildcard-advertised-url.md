# Repaired defect DEL-1ZIM2-WILDCARD-ADVERTISED-URL

Owner: Engineering
Status: superseded
Last verified: 2026-10-01

Memory ID: `1zim7-mem repaired-defect-del-1zim2-wildcard-advertised-url`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 113318
Source event: `finding:1zim2:DEL-1ZIM2-WILDCARD-ADVERTISED-URL`
Validation: rewrite
Validated by: agent
Action delta: When adding a request Host/origin check to a local server, check every URL the server records or prints, including the one built from a wildcard bind host.
Validation rationale: The dashboard Host check refused the URL main recorded for a 0.0.0.0 bind; fixed by advertising 127.0.0.1 for wildcard binds (dashboard_server._advertised_host), verified on a real server.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zfq4-mem a-host-check-must-admit-the-url-the-server-advertises`

## Summary

Real defect fixed in wave 1zim2: Mutations killed.

## Evidence

- `DEL-1ZIM2-WILDCARD-ADVERTISED-URL`
- `ev-del-1zim2-wildcard-advertised-url-4`
- `1zim2`

## Targets

- `tests/test_dashboard_server.py`
