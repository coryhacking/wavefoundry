import json, shutil, tempfile
from pathlib import Path
import reconcile_scan as scan
root=Path.cwd()
with tempfile.TemporaryDirectory(prefix='wf-c6-doc-disposition-') as td:
    scratch=Path(td)
    for rel in ('docs/agents/session-handoff.md','docs/architecture/data-and-control-flow.md','docs/specs/mcp-tool-surface.md','docs/reconcile-dispositions.json'):
        source=root/rel
        if source.exists():
            target=scratch/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
    refs=scan.scan_repo_channels(scratch)[0]
    assert len(refs)==4, [(r.file,r.line,r.matched) for r in refs]
    store=scratch/scan.DISPOSITIONS_REL
    records=json.loads(store.read_text()) if store.exists() else []
    additions=[{'key':scan.disposition_key(r),'status':scan.HISTORICAL_RECORD,'rationale':'Retained reference to historical journal source consumed by migration, not permission to write new journals.'} for r in refs]
    records.extend(additions); store.write_text(json.dumps(records,indent=2))
    assert scan.scan_repo_channels(scratch)[0]==[], 'exact judged retained-source references should suppress'
    assert len([r for r in scan.scan_repo(scratch) if r.retired_surface=='docs/agents/journals'])>=4, 'raw audit must retain original hits'
    original=scratch/refs[2].file
    lines=original.read_text().splitlines(True)
    lines[refs[2].line-1]=lines[refs[2].line-1].rstrip('\n')+' Write fresh ongoing journals into that directory.\n'
    original.write_text(''.join(lines))
    changed=scan.scan_repo_channels(scratch)[0]
    assert any(r.file==refs[2].file and r.retired_surface=='docs/agents/journals' for r in changed), 'changed logical line must not inherit judgment'
    runbook=scratch/'docs/live-journaling-control.md'
    runbook.write_text('At close, write new findings into docs/agents/journals/reviewer.md.\n')
    remaining=scan.scan_repo_channels(scratch)[0]
    assert any(r.file=='docs/live-journaling-control.md' for r in remaining), 'new live journal directive must be detected'
    print(json.dumps({'baseline_exact_hits':len(refs),'after_v2_judgments':0,'raw_audit_retains_hits':True,'changed_line_detected':True,'new_live_directive_detected':True,'proposed_entries':additions},indent=2))
