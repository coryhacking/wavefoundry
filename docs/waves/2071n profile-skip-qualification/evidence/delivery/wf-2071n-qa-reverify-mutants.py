import os,sys,json,pathlib,subprocess
p=json.loads(pathlib.Path('/private/tmp/wf-2071n-qa-reverify-probe-results.json').read_text());scripts=pathlib.Path(p['scratch'])/'.wavefoundry/framework/scripts'
code=r'''
import sys,json,unittest,io
from unittest import mock
sys.path[:0]=[sys.argv[1]+'/tests',sys.argv[1]]
import test_server_tools_retrieval as r,graph_fixture_support as f,test_change_id_path_guard as c
names=['test_the_limit_applies_independently_to_each_half','test_evidence_communities_remain_queryable_by_id']
def run(tests):
 o=io.StringIO();res=unittest.TextTestRunner(stream=o,verbosity=2).run(unittest.TestSuite(tests));return dict(tests=res.testsRun,failures=len(res.failures),errors=len(res.errors),skips=len(res.skipped),log=o.getvalue())
results={}
with mock.patch.object(f.graph_indexer,'classify_evidence_payload',return_value=(False,[])):
 results['classification_removed']=run([r.EvidencePartitionResponseTests(x) for x in names])
real=r.EvidencePartitionResponseTests._report
def reverse(self,**kwargs):
 data=real(self,**kwargs)
 for section in ('communities','evidence_communities'): data[section].reverse()
 return data
with mock.patch.object(r.EvidencePartitionResponseTests,'_report',reverse):results['ranking_reversed']=run([r.EvidencePartitionResponseTests(names[0])])
with mock.patch.object(c.lgs,'is_change_id',return_value=False):results['corpus_acceptance_removed']=run([c.IsChangeIdTests('test_accepts_every_admitted_id_in_this_repository')])
print(json.dumps(results))
'''
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPYCACHEPREFIX','PYTHONPATH','WAVEFOUNDRY_TEST_PROFILE')};env['PYTHONDONTWRITEBYTECODE']='1'
r=subprocess.run([sys.executable,'-B','-c',code,str(scripts)],env=env,text=True,capture_output=True,timeout=60);assert r.returncode==0,(r.stdout,r.stderr)
a=json.loads(r.stdout.strip().splitlines()[-1]);pathlib.Path('/private/tmp/wf-2071n-qa-reverify-mutants-results.json').write_text(json.dumps(a,indent=2));print(json.dumps({k:{x:y for x,y in v.items() if x!='log'} for k,v in a.items()}));assert all(x['failures']==x['tests'] and x['errors']==x['skips']==0 for x in a.values())
