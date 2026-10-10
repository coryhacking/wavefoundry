import sys,os,json,pathlib,unittest,io,contextlib,subprocess,base64,hashlib
from unittest import mock
ROOT=pathlib.Path('/Users/coryhacking/Developer/wavefoundry'); S=ROOT/'.wavefoundry/framework/scripts'
sys.path[:0]=[str(S),str(S/'tests')]
os.environ.pop('PYTHONPYCACHEPREFIX',None);os.environ['WAVEFOUNDRY_DISABLE_BYTECODE_CACHE']='1'
import test_graph_quality_eval as q,test_server_tools_retrieval as r,test_review_policy as p,test_storage_upgrade_resume as u,test_sqlite_storage_migration as m,test_historical_fixture_support as h
import graph_query,historical_fixture_support as hs
out={}
def run(name,tests,patch=None):
 stream=io.StringIO()
 with patch or contextlib.nullcontext():
  result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(tests))
 out[name]={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'log':stream.getvalue()}
 print(name, {k:v for k,v in out[name].items() if k!='log'},flush=True)
def cases(cls):return list(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
run('graph_baseline',cases(q.LiveGraphEvidenceControlTests)+[q.ClassificationControlScorerTests('test_the_live_graph_satisfies_the_frozen_expectation')]+cases(r.EvidencePartitionResponseTests)+cases(r.EvidenceNodesStayQueryableTests))
# Reviewer-owned mutation: retain lookup success, nodes, ranking and result shape but corrupt exact queried community count.
old=r.load_server
def bad_server():
 srv=old(); original=srv.code_graph_community_response
 def bad(*a,**kw):
  response=original(*a,**kw)
  if response.get('status')=='ok': response['data']['total_node_count']=61
  return response
 srv.code_graph_community_response=bad
 return srv
run('lookup_count_mutant',[r.EvidencePartitionResponseTests('test_evidence_communities_remain_queryable_by_id')],mock.patch.object(r,'load_server',side_effect=bad_server))
# Delete only crossing edges after reading actual published graph, keeping real graph/node classes.
original_init=graph_query.GraphQueryIndex.__init__
def without_crossing(self,*a,**kw):
 original_init(self,*a,**kw); ids={n['id'] for n in self.nodes if n.get('evidence_data')}; own=lambda x:str(x).split('::',1)[0]
 self.edges=[e for e in self.edges if (own(e.get('source')) in ids)==(own(e.get('target')) in ids)]
run('crossing_edge_mutant',[r.EvidenceNodesStayQueryableTests('test_cross_boundary_edges_survive_the_partition')],mock.patch.object(graph_query.GraphQueryIndex,'__init__',without_crossing))
run('historical_behavior_baseline',[p.ReviewPolicyReconcilerTests('test_real_v114_carrier_family_reconciles_and_retries_byte_stably'),p.ReviewPolicyReconcilerTests('test_real_v114_carriers_render_policy_and_pass_production_validator'),u.StorageUpgradeProcessResumeTests('test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry'),m.SchemaEightKindTests('test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing')])
run('historical_integrity_baseline',cases(h.HistoricalFixtureIntegrityTests))
# Remove source-integrity branch in memory only; named corrupted-byte assertion must now fail.
code=pathlib.Path(hs.__file__).read_text().replace('if len(source) != entry["size"] or hashlib.sha256(source).hexdigest() != entry["sha256"]:', 'if False:')
namespace=dict(hs.__dict__);exec(compile(code,hs.__file__,'exec'),namespace)
run('source_integrity_guard_mutant',[h.HistoricalFixtureIntegrityTests('test_source_digest_is_checked_even_if_bundle_digest_is_recomputed')],mock.patch.object(hs,'historical_bytes',namespace['historical_bytes']))
provenance=[]
bundle=json.loads(hs.BUNDLE_PATH.read_bytes())
for key,entry in bundle['entries'].items():
 path=base64.b64decode(entry['source_path_b64']).decode(); ref=entry['revision']+':'+path
 cp=subprocess.run(['git','show',ref],cwd=ROOT,capture_output=True)
 if entry['absent']: assert cp.returncode!=0; result='recorded absence verified'
 else:
  raw=base64.b64decode(''.join(entry['content_b64']));assert cp.returncode==0 and raw==cp.stdout;assert len(raw)==entry['size'];assert hashlib.sha256(raw).hexdigest()==entry['sha256']; result='git raw bytes exact'
 provenance.append({'key':key,'ref':ref,'result':result})
out['provenance']=provenance
pathlib.Path('/private/tmp/wf-2071n-code-probe.json').write_text(json.dumps(out,indent=2))
