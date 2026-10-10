import ast,contextlib,hashlib,io,json,sys,tempfile,types
from pathlib import Path
from unittest.mock import patch
R=Path('/Users/coryhacking/Developer/wavefoundry'); S=R/'.wavefoundry/framework/scripts'
sys.path[:0]=[str(S),str(S/'tests')]
import upgrade_extensions as e
import test_upgrade_wavefoundry as t
packet=json.loads(Path('/tmp/wf-206is-readiness-focused-packet.json').read_text())
sha={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in packet['files_in_scope']}
assert sha==packet['scope_sha256']
result={'scope_before_sha256':sha,'probes':[]}
with tempfile.TemporaryDirectory(prefix='wf-security-collision-') as d:
 root=Path(d); scripts=root/'.wavefoundry/framework/scripts';scripts.mkdir(parents=True)
 (scripts/'c6_security_dep.py').write_text("VALUE='INCOMING'\n")
 (scripts/'c6_security_hook.py').write_text("import c6_security_dep\nIMPORT_VALUE=c6_security_dep.VALUE\ndef prepare(root):\n import c6_security_dep\n (root/'seen.json').write_text(__import__('json').dumps([IMPORT_VALUE,c6_security_dep.VALUE]))\n")
 old=types.ModuleType('c6_security_dep');old.VALUE='OLD'
 before=list(sys.path)
 with patch.dict(sys.modules,{'c6_security_dep':old}):
  with e._scripts_on_sys_path(scripts):
   hook=e._load_journal_hook(scripts,'c6_security_hook:prepare');hook(root)
  collision=json.loads((root/'seen.json').read_text());assert collision==['OLD','OLD']
  known_bad_rejected=collision!=['INCOMING','INCOMING']
  assert sys.modules['c6_security_dep'] is old
 assert sys.path==before
 sys.modules.pop('c6_security_dep',None)
 with e._scripts_on_sys_path(scripts):
  hook=e._load_journal_hook(scripts,'c6_security_hook:prepare');hook(root)
 control=json.loads((root/'seen.json').read_text());assert control==['INCOMING','INCOMING']
 sys.modules.pop('c6_security_dep',None)
 result['probes'].append({'name':'incoming_dependency_collision_import_and_call','expected_ac4':['INCOMING','INCOMING'],'known_bad_observed':collision,'negative_control_observed':control,'known_bad_rejected':known_bad_rejected,'path_restored':sys.path==before,'old_module_restored_by_fixture':True,'product_module_restoration_proven':False})
 (scripts/'c6_security_hook.py').write_text("def prepare(root):\n raise ValueError('/do/not/expose/secret')\n")
 out=io.StringIO()
 with contextlib.redirect_stdout(out),e._scripts_on_sys_path(scripts):
  ok=e._run_journal_pre_migration_hook(root,'c6_security_hook:prepare',e._load_journal_hook(scripts,'c6_security_hook:prepare'))
 assert ok is False and '/do/not/expose/secret' not in out.getvalue() and sys.path==before
 result['probes'].append({'name':'failure_exception_diagnostic_and_path_restoration','expected':'False, exception-class only, restored path','observed':{'return':ok,'path_restored':sys.path==before,'exception_text_hidden':'/do/not/expose/secret' not in out.getvalue()},'limit':'Actual hook seam; dependent migration stop separately exercised by registered existing gate fixture.'})
name='EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER'
cases={'absent':'x=1','valid':f'{name}="journals_present"','invalid_literal':f'{name}="typo"','nonliteral':f'{name}=str("journals_present")','conditional':f'if True:\n {name}="journals_present"'}
observed={}
for label,source in cases.items():
 try:observed[label]=repr(e._static_module_literal(ast.parse(source),name))
 except ValueError:observed[label]='ValueError'
assert observed=={'absent':'()','valid':"'journals_present'",'invalid_literal':"'typo'",'nonliteral':'ValueError','conditional':'ValueError'}
result['probes'].append({'name':'static_trigger_selection_feasibility','observed':observed,'limit':'AST literal precedent only; new policy validator and scheduling do not exist.'})
# Known-bad consumer of preview template discovery: force declaration execution.
# Existing oracle explicitly rejects any declaration execution on the public preview.
case=t.JournalStaticPreviewTests('test_preview_applies_a_literal_template_without_executing_the_module')
case.setUp()
try:
 def bad_preview(root,zip_path=None):
  case.ext._exec_module_from_file('_security_bad_preview',case.ext._journal_scripts_dir(root)/'mcp_tool_extensions.py')
  return (),True
 with patch.object(case.ext,'_static_journal_templates',bad_preview):
  try:case.test_preview_applies_a_literal_template_without_executing_the_module()
  except AssertionError as ex:
   caught='preview executed a module' in str(ex)
  else:caught=False
 assert caught
 result['probes'].append({'name':'public_preview_known_bad_execution_oracle','expected':'known-bad declaration import rejected','observed':caught,'limit':'Injected old/bad behavior in scratch fixture; baseline test run separately passed.'})
finally:case.doCleanups()
result['scope_after_sha256']={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in packet['files_in_scope']}
result['scope_freeze_unchanged']=result['scope_after_sha256']==sha
assert result['scope_freeze_unchanged']
Path('/tmp/wf-206is-focused-security-probe-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
