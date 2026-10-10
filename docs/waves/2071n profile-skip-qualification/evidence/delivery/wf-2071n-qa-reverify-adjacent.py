import sys,json,pathlib,subprocess,os
p=json.loads(pathlib.Path('/private/tmp/wf-2071n-qa-reverify-probe-results.json').read_text());scripts=pathlib.Path(p['scratch'])/'.wavefoundry/framework/scripts'
sys.path[:0]=['/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts/tests','/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts']
import record_layout_support as rls
rls.apply_profile(scripts,rls.shipped_default_profile())
program=r'''
import sys,unittest,io,json
sys.path[:0]=[sys.argv[1]+'/tests',sys.argv[1]]
names=[
 'test_graph_quality_eval.LiveGraphEvidenceControlTests',
 'test_server_tools_retrieval.EvidencePartitionResponseTests',
 'test_server_tools_retrieval.EvidenceNodesStayQueryableTests',
 'test_historical_fixture_support.HistoricalFixtureIntegrityTests',
 'test_review_policy.ReviewPolicyReconcilerTests.test_real_v114_carrier_family_reconciles_and_retries_byte_stably',
 'test_review_policy.ReviewPolicyReconcilerTests.test_real_v114_carriers_render_policy_and_pass_production_validator',
 'test_storage_upgrade_resume.StorageUpgradeProcessResumeTests.test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry',
 'test_sqlite_storage_migration.SchemaEightKindTests.test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing']
out=io.StringIO();result=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=[(str(t),why) for t,why in result.skipped],log=out.getvalue(),names=names)))
'''
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPYCACHEPREFIX','PYTHONPATH','WAVEFOUNDRY_TEST_PROFILE')};env['PYTHONDONTWRITEBYTECODE']='1'
r=subprocess.run([sys.executable,'-B','-c',program,str(scripts)],env=env,text=True,capture_output=True,timeout=150)
pathlib.Path('/private/tmp/wf-2071n-qa-reverify-adjacent-stderr.log').write_text(r.stderr)
assert r.returncode==0,(r.stdout,r.stderr[-3000:])
a=json.loads(r.stdout.strip().splitlines()[-1]);pathlib.Path('/private/tmp/wf-2071n-qa-reverify-adjacent-results.json').write_text(json.dumps(a,indent=2));print(json.dumps({k:v for k,v in a.items() if k!='log'}));assert a['failures']==a['errors']==0 and not a['skips']
