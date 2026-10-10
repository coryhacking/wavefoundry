import json, hashlib, re, ast, subprocess, sys
from pathlib import Path
ROOT=Path('/Users/coryhacking/Developer/wavefoundry');S=ROOT/'.wavefoundry/framework/scripts';sys.path.insert(0,str(S));import run_tests
B=ROOT/'docs/waves/2071n profile-skip-qualification/evidence/delivery/final'
manifest=json.loads((B/'capture-manifest.json').read_text());summary={p:{'files':0,'tests':0,'skips':{}} for p in ('default','second','declared')}
for entry in manifest:
 d=json.loads((B/('raw-'+entry['profile'])/entry['worker']).read_text())
 old={k:d[k] for k in ['argv','returncode']}
 for k in ['stdout','stderr']:old[k]=None if d[k+'_chunks'] is None else ''.join(d[k+'_chunks'])
 assert hashlib.sha256(json.dumps(old,indent=2).encode()).hexdigest()==entry['original_capture_sha256']==d['original_capture_sha256']
 assert old['returncode']==entry['returncode']==0
 text='\n'.join(old[k] or '' for k in ['stdout','stderr']);p=summary[entry['profile']];p['files']+=1
 counts=re.findall(r'^Ran (\d+) tests? in ',text,re.M);assert len(counts)==1;p['tests']+=int(counts[0])
 pending=None
 for line in text.splitlines():
  header=re.match(r'^(test_\w+|setUpClass) \(([^)]+)\)',line)
  if header:
   name,owner=header.groups();pending=owner if owner.endswith('.'+name) else owner+'.'+name
  skip=re.search(r' \.\.\. skipped (.+)$',line)
  if skip:
   assert pending is not None and pending not in p['skips'];p['skips'][pending]=ast.literal_eval(skip.group(1));pending=None

inventory=json.loads(Path('/private/tmp/wf-2071n-qualification/skip-inventory.json').read_text())
for p,v in summary.items():
 assert v['files']==inventory[p]['files'] and v['tests']==inventory[p]['tests'] and v['skips']==inventory[p]['skips']
b=summary['default']['skips'];s=summary['second']['skips'];d=summary['declared']['skips']
assert d==b and set(b)<=set(s)
extra={k:v for k,v in s.items() if k not in b};assert len(extra)==15 and all(x.startswith('default-profile-only:') for x in extra.values())
changed={k:{'default':b[k],'second':s[k]} for k in b if b[k]!=s[k]};assert len(changed)==1 and all(v['second'].startswith('default-profile-only:') for v in changed.values())
receipt=(ROOT/'.wavefoundry/framework/test-cache.json').read_bytes();r=json.loads(receipt);assert r['result']=='ok' and r['inputs_hash']==run_tests._hash_inputs()=='168eafe7d59e87c2acf0ab232ae3ac0a418b3aeec0a6972fef0fad78b9e1c22d';assert receipt==(B/'canonical-receipt.json').read_bytes()
packet=json.loads(Path('/private/tmp/wf-2071n-delivery-packet-repair-1.json').read_text());hashes=[]
for x in packet['paths']:
 p=ROOT/x['path'];digest=hashlib.sha256(p.read_bytes()).hexdigest();blob=subprocess.check_output(['git','hash-object',str(p)],text=True).strip();assert digest==x['sha256'] and blob==x['git_blob'];hashes.append({'path':x['path'],'sha256':digest,'git_blob':blob})
out={'all534capture_original_hashes_valid':len(manifest)==534,'all_worker_returncodes_zero':True,'summary':summary,'declared_map_exact_default':True,'second_extras_all_explicit_marker':True,'second_extra_count':len(extra),'shared_changed_reason':changed,'receipt_current':True,'receipt_unchanged':receipt==(ROOT/'.wavefoundry/framework/test-cache.json').read_bytes(),'source15exact':True,'source_hashes':hashes,'tree_fingerprint':packet['tree_fingerprint'],'method':'Independently reconstruct all534 original capture byte sequences, parse actual verbose skip lines with ast.literal_eval, reconcile exact maps; hash current framework inputs via canonical read-only function; verify15SHA256/git blobs.'}
Path('/private/tmp/wf-2071n-chair-final-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['summary','source_hashes','shared_changed_reason']},indent=2))
print({p:(x['files'],x['tests'],len(x['skips'])) for p,x in summary.items()});print('changed shared reason IDs:',list(changed))
