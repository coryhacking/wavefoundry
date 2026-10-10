import pathlib,sys,subprocess,unittest,io,json
from unittest import mock
S=pathlib.Path('/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts');sys.path[:0]=[str(S),str(S/'tests')]
import test_review_policy as p,test_storage_upgrade_resume as u,test_sqlite_storage_migration as m
original=subprocess.run;seen=[]
def without_git(*a,**kw):
 argv=a[0] if a else kw.get('args')
 if isinstance(argv,(list,tuple)) and pathlib.Path(str(argv[0])).name=='git':
  seen.append(list(argv));return subprocess.CompletedProcess(argv,1,stdout=b'',stderr=b'git refs deliberately unavailable')
 return original(*a,**kw)
stream=io.StringIO()
with mock.patch.object(subprocess,'run',without_git):
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite([p.ReviewPolicyReconcilerTests('test_real_v114_carrier_family_reconciles_and_retries_byte_stably'),p.ReviewPolicyReconcilerTests('test_real_v114_carriers_render_policy_and_pass_production_validator'),u.StorageUpgradeProcessResumeTests('test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry'),m.SchemaEightKindTests('test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing')]))
r={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'git_calls_denied':seen,'log':stream.getvalue()};pathlib.Path('/private/tmp/wf-2071n-history-nogit-probe.json').write_text(json.dumps(r,indent=2));print(r)
