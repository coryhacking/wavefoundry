import hashlib, json, shutil, sys, tempfile
from pathlib import Path
root=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path.insert(0,str(root/'.wavefoundry/framework/scripts'))
import reconcile_scan as scan
packet=json.loads(Path('/tmp/wf-206is-qualification-readiness-packet.json').read_text())
def verify_packet():
 rows=[]
 for item in packet['paths']:
  p=root/item['path']
  data=p.read_bytes() if p.exists() else None
  sha=hashlib.sha256(data).hexdigest() if data is not None else None
  blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() if data is not None else None
  assert sha==item['sha256'] and blob==item['git_blob'], item['path']
  assert (data is None)==bool(item.get('absent',False)), item['path']
  rows.append({'path':item['path'],'sha256':sha,'git_blob':blob,'absent':data is None})
 assert len(rows)==12
 return rows
before=verify_packet()
with tempfile.TemporaryDirectory(prefix='wf-c6-chair-qualification-') as td:
 target=Path(td)
 for rel in ('docs/agents/session-handoff.md','docs/architecture/data-and-control-flow.md','docs/specs/mcp-tool-surface.md'):
  p=target/rel
  p.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(root/rel,p)
 initial=scan.scan_repo_channels(target)[0]
 assert len(initial)==3
 judged=[{'key':scan.disposition_key(r),'status':scan.HISTORICAL_RECORD,'rationale':'Independent readiness feasibility: retained migration input or historical source-location decision; no ongoing authoring permission.'} for r in initial]
 store=target/scan.DISPOSITIONS_REL
 store.write_text(json.dumps(judged[:-1]))
 omitted=scan.scan_repo_channels(target)[0]
 assert len(omitted)==1 and omitted[0].file==initial[-1].file
 invalid=[dict(j) for j in judged]
 invalid[-1]['key']=scan.legacy_disposition_key(initial[-1])
 store.write_text(json.dumps(invalid))
 invalid_visible=scan.scan_repo_channels(target)[0]
 assert len(invalid_visible)==1
 store.write_text(json.dumps(judged))
 exact=scan.scan_repo_channels(target)[0]
 raw=scan.scan_repo(target)
 assert len(exact)==0 and len(raw)==3
 ref=next(r for r in initial if r.file=='docs/architecture/data-and-control-flow.md')
 p=target/ref.file
 baseline=p.read_text()
 lines=baseline.splitlines(True)
 heading=max(i for i in range(ref.line-1) if lines[i].startswith('#'))
 lines[heading]=lines[heading].rstrip('\n')+' altered context\n'
 p.write_text(''.join(lines))
 heading_visible=scan.scan_repo_channels(target)[0]
 assert len(heading_visible)==1 and heading_visible[0].file==ref.file
 p.write_text(baseline)
 live=target/'docs/chair-live-instruction.md'
 live.write_text('# Current instructions\nAfter each review append findings to docs/agents/journals/current.md.\n')
 new_visible=scan.scan_repo_channels(target)[0]
 assert len(new_visible)==1 and new_visible[0].file=='docs/chair-live-instruction.md'
 after=verify_packet()
 assert before==after and not (root/scan.DISPOSITIONS_REL).exists()
 result={'baseline':3,'omitted_judgment_visible':1,'invalid_legacy_key_visible':1,'exact_reported':0,'raw_audit':3,'changed_heading_visible':1,'new_live_instruction_visible':1,'before':before,'after':after,'hashes_unchanged':True,'absent_repository_store_preserved':True,'inventory':[{'file':r.file,'line':r.line,'logical_line':r.logical_line,'heading_context':r.heading_context,'key':scan.disposition_key(r)} for r in initial]}
 Path('/tmp/wf-206is-qualification-chair-probe.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('before','after','inventory')},indent=2))
