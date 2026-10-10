from pathlib import Path
import sys,json,hashlib,collections
root=Path('/Users/coryhacking/Developer/wavefoundry')
packet=json.load(open('/tmp/wf-206is-qualification-readiness-packet.json'))
for row in packet['paths']:
 p=root/row['path']
 assert (not p.exists()) if row.get('absent') else hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'], 'Reviewed path moved: '+row['path']
scripts=root/'.wavefoundry/framework/scripts'
sys.path.insert(0,str(scripts))
import reconcile_scan
paths={
 scripts/'tests/test_extension_tool_modules.py':('EXTENSION_JOURNAL_TEMPLATES=(), EXTENSION_JOURNAL_PRE_MIGRATION_HOOK="",\n                     EXTENSION_REPLACEMENTS={})','EXTENSION_JOURNAL_TEMPLATES=(), EXTENSION_JOURNAL_PRE_MIGRATION_HOOK="",\n                     EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="legacy_cutover",\n                     EXTENSION_REPLACEMENTS={})'),
 scripts/'tests/test_upgrade_wavefoundry.py':('(SCRIPTS_ROOT / f"{helper}.py").read_bytes()','source_path(f"{helper}.py").read_bytes()')}
updates={}
for p,(old,new) in paths.items():
 text=p.read_text();assert text.count(old)==1,(p,text.count(old));updates[p]=text.replace(old,new,1)
raw=reconcile_scan.scan_repo(root)
allowed={'docs/agents/session-handoff.md','docs/architecture/data-and-control-flow.md','docs/specs/mcp-tool-surface.md'}
refs=[r for r in raw if r.file in allowed and r.retired_surface=='docs/agents/journals']
assert len(refs)==3,[(r.file,r.line,r.logical_line) for r in refs]
keys=[reconcile_scan.disposition_key(r) for r in refs]
assert len(set(keys))==3
entries=[{'key':reconcile_scan.disposition_key(r),'status':'historical-record','reason':'Correct retained legacy migration input in C6 contract or historical implementation checkpoint; this does not instruct creation of new journals. Exact logical-line and heading-context identity retains raw audit and re-reports changed or new live instructions.','file':r.file,'matched':r.matched,'logical_line':r.logical_line,'heading_context':r.heading_context,'reviewed_by':'docs-contract-reviewer (independent agent assessment; no human identity asserted)','evidence':'docs/waves/206is journal-hook-follow-up/evidence/delivery/wf-206is-delivery-docs-disposition-probe.log'} for r in refs]
store=root/'docs/reconcile-dispositions.json';assert not store.exists(),'Frozen packet declared this store absent; do not overwrite a new store.'
print(json.dumps({'tests':list(map(str,updates)),'exact_historical_judgments':entries,'apply':'--apply' in sys.argv},indent=2))
if '--apply' in sys.argv:
 for p,text in updates.items():p.write_text(text)
 with store.open('x',encoding='utf-8') as f:f.write(json.dumps(entries,indent=2)+'\n')
 print('Applied only two test fixture substitutions and three exact historical judgments.')
