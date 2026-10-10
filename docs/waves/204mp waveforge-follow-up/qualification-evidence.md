# Frozen-tree qualification

Owner: Engineering
Status: draft
Last verified: 2026-10-08

The canonical graph-only full rebuild succeeded: 2,977 changed files, 75,517 nodes and 218,029 edges in 410.0s. The original eight evidence-partition response tests then passed with zero skips in 12.132s. Graph-only setup explicitly does not verify full core readiness. Logs: `/tmp/wf-207t4-canonical-graph-setup.log`, `/tmp/wf-207t4-original-evidence-responses.log`.

The full framework runner passed 11,967 tests across 177 files in 489.549s, with 20 skips, result `ok`. Receipt input hash: `bc0585890c0363e65becec360079a59b697a2c26fa7e7c31ec05bcc6e12a8ee1`, recorded `2026-10-09T05:40:02.702939+00:00`. Command: `python3 .wavefoundry/framework/scripts/run_tests.py`; log `/tmp/wf-integrated-canonical-suite.log`. The 39 reviewed source, test and contract paths stayed unchanged through graph setup and the suite. These results qualify implementation; independent delivery judgments remain pending.

Public C5's full upgrade test file passes 701 tests with two existing native-platform skips in 102.854s. Its focused owner passes 17 tests without skips and includes 35 exact-byte installing/reinstall cases. Four inline/setext and six recursive/container source mutants are detected. Distribution tests pass 107 tests without skips; the ownership inventory verifies 524 files after adding the new graph transaction test. Subprocess/routing tests pass 61 tests without skips in 33.859s.

Focused logs are `/tmp/wf-204mp-block-upgrade-owner.log`, `/tmp/wf-204mp-block-c5-owner.log`, `/tmp/wf-204mp-block-mutants.log`, `/tmp/wf-204mp-block-recursive-mutants.log`, `/tmp/wf-204mp-block-distribution-owners.log` and `/tmp/wf-204mp-block-subprocess-owners.log`.

No native Windows, live downstream Waveforge/Tensorwell, separate private follow-up, journal-hook C6, updated archive or host-restart qualification is included. Loaded MCP setup/index assessment remains indeterminate; reviewers use current disk reads and fresh processes. No wave closure, commit, push or publication is performed.

## Current final qualification — 2026-10-09

The later canonical run supersedes the standing shared receipt above: 11,977 tests across177 files,20 skips,485.889s, result `ok`. Current inputs hash is `a77f5893ba5fc13cdddf41a465cd5e8f70d958f234cc722a11bdf2d879dbebac`, recorded `2026-10-09T07:30:53.840047+00:00`. The final public24-path packet and the phase12/graph9 own source packets remain unchanged after the run. Durable log and receipt are in `evidence/delivery-20261009-final-qualification/`.

Phase207lx and graph207t4 already have all five independent typed delivery approvals and remain paused. Their latest dry-run closure checks prove the current framework receipt and report only operator approval outstanding; focus-attribution notices are observational. Public204mp has all fourteen finding chains independently cleared and current code/architecture/docs/security approvals; final QA independently verified the current receipt and approved delivery. No operator signoff, wave close, commit, push or new pack is recorded. Full setup readiness, loaded-host freshness, native Windows and downstream qualification remain outside these facts.
