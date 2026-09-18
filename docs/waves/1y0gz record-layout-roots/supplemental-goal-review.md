# Supplemental Goal and Integration Review

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Original verdict — superseded by the repair review below

The core goal is substantially achieved: one stdlib module defines fork-editable roots, bounded nested discovery is shared, lifecycle schemas are unchanged, and ordinary relocated lifecycle operations work. The operator-approved constants decision replaces runtime configuration; it does not abandon the centralization goal. Closure is not recommended until the four executed gaps below are repaired. This is supplemental review, not operator signoff or permission to close.

Original versus delivered: the first wave removes record-path coupling; it does not deliver Waveforge's four-tier model, vocabulary substitution, or all later modularity waves. Creates still land directly under the waves root, and grouping is by relocation. Native Windows execution was not performed.

## Findings

1. **P2 — dashboard document reads do not honor the layout.** `dashboard_server.DashboardHandler._handle_doc` constructs wave paths as direct children and still confines reads to `docs/`. The existing UI calls this route with a wave ID (`dashboard.js`, wave document URL). Real-handler temporary-fixture probes return 403 for valid relocated waves and plans, and 404 for a nested wave under `docs/`. Expected 200 and the correct content. Repair discovery-based resolution and containment against validated allowed document roots; keep traversal refusal. Requirements 1y042 R6 and 1y043 R6 are affected.
2. **P2 — memory-ID migration misses relocated and nested references.** `memory_records.migrate_memory_ids_to_lifecycle_naming` scans only `docs/` and determines wave status from the first directory below the root. A legacy memory is renamed, but references in relocated plans/waves and nested active waves remain stale. Ordinary docs and a flat active-wave control are repaired. Closed historical waves remain unchanged, as intended. Union the proper document corpus and resolve actual discovered wave ownership before applying the existing closed-history rule. Requirement 1y042 R6 is affected.
3. **P2 — Windows drive components bypass invalid-root validation.** `record_paths._check_root` rejects a drive prefix only at the beginning of the complete string, while `_join_rel` joins components separately. With Windows path semantics, repo `C:/repo` and constant `docs/D:/waves` yield `D:waves`, outside the repo, with no validation diagnostic. This models a malformed fork edit, not hostile runtime input. Reject drive-qualified components before filesystem traversal; add a portable Windows-path regression. Requirement 1y042 R3 / AC-3 are affected. Probe uses the real resolver with PureWindowsPath and empty-repository existence simulated; native Windows lifecycle execution remains unverified.
4. **P2 — the cache fingerprint bypasses the traversal depth budget.** `McpRepoCache.list_waves_cached` performs bounded discovery, then `_wave_fingerprint` calls `_dir_fingerprint(..., recursive=True)`, which recursively scans the entire root again. A real `wf_current_wave_response` with MAX_DEPTH=1 correctly lists only the direct wave but its fingerprint reads a depth-six wave too. The call-counter test only counts `discover_wave_dirs`, missing the second filesystem walk. Reuse discovered wave paths for fingerprinting and test the actual traversal boundary, retaining warm-cache invalidation. Requirement 1y043 R7 is affected. The first probe failed because macOS temporary-root aliases differed; resolving the fixture root corrected the probe, which then executed successfully.

## Verification and limits

- Independently recomputed full-suite receipt input hash: `82dd7ebe3564ebdb4dcd210f35f73b7bd5c84602877b0f5558b48353c84f5102`, matching the stored successful 9,264-test receipt. The full suite was not rerun.
- Independently ran `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_record*.py' -q`: 81 tests passed. Separate resolver reviewer ran 43 resolver tests successfully.
- Guided delivery inspection confirmed only operator approval was missing before these new findings. Existing approvals did not establish coverage of these scenarios.
- No production code, constants, tests, or host settings changed. Tests and probes used temporary roots. Reviewer source snapshots remained unchanged; `record_paths.py` hash `384dab2309dcf5b6c6e0e9fd3cf6845223b369e4`, `server_impl.py` hash `559f836eaa47a4268e40296b67dc2ca256b5be5e`.
- Mutation table: no production mutant applied. Known-bad controls were the existing implementation exercised against realistic layouts; every finding reproduced the wrong output. Flat memory references and valid direct wave discovery supplied positive controls. Green existing tests alongside these failures demonstrate missing coverage.
- Independent roles: layout_review inspected resolver boundaries; layout_integration inspected routed consumers; coordinator verified receipt, targeted suite, cache probe and re-executed integration probes. Effective worker model/effort identity was not observed.
- Follow-up during repair executed the adjacent nested historical-attribution concern: identical two-commit ancestry gave direct-wave attribution 1/1 but grouped-wave attribution 0/0. Finding `supplemental-nested-drift-attribution` is recorded; the repair and full indexing regression `HistoricalClassTests.test_nested_wave_keeps_landing_attribution_after_relocation` now pass, and bypassing ownership discovery makes that test fail.

## Reproduce dashboard and memory gaps

Run from repository root. Only temporary fixture files are written.

```python
import sys, tempfile, io
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
sys.path.insert(0, str(Path('.wavefoundry/framework/scripts').resolve()))
import dashboard_server as d
import memory_records as m
import record_paths as rp

class HandlerProbe:
    def __init__(self, root, params):
        self.path = '/api/doc?' + urlencode(params)
        self._store = SimpleNamespace(_root=root, _record_roots=rp.load_record_roots(root))
        self.wfile = io.BytesIO()
    def send_error(self, code, message): self.code = int(code); self.message = message
    def send_response(self, code): self.code = int(code)
    def send_header(self, *args): pass
    def end_headers(self): pass

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    rp.WAVES_ROOT = 'project/records/waves'
    rp.PLANS_ROOT = 'project/records/plans'
    rp.NESTED = True
    for rel in ['project/records/waves/1abcd demo/wave.md', 'project/records/plans/1abcd-enh test.md']:
        p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('# Probe')
    for params in [{'type': 'wave', 'id': '1abcd demo'}, {'type': 'change', 'id': '1abcd-enh test', 'path': 'project/records/plans/1abcd-enh test.md'}]:
        p = HandlerProbe(root, params); d.DashboardHandler._handle_doc(p)
        print('relocated dashboard', params['type'], p.code)
    rp.WAVES_ROOT = 'docs/records'; rp.PLANS_ROOT = 'docs/plans'
    p = root / 'docs/records/team/1abcd demo/wave.md'
    p.parent.mkdir(parents=True); p.write_text('# Probe')
    h = HandlerProbe(root, {'type': 'wave', 'id': '1abcd demo'})
    d.DashboardHandler._handle_doc(h); print('nested dashboard wave', h.code)

for waves_root, plans_root in [('project/records/waves', 'project/records/plans'), ('docs/records', 'docs/plans')]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); (root / 'docs/agents').mkdir(parents=True)
        rp.WAVES_ROOT = waves_root; rp.PLANS_ROOT = plans_root; rp.NESTED = True
        text = m.render_memory_record(memory_id='mem-probe-lesson', kind='decision', summary='Probe.', evidence=['`1abcd-bug test` observed'], targets=['src/a.py'], title='Probe', confidence=0.8, status='active', date='2026-07-13')
        m.write_memory_record(root, text, 'mem-probe-lesson')
        paths = [(f'{waves_root}/1abcd flat/wave.md', 'active'), (f'{waves_root}/team/1abce nested/wave.md', 'active'), (f'{waves_root}/team/1abcf closed/wave.md', 'closed'), (f'{plans_root}/1abcd-enh test.md', 'active'), ('docs/test.md', 'active')]
        for rel, status in paths:
            p = root / rel; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'Status: {status}\n\n`mem-probe-lesson`\n')
        result = m.migrate_memory_ids_to_lifecycle_naming(root)
        print('memory layout:', waves_root, 'renamed:', result['renamed'], 'repaired:', result['references_repaired'])
        for rel, status in paths:
            print(rel, status, 'stale reference:', '`mem-probe-lesson`' in (root / rel).read_text())
```

## Repair review — 2026-09-17

All five findings (the four original findings plus the confirmed adjacent historical-attribution gap) are repaired and independently reverified. The approved constants design and tool API are unchanged. Full-suite confirmation is recorded in the wave checkpoint once complete; this report does not grant operator closure approval.

| Finding | Repair and regression | Independent negative control |
| --- | --- | --- |
| dashboard-layout-read | `_handle_doc` discovers wave IDs and validates resolved document roots; `DashboardDocumentLayoutTests` exercises the GET router | Code reviewer killed roots/containment/ambiguity controls; QA docs-only allowlist gives 403 instead of 200 |
| memory-reference-corpus | Migration unions docs/plans/waves, deduplicates, and resolves discovered ownership; `LifecycleMemoryIdTests` covers interrupted rerun and preserved closed/archive/ledger bytes | Code corpus/history/alias mutants killed; QA docs-only corpus leaves stale references |
| windows-drive-component | `_check_root` rejects every drive-qualified component before inspecting ancestors; portable both-root test with present/absent ancestors | Guard bypass returns empty diagnostics and fails 12 subcases |
| fingerprint-depth-budget | `_wave_fingerprint(wave_dirs=...)` stats only supplied discovered records; cold/warm current-wave regression forbids recursive traversal | Restoring recursive fingerprint fails boundary test |
| nested-drift-attribution | `compute_doc_drift` uses discovered nested ownership prefixes; real indexing/Git-history regression verifies stored historical attribution | Empty discovery gives 0 rather than 1; QA grouping folder named `1bbbb grouping` still preserves old/new 1/0 |

Independent code context `layout-supplemental-code-review-20260917-independent`: 64 baseline tests, no skips; nine focused controls killed. Independent QA context `qa-supplemental-independent-20260917-c3`: 75 baseline tests, no skips; five controls killed. Council context `/root/supplemental_council`: 11 independent checks, two personally executed killed controls (recursive fingerprint and docs-only dashboard allowlist), two restored baseline checks, plus focused synthesis of code/QA outputs; unanimous approval, no new blocker. Counts overlap and must not be added as distinct coverage. Coordinator full suite passed: 9,277 tests across 103 files, 12 skips, fresh receipt.

Council standard primer applied adversarial, constructive and simplicity stances. Strongest challenge: a partial consumer repair could widen dashboard access or alter historical memory. Strongest alternative: reuse validated roots and discovered identities directly; that is the repair. Two questions: do valid relocated/nested reads preserve containment, ambiguity refusal and history, and do drive rejection, bounded traversal and attribution work without a new config surface? Both answered by current-tree inspection and executed checks. This was a focused repair replay, not a claim of rerunning all prior council seats.

All reviewed production hashes stayed frozen: record_paths `f95be55850dd7af68d610395d1629ad3f5cb2cee`, server_impl `438e1e8be7cb4606f99ec7011047dd5c86b88983`, dashboard_server `97d55601c2bb481b30d0d1ba310186eb8f790981`, memory_records `c6b3fb5d33de774decd56d568d7127a3e38979e0`, index_state_store `d6c1cbd7c8b0b577aa18bc4155bf06c8418da4fd`.

Limitations: no native Windows/Linux execution or new browser visual test. Windows drive validation uses actual portable Windows-path semantics. All mutants ran in isolated copies or process memory; shared source was never mutated by reviewers. One compiled drift mutant triggered the runtime-integrity guard; it was replaced with a dependency-control mutant which failed the intended semantic assertion. QA corrected one mismatched substitution before executing its drive mutant. Neither setup error counted as a killed mutant.
