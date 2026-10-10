import sys,json,unittest,tempfile,shutil,subprocess,base64,hashlib,os
from pathlib import Path
repo=Path('/Users/coryhacking/Developer/wavefoundry');out={}
bundle=json.loads((repo/'.wavefoundry/framework/scripts/tests/fixtures/historical_sources.json').read_bytes());matches=[];absences=[]
for key,e in bundle['entries'].items():
 path=base64.b64decode(e['source_path_b64']).decode();p=subprocess.run(['git','show',e['revision']+':'+path],cwd=repo,capture_output=True)
 if e['absent']:
  assert p.returncode!=0,(key,'unexpected present');absences.append(key)
 else:
  captured=base64.b64decode(''.join(e['content_b64']));assert p.returncode==0 and p.stdout==captured,(key,'mismatch');matches.append(key)
out['git_provenance']={'present_matches':matches,'recorded_absences':absences}
with tempfile.TemporaryDirectory(prefix='wf-2071n-qa-no-ref-',dir='/private/tmp')as temp:
 root=Path(temp)/'repo';framework=root/'.wavefoundry/framework';shutil.copytree(repo/'.wavefoundry/framework',framework,ignore=shutil.ignore_patterns('__pycache__','test-cache.json','test-run.lock','index','.pytest_cache'))
 scripts=framework/'scripts';sys.path[:0]=[str(scripts/'tests'),str(scripts)];os.chdir(root)
 p=subprocess.run(['git','rev-parse','--git-dir'],capture_output=True);out['no_git_repository']=p.returncode!=0
 names=['test_review_policy.ReviewPolicyReconcilerTests.test_real_v114_carrier_family_reconciles_and_retries_byte_stably','test_review_policy.ReviewPolicyReconcilerTests.test_real_v114_carriers_render_policy_and_pass_production_validator','test_storage_upgrade_resume.StorageUpgradeProcessResumeTests.test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry','test_sqlite_storage_migration.SchemaEightKindTests.test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing','test_historical_fixture_support.HistoricalFixtureIntegrityTests']
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n)for n in names);r=unittest.TestResult();suite.run(r);out['no_ref_tests']={'tests':r.testsRun,'skips':[(t.id(),m)for t,m in r.skipped],'failures':[(t.id(),m)for t,m in r.failures],'errors':[(t.id(),m)for t,m in r.errors]}
 print('no_ref',r.testsRun,len(r.skipped),len(r.failures),len(r.errors),flush=True)
packet=json.loads(Path('/private/tmp/wf-2071n-delivery-packet.json').read_text());out['frozen_paths_match']=all(hashlib.sha256((repo/p['path']).read_bytes()).hexdigest()==p['sha256']for p in packet['paths'])
Path('/private/tmp/wf-2071n-qa-history-probe.json').write_text(json.dumps(out,indent=2));print('provenance',len(matches),len(absences),'frozen',out['frozen_paths_match'])
