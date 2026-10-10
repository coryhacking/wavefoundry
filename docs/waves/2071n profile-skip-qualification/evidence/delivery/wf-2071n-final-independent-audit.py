import ast,hashlib,json,re,sys
from pathlib import Path
root=Path('/Users/coryhacking/Developer/wavefoundry'); capture=Path('/private/tmp/wf-2071n-qualification'); durable=root/'docs/waves/2071n profile-skip-qualification/evidence/delivery/final'; scripts=root/'.wavefoundry/framework/scripts'
expected={p.name for p in (scripts/'tests').glob('test_*.py')}; assert len(expected)==178
manifest=json.loads((durable/'capture-manifest.json').read_text()); assert len(manifest)==534
manifest_map={(z['profile'],z['worker']):z for z in manifest}; assert len(manifest_map)==534
inventories={}
for profile in ['default','second','declared']:
 files={p.name[:-5]:p for p in (capture/profile).glob('test_*.py.json')}; assert set(files)==expected
 skips={}; count=0; observations=[]
 for name,path in sorted(files.items()):
  raw=path.read_bytes(); record=json.loads(raw); assert record['returncode']==0
  meta=manifest_map[profile,path.name]; assert hashlib.sha256(raw).hexdigest()==meta['original_capture_sha256'] and meta['returncode']==0
  chunks=json.loads((durable/('raw-'+profile)/path.name).read_text()); rebuilt={k:record[k] for k in ('argv','returncode')}
  for stream in ('stdout','stderr'): rebuilt[stream]=None if chunks[stream+'_chunks'] is None else ''.join(chunks[stream+'_chunks'])
  assert rebuilt==record and json.dumps(rebuilt,indent=2).encode()==raw
  text=record['stderr'] or ''; lines=text.splitlines(); total=[re.fullmatch(r'Ran (\d+) tests? in ([0-9.]+)s',l) for l in lines]; totals=[x for x in total if x]; assert len(totals)==1,(profile,name); count+=int(totals[0][1]); assert any(l=='OK' or l.startswith('OK (skipped=') for l in lines)
  identity=None; found=[]
  for line in lines:
   head=re.match(r'(test_\w+|setUpClass) \(([^)]+)\)',line)
   if head: identity=head[2] if head[2].endswith('.'+head[1]) else head[2]+'.'+head[1]
   if ' ... skipped ' in line:
    assert identity is not None; reason=ast.literal_eval(line.split(' ... skipped ',1)[1]); assert identity not in skips; skips[identity]=reason;found.append(identity)
  finalok=[l for l in lines if l=='OK' or l.startswith('OK (skipped=')][-1]; declaredcount=0 if finalok=='OK' else int(re.search(r'skipped=(\d+)',finalok)[1]); assert len(found)==declaredcount
  observations.append({'worker':name,'returncode':0,'tests':int(totals[0][1]),'skip_count':declaredcount})
 inventories[profile]={'files':len(files),'tests':count,'skips':skips,'worker_observations':observations}
base=inventories['default']['skips']; assert inventories['declared']['skips']==base
second=inventories['second']['skips']; assert set(base)<=set(second); extra={k:v for k,v in second.items() if k not in base}; changes={k:{'default':v,'second':second[k]} for k,v in base.items() if second[k]!=v}; assert len(extra)==15 and len(changes)==1 and all(v.startswith('default-profile-only:') for v in extra.values()) and all(v['second'].startswith('default-profile-only:') for v in changes.values())
persist=json.loads((capture/'skip-inventory.json').read_text()); assert all({k:inventories[p][k] for k in ('files','tests','skips')}=={k:persist[p][k] for k in ('files','tests','skips')} for p in inventories)
packet=json.loads(Path('/private/tmp/wf-2071n-delivery-packet-repair-1.json').read_text()); sha=[]
for z in packet['paths']:
 digest=hashlib.sha256((root/z['path']).read_bytes()).hexdigest();assert digest==z['sha256'];sha.append({'path':z['path'],'sha256':digest})
receipt_path=root/'.wavefoundry/framework/test-cache.json'; receipt=json.loads(receipt_path.read_text()); assert receipt_path.read_bytes()==(durable/'canonical-receipt.json').read_bytes();sys.path.insert(0,str(scripts));import run_tests; currenthash=run_tests._hash_inputs();assert currenthash==receipt['inputs_hash']=='168eafe7d59e87c2acf0ab232ae3ac0a418b3aeec0a6972fef0fad78b9e1c22d';assert receipt['result']=='ok' and receipt['test_count']==12040 and len(receipt['durations_s'])==178
out={'auditor':'independently written /private/tmp/wf-2071n-final-independent-audit.py','worker_rows':534,'worker_rc_zero':534,'durable_chunked_reconstruction_byte_exact':534,'profile_totals':{p:{'files':x['files'],'tests':x['tests'],'skip_count':len(x['skips'])} for p,x in inventories.items()},'declared_exact_default_map':True,'second_extra_skip_ids_reasons':extra,'second_shared_reason_change':changes,'source_packet_fingerprint':packet['tree_fingerprint'],'source_constituent_sha256':sha,'source15_hash_match':True,'receipt':{'result':receipt['result'],'inputs_hash':currenthash,'ran_at':receipt['ran_at'],'test_count':receipt['test_count'],'worker_files':len(receipt['durations_s']),'current_framework_hash_matches':True,'durable_receipt_byte_exact':True},'inventory_matches_recorded':True,'actual_skip_maps':{p:x['skips'] for p,x in inventories.items()}}
Path('/private/tmp/wf-2071n-final-independent-audit.json').write_text(json.dumps(out,indent=2)); print(json.dumps({k:v for k,v in out.items() if k not in ('actual_skip_maps','source_constituent_sha256','second_extra_skip_ids_reasons','second_shared_reason_change')},indent=2)); print('second_extra_ids',list(extra));print('shared_reason_change_ids',list(changes))
