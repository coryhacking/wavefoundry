import ast, hashlib, json, os, pathlib, shutil, subprocess, time
ROOT=pathlib.Path('/Users/coryhacking/Developer/wavefoundry')
PY='/Users/coryhacking/.wavefoundry/venv/bin/python'
PACK=json.load(open('/tmp/wf-206is-final-delivery-packet.json'))
OUT=pathlib.Path('/tmp/wf-206is-reverify-code-work'); OUT.mkdir(exist_ok=True)

def hashes():
 r={}
 for row in PACK['paths']:
  b=(ROOT/row['path']).read_bytes(); sha=hashlib.sha256(b).hexdigest(); blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
  r[row['path']]={'sha256':sha,'git_blob':blob}
 return r
before=hashes()
assert all(before[x['path']]=={'sha256':x['sha256'],'git_blob':x['git_blob']} for x in PACK['paths'])

def run(name,root,tests):
 scripts=root/'.wavefoundry/framework/scripts'
 env=os.environ.copy(); env['PYTHONPATH']=str(scripts)+os.pathsep+str(scripts/'tests'); env['PYTHONDONTWRITEBYTECODE']='1'
 cmd=[PY,'-B','-m','unittest','-v',*tests]
 st=time.monotonic(); p=subprocess.run(cmd,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
 log=OUT/(name+'.log');log.write_text(p.stdout)
 return {'name':name,'command':cmd,'cwd':str(root),'returncode':p.returncode,'elapsed':round(time.monotonic()-st,3),'log':str(log),'output_tail':p.stdout[-6000:]}

reset='test_extension_tool_modules.DeclarationConstantCensusTests.test_the_refusal_driver_resets_every_declaration_constant'
source='test_server_package.TestCensusTests.test_no_source_read_of_a_moved_flat_path'
controls=[reset,'test_extension_tool_modules.DeclarationConstantCensusTests.test_every_declaration_constant_is_classified',source,'test_server_package.TestCensusTests.test_helpers_resolve_the_implementation','test_upgrade_wavefoundry.JournalTriggerPolicyTests','test_upgrade_protocol.JournalIncomingRunnerTests']
records=[run('current-controls',ROOT,controls)]
assert records[0]['returncode']==0,records[0]
scratch=OUT/'scratch'
if not scratch.exists():
 shutil.copytree(ROOT/'.wavefoundry/framework/scripts',scratch/'.wavefoundry/framework/scripts',ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
 shutil.copytree(ROOT/'.wavefoundry/framework/seeds',scratch/'.wavefoundry/framework/seeds')
 shutil.copy2(ROOT/'.wavefoundry/framework/VERSION',scratch/'.wavefoundry/framework/VERSION')
mutations=[('declaration-reset-removed','test_extension_tool_modules.py','                     EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="legacy_cutover",\n','',reset),('source-resolver-reverted','test_upgrade_wavefoundry.py','source_path(f"{helper}.py").read_bytes()','(SCRIPTS_ROOT / f"{helper}.py").read_bytes()',source)]
for name,file,old,new,test in mutations:
 p=scratch/'.wavefoundry/framework/scripts/tests'/file; saved=p.read_text();assert saved.count(old)==1,(name,saved.count(old))
 baseline=run(name+'-baseline',scratch,[test]);assert baseline['returncode']==0,baseline
 p.write_text(saved.replace(old,new))
 try:
  mutant=run(name+'-mutant',scratch,[test]);assert mutant['returncode']!=0 and 'FAIL:' in mutant['output_tail'] and 'Ran 1 test' in mutant['output_tail'],mutant
 finally:p.write_text(saved)
 records += [baseline,mutant]

# Independent compatibility oracle: the two concrete archived helper inputs keep exact bytes;
# the same resolver also selects an existing relocated server implementation rather than its alias.
import sys
sys.path.insert(0,str(ROOT/'.wavefoundry/framework/scripts/tests'))
from framework_files import source_path
parity=[]
for name in ('path_containment','contained_files'):
 direct=ROOT/'.wavefoundry/framework/scripts'/(name+'.py'); resolved=source_path(name+'.py');assert resolved.read_bytes()==direct.read_bytes()
 parity.append({'name':name,'resolved':str(resolved),'same_bytes':True,'sha256':hashlib.sha256(resolved.read_bytes()).hexdigest()})
assert source_path('server_impl.py').parent.name=='wf_server'
assert source_path('server_impl.py').read_bytes()!=(ROOT/'.wavefoundry/framework/scripts/server_impl.py').read_bytes()
# Same-root-cause bounded census is the production complete key-name assertion plus the
# unchanged current whole test-tree flat-source assertion and resolver sibling shape.
# No broad exemptions or production runtime changes.
after=hashes();assert before==after
json.dump({'before':before,'after':after,'unchanged':True,'packet_match':True,'records':records,'parity':parity,'relocated_sibling':'server_impl.py resolves wf_server implementation distinct from flat alias','scratch':str(scratch)},open(OUT/'results.json','w'),indent=2)
print(json.dumps({'logs':[r['log'] for r in records],'results':[{'name':r['name'],'returncode':r['returncode'],'tail':r['output_tail'][-1400:]} for r in records],'tree_unchanged':True,'parity':parity},indent=2))
