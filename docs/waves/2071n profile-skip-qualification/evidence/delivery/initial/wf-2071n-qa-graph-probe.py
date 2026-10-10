import sys,unittest,json,io,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
root=Path('/Users/coryhacking/Developer/wavefoundry');sys.path[:0]=[str(root/'.wavefoundry/framework/scripts/tests'),str(root/'.wavefoundry/framework/scripts')]
import test_graph_quality_eval as q,test_server_tools_retrieval as r,graph_fixture_support as gfs
out={}
def run(label,names):
 tests=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names)
 result=unittest.TestResult();tests.run(result)
 out[label]={'tests':result.testsRun,'skips':[(t.id(),x)for t,x in result.skipped],'failures':[(t.id(),x)for t,x in result.failures],'errors':[(t.id(),x)for t,x in result.errors]}
 print(label,result.testsRun,len(result.skipped),len(result.failures),len(result.errors),flush=True)
quality='test_graph_quality_eval.LiveGraphEvidenceControlTests.';parts='test_server_tools_retrieval.EvidencePartitionResponseTests.';nodes='test_server_tools_retrieval.EvidenceNodesStayQueryableTests.'
run('baseline21',['test_graph_quality_eval.LiveGraphEvidenceControlTests','test_graph_quality_eval.ClassificationControlScorerTests.test_the_live_graph_satisfies_the_frozen_expectation','test_server_tools_retrieval.EvidencePartitionResponseTests','test_server_tools_retrieval.EvidenceNodesStayQueryableTests','test_server_tools_retrieval.EvidencePairDocumentationTests.test_the_pair_list_matches_what_the_report_actually_emits'])
with patch.object(gfs.graph_indexer,'classify_evidence_payload',return_value=(False,[])):
 run('classification_false',[quality+'test_the_machine_result_control_is_classified_as_evidence',parts+'test_evidence_communities_do_not_appear_in_the_production_ranking'])
with patch.object(gfs.graph_indexer,'classify_evidence_payload',return_value=(True,['incorrect stamp'])):
 run('classification_true',[quality+'test_the_legitimate_controls_stay_in_their_ordinary_domains'])
srv=r.load_server();real_report=srv.wf_graph_report_response
for label,method,mutate in [('partition_overlap','test_evidence_communities_do_not_appear_in_the_production_ranking',lambda d:d['communities'].extend(d['evidence_communities'])),('ranking_reverse','test_the_limit_applies_independently_to_each_half',lambda d:(d['communities'].reverse(),d['evidence_communities'].reverse())),('empty_evidence','test_evidence_rows_carry_their_type_and_a_nonempty_reason',lambda d:d.update(evidence_communities=[]))]:
 def changed(*a,**k):
  resp=real_report(*a,**k);mutate(resp['data']);return resp
 with patch.object(r,'load_server',return_value=srv),patch.object(srv,'wf_graph_report_response',side_effect=changed):run(label,[parts+method])
real_lookup=srv.code_graph_community_response
def badlookup(*a,**k):
 resp=real_lookup(*a,**k);resp['data']['nodes']=[];return resp
with patch.object(r,'load_server',return_value=srv),patch.object(srv,'code_graph_community_response',side_effect=badlookup):run('lookup_empty_nodes',[parts+'test_evidence_communities_remain_queryable_by_id'])
real_pub=gfs.publish_evidence_fixture
def empty(*a,**k):
 result=real_pub(*a,**k);return dict(result,nodes=[])
with patch.object(gfs,'publish_evidence_fixture',side_effect=empty):run('empty_graph',[quality+'test_the_control_directory_is_indexed_at_all'])
def missing(*a,**k):
 result=real_pub(*a,**k);return dict(result,nodes=[n for n in result['nodes'] if n.get('source_file')!='.wavefoundry/framework/scripts/retrieval_eval.py'])
with patch.object(gfs,'publish_evidence_fixture',side_effect=missing):run('missing_ordinary_control',[quality+'test_retrieval_eval_remains_ordinary_framework_code'])
import graph_query
real_read=graph_query._get_graph_indexer().read_published_graph_snapshot
def noedges(*a,**k):
 result=real_read(*a,**k)
 if result:result=dict(result,payload=dict(result['payload'],edges=[]))
 return result
with patch.object(graph_query._get_graph_indexer(),'read_published_graph_snapshot',side_effect=noedges):run('crossing_removed',[nodes+'test_cross_boundary_edges_survive_the_partition'])
packet=json.loads(Path('/private/tmp/wf-2071n-delivery-packet.json').read_text());out['frozen_paths_match']=all(hashlib.sha256((root/p['path']).read_bytes()).hexdigest()==p['sha256']for p in packet['paths'])
Path('/private/tmp/wf-2071n-qa-graph-probe.json').write_text(json.dumps(out,indent=2));print('frozen',out['frozen_paths_match'])
