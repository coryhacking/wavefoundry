# BOM Repair QA Review

Owner: qa-reviewer
Status: active
Last verified: 2026-09-21

Fresh independent context: `bom-qa-recheck-20260921`; repair actor was implementer in a distinct context. Requested host-default model/effort for bounded renderer risk; actual runtime identity unknown. Budget: eight minutes, targeted probes only; no survivors justify a broad sweep. Review uses the wf-review-wave skill and MCP-first outline/read validation.

Frozen 16-path packet `evidence/delivery-fingerprint.json`: `1f5f39ecbe246fa2d9fd638adb2eddfd6d4a3bd7d15aee983c098e9198590ffa`; all per-path git object hashes independently matched before probes.

## Executed evidence

`python3 -B /tmp/1ycrj-bom-qa-probe.py` independently drives `render_platform_surfaces.main --repo-root TEMP --platform claude --manifest TEMP/m.json`. Eight combinations cover Guru available/unavailable, valid/duplicate-model BOM+CRLF frontmatter, and missing/stale protocol regions. Each runs twice. All 16 invocations pass: valid headers retain BOM, CRLF, model/effort, tools and unrelated metadata bytes; available Guru refreshes its body; malformed bytes remain exact, warning appears, wrapper is absent from manifest, exit is zero. Repeat wrapper bytes and manifest reporting are stable. Interpreter preflight alone is stubbed; renderer and both reconciler passes execute normally.

| Mutation | Boundary / oracle | Result |
| --- | --- | --- |
| Production unchanged | Eight cases, two public renders each | 16 passes |
| Restore old opening-delimiter check in memory | Valid BOM header must remain byte exact | Killed: BOM/header bytes lost |
| Same old check, malformed duplicate model | Whole file must remain unchanged | Killed: malformed bytes changed |

The mutant replaces exactly one known source fragment and modifies no repository file. Production success is established before mutation, so the controls are non-vacuous. No new findings. MODEL-BOM-1 cycle-2 QA reverification recorded through dry-run/create typed events. Full suite is coordinator-owned and final QA delivery approval waits for a current green receipt.

## Focused readiness and adversarial conclusion

The plan's Intended edits correction retains the shared implementation-wave pointer and keeps detailed policy in canonical seed 180. Strongest challenge: removing repeated policy might sever task-fit guidance. The explicit pointer and required AC-4 retain the route; required AC-2 and its whole-render protection remain unchanged. Strongest alternative: duplicate full policy in both prompt twins, which adds drift without extending authority. No readiness blocker, ownership shift, or contract weakening; MODEL-BOM-1 is a delivery finding. Focused readiness QA and red-team conclusion: pass for the current receipt delta.

## Limits

Configuration preservation only; no live model calls or effective runtime identity/cost claims. No Windows host execution or general YAML-parser guarantee. Existing AC-1/AC-4 evidence remains in delivery-qa.md; this focused repair does not re-run unrelated policy tests or the full suite. No source edits, closure or commit.

## Reproduction

The complete independent probe is retained here for repeatable evidence:

```python
import contextlib, io, inspect, json, sys, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path.cwd()/'.wavefoundry/framework/scripts'))
import render_agent_surfaces as ras
import render_platform_surfaces as rps
import venv_bootstrap

def probe(guru, malformed, protocol):
 with tempfile.TemporaryDirectory() as d:
  root=Path(d); wrapper=root/'.claude/agents/guru.md';wrapper.parent.mkdir(parents=True)
  if guru:
   role=root/'docs/agents/guru.md';role.parent.mkdir(parents=True);role.write_text('# Guru\n')
  header='\ufeff---\r\nname: local-guru\r\nmodel: future/provider-v9\r\neffort: high\r\ntools: Read\r\ncustom: retain\r\n'
  header+= ('model: sonnet\r\n' if malformed else '')+'---\r\n'
  body='\r\nOld body\r\n'
  if protocol: body+=ras.REVIEW_PROTOCOL_MARKER_BEGIN+'\r\nstale\r\n'+ras.REVIEW_PROTOCOL_MARKER_END+'\r\n'
  original=(header+body).encode();wrapper.write_bytes(original)
  first=None
  for n in range(2):
   manifest=root/f'm{n}.json';err=io.StringIO()
   with patch.object(venv_bootstrap,'ensure_python_resolves',return_value='ok'),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(err):
    code=rps.main(['--repo-root',str(root),'--platform','claude','--manifest',str(manifest)])
   assert code==0
   written=json.loads(manifest.read_text())['written'];actual=wrapper.read_bytes()
   if malformed:
    assert actual==original, 'malformed bytes changed'
    assert '.claude/agents/guru.md' not in written, 'malformed reported written'
    assert 'render_agent_surfaces: WARNING' in err.getvalue(), 'warning missing'
   else:
    assert actual.startswith(header.encode()),'BOM/header bytes lost'
    assert ras.REVIEW_PROTOCOL_MARKER_BEGIN.encode() in actual
    if guru: assert b'## Your job' in actual and b'Old body' not in actual
   if n:
    assert actual==first, 'repeat bytes changed'
    assert '.claude/agents/guru.md' not in written, 'repeat wrapper write reported'
   first=actual

for guru in (False,True):
 for malformed in (False,True):
  for protocol in (False,True): probe(guru,malformed,protocol)
print('production: 8 public-entry cases x 2 renders PASS')
source=inspect.getsource(ras._claude_agent_frontmatter)
old='lines[0].lstrip("\\ufeff").strip()'
assert source.count(old)==1
namespace=dict(ras.__dict__)
exec(source.replace(old,'lines[0].strip()'),namespace)
killed=[]
for malformed in (False,True):
 with patch.object(ras,'_claude_agent_frontmatter',namespace['_claude_agent_frontmatter']):
  try: probe(True,malformed,False)
  except AssertionError as exc: killed.append((malformed,str(exc)))
assert len(killed)==2,killed
print('old-delimiter mutant killed:',json.dumps(killed))
```

## Final receipt verification

Coordinator's full suite log independently read: 9,452 tests across 117 files in 293.628 seconds, 12 reported skips, OK. Receipt result is `ok`, ran_at `2026-09-21T17:06:05.478207+00:00`; independently recomputed `run_tests._hash_inputs()` equals `f32695c6f1743b84f994f6d742e96bac32b21b74e643fa22257866900eb6fff0`. All 16 frozen path hashes still match the reviewed packet. Guided delivery validation reports `lint_passed=true`. Existing AC-1/AC-4 evidence remains valid; focused repair covers AC-2/AC-3, and refreshed scoped/full-suite and docs evidence covers AC-5. No `[~]` deferrals. QA delivery approval restored after independent receipt verification.
