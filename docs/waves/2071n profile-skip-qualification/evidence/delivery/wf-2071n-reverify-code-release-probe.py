import ast,hashlib,io,json,os,re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
root=Path('/Users/coryhacking/Developer/wavefoundry'); scripts=root/'.wavefoundry/framework/scripts'; sys.path[:0]=[str(scripts/'tests'),str(scripts)]
import run_tests,record_layout_support as s
out={}
with tempfile.TemporaryDirectory(prefix='wf-2071n-code-mutant-') as tmp:
 repo=Path(tmp)/'repo'; repo.mkdir(); copied,error=run_tests._copy_listed_tree(root,repo); assert error is None,error
 cs=repo/'.wavefoundry/framework/scripts'; s.apply_profile(cs,s.load_profile('second'),repo_root=repo,python=sys.executable)
 env={k:v for k,v in os.environ.items() if k not in ('PYTHONPYCACHEPREFIX','PYTHONPATH')}; env.update(PYTHONDONTWRITEBYTECODE='1',WAVEFOUNDRY_TEST_PROFILE='second')
 driver="import sys,io,json,unittest; sys.path[:0]=[sys.argv[1]+'/tests',sys.argv[1]]; import test_profile_support as t; r=unittest.TestResult(); t.DefaultProfileOnlyMarkerTests('test_repository_corpus_runs_under_declared_tools').run(r); print(json.dumps(dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skips=len(r.skipped),details=[v for _,v in r.failures+r.errors])))"
 def run():
  p=subprocess.run([sys.executable,'-B','-c',driver,str(cs)],env=env,capture_output=True,text=True,timeout=120); assert p.returncode==0,p.stderr; return json.loads(p.stdout.strip().splitlines()[-1])
 out['marker_baseline']=run(); target=cs/'tests/test_profile_support.py'; txt=target.read_text(); before='with self._loaded(), mock.patch.object(\n                corpus.vp, "MEMBER_ID_LABEL_RE", re.escape(corpus.vp.MEMBER_ID_LABEL)), \\\n                mock.patch.dict'
 assert txt.count(before)==1; target.write_text(txt.replace(before,'with self._loaded(), mock.patch.dict')); out['derived_regex_deleted']=run()
 assert out['marker_baseline']['tests']==1 and out['marker_baseline']['failures']==out['marker_baseline']['errors']==out['marker_baseline']['skips']==0
 assert out['derived_regex_deleted']['failures']==1 and out['derived_regex_deleted']['errors']==out['derived_regex_deleted']['skips']==0
import test_graph_quality_eval as g,test_server_tools_retrieval as t
suite=unittest.TestSuite()
for cls in [g.LiveGraphEvidenceControlTests,t.EvidencePartitionResponseTests,t.EvidenceNodesStayQueryableTests]: suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
suite.addTest(g.ClassificationControlScorerTests('test_the_live_graph_satisfies_the_frozen_expectation')); suite.addTest(t.EvidencePairDocumentationTests('test_the_pair_list_matches_what_the_report_actually_emits'))
ids=[]
def flatten(x):
 for z in x:
  if isinstance(z,unittest.TestSuite): flatten(z)
  else: ids.append(z.id())
flatten(suite); stream=io.StringIO(); r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite); out['hermetic21']={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skips':len(r.skipped),'ids':ids,'details':stream.getvalue()}; assert r.testsRun==21 and r.wasSuccessful() and not r.skipped
out['doc_current_statement']='The formerly live partition tests now use the hermetic published fixture described above (wave 2071n). Any executed live setup or graph smoke check remains separately labeled qualification; these fixture tests do not establish it.'
text=(root/'docs/architecture/testing-architecture.md').read_text(); normalized=' '.join(text.split()); assert out['doc_current_statement'] in normalized
out['documentation_contract']='executed 21 actual affected tests; both graph helper paths create TemporaryDirectory and publish_evidence_fixture, with no checkout-index requirement; revised statement truthfully separates live setup'
Path('/private/tmp/wf-2071n-reverify-code-release-probe.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
