import ast, contextlib, importlib.util, io, json, sys, tempfile, types
from pathlib import Path
from unittest.mock import patch
REPO=Path('/Users/coryhacking/Developer/wavefoundry')
scripts=REPO/'.wavefoundry/framework/scripts'
spec=importlib.util.spec_from_file_location('readiness_code_ext', scripts/'upgrade_extensions.py')
ext=importlib.util.module_from_spec(spec);spec.loader.exec_module(ext)
result=[]
with tempfile.TemporaryDirectory(prefix='wf-readiness-code-') as d:
 root=Path(d);incoming=root/'.wavefoundry/framework/scripts';incoming.mkdir(parents=True)
 (incoming/'code_review_dep.py').write_text('VALUE="INCOMING"\n')
 (incoming/'code_review_hooks.py').write_text('import code_review_dep\nAT_LOAD=code_review_dep.VALUE\ndef prepare(root):\n import code_review_dep\n return AT_LOAD+":"+code_review_dep.VALUE\n')
 old=types.ModuleType('code_review_dep');old.VALUE='OLD';sys.modules['code_review_dep']=old
 original_path=list(sys.path)
 with ext._scripts_on_sys_path(incoming):
  observed=ext._load_journal_hook(incoming,'code_review_hooks:prepare')(root)
 assert observed=='OLD:OLD',observed
 assert sys.path==original_path
 result.append({'probe':'actual_cached_sibling_baseline','expected_under_AC4':'INCOMING:INCOMING','observed':observed,'known_bad_detected':observed!='INCOMING:INCOMING'})
 # Feasibility only: explicit scratch module-key isolation, not a proposed implementation.
 del sys.modules['code_review_dep']
 try:
  with ext._scripts_on_sys_path(incoming):
   observed=ext._load_journal_hook(incoming,'code_review_hooks:prepare')(root)
 finally:
  sys.modules.pop('code_review_dep',None);sys.modules['code_review_dep']=old
 assert observed=='INCOMING:INCOMING';assert sys.modules['code_review_dep'] is old;assert sys.path==original_path
 result.append({'probe':'explicit_scratch_eviction_feasibility_control','expected':'INCOMING:INCOMING','observed':observed,'old_identity_restored':sys.modules['code_review_dep'] is old,'path_restored':sys.path==original_path})
 (incoming/'code_review_hooks.py').write_text('def prepare(root):\n import code_review_dep\n raise RuntimeError(code_review_dep.VALUE)\n')
 del sys.modules['code_review_dep']
 try:
  with ext._scripts_on_sys_path(incoming):
   hook=ext._load_journal_hook(incoming,'code_review_hooks:prepare')
   with contextlib.redirect_stdout(io.StringIO()) as captured:
    allowed=ext._run_journal_pre_migration_hook(root,'code_review_hooks:prepare',hook)
 finally:
  sys.modules.pop('code_review_dep',None);sys.modules['code_review_dep']=old
 assert allowed is False;assert sys.modules['code_review_dep'] is old;assert sys.path==original_path
 result.append({'probe':'scratch_failure_restoration_control','dependent_migration_allowed':allowed,'old_identity_restored':sys.modules['code_review_dep'] is old,'path_restored':sys.path==original_path,'diagnostic':captured.getvalue().strip()})
 # Faithful current pre_docs_gate boundary with unrelated mechanisms patched.
 (incoming/'mcp_tool_extensions.py').write_text('from pathlib import Path\nPath('+repr(str(root/'decl-marker'))+').write_text("executed")\nEXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="journals_present"\nEXTENSION_JOURNAL_PRE_MIGRATION_HOOK="code_review_hooks:prepare"\nEXTENSION_JOURNAL_TEMPLATES=()\ndef journal_declaration_problems(): return []\n')
 journal=root/'docs/agents/journals/live.md';journal.parent.mkdir(parents=True);journal.write_text('meaningful content\n')
 for version in ['1.15.0','1.29.0']:
  ctx=types.SimpleNamespace(root=root,from_version=version)
  with patch.object(ext,'repair_declaring_scaffold'), patch.object(ext,'_reconcile_graph_builder_doc_claim'), patch.object(ext,'_read_json_object',return_value={'review_sidecar_cleanup':{}}):
   ext.pre_docs_gate(ctx)
  assert not (root/'decl-marker').exists();assert journal.read_text()=='meaningful content\n'
  result.append({'probe':'current_later_gate_no_import_baseline','from_version':version,'declaration_executed':False,'journal_unchanged':True})
 sys.modules.pop('code_review_dep',None)
name='EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER'
for label,source in [('absent','X=1'),('literal',name+'="journals_present"'),('invalid_literal',name+'="typo"'),('dynamic',name+'=choose()'),('conditional','if True:\n '+name+'="journals_present"'),('duplicate_literal',name+'="typo"\n'+name+'="journals_present"')]:
 try: observed=repr(ext._static_module_literal(ast.parse(source),name))
 except ValueError: observed='ValueError'
 result.append({'probe':'actual_static_literal_reader','case':label,'observed':observed})
# Existing positional API is directly executable and valid.
spec=importlib.util.spec_from_file_location('readiness_code_decl', scripts/'mcp_tool_extensions.py')
decl=importlib.util.module_from_spec(spec);spec.loader.exec_module(decl)
observed=decl.journal_declaration_problems((), 'code_review_hooks:prepare', ('code_review_hooks',))
assert observed==[]
result.append({'probe':'pure_validator_three_positional_api','observed':observed,'third_parameter':list(__import__('inspect').signature(decl.journal_declaration_problems).parameters)[2]})
Path('/tmp/wf-206is-code-probe-results.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
