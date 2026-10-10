import json,sys,hashlib,tempfile,shutil
from pathlib import Path
root=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path.insert(0,str(root/'.wavefoundry/framework/scripts'))
import reconcile_scan as s
packet=json.loads(Path('/tmp/wf-206is-qualification-readiness-packet.json').read_text())
def hashes():
 return [{'path':p['path'],'sha256':hashlib.sha256((root/p['path']).read_bytes()).hexdigest() if (root/p['path']).exists() else None,'absent':not (root/p['path']).exists()} for p in packet['paths']]
before=hashes()
assert all(a['sha256']==p['sha256'] for a,p in zip(before,packet['paths']))
with tempfile.TemporaryDirectory(prefix='wf-c6-docs-own-') as td:
 scratch=Path(td)
 for rel in ['docs/agents/session-handoff.md','docs/architecture/data-and-control-flow.md','docs/specs/mcp-tool-surface.md']:
  p=scratch/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,p)
 refs=s.scan_repo_channels(scratch)[0];assert len(refs)==3
 judgments=[{'key':s.disposition_key(r),'status':s.HISTORICAL_RECORD,'rationale':'Independent docs-contract judgment: historical source decision or retained migration-input selector; no ongoing authoring authorization.'} for r in refs]
 store=scratch/s.DISPOSITIONS_REL
 store.write_text(json.dumps(judgments[:-1]));assert len(s.scan_repo_channels(scratch)[0])==1
 store.write_text(json.dumps(judgments));assert not s.scan_repo_channels(scratch)[0]
 assert len(s.scan_repo(scratch))==3
 chosen=next(r for r in refs if r.file=='docs/architecture/data-and-control-flow.md')
 p=scratch/chosen.file;original=p.read_text();lines=original.splitlines(True)
 lines[chosen.line-1]=lines[chosen.line-1].rstrip('\n')+' Append ongoing review findings there.\n';p.write_text(''.join(lines))
 assert len(s.scan_repo_channels(scratch)[0])==1
 p.write_text(original)
 lines=original.splitlines(True)
 idx=max(i for i in range(chosen.line-1) if lines[i].startswith('#'))
 lines[idx]=lines[idx].rstrip('\n')+' revised\n';p.write_text(''.join(lines))
 assert len(s.scan_repo_channels(scratch)[0])==1
 p.write_text(original)
 live=scratch/'docs/new-live-docs-control.md';live.write_text('# Current authoring\nAfter each review append findings to docs/agents/journals/new.md.\n')
 visible=s.scan_repo_channels(scratch)[0];assert len(visible)==1 and visible[0].file=='docs/new-live-docs-control.md'
 out={'baseline':3,'omitted_key':1,'exact_remaining':0,'raw_audit':3,'changed_line':1,'changed_heading':1,'new_directive':1,'references':[{'file':r.file,'line':r.line,'logical_line':r.logical_line,'heading_context':r.heading_context,'key':s.disposition_key(r)} for r in refs],'source_hashes_before':before,'source_hashes_after':hashes()}
 assert out['source_hashes_before']==out['source_hashes_after']
 assert not (root/s.DISPOSITIONS_REL).exists()
 Path('/tmp/wf-206is-qualification-docs-probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
