import pathlib,json,re,ast,hashlib,datetime,sys
ROOT=pathlib.Path('/Users/coryhacking/Developer/wavefoundry');CAP=pathlib.Path('/private/tmp/wf-2071n-qualification');DUR=ROOT/'docs/waves/2071n profile-skip-qualification/evidence/delivery/final'
expected=set(json.loads((DUR/'wf-2071n-expected-files.json').read_text()));assert len(expected)==178
manifest=json.loads((DUR/'capture-manifest.json').read_text());assert len(manifest)==534
manifest_map={(x['profile'],x['worker']):x for x in manifest}
inv={};fingerprints={};observed_tests={};durable_matches=0
for profile in ('default','second','declared'):
 files=sorted((CAP/profile).glob('test_*.py.json'));assert {p.stem for p in files}==expected
 skips={};total=0;ok=0;test_outcomes={}
 for file in files:
  original=file.read_bytes();r=json.loads(original);assert r['returncode']==0;ok+=1
  d=json.loads((DUR/('raw-'+profile)/file.name).read_text())
  reconstructed={k:d[k] for k in ('argv','returncode')}
  for name in ('stdout','stderr'):
   chunks=d[name+'_chunks'];assert chunks is None or all(len(c)<=1024 for c in chunks)
   reconstructed[name]=None if chunks is None else ''.join(chunks)
  rebuilt=json.dumps(reconstructed,indent=2).encode();assert rebuilt==original
  digest=hashlib.sha256(original).hexdigest();assert digest==d['original_capture_sha256']==manifest_map[(profile,file.name)]['original_capture_sha256'];durable_matches+=1
  output=r['stderr'] or '';summaries=list(re.finditer(r'^Ran (\d+) tests? in [0-9.]+s$',output,re.M));assert summaries;total+=int(summaries[-1].group(1))
  expected_skip=re.search(r'OK \(skipped=(\d+)\)',output[summaries[-1].end():]);expected_skip=int(expected_skip.group(1)) if expected_skip else 0
  heading=None;count=0
  for line in output.splitlines():
   match=re.match(r'^(test_\w+|setUpClass) \(([^)]+)\)',line)
   if match: heading=(match.group(1),match.group(2))
   if heading and ' ... ok' in line:
    method,owner=heading;identity=owner if owner.endswith('.'+method) else owner+'.'+method;test_outcomes[identity]='ok'
   if ' ... skipped ' in line:
    assert heading;method,owner=heading;identity=owner if owner.endswith('.'+method) else owner+'.'+method
    reason=ast.literal_eval(line.split(' ... skipped ',1)[1]);assert identity not in skips;skips[identity]=reason;test_outcomes[identity]='skipped';count+=1
  assert count==expected_skip,(file,count,expected_skip)
 inv[profile]={'files':len(files),'tests':total,'rc0_workers':ok,'skips':skips};observed_tests[profile]=test_outcomes
baseline=inv['default']['skips'];assert len(baseline)==13;assert inv['declared']['skips']==baseline
second=inv['second']['skips'];assert len(second)==28;assert set(baseline)<=set(second)
extras={k:v for k,v in second.items() if k not in baseline};assert len(extras)==15 and all(v.startswith('default-profile-only:') for v in extras.values())
changes={k:{'default':v,'second':second[k]} for k,v in baseline.items() if second[k]!=v};assert len(changes)==1 and all(v['second'].startswith('default-profile-only:') for v in changes.values())
reported=json.loads((CAP/'skip-inventory.json').read_text());assert all(inv[p]['skips']==reported[p]['skips'] and inv[p]['tests']==reported[p]['tests'] for p in inv)
corpus='test_change_id_path_guard.IsChangeIdTests.test_accepts_every_admitted_id_in_this_repository';meta='test_profile_support.DefaultProfileOnlyMarkerTests.test_repository_corpus_runs_under_declared_tools'
assert observed_tests['default'][corpus]==observed_tests['declared'][corpus]=='ok';assert observed_tests['second'][corpus]=='skipped';assert all(observed_tests[p][meta]=='ok' for p in inv)
packet=json.loads(pathlib.Path('/private/tmp/wf-2071n-delivery-packet-repair-1.json').read_text());hashes={x['path']:hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest() for x in packet['paths']};assert all(hashes[x['path']]==x['sha256'] for x in packet['paths'])
sys.path.insert(0,str(ROOT/'.wavefoundry/framework/scripts'));import run_tests
receipt_path=ROOT/'.wavefoundry/framework/test-cache.json';receipt_before=receipt_path.read_bytes();receipt=json.loads(receipt_before);current_hash=run_tests._hash_inputs();assert receipt['result']=='ok' and receipt['test_count']==12040 and receipt['inputs_hash']==current_hash=='168eafe7d59e87c2acf0ab232ae3ac0a418b3aeec0a6972fef0fad78b9e1c22d';assert (DUR/'canonical-receipt.json').read_bytes()==receipt_before;assert receipt_before==receipt_path.read_bytes()
report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'profiles':inv,'extra_second_skips':extras,'shared_changed_reasons':changes,'534_durable_captures_exact_original_matches':durable_matches,'corpus_outcomes':{p:observed_tests[p][corpus] for p in inv},'meta_outcomes':{p:observed_tests[p][meta] for p in inv},'packet_fingerprint':packet['tree_fingerprint'],'path_hashes':hashes,'current_receipt':{k:receipt[k] for k in ('inputs_hash','ran_at','test_count','result')},'receipt_unchanged_by_check':True}
pathlib.Path('/private/tmp/wf-2071n-final-qa-audit-results.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:dict(files=v['files'],tests=v['tests'],skips=len(v['skips']),rc0_workers=v['rc0_workers']) for k,v in inv.items()}));print('Exact skip audit, all534 durable reconstructions,15 source hashes, corpus executions and current unchanged receipt verified.')
