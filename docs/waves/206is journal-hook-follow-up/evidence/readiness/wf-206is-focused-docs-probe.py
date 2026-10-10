import ast,json,hashlib,pathlib,sys,tempfile,types,subprocess
root=pathlib.Path('/Users/coryhacking/Developer/wavefoundry'); scripts=root/'.wavefoundry/framework/scripts'
plan=(root/'docs/waves/206is journal-hook-follow-up/204mo-enh version-independent-journal-hook.md').read_text()
packet=json.load(open('/tmp/wf-206is-readiness-focused-packet.json'))
results=[]
def record(case,expected,observed):
 assert expected==observed,(case,expected,observed)
 results.append(dict(case=case,expected=expected,observed=observed))
# Readiness contract/census checks; these deliberately do not implement a trigger parser.
requirements={
 'literal_grammar':['exactly one direct module-level literal string assignment, plain or annotated','Only these two strings','empty/non-string/invalid literals, nonliteral expressions, conditional or duplicate bindings','before declaration execution or dependent migration'],
 'unknown_separate':['Unreadable or unparseable source is unknown, not an absent declaration','later-version apply skips the hook with a path-free uncertainty diagnostic and no declaration execution','original pre-1.15 path retains its validated apply-time load/refusal'],
 'preview_trust':['free of declaration, hook and distribution-helper execution','Trusted shipped read-only framework helpers'],
 'incoming_restoration':['journal-only incoming import context spanning selected declaration validation and hook loading/call','top-level module/package names and their descendant keys','Restore prior sys.modules identities','remove newly introduced affected modules','restore sys.path on success and failure','already later on sys.path','do not change the generic _scripts_on_sys_path helper'],
 'registry':['EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER = legacy_cutover','SHIPPED_DECLARATION','third positional helper_modules','outside declared() MCP-extension activation'],
 'delivery_obligations':['actual older-runner upgrade fixture','both import and call time','once per invocation','hook-owned idempotence','exactly-once-across-crashes promise']}
for name,clauses in requirements.items():
 record(name,True,all(c in plan for c in clauses))
 record(name+'_deleted_clause_control',False,all(c in plan.replace(clauses[0],'DELETED') for c in clauses))
for path in ['docs/architecture/layering-rules.md','.wavefoundry/framework/scripts/tests/record_layout_support.py']:
 record('scope_'+path,True,path in packet['files_in_scope'] and path in plan)
 record('omitted_scope_control_'+path,False,path in [p for p in packet['files_in_scope'] if p!=path])
# Exact existing production declaration snapshot assertion, independently extracted without extension execution.
t=ast.parse((scripts/'mcp_tool_extensions.py').read_text()); names={node.target.id if isinstance(node,ast.AnnAssign) else node.targets[0].id for node in t.body if isinstance(node,(ast.Assign,ast.AnnAssign))}; names={n for n in names if n.startswith('EXTENSION_')}
t=ast.parse((scripts/'tests/record_layout_support.py').read_text()); binding=next(n for n in t.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id=='SHIPPED_DECLARATION'); registry=ast.literal_eval(binding.value)
record('current_exact_registry',True,set(registry)==names)
new='EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER'; incoming=names|{new}
record('new_key_unregistered_known_bad',False,set(registry)==incoming)
planned=dict(registry);planned[new]='legacy_cutover'
record('planned_registry_keyset_and_default_control',True,set(planned)==incoming and planned[new]=='legacy_cutover')
# Existing actual loader with realistic cached old sibling, plus fresh-child alternative; no repo targets.
sys.path.insert(0,str(scripts)); import upgrade_extensions as u
with tempfile.TemporaryDirectory(prefix='wf-c6-docs-focused-') as td:
 p=pathlib.Path(td);(p/'focused_dep.py').write_text("VALUE='INCOMING'\n");(p/'focused_hook.py').write_text("import focused_dep\ndef move(root):\n import focused_dep\n return focused_dep.VALUE\n")
 old=types.ModuleType('focused_dep');old.VALUE='OLD';sys.modules['focused_dep']=old
 try:
  hook=u._load_journal_hook(p,'focused_hook:move');record('actual_cached_loader_baseline','OLD',hook(p))
  del sys.modules['focused_dep'];hook=u._load_journal_hook(p,'focused_hook:move')
  with u._scripts_on_sys_path(p):record('actual_uncached_loader_control','INCOMING',hook(p))
  child=subprocess.run([sys.executable,'-B','-c',"import sys;sys.path[:0]=[sys.argv[1],sys.argv[2]];import upgrade_extensions as u;from pathlib import Path;p=Path(sys.argv[2]);print(u._load_journal_hook(p,'focused_hook:move')(p))",str(scripts),str(p)],capture_output=True,text=True,check=True)
  record('fresh_child_alternative','INCOMING',child.stdout.strip())
 finally:sys.modules.pop('focused_dep',None)
 # Current public preview must remain inert even with side-effecting declaration and helper present.
 target=p/'target';sp=target/'.wavefoundry/framework/scripts';sp.mkdir(parents=True);jp=target/'docs/agents/journals';jp.mkdir(parents=True);(jp/'live.md').write_text('Human-owned journal content\n')
 marker=target/'executed';(sp/'mcp_tool_extensions.py').write_text("from pathlib import Path\nPath("+repr(str(marker))+").write_text('bad')\nEXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER='journals_present'\nEXTENSION_JOURNAL_TEMPLATES=()\n")
 before={str(f.relative_to(target)):f.read_bytes() for f in target.rglob('*') if f.is_file()};preview=u.migrate_journals(target,apply=False);after={str(f.relative_to(target)):f.read_bytes() for f in target.rglob('*') if f.is_file()}
 record('actual_public_preview_inert',True,before==after and not marker.exists());results.append({'case':'preview_result','observed':preview})
pathlib.Path('/tmp/wf-206is-focused-docs-probes.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
