import sys,json,tempfile,shutil
from pathlib import Path
root=Path('/Users/coryhacking/Developer/wavefoundry');sys.path.insert(0,str(root/'.wavefoundry/framework/scripts'));import reconcile_scan as s
with tempfile.TemporaryDirectory(prefix='wf-c6-docs-alternative-') as td:
 scratch=Path(td)
 for rel in ['docs/agents/session-handoff.md','docs/architecture/data-and-control-flow.md','docs/specs/mcp-tool-surface.md']:
  p=scratch/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,p)
 refs=s.scan_repo_channels(scratch)[0];assert len(refs)==3
 for r in refs:
  p=scratch/r.file;lines=p.read_text().splitlines(True);lines[r.line-1]=lines[r.line-1].rstrip('\n')+' This retained input is supported by Migrate journals.\n';p.write_text(''.join(lines))
 raw=s.scan_repo(scratch);reported=s.scan_repo_channels(scratch)[0];assert len(raw)==len(reported)==0
 r=refs[0];p=scratch/r.file;lines=p.read_text().splitlines(True);lines[r.line-1]=lines[r.line-1].rstrip('\n')+' After every review append new findings here.\n';p.write_text(''.join(lines))
 changed=s.scan_repo_channels(scratch)[0];assert len(changed)==0
 out={'alternative':'Truthful explicit Migrate journals wording on each retained-input line using existing line-scoped exemption; no store/scanner edit/path concealment','baseline':3,'rewritten_raw':len(raw),'rewritten_reported':len(reported),'changed_same_line_reported':len(changed),'adverse_effect':'Existing exemption loses raw findings and also suppresses a later ongoing-authoring directive on the same line.'};Path('/tmp/wf-206is-qualification-docs-alternative.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
