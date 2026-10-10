import os, sys, json, hashlib, unittest, io, tempfile, subprocess, base64, ast
from pathlib import Path
from unittest.mock import patch
ROOT=Path('/Users/coryhacking/Developer/wavefoundry')
S=ROOT/'.wavefoundry/framework/scripts'
sys.path[:0]=[str(S/'tests'),str(S)]
import test_server_tools_retrieval as queries, graph_fixture_support as gfs, graph_indexer
import test_historical_fixture_support as integrity, historical_fixture_support as history
import test_review_policy as policy, test_storage_upgrade_resume as resume
import test_sqlite_storage_migration as migration, build_pack
PACKET=json.loads(Path('/private/tmp/wf-2071n-delivery-packet-repair-1.json').read_text())
def snapshot():
    return {p['path']:hashlib.sha256((ROOT/p['path']).read_bytes()).hexdigest() for p in PACKET['paths']}
before=snapshot()
def run(cases):
    suite=unittest.TestSuite()
    for case in cases:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case) if isinstance(case,type) else [case])
    stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream).run(suite)
    return {'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'failed_ids':[x.id() for x,_ in result.failures+result.errors], 'diagnostics':stream.getvalue()[-5000:]}
roots=[]; real_publish=gfs.publish_evidence_fixture
def observe_publish(root):
    root=Path(root).resolve()
    assert not root.is_relative_to(ROOT)
    assert not (root/'.wavefoundry/index').exists()
    result=real_publish(root)
    roots.append({'root':str(root),'nodes':len(result['nodes']),'edges':len(result['edges']),'index_absent_before':True})
    return result
with patch.object(gfs,'publish_evidence_fixture',observe_publish):
    graph=run([queries.EvidencePartitionResponseTests,queries.EvidenceNodesStayQueryableTests,queries.EvidencePairDocumentationTests])
selected=[queries.EvidencePartitionResponseTests('test_evidence_rows_carry_their_type_and_a_nonempty_reason'),queries.EvidencePartitionResponseTests('test_the_limit_applies_independently_to_each_half')]
with patch.object(graph_indexer,'classify_evidence_payload',return_value=(False,[])):
    bad_classification=run(selected)
with tempfile.TemporaryDirectory(prefix='wf-own-edge-') as td:
    root=Path(td); payload=real_publish(root)
    control=queries.EvidenceNodesStayQueryableTests.CONTROL
    assert any(e['source']=='docs/design/controls.md' and e['target']==control and e['relation']=='doc_references_doc' and e['confidence']=='EXTRACTED' for e in payload['edges'])
    import graph_query
    q=graph_query.GraphQueryIndex(dict(payload,present=True))
    assert q.is_evidence_node(control)
    assert not q.is_evidence_node('.wavefoundry/framework/scripts/retrieval_eval.py')
    rep=queries.load_server().wf_graph_report_response(root,limit=2)
    assert rep['status']=='ok'
    assert [r['node_count'] for r in rep['data']['communities']]==[31,21]
    assert [r['node_count'] for r in rep['data']['evidence_communities']]==[62,52]
    direct={'nodes':len(payload['nodes']),'edges':len(payload['edges']),'ranking_counts':[[31,21],[62,52]],'cross_boundary_identity':control,'relation':'doc_references_doc','confidence':'EXTRACTED'}
text=(ROOT/'docs/architecture/testing-architecture.md').read_text()
paragraph=text.split('membership repair. The fixture does not copy')[1].split('Known-bad source controls')[0]
def coverage_contract(s):
    normal=' '.join(s.lower().split())
    return bool(roots) and all(r['index_absent_before'] for r in roots) and 'hermetic published fixture' in normal and 'separately' in normal and 'these fixture tests do not establish it' in normal and 'existing live partition tests remain' not in normal
assert coverage_contract(paragraph)
old_claim='Existing live partition tests remain a separate qualification after canonical setup.'
assert not coverage_contract(old_claim)
real_run=subprocess.run; calls=[]
def confined_run(argv,*a,**kw):
    if isinstance(argv,(list,tuple)) and argv and Path(str(argv[0])).name=='git' and any(x in argv for x in ('show','rev-parse')):
        raise AssertionError('historical Git-ref dependency reached')
    if isinstance(argv,(list,tuple)) and ('-c' in argv or any('driver.py' in str(x) for x in argv)):
        assert not kw.get('shell',False)
        cwd=Path(kw['cwd']).resolve(); assert not cwd.is_relative_to(ROOT)
        calls.append({'argv_type':'list','shell':False,'cwd_scratch':True,'bytecode_disabled':'-B' in argv})
    return real_run(argv,*a,**kw)
history_cases=[policy.ReviewPolicyReconcilerTests('test_real_v114_carrier_family_reconciles_and_retries_byte_stably'),policy.ReviewPolicyReconcilerTests('test_real_v114_carriers_render_policy_and_pass_production_validator'),resume.StorageUpgradeProcessResumeTests('test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry'),migration.SchemaEightKindTests('test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing')]
with patch.object(subprocess,'run',confined_run):
    historical_behavior=run(history_cases)
historical_integrity=run([integrity.HistoricalFixtureIntegrityTests])
with patch.object(history,'BUNDLE_SHA256','0'*64):
    bad_bundle=run([integrity.HistoricalFixtureIntegrityTests('test_old_python_bytes_match_the_independently_recorded_source_digests')])
bundle=json.loads(history.BUNDLE_PATH.read_text()); provenance=[]
for key,e in bundle['entries'].items():
    revision=e['revision']; path=base64.b64decode(e['source_path_b64']).decode() if 'source_path_b64' in e else e.get('source_path',e.get('path',''))
    if not path:
        # The bundle deliberately base64-encodes both source path and bytes.
        path=base64.b64decode(''.join(e['path_b64'])).decode()
    r=real_run(['git','show',revision+':'+path],cwd=ROOT,capture_output=True)
    if e['absent']: assert r.returncode!=0
    else: assert r.returncode==0 and r.stdout==history.historical_bytes(key)
    provenance.append({'key':key,'absent':e['absent'],'matched':True})
entries=build_pack.collect_files(ROOT/'.wavefoundry/framework')
assert not any('/scripts/tests/' in arc for _,arc in entries)
assert any(arc.endswith('/scripts/graph_indexer.py') for _,arc in entries)
pack={'collect_files':len(entries),'historical_bundle_excluded':True,'graph_fixture_excluded':True,'production_graph_included':True,'zip_built':False}
after=snapshot(); assert before==after
assert all(before[p['path']]==p['sha256'] for p in PACKET['paths'])
out={'graph_baseline':graph,'observed_query_roots':roots,'direct_query':direct,'documentation_control':{'current_contract_matches_executed_paths':True,'original_false_live_claim_rejected':True,'old_claim':old_claim},'classification_mutant':bad_classification,'historical_behavior':historical_behavior,'historical_child_calls':calls,'historical_integrity':historical_integrity,'bad_bundle_pin':bad_bundle,'provenance':provenance,'pack_boundary':pack,'hashes_before':before,'hashes_after':after,'packet_match':True}
Path('/private/tmp/wf-2071n-reverify-arch-security-probe.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('hashes_before','hashes_after','observed_query_roots')},indent=2))
