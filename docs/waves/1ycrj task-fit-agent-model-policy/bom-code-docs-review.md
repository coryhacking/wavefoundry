# BOM Repair Code And Docs Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Verdict: PASS for focused MODEL-BOM-1 code repair and correlated docs-contract recheck. Context: `bom-code-docs-independent-20260921`, independent of implementer and its repair context. Requested model/effort: host defaults, sufficient for bounded code-grounded review. Observed runtime identity: unknown. Eight-minute risk-selected budget; broaden only for failures or surviving mutants.

All 16 git blob hashes matched evidence/delivery-fingerprint.json before and after execution, fingerprint `1f5f39ecbe246fa2d9fd638adb2eddfd6d4a3bd7d15aee983c098e9198590ffa`. Seven paths differ from pre-BOM packet: renderer, renderer tests, seed160, platform mapping, team workflow, implement-feature and local upgrade prompt. No unrelated frozen path changed.

MCP-first targeted reads validated the parser, merge and both reconciliation paths. Public render_platform_surfaces.main probe executed eight BOM+CRLF cases (valid or duplicate-model, Guru present or absent, protocol absent or stale), each twice. Valid complete header bytes survived including model, effort, restricted tools and permissionMode; Guru body refreshed when available. Malformed whole-file bytes stayed identical, stderr warned, manifest omitted path and exit was zero. Repeat renders were stable.

| Mutation | Oracle | Result |
| --- | --- | --- |
| Restore old delimiter recognition in memory | Valid BOM header exact-byte prefix through public renderer | Killed: valid BOM header changed |
| Same old-line mutant | Malformed BOM exact whole-file bytes through public renderer | Killed: malformed BOM changed |

Seed160 and local upgrade reconciliation sections are identical, preserve deliberate restrictions and surface tool/body mismatch. Implement-feature and implement-wave orchestration pointers are identical. Current Intended edits now explicitly retains this shared pointer: AC4 still reaches canonical seed180 without duplicated policy. Focused docs-contract readiness seat approves this plan delta; no expanded requirements, authority or runtime boundary. Against the red-team primer, the shared pointer still reaches the canonical delegation policy; duplicating the full policy would add drift risk. AC2 preservation does not weaken and ownership remains seed180 for policy and the operator for existing header choices.

Limitations: code/docs are correlated roles in one independent context. No live provider or host behavior, effective model identity, or performance claim. Full suite belongs to coordinator and was not duplicated. Native Python discovery was stubbed; actual rendering used temporary roots. Initial prose section extraction used the wrong heading level and failed; corrected extraction then passed. No source edits, external effects or credentials.

## Reproduction

Run with `PYTHONPATH=.wavefoundry/framework/scripts python3 -B <probe.py>` from repository root.

```python
import contextlib,io,json,tempfile,inspect,subprocess
from pathlib import Path
from unittest.mock import patch
import render_agent_surfaces as ras
import render_platform_surfaces as rps
import venv_bootstrap
repo=Path.cwd(); wave=repo/'docs/waves/1ycrj task-fit-agent-model-policy'
def fingerprint():
 f=json.loads((wave/'evidence/delivery-fingerprint.json').read_text()); assert all(subprocess.check_output(['git','hash-object',p],text=True).strip()==h for p,h in f['paths'].items()); return f
f=fingerprint(); old=json.loads((wave/'evidence/delivery-fingerprint-pre-bom.json').read_text()); print('delta', [p for p,h in f['paths'].items() if old['paths'].get(p)!=h])
def exercise(guru=True, malformed=False, stale=False):
 with tempfile.TemporaryDirectory() as d:
  root=Path(d); target=root/'.claude/agents/guru.md'; target.parent.mkdir(parents=True)
  if guru:
   role=root/'docs/agents/guru.md';role.parent.mkdir(parents=True);role.write_text('# Guru\n')
  header='\ufeff---\r\nname: custom\r\nmodel: "future/provider"\r\neffort: high # deliberate\r\ntools: Read\r\npermissionMode: plan\r\n'+('model: sonnet\r\n' if malformed else '')+'---\r\n'
  original=(header+'Old body\r\n'+(ras.REVIEW_PROTOCOL_MARKER_BEGIN+'\r\nstale\r\n'+ras.REVIEW_PROTOCOL_MARKER_END+'\r\n' if stale else '')).encode(); target.write_bytes(original)
  for i in range(2):
   err=io.StringIO();manifest=root/f'm{i}.json'
   with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(err),patch.object(venv_bootstrap,'ensure_python_resolves',return_value='ok'):
    assert rps.main(['--repo-root',str(root),'--platform','claude','--manifest',str(manifest)])==0
   actual=target.read_bytes(); written=json.loads(manifest.read_text())['written']
   if malformed:
    assert actual==original,'malformed BOM changed'; assert 'WARNING' in err.getvalue(); assert '.claude/agents/guru.md' not in written
   else:
    assert actual.startswith(header.encode()),'valid BOM header changed'
    if guru: assert b'## Your job' in actual and b'Old body' not in actual
   if i: assert actual==first,'second render changed'
   first=actual
for guru in (True,False):
 for malformed in (True,False):
  for stale in (True,False):exercise(guru,malformed,stale)
print('8 BOM CRLF public-path rows x 2 renders passed')
source=inspect.getsource(ras._claude_agent_frontmatter); oldline='lines[0].strip() != "---"'; source=source.replace('lines[0].lstrip("\\ufeff").strip() != "---"',oldline); assert oldline in source
ns={};exec(source,ras.__dict__,ns)
for malformed in (False,True):
 with patch.object(ras,'_claude_agent_frontmatter',ns['_claude_agent_frontmatter']):
  try: exercise(malformed=malformed)
  except AssertionError as exc: print('old delimiter mutant killed:',str(exc))
  else: raise AssertionError('mutant survived')
a=(repo/'.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md').read_text();b=(repo/'docs/prompts/upgrade-wavefoundry.prompt.md').read_text()
def section(t):return t.split('Host-neutral orchestration reconciliation',1)[1].split('### Post-Git readiness',1)[0]
assert section(a)==section(b)
for clause in ('The renderer also preserves `tools:` verbatim','Preserve deliberate operator restrictions','surface any unresolved mismatch'):
 assert clause in section(a)
for p in ('implement-wave','implement-feature'):
 t=(repo/f'docs/prompts/{p}.prompt.md').read_text(); s=t.split('## Host-neutral orchestration',1)[1].split('\n## ',1)[0]
 if p=='implement-wave': pointer=s
 else: assert s==pointer
fingerprint();print('policy parity and same lifecycle pointer passed; all 16 blob hashes remain frozen')
```
