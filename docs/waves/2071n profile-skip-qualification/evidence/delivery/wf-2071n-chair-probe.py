import os, sys, json, hashlib, base64, subprocess, unittest, io
from pathlib import Path
from unittest.mock import patch
ROOT=Path('/Users/coryhacking/Developer/wavefoundry')
S=ROOT/'.wavefoundry/framework/scripts';sys.path[:0]=[str(S/'tests'),str(S)]
PACKET=json.loads(Path('/private/tmp/wf-2071n-delivery-packet-repair-1.json').read_text())
def guard():
 return [{'path':x['path'],'sha256_match':hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256'],'git_blob_match':subprocess.check_output(['git','hash-object',str(ROOT/x['path'])],text=True).strip()==x['git_blob']} for x in PACKET['paths']]
before=guard()
import test_server_tools_retrieval as tr
import test_review_policy as rp
import test_storage_upgrade_resume as sr
import test_sqlite_storage_migration as sm
import test_historical_fixture_support as hi
import test_profile_support as ps

def run(cases):
 suite=unittest.TestSuite(cls(name) for cls,name in cases)
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream).run(suite)
 return {'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'failure_details':[{'test':x.id(),'trace':y} for x,y in result.failures],'error_details':[{'test':x.id(),'trace':y} for x,y in result.errors],'log':stream.getvalue()}
graph=[(tr.EvidencePartitionResponseTests,'test_the_limit_applies_independently_to_each_half'),(tr.EvidencePartitionResponseTests,'test_evidence_communities_remain_queryable_by_id'),(tr.EvidenceNodesStayQueryableTests,'test_cross_boundary_edges_survive_the_partition')]
history=[(rp.ReviewPolicyReconcilerTests,'test_real_v114_carrier_family_reconciles_and_retries_byte_stably'),(rp.ReviewPolicyReconcilerTests,'test_real_v114_carriers_render_policy_and_pass_production_validator'),(sr.StorageUpgradeProcessResumeTests,'test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry'),(sm.SchemaEightKindTests,'test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing')]
marker=[(ps.DefaultProfileOnlyMarkerTests,'test_repository_corpus_runs_under_declared_tools'),(ps.DefaultProfileOnlyMarkerTests,'test_repository_corpus_names_its_renamed_layout_skip')]
integrity=[(hi.HistoricalFixtureIntegrityTests,n) for n in unittest.defaultTestLoader.getTestCaseNames(hi.HistoricalFixtureIntegrityTests)]
results={'baseline_graph':run(graph),'baseline_historical':run(history),'baseline_integrity':run(integrity),'baseline_marker':run(marker)}
with patch.object(tr.gfs.graph_indexer,'classify_evidence_payload',return_value=(False,[])):
 results['classification_erasure_mutant']=run(graph[:2])
original=tr.EvidencePartitionResponseTests._report
def reversed_response(self,**kwargs):
 data=original(self,**kwargs)
 for key in ['communities','evidence_communities']:data[key]=list(reversed(data[key]))
 return data
with patch.object(tr.EvidencePartitionResponseTests,'_report',reversed_response):
 results['rank_reversal_mutant']=run(graph[:1])
with patch.object(sm,'historical_bytes',return_value=(S/'sqlite_storage_migration.py').read_bytes()):
 results['current_reader_substitution_mutant']=run(history[-1:])
bundle=json.loads(hi.subject.BUNDLE_PATH.read_text());provenance=[]
for key,entry in bundle['entries'].items():
 path=base64.b64decode(entry['source_path_b64']).decode();ref=entry['revision']+':'+path
 got=subprocess.run(['git','show',ref],cwd=ROOT,capture_output=True)
 if entry['absent']:assert got.returncode!=0;status='recorded absence'
 else:
  value=hi.subject.historical_bytes(key);assert got.returncode==0 and value==got.stdout;status='exact original bytes'
 provenance.append({'key':key,'ref':ref,'status':status})
after=guard()
out={'wave_id':'2071n','phase':'delivery','context':'2071n-delivery-chair-independent-20261009','tree_fingerprint':PACKET['tree_fingerprint'],'guard_before':before,'guard_after':after,'results':results,'provenance':provenance,'primary_mutations':False,'limitations':['Finite contracts and mutants only','No full suite or final profile census in this chair probe','Curated membership does not qualify clustering']}
Path('/private/tmp/wf-2071n-chair-probe.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'results':{k:{kk:vv for kk,vv in v.items() if kk in ['tests','failures','errors','skips']} for k,v in results.items()},'provenance_present':sum(x['status']=='exact original bytes' for x in provenance),'provenance_absence':sum(x['status']=='recorded absence' for x in provenance),'all15exact_before_after':all(x['sha256_match'] and x['git_blob_match'] for x in before+after)},indent=2))
