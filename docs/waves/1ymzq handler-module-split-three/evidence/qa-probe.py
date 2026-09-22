from pathlib import Path
import sys, tempfile,shutil,subprocess,os,json,unittest,io,importlib
from unittest.mock import patch
S=Path('/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts');sys.path[:0]=[str(S/'tests'),str(S)]
import test_handler_modules as h
out=[]
for owner,response,tool in [('index_handlers','index_build_response','index_build'),('upgrade_handlers','wf_upgrade_response','wf_upgrade'),('edit_gate_handlers','wave_open_gate_response','wf_open_gate'),('dashboard_handlers','wf_start_dashboard_response','wf_start_dashboard'),('docs_handlers','wf_validate_docs_response','wf_validate_docs'),('context_efficiency_handlers','wf_context_efficiency_eval_response','wf_context_efficiency_eval')]:
 with tempfile.TemporaryDirectory() as t:
  scratch=Path(t)/'scripts';shutil.copytree(S,scratch,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));p=scratch/'server_impl.py';old=p.read_text();needle='            "'+owner+'",\n';assert old.count(needle)==1;p.write_text(old.replace(needle,''))
  r=subprocess.run([sys.executable,'-B','-c',h._RELOAD,owner,response,tool],cwd=scratch,env=dict(os.environ,PYTHONPATH=str(scratch),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=90)
  out.append({'mechanism':owner+' reload','mutation':'omit purge membership','caught':r.returncode!=0,'failure':r.stderr[-400:]});print(out[-1],flush=True)
def run(name,ctx):
 with ctx:
  result=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromName(name))
 out.append({'mechanism':name,'caught':not result.wasSuccessful(),'tests':result.testsRun,'skips':len(result.skipped),'failure':str((result.failures+result.errors)[0][1])[-500:] if not result.wasSuccessful() else ''});print(out[-1],flush=True)
import retrieval_eval
run('test_index_handler_identity.IndexHandlerIdentityTests',patch.object(retrieval_eval,'PRODUCTION_RETRIEVAL_MODULES',tuple(x for x in retrieval_eval.PRODUCTION_RETRIEVAL_MODULES if x!='index_handlers.py')))
import test_path_containment as pc
orig=pc.subject.contained_resolved_path
run('test_path_containment.ResolvedComparisonTests',patch.object(pc.subject,'contained_resolved_path',side_effect=lambda root,path:orig(root.resolve(),path.resolve())))
import build_pack
origcollect=build_pack.collect_files
run('test_handler_modules.HandlerPackagingAndEvaluatorTests.test_generated_manifest_contains_all_handler_modules',patch.object(build_pack,'collect_files',side_effect=lambda *a,**k:[row for row in origcollect(*a,**k) if not str(row[0]).endswith('index_handlers.py')]))
# Old-install branch mutation uses scratch source and exact production helper tests.
with tempfile.TemporaryDirectory() as t:
 scratch=Path(t)/'scripts';shutil.copytree(S,scratch,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));p=scratch/'upgrade_extensions.py';old=p.read_text();assert 'except ImportError:' in old;p.write_text(old.replace('except ImportError:','except ValueError:',1))
 r=subprocess.run([sys.executable,'-B','-m','unittest','test_upgrade_wavefoundry.RuntimeLockCutoverMigrationTests.test_cutover_module_absence_uses_installed_modern_stop','test_upgrade_wavefoundry.RuntimeLockCutoverMigrationTests.test_cutover_falls_back_to_pre_rename_dashboard_stop_symbol'],cwd=scratch/'tests',env=dict(os.environ,PYTHONPATH=str(scratch),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=90)
 out.append({'mechanism':'upgrade fallback','caught':r.returncode!=0,'failure':r.stderr[-1300:]});print(out[-1],flush=True)
Path('/private/tmp/1ymzq-qa-mutations.json').write_text(json.dumps(out,indent=2))
