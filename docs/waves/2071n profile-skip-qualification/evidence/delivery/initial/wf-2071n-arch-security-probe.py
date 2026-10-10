import os, sys, json, hashlib, base64, subprocess, tempfile, io, unittest
from pathlib import Path
from unittest.mock import patch
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ.pop('PYTHONPYCACHEPREFIX',None)
repo=Path('/Users/coryhacking/Developer/wavefoundry')
scripts=repo/'.wavefoundry/framework/scripts'
sys.path[:0]=[str(scripts/'tests'),str(scripts)]
packet=json.loads(Path('/private/tmp/wf-2071n-delivery-packet.json').read_bytes())
def fingerprints():
 return {p['path']:hashlib.sha256((repo/p['path']).read_bytes()).hexdigest() for p in packet['paths']}
expected={p['path']:p['sha256'] for p in packet['paths']}
out={'before_match':fingerprints()==expected,'mutations':[], 'trace':[]}
import historical_fixture_support as hist
bundle=json.loads(hist.BUNDLE_PATH.read_bytes())
pins=[]
for key,e in bundle['entries'].items():
 path=base64.b64decode(e['source_path_b64']).decode()
 child=subprocess.run(['git','show',e['revision']+':'+path],cwd=repo,capture_output=True)
 if e['absent']:
  assert child.returncode!=0
  pins.append({'key':key,'verified_absence':True})
 else:
  source=hist.historical_bytes(key)
  assert child.returncode==0 and source==child.stdout
  pins.append({'key':key,'size':len(source),'git_match':True})
out['provenance']=pins
import test_graph_quality_eval as quality
import test_server_tools_retrieval as retrieval
import test_historical_fixture_support as integrity
import test_review_policy as policy
import test_storage_upgrade_resume as resume
import test_sqlite_storage_migration as storage
import graph_indexer, graph_fixture_support as gfs, graph_snapshot, graph_query
def run(tests):
 stream=io.StringIO()
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(tests))
 return {'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'output':stream.getvalue()}
def case(cls,name): return cls(name)
graph_tests=[]
for cls in [quality.LiveGraphEvidenceControlTests,retrieval.EvidencePartitionResponseTests,retrieval.EvidenceNodesStayQueryableTests]:
 graph_tests.extend(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
out['graph_baseline']=run(graph_tests)
realrun=subprocess.run
realwrite=Path.write_bytes
def guarded_run(argv,*a,**kw):
 assert isinstance(argv,(list,tuple)) and not kw.get('shell',False),argv
 if argv[0]=='git' and any(x in argv for x in ['show','rev-parse','cat-file']):
  raise AssertionError('Historical runtime must not consult Git refs')
 cwd=kw.get('cwd')
 if cwd is not None: assert Path(cwd).resolve()!=repo
 out['trace'].append({'argv_head':[str(x)[:100] for x in argv[:3]],'cwd':str(cwd),'shell':False})
 return realrun(argv,*a,**kw)
def guarded_write(path,body):
 if body in [hist.historical_bytes(k) for k,e in bundle['entries'].items() if not e['absent']]:
  assert not path.resolve().is_relative_to(repo)
  out.setdefault('historical_destinations',[]).append(str(path))
 return realwrite(path,body)
historic=[case(policy.ReviewPolicyReconcilerTests,'test_real_v114_carrier_family_reconciles_and_retries_byte_stably'),case(policy.ReviewPolicyReconcilerTests,'test_real_v114_carriers_render_policy_and_pass_production_validator'),case(resume.StorageUpgradeProcessResumeTests,'test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry'),case(storage.SchemaEightKindTests,'test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing')]
with patch.object(subprocess,'run',guarded_run),patch.object(Path,'write_bytes',guarded_write):
 out['historical_behavior']=run(historic)
out['historical_integrity']=run(unittest.defaultTestLoader.loadTestsFromTestCase(integrity.HistoricalFixtureIntegrityTests))
with patch.object(graph_indexer,'classify_evidence_payload',return_value=(False,[])):
 out['mutations'].append({'name':'real extractor erases evidence','result':run([case(quality.LiveGraphEvidenceControlTests,'test_the_machine_result_control_is_classified_as_evidence'),case(retrieval.EvidencePartitionResponseTests,'test_evidence_communities_remain_queryable_by_id')])})
with patch.object(gfs,'publish_evidence_fixture',return_value={'nodes':[],'edges':[]}):
 out['mutations'].append({'name':'empty published fixture','result':run([case(quality.LiveGraphEvidenceControlTests,'test_the_control_directory_is_indexed_at_all'),case(retrieval.EvidencePartitionResponseTests,'test_every_pair_is_present_including_its_evidence_half')])})
with patch.object(hist,'BUNDLE_SHA256','0'*64):
 out['mutations'].append({'name':'bundle pin incorrect','result':run([case(integrity.HistoricalFixtureIntegrityTests,'test_old_python_bytes_match_the_independently_recorded_source_digests')])})
with patch.object(hist,'historical_bytes',return_value=(scripts/'sqlite_storage_migration.py').read_bytes()):
 out['mutations'].append({'name':'current source substituted under old-reader key','result':run([case(integrity.HistoricalFixtureIntegrityTests,'test_old_python_bytes_match_the_independently_recorded_source_digests')])})
with tempfile.TemporaryDirectory(prefix='wf-2071n-boundary-') as tmp:
 root=Path(tmp)
 assert not (root/'.wavefoundry/index').exists()
 payload=gfs.publish_evidence_fixture(root)
 snap=graph_snapshot.acquire(root,'project')
 ids={n['id'] for n in payload['nodes']}
 control=quality.subject.CONTROL_DIRECTORY+'/machine-result-control.json'
 assert control in ids and 'docs/evals/ignored-control.json' not in ids
 crossing=[e for e in payload['edges'] if e['source']=='docs/design/controls.md' and e['target']==control]
 assert len(crossing)==1 and crossing[0]['relation']=='doc_references_doc'
 first=snap.generation
 # Consumers call this source helper exactly once per new scratch root.
 # Repeat the existing canonical publication helper, rather than re-extraction
 # under the new helper's deliberately synthetic chunker version.
 gfs.publish_graph(root,graph=payload,clusters=snap.clusters)
 second=graph_snapshot.acquire(root,'project')
 assert second.generation>first
 assert len(second.graph['nodes'])==len(payload['nodes'])
 out['publication']={'root':str(root),'nodes':len(payload['nodes']),'edges':len(payload['edges']),'crossing':crossing,'first_generation':first,'second_generation':second.generation,'temporary_root':True,'present':second.present}
out['after_match']=fingerprints()==expected
Path('/private/tmp/wf-2071n-arch-security-probe.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k not in ['trace','historical_destinations','mutations','provenance','graph_baseline','historical_behavior','historical_integrity']},indent=2))
print({k:{a:v for a,v in out[k].items() if a!='output'} for k in ['graph_baseline','historical_behavior','historical_integrity']})
print([{ 'name':m['name'],**{k:v for k,v in m['result'].items() if k!='output'}} for m in out['mutations']])
