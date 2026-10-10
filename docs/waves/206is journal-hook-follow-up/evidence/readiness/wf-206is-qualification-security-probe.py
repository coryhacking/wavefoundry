import json,sys,hashlib,tempfile,shutil
from pathlib import Path
root=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path.insert(0,str(root/'.wavefoundry/framework/scripts'))
import reconcile_scan as scan
packet=json.loads(Path('/tmp/wf-206is-qualification-readiness-packet.json').read_text())
def hashes():
 return [{'path':p['path'],'sha256':hashlib.sha256((root/p['path']).read_bytes()).hexdigest() if (root/p['path']).exists() else None,'absent':not (root/p['path']).exists()} for p in packet['paths']]
before=hashes()
with tempfile.TemporaryDirectory(prefix='wf-c6-qualification-security-') as td:
 scratch=Path(td)
 for rel in ('docs/agents/session-handoff.md','docs/architecture/data-and-control-flow.md','docs/specs/mcp-tool-surface.md'):
  dest=scratch/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,dest)
 refs=scan.scan_repo_channels(scratch)[0]
 assert len(refs)==3, [(r.file,r.line) for r in refs]
 actual=[{'file':r.file,'line':r.line,'matched':r.matched,'full_line':(scratch/r.file).read_text().splitlines()[r.line-1],'key':scan.disposition_key(r)} for r in refs]
 additions=[{'key':scan.disposition_key(r),'status':scan.HISTORICAL_RECORD,'rationale':'Retained migration-input source reference; not authorization for ongoing journal authorship.'} for r in refs]
 store=scratch/scan.DISPOSITIONS_REL
 store.write_text(json.dumps(additions[:-1]))
 omitted=scan.scan_repo_channels(scratch)[0]
 assert len(omitted)==1 and scan.disposition_key(omitted[0])==scan.disposition_key(refs[-1])
 store.write_text(json.dumps(additions))
 assert scan.scan_repo_channels(scratch)[0]==[]
 raw=[r for r in scan.scan_repo(scratch) if r.retired_surface=='docs/agents/journals']
 assert len(raw)==3
 chosen=refs[0];path=scratch/chosen.file;lines=path.read_text().splitlines(True)
 lines[chosen.line-1]=lines[chosen.line-1].rstrip('\n')+' Write ongoing findings there after every review.\n'
 path.write_text(''.join(lines))
 changed=scan.scan_repo_channels(scratch)[0]
 assert len(changed)==1 and changed[0].file==chosen.file
 assert scan.disposition_key(changed[0])!=scan.disposition_key(chosen)
 live=scratch/'docs/new-live-security-control.md';live.write_text('After each review, append new findings to docs/agents/journals/security.md.\n')
 visible=scan.scan_repo_channels(scratch)[0]
 assert len(visible)==2 and any(r.file=='docs/new-live-security-control.md' for r in visible)
 result={'baseline_hits':3,'references':actual,'omitted_key_visible':1,'exact_v2_remaining':0,'raw_audit_hits':3,'changed_line_visible':1,'new_live_and_changed_visible':2,'repository_store_absent':not(root/scan.DISPOSITIONS_REL).exists(),'hashes_before':before,'hashes_after':hashes()}
 assert result['hashes_before']==result['hashes_after']
 Path('/tmp/wf-206is-qualification-security-probe.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))
