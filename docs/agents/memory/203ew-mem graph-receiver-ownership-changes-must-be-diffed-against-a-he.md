# Graph receiver-ownership changes must be diffed against a HEAD build for every established receiver shape

Owner: Engineering
Status: active
Last verified: 2026-10-08

Memory ID: `203ew-mem graph-receiver-ownership-changes-must-be-diffed-against-a-he`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-10-08
Updated: 2026-10-08

## Summary

Before changing graph_indexer._ts_call_receiver_unowned or any receiver-ownership rule, build the same fixtures with HEAD and with the change and compare targets for every owned shape: self/this/super/base (and parenthesized), Ruby constants and constant-only scope_resolution, Java Outer.this/Outer.super, Rust identifiers typed S, &S, &mut S, &'a S or let s = S, and parenthesized callees. Wave 203pu's first classifier silently dropped correct targets for Ruby M::K, Java Outer.this and Rust &T receivers; only a HEAD-vs-new probe found it. Residual gaps still name-bind: PHP $x->m(), C/C++ obj.m(), Ruby lowercase receivers, JS super with an external parent.

## Evidence

- `203pu`
- `201wg-bug graph-receiver-call-target-integrity`
- `DEL-1`
- `test_graph_call_integrity.UnownedMemberCallTests`

## Targets

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_call_integrity.py`
- `docs/architecture/graph-index-system.md`
