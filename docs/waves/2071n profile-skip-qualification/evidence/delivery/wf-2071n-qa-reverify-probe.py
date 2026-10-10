import os,sys,json,hashlib,pathlib,tempfile,shutil,subprocess,datetime
ROOT=pathlib.Path('/Users/coryhacking/Developer/wavefoundry')
PACK=json.loads(pathlib.Path('/private/tmp/wf-2071n-delivery-packet-repair-1.json').read_text())
def hashes(): return {x['path']:hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest() for x in PACK['paths']}
before=hashes(); assert all(before[x['path']]==x['sha256'] for x in PACK['paths'])
sys.path[:0]=[str(ROOT/'.wavefoundry/framework/scripts/tests'),str(ROOT/'.wavefoundry/framework/scripts')]
import record_layout_support as rls
scratch=pathlib.Path(tempfile.mkdtemp(prefix='wf-2071n-qa-independent-',dir='/private/tmp'))
shutil.copytree(ROOT/'.wavefoundry/framework',scratch/'.wavefoundry/framework',ignore=shutil.ignore_patterns('__pycache__','*.pyc','test-cache.json','test-run.lock'))
shutil.copytree(ROOT/'docs',scratch/'docs')
scripts=scratch/'.wavefoundry/framework/scripts'
DRIVER=r'''
import sys,os,json,unittest,io
from unittest import mock
sys.path[:0]=[sys.argv[1]+'/tests',sys.argv[1]]
import test_profile_support as m, test_change_id_path_guard as c
observed=[]
original=unittest.TestCase.assertGreater
def observe(self,a,b,*args,**kwargs):
    if self.__class__ is c.IsChangeIdTests: observed.append({'observed_corpus_size':a,'required_minimum':b})
    return original(self,a,b,*args,**kwargs)
def run(test):
    out=io.StringIO(); result=unittest.TextTestRunner(stream=out,verbosity=2).run(test)
    return dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=[(str(t),why) for t,why in result.skipped],log=out.getvalue())
with mock.patch.object(unittest.TestCase,'assertGreater',observe):
    if sys.argv[2]=='raw':
        with mock.patch.object(c.record_paths,'discover_wave_dirs',side_effect=AssertionError('body reached')):
            result=run(c.IsChangeIdTests('test_accepts_every_admitted_id_in_this_repository'))
    else:
        result=run(m.DefaultProfileOnlyMarkerTests('test_repository_corpus_runs_under_declared_tools'))
result['corpus_observations']=observed
result['loaded_label']=c.vp.MEMBER_ID_LABEL
result['loaded_regex']=c.vp.MEMBER_ID_LABEL_RE
print(json.dumps(result))
'''
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPYCACHEPREFIX','PYTHONPATH','WAVEFOUNDRY_TEST_PROFILE')};env['PYTHONDONTWRITEBYTECODE']='1'
def probe(name,mode='meta'):
    res=subprocess.run([sys.executable,'-B','-c',DRIVER,str(scripts),mode],env=env,text=True,capture_output=True,timeout=90)
    assert res.returncode==0,(res.stdout,res.stderr)
    return json.loads(res.stdout.strip().splitlines()[-1])
results={}
results['default_meta']=probe('default')
rls.apply_profile(scripts,rls.load_profile('declared'))
results['declared_meta']=probe('declared')
rls.apply_profile(scripts,rls.load_profile('second'))
results['second_meta']=probe('second')
results['second_raw_prebody_skip']=probe('second','raw')
p=scripts/'tests/test_profile_support.py';original_text=p.read_text()
old='with self._loaded(), mock.patch.object(\n                corpus.vp, "MEMBER_ID_LABEL_RE", re.escape(corpus.vp.MEMBER_ID_LABEL)), \\\n                mock.patch.dict'
new='with self._loaded(), mock.patch.dict'
assert original_text.count(old)==1
p.write_text(original_text.replace(old,new))
results['second_derived_regex_removal_mutant']=probe('second-mutant')
p.write_text(original_text)
assert all(results[n]['tests']==1 and results[n]['failures']==0 and results[n]['errors']==0 and not results[n]['skips'] and results[n]['corpus_observations'][0]['observed_corpus_size']>100 for n in ('default_meta','declared_meta','second_meta'))
assert results['second_raw_prebody_skip']['failures']==0 and results['second_raw_prebody_skip']['errors']==0 and len(results['second_raw_prebody_skip']['skips'])==1
bad=results['second_derived_regex_removal_mutant'];assert (bad['tests'],bad['failures'],bad['errors'],len(bad['skips']))==(1,1,0,0)
assert bad['corpus_observations']==[{'observed_corpus_size':0,'required_minimum':100}]
after=hashes();assert before==after
report={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scratch':str(scratch),'results':results,'before':before,'after':after,'packet_match':True,'source_fingerprint':PACK['tree_fingerprint'],'canonical_receipt_untouched':True}
pathlib.Path('/private/tmp/wf-2071n-qa-reverify-probe-results.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'scratch':str(scratch),'results':results},indent=2))
