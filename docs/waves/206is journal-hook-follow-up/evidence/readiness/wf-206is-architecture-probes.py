import ast,importlib.util,json,pathlib,sys,tempfile,types
from unittest.mock import patch
S=pathlib.Path.cwd()/'.wavefoundry/framework/scripts'
sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('c6_arch_extensions',S/'upgrade_extensions.py')
ext=importlib.util.module_from_spec(spec);spec.loader.exec_module(ext)
rows=[]
with tempfile.TemporaryDirectory(prefix='c6-architecture-') as td:
 root=pathlib.Path(td);inc=root/'.wavefoundry/framework/scripts';inc.mkdir(parents=True)
 (root/'docs/agents/journals').mkdir(parents=True);j=root/'docs/agents/journals/current.md';j.write_text('retained content\n')
 (inc/'arch_dep.py').write_text('VALUE="PACK"\n')
 (inc/'arch_call_dep.py').write_text('VALUE="PACK_CALL"\n')
 (inc/'arch_hook.py').write_text('import arch_dep\nfrom pathlib import Path\ndef relocate(root):\n import arch_call_dep\n Path(root,"result").write_text(arch_dep.VALUE+":"+arch_call_dep.VALUE)\n')
 for cached in [True,False]:
  for n,v in [('arch_dep','OLD'),('arch_call_dep','OLD_CALL')]:
   if cached:
    m=types.ModuleType(n);m.VALUE=v;sys.modules[n]=m
   else:sys.modules.pop(n,None)
  before=list(sys.path)
  with ext._scripts_on_sys_path(inc):ext._load_journal_hook(inc,'arch_hook:relocate')(root)
  observed=(root/'result').read_text()
  assert observed==('OLD:OLD_CALL' if cached else 'PACK:PACK_CALL')
  assert sys.path==before
  rows.append({'case':'cached_both_import_and_call' if cached else 'uncached_control','expected_current': 'OLD:OLD_CALL' if cached else 'PACK:PACK_CALL','observed':observed,'expected_required_ac4':'PACK:PACK_CALL','known_bad_detected':cached,'sys_path_restored':True})
 # Explicitly inspect the existing failure boundary: the path restores while fresh imports stay cached.
 (inc/'arch_fail.py').write_text('def relocate(root):\n import arch_call_dep\n raise RuntimeError("scratch failure")\n')
 sys.modules.pop('arch_call_dep',None);before=list(sys.path)
 with ext._scripts_on_sys_path(inc):
  hook=ext._load_journal_hook(inc,'arch_fail:relocate')
  ok=ext._run_journal_pre_migration_hook(root,'arch_fail:relocate',hook)
 assert ok is False and sys.path==before and 'arch_call_dep' in sys.modules
 rows.append({'case':'current_failure_restoration_boundary','hook_return':ok,'sys_path_restored':True,'imported_module_remains_cached':True})
 # Actual pre_docs_gate faithful boundary; unrelated work patched, destructive migration replaced by counters.
 (root/'.wavefoundry/upgrade-in-progress.json').write_text('{"review_sidecar_cleanup":{}}')
 (inc/'mcp_tool_extensions.py').write_text('from pathlib import Path\nPath(__file__).with_name("declared.marker").write_text("loaded")\nEXTENSION_JOURNAL_TEMPLATES=()\nEXTENSION_JOURNAL_PRE_MIGRATION_HOOK="arch_hook:relocate"\nEXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="journals_present"\ndef journal_declaration_problems():return []\n')
 for v in ['1.14.9','1.15.0','1.29.0']:
  (inc/'declared.marker').unlink(missing_ok=True);(root/'result').unlink(missing_ok=True)
  calls=[]
  with patch.object(ext,'repair_declaring_scaffold'),patch.object(ext,'_reconcile_graph_builder_doc_claim'),patch.object(ext,'_migrate_memory_naming'),patch.object(ext,'_migrate_journals',side_effect=lambda *args:calls.append(True)):
   ext.pre_docs_gate(types.SimpleNamespace(root=root,from_version=v))
  expected=v=='1.14.9';observed={'declaration':(inc/'declared.marker').exists(),'hook':(root/'result').exists(),'builtin':bool(calls)}
  assert all(x==expected for x in observed.values()) and j.read_text()=='retained content\n'
  rows.append({'case':'current_pre_docs_gate_baseline','from_version':v,'observed':observed,'journal_bytes_preserved':True,'future_optin_not_claimed':True})
 for label,source in [('absent','X=1'),('literal','EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="journals_present"'),('invalid_literal','EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="invalid"'),('dynamic','EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER=str("journals_present")'),('conditional','if True:\n EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="journals_present"')]:
  try:value=ext._static_module_literal(ast.parse(source),'EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER');out=repr(value)
  except ValueError:out='ValueError'
  rows.append({'case':'static_selection_feasibility','input':label,'observed':out})
pathlib.Path('/tmp/wf-206is-architecture-probe-results.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
