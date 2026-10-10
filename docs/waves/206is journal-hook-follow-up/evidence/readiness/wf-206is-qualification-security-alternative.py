import sys,json,tempfile,shutil,hashlib
from pathlib import Path
root=Path('/Users/coryhacking/Developer/wavefoundry');sys.path.insert(0,str(root/'.wavefoundry/framework/scripts'))
import reconcile_scan as scan
reportpath=Path('/tmp/wf-206is-qualification-ready-security.json');report=json.loads(reportpath.read_text())
with tempfile.TemporaryDirectory(prefix='wf-c6-sec-alternative-') as td:
 scratch=Path(td)
 for rel in ('docs/agents/session-handoff.md','docs/architecture/data-and-control-flow.md','docs/specs/mcp-tool-surface.md'):
  p=scratch/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,p)
 refs=scan.scan_repo_channels(scratch)[0];assert len(refs)==3
 for ref in refs:
  p=scratch/ref.file;lines=p.read_text().splitlines(True);lines[ref.line-1]=lines[ref.line-1].rstrip('\n')+' Migrate journals consumes this retained input.\n';p.write_text(''.join(lines))
 raw=len(scan.scan_repo(scratch));reported=len(scan.scan_repo_channels(scratch)[0]);assert raw==0 and reported==0
 p=scratch/refs[0].file;lines=p.read_text().splitlines(True);lines[refs[0].line-1]=lines[refs[0].line-1].rstrip('\n')+' Append new ongoing findings to docs/agents/journals/security.md.\n';p.write_text(''.join(lines))
 changed=len(scan.scan_repo_channels(scratch)[0]);assert changed==0
 observed={'baseline':3,'alternative_raw':raw,'alternative_reported':reported,'new_same_line_directive_reported':changed,'known_bad_concealment_detected':True}
 after=[{'path':x['path'],'sha256':hashlib.sha256((root/x['path']).read_bytes()).hexdigest() if (root/x['path']).exists() else None,'absent':not(root/x['path']).exists()} for x in report['source_hashes_before']]
 assert after==report['source_hashes_before']
 report['source_hashes_after']=after
 report['alternative_weighing']={'actual_report':'/tmp/wf-206is-qualification-ready-docs.json','independently_executed':True,'command':'python3 -B /tmp/wf-206is-qualification-security-alternative.py > /tmp/wf-206is-qualification-security-alternative.log','observed':observed,'decision':'Prefer current exact v2 judgments. The alternative legitimately avoids key maintenance and can clarify migration provenance, but its existing command exemption erases raw audit and hides new ongoing-authoring directives on the same line. Those are explicit required detection properties and this bounded repair may not trade them away. Naming Migrate journals beside hook-only eligibility also risks implying a public command calls the opt-in hook; it does not. No new attacker boundary asserted; the demonstrated alternative is a required-contract correctness failure.'}
 report['same_assessment_correlation']='One assessment supplies specialist readiness and fixed security seat; these are correlated roles, not two independent confirmations. Actual rotating alternative independently weighed in same retained readiness context; no implementation context or repository mutation.'
 report['limitations']=[x for x in report['limitations'] if not x.startswith('Rotating docs alternative')]
 reportpath.write_text(json.dumps(report,indent=2));print(json.dumps(observed))
