#!/usr/bin/env python3
import ast, hashlib, json, os, pathlib, shutil, subprocess, sys, time
ROOT=pathlib.Path('/Users/coryhacking/Developer/wavefoundry')
BASE=pathlib.Path('/tmp/wf-206is-guard-pins-work')
S=ROOT/'.wavefoundry/framework/scripts'
OWNERS=['upgrade_extensions.py','mcp_tool_extensions.py','upgrade_wavefoundry.py','tests/test_upgrade_wavefoundry.py','tests/test_upgrade_protocol.py','tests/record_layout_support.py']
def hashes(): return {str(S/x): hashlib.sha256((S/x).read_bytes()).hexdigest() for x in OWNERS}
def chunk(s, func):
 n=next(n for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==func)
 lines=s.splitlines(keepends=True);return ''.join(lines[n.lineno-1:n.end_lineno])
def alter(s,func,old,new):
 c=chunk(s,func); assert c.count(old)==1,(func,old,c.count(old));return s.replace(c,c.replace(old,new),1)
P='test_upgrade_wavefoundry.JournalTriggerPolicyTests.'
I='test_upgrade_protocol.JournalIncomingRunnerTests.'
static=P+'test_static_preview_decision_table_and_apply_invalid_refusal_before_execution'
incoming=I+'test_cached_old_modules_and_descendants_restore_after_success_and_idempotent_retry'
mutants=[
 ('invalid_preexecution','upgrade_extensions.py','pre_docs_gate','if selection["status"] == "invalid":','if False:',static,'Invalid apply refuses before executing declaration'),
 ('duplicate_binding','upgrade_extensions.py','_static_journal_trigger','len(direct) != 1','len(direct) < 1',static,'Duplicate direct trigger bindings invalid'),
 ('literal_policy_allowlist','upgrade_extensions.py','_static_journal_trigger',' or value not in _JOURNAL_TRIGGER_POLICIES','',static,'Unsupported literal trigger invalid'),
 ('literal_type','upgrade_extensions.py','_static_journal_trigger','not isinstance(value, str) or value not in _JOURNAL_TRIGGER_POLICIES','False',static,'Non-string trigger invalid'),
 ('builtin_permission','upgrade_extensions.py','pre_docs_gate','if legacy and hook_ok:','if hook_ok:',P+'test_opt_in_versions_and_multiple_sources_call_once_without_permission_expansion','Builtin remains independently gated before 1.15'),
 ('default_dormancy','upgrade_extensions.py','pre_docs_gate','if legacy or (trigger == "journals_present" and eligible):','if legacy or eligible:',P+'test_legacy_absent_and_explicit_defaults_keep_no_source_cutover','Default later hook remains dormant'),
 ('readme_exclusion','upgrade_extensions.py','_journals_present',' or entry.name == "README.md"','',P+'test_nonqualifying_direct_sources_never_call_opted_in_hook','README-only is ineligible'),
 ('single_link','upgrade_extensions.py','_journals_present','_journal_source_ok(original)','(original is not None and stat.S_ISREG(original.st_mode))',P+'test_nonqualifying_direct_sources_never_call_opted_in_hook','Hardlinked source is ineligible'),
 ('ancestor_refusal_partial','upgrade_extensions.py','_journals_present',None,None,P+'test_linked_source_ancestor_is_not_followed','Ancestor no-follow plus descriptor walk refuse linked path'),
 ('cached_name_eviction','upgrade_extensions.py','_journal_incoming_imports','for name in previous_modules:\n        sys.modules.pop(name, None)','for name in ():\n        sys.modules.pop(name, None)',incoming,'Incoming dependency shadows cached old module'),
 ('descendant_shadowing','upgrade_extensions.py','_journal_incoming_imports','return name.partition(".")[0] in names','return name in names',incoming,'Incoming package child shadows cached old descendant'),
 ('path_precedence','upgrade_extensions.py','_journal_incoming_imports','sys.path[:] = [path] + [entry for entry in previous_path if entry != path]','sys.path[:] = previous_path if path in previous_path else [path] + previous_path',incoming,'Incoming directory precedes old disk dependencies even when already present'),
 ('module_identity_restoration','upgrade_extensions.py','_journal_incoming_imports','sys.modules.update(previous_modules)','pass # mutant: old identities not restored',incoming,'Old cached module identities restore after success'),
 ('path_restoration_failure','upgrade_extensions.py','_journal_incoming_imports','sys.path[:] = previous_path','pass # mutant: path not restored',I+'test_call_failure_restores_modules_path_and_reports_partial_effect_truthfully','Path restores after failed hook'),
 ('new_descendant_cleanup','upgrade_extensions.py','_journal_incoming_imports','if affected(name):','if affected(name) and name != "c6_package.new_child":',incoming,'New affected descendant is removed'),
 ('preview_noexecution','upgrade_extensions.py','_journal_hook_preview','selection = _static_journal_trigger(root, zip_path)','_load_journal_declaration(root)\n    selection = _static_journal_trigger(root, zip_path)',static,'Public preview executes no declaration'),
 ('ancestor_refusal_complete','upgrade_extensions.py','_journals_present',None,None,P+'test_linked_source_ancestor_is_not_followed','Full ancestor no-follow clause refusal'),
 ('conditional_binding','upgrade_extensions.py','_static_module_literal','if id(node) not in owned:','if False:',static,'Conditional/augmented trigger binding invalid'),
 ('unknown_not_default','upgrade_extensions.py','_static_journal_trigger','return {"policy": None, "status": "unknown", "detail":','return {"policy": "legacy_cutover", "status": "valid", "detail":',static,'Unknown source cannot silently default'),
 ('regular_source_only','upgrade_extensions.py','_journals_present','_journal_source_ok(original)','(original is not None and original.st_nlink == 1)',P+'test_fifo_named_markdown_is_not_opened_or_selected','FIFO cannot qualify as regular journal'),
 ('module_restore_import_failure','upgrade_extensions.py','_journal_incoming_imports','sys.modules.update(previous_modules)','pass # mutant: old identities not restored',I+'test_import_failure_restores_modules_path_and_uses_actual_runner_refusal','Cached module identity restored after failed import'),
 ('pure_validator_allowlist','mcp_tool_extensions.py','journal_declaration_problems','if not isinstance(trigger, str) or trigger not in ("legacy_cutover", "journals_present"):','if False:',P+'test_registry_base_profiles_positional_validator_and_activation_are_compatible','Pure validator rejects invalid trigger'),
]
DRIVER='''import json,sys,unittest\nfrom pathlib import Path\ns=Path(sys.argv[1]);sys.path[:0]=[str(s),str(s/'tests')]\ndef trace(frame,event,arg):\n if event=='exception' and isinstance(arg[1],(AssertionError,AttributeError)):\n  message=str(arg[1]);\n  if any(x in message for x in ('old dependency','old child','old descendant','selected','loaded declaration','executed declaration','preview loaded','c6_package')): print('PROPERTY_EXCEPTION '+message+' MODULE_FILES '+json.dumps({name:getattr(sys.modules.get(name),'__file__',None) for name in ('c6_dependency','c6_package','c6_package.child','c6_package.new_child')}),file=sys.__stderr__)\n return trace\nsys.settrace(trace)\nsuite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:]);result=unittest.TextTestRunner(verbosity=2).run(suite)\nprint('RESULT_JSON '+json.dumps({'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped)}))\nsys.exit(not result.wasSuccessful())\n'''
def run(s,test,label):
 t=time.monotonic();r=subprocess.run([sys.executable,'-B','-c',DRIVER,str(s),test],cwd=BASE,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=60)
 log=BASE/(label+'.log');log.write_text(r.stdout+r.stderr); summary=json.loads(next(x.split(' ',1)[1] for x in r.stdout.splitlines() if x.startswith('RESULT_JSON ')))
 return {'command':[sys.executable,'-B','-c','DRIVER (in replay script)',str(s),test],'exit':r.returncode,'elapsed':time.monotonic()-t,'log':str(log),**summary,'tail':(r.stdout+r.stderr)[-4500:]}
def main():
 before=hashes();BASE.mkdir(exist_ok=True);tree=BASE/'scratch/.wavefoundry/framework';tree.mkdir(parents=True,exist_ok=True)
 if (tree/'scripts').exists():shutil.rmtree(tree/'scripts')
 shutil.copytree(S,tree/'scripts',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 shutil.copytree(S.parent/'seeds',tree/'seeds',dirs_exist_ok=True)
 scripts=tree/'scripts';records=[]
 for id,file,func,old,new,test,property in mutants:
  target=scripts/file;original=target.read_text();baseline=run(scripts,test,id+'-baseline')
  if id == 'ancestor_refusal_complete':
   c=chunk(original,func); changed=original.replace(c,c.replace('refuse_symlink_components=True','refuse_symlink_components=False').replace('if _journal_dir_fd_supported():','if False:'),1)
  elif old is None:
   changed=alter(original,func,'folder = containment.contained_path(root, _JOURNALS_REL, refuse_symlink_components=True)','folder = root / _JOURNALS_REL')
   changed=alter(changed,func,'if _journal_dir_fd_supported():','if False:')
  else:changed=alter(original,func,old,new)
  target.write_text(changed)
  try: mutant=run(scripts,test,id+'-mutant')
  finally:target.write_text(original)
  classification='detected' if baseline['exit']==0 and mutant['exit']!=0 and not baseline['skips'] and not mutant['skips'] else 'survived' if baseline['exit']==mutant['exit']==0 else 'invalid_evidence'
  records.append({'id':id,'source':str(S/file),'symbol':func,'old':old,'new':new,'property':property,'test':test,'baseline':baseline,'mutant':mutant,'classification':classification})
  print(id,classification, 'baseline',baseline['exit'],'mutant',mutant['exit'],flush=True)
 after=hashes();report={'purpose':'Builder guard-pin verification only, not delivery approval','source_hashes_before':before,'source_hashes_after':after,'unchanged':before==after,'scratch_scripts':str(scripts),'records':records,'limitations':['Finite chosen mutants, no full suite','Partial ancestor mutant survives redundant per-candidate containment; complete mutant removes all presence no-follow clauses plus descriptor walk','No source edits; real older-runner zip loader/extraction uses copied scripts and pack']}
 pathlib.Path('/tmp/wf-206is-guard-pins.json').write_text(json.dumps(report,indent=2));print('REPORT /tmp/wf-206is-guard-pins.json',flush=True)
if __name__=='__main__':main()
