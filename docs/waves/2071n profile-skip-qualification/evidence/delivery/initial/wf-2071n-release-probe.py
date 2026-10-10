import json,pathlib,subprocess,tempfile,shutil
A=pathlib.Path('/private/tmp/wf-2071n-skip-capture/audit.py');out={}
base="test_platform (test_contract.Contract.test_platform)\nMultiline documentation ... skipped 'native platform unavailable'\n\n----------------------------------------------------------------------\nRan 2 tests in 0.001s\n\nOK (skipped=1)\n"
extra="test_default (test_contract.Contract.test_default) ... skipped 'default-profile-only: loaded record_paths.WAVES_ROOT differs'\n"
with tempfile.TemporaryDirectory(prefix='wf-review-skip-') as tmp:
 root=pathlib.Path(tmp);manifest=root/'manifest.json';manifest.write_text(json.dumps(['test_contract.py']))
 def reset():
  for name in ('default','second','declared'):
   d=root/name;d.mkdir(exist_ok=True);(d/'test_contract.py.json').write_text(json.dumps({'returncode':0,'stdout':'','stderr':base}))
 def run(name,expected):
  cp=subprocess.run(['python3','-B',str(A),str(root),str(manifest)],capture_output=True,text=True); assert (cp.returncode==0)==expected,(name,cp.stdout,cp.stderr)
  out[name]={'expected_rc':0 if expected else 'nonzero','returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr};print(name,cp.returncode,flush=True)
 reset();run('multiline_fully_qualified_baseline',True)
 reset();p=root/'second'/'test_contract.py.json';r=json.loads(p.read_text());r['stderr']=base.replace('Ran 2','Ran 3').replace('OK (skipped=1)','OK (skipped=2)').replace('\n----------------------------------------------------------------------',extra+'\n----------------------------------------------------------------------');p.write_text(json.dumps(r));run('second_marker_extra_accepted',True)
 reset();p=root/'declared'/'test_contract.py.json';r=json.loads(p.read_text());r['stderr']=base.replace('test_platform','test_different');p.write_text(json.dumps(r));run('equal_count_wrong_identity_rejected',False)
 reset();p=root/'second'/'test_contract.py.json';r=json.loads(p.read_text());r['stderr']=base.replace('native platform unavailable','unexpected runtime reason');p.write_text(json.dumps(r));run('same_identity_changed_reason_rejected',False)
 reset();p=root/'second'/'test_contract.py.json';r=json.loads(p.read_text());r['stderr']=base.replace('test_platform','test_different').replace('native platform unavailable','copied checkout has no index');p.write_text(json.dumps(r));run('extra_unmarked_skip_rejected',False)
 reset();(root/'declared'/'test_contract.py.json').unlink();run('missing_capture_rejected',False)
 reset();p=root/'second'/'test_contract.py.json';r=json.loads(p.read_text());r['returncode']=1;p.write_text(json.dumps(r));run('failed_worker_rejected',False)
 # Contract only forbids added unjustified skips; fewer existing skips under renamed profile permitted by oracle.
 reset();p=root/'second'/'test_contract.py.json';r=json.loads(p.read_text());r['stderr']='Ran 2 tests in 0.001s\n\nOK\n';p.write_text(json.dumps(r));run('second_removed_baseline_skip_permitted',True)
pathlib.Path('/private/tmp/wf-2071n-release-probe.json').write_text(json.dumps(out,indent=2))
